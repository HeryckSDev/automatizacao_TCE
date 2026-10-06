"""Cliente para os relatórios LRF do TCE-PR/SIM-AM.

O portal utiliza ASP.NET Web Forms. Por isso cada seleção envia de volta os
campos ocultos da página, como ``__VIEWSTATE``. Esta classe esconde esse detalhe
do restante do sistema e entrega opções ou relatórios em CSV.
"""

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlencode, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class TCEError(RuntimeError):
    """Erro compreensível relacionado à consulta ou leitura do TCE-PR."""


class TCEConsultaIndisponivel(TCEError):
    """A entidade não oferece um relatório exigido pela consulta."""


@dataclass(frozen=True)
class Opcao:
    id: str
    nome: str

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}


class _FormParser(HTMLParser):
    """Extrai campos ocultos e opções dos elementos ``select``."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = {}
        self.selects = {}
        self._select_id = None
        self._option_value = None
        self._option_text = []

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "input" and atributos.get("type", "").lower() == "hidden":
            nome = atributos.get("name")
            if nome:
                self.hidden[nome] = atributos.get("value", "")
        elif tag == "select":
            self._select_id = atributos.get("id")
            if self._select_id:
                self.selects.setdefault(self._select_id, [])
        elif tag == "option" and self._select_id:
            self._option_value = atributos.get("value", "")
            self._option_text = []

    def handle_data(self, data):
        if self._option_value is not None:
            self._option_text.append(data)

    def handle_endtag(self, tag):
        if tag == "option" and self._select_id and self._option_value is not None:
            texto = " ".join("".join(self._option_text).split())
            self.selects[self._select_id].append(Opcao(self._option_value, unescape(texto)))
            self._option_value = None
            self._option_text = []
        elif tag == "select":
            self._select_id = None


class TCEClient:
    BASE_URL = "https://simam.tce.pr.gov.br/Paginas/Rel_LRF.aspx?relTipo=1"
    ORIGIN = "https://simam.tce.pr.gov.br"

    TIPO = "ctl00$ContentPlaceHolder1$ddlTipo"
    MUNICIPIO = "ctl00$ContentPlaceHolder1$ddlMunicipio"
    ENTIDADE = "ctl00$ContentPlaceHolder1$ddlEntidade"
    RELATORIO = "ctl00$ContentPlaceHolder1$ddlRelatorio"
    ANO = "ctl00$ContentPlaceHolder1$ddlAno"
    PERIODO = "ctl00$ContentPlaceHolder1$ddlPeriodo"
    CONSULTAR = "ctl00$ContentPlaceHolder1$btnConsulta"

    SELECT_MUNICIPIO = "ContentPlaceHolder1_ddlMunicipio"
    SELECT_ENTIDADE = "ContentPlaceHolder1_ddlEntidade"
    SELECT_RELATORIO = "ContentPlaceHolder1_ddlRelatorio"
    SELECT_ANO = "ContentPlaceHolder1_ddlAno"
    SELECT_PERIODO = "ContentPlaceHolder1_ddlPeriodo"

    RELATORIO_RCL = "10"
    RELATORIO_PESSOAL = "20"
    RELATORIO_MDE = "15"

    def __init__(self, timeout=45):
        self.timeout = timeout
        self.session = requests.Session()
        repeticao = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=repeticao))
        self.session.headers.update({"User-Agent": "Mozilla/5.0 ProjetoAcademico/0.6"})
        self.html_atual = ""

    def _requisicao(self, metodo, url, **opcoes):
        try:
            resposta = self.session.request(metodo, url, timeout=self.timeout, **opcoes)
            resposta.raise_for_status()
            return resposta
        except requests.Timeout as erro:
            raise TCEError("A consulta ao TCE-PR excedeu o tempo limite.") from erro
        except requests.HTTPError as erro:
            codigo = erro.response.status_code if erro.response is not None else "desconhecido"
            raise TCEError(f"O TCE-PR respondeu com erro HTTP {codigo}.") from erro
        except requests.RequestException as erro:
            raise TCEError("Não foi possível conectar ao TCE-PR neste momento.") from erro

    @staticmethod
    def _parser(html):
        parser = _FormParser()
        parser.feed(html)
        return parser

    def _carregar_pagina(self):
        self.html_atual = self._requisicao("GET", self.BASE_URL).text

    def _postback(self, alvo, valores):
        parser = self._parser(self.html_atual)
        formulario = dict(parser.hidden)
        formulario["__EVENTTARGET"] = alvo
        formulario["__EVENTARGUMENT"] = ""
        formulario.update(valores)
        corpo = urlencode(formulario)
        self.html_atual = self._requisicao(
            "POST",
            self.BASE_URL,
            data=corpo,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).text

    @staticmethod
    def _opcoes_validas(opcoes):
        return [opcao.to_dict() for opcao in opcoes if opcao.id]

    def _validar_relatorio_disponivel(self, relatorio_id):
        parser = self._parser(self.html_atual)
        if self.SELECT_RELATORIO not in parser.selects:
            raise TCEError("Não foi possível identificar o catálogo de relatórios na resposta do TCE-PR.")
        disponiveis = self._opcoes_validas(parser.selects[self.SELECT_RELATORIO])
        if any(opcao["id"] == str(relatorio_id) for opcao in disponiveis):
            return
        nomes = {
            self.RELATORIO_RCL: "Receita Corrente Líquida",
            self.RELATORIO_PESSOAL: "Despesa com Pessoal",
            self.RELATORIO_MDE: "MDE/FUNDEB",
        }
        nome = nomes.get(str(relatorio_id), "solicitado")
        raise TCEConsultaIndisponivel(
            f"A entidade selecionada não disponibiliza o relatório {nome} ({relatorio_id}) no TCE-PR. "
            "Para a análise municipal, selecione a entidade Município/Prefeitura quando disponível."
        )

    def listar_municipios(self):
        self._carregar_pagina()
        self._postback(self.TIPO, {self.TIPO: "1"})
        parser = self._parser(self.html_atual)
        return self._opcoes_validas(parser.selects.get(self.SELECT_MUNICIPIO, []))

    def listar_entidades(self, municipio_id):
        self._carregar_pagina()
        self._postback(self.TIPO, {self.TIPO: "1"})
        self._postback(self.MUNICIPIO, {self.TIPO: "1", self.MUNICIPIO: str(municipio_id)})
        parser = self._parser(self.html_atual)
        return self._opcoes_validas(parser.selects.get(self.SELECT_ENTIDADE, []))

    def listar_anos(self, municipio_id, entidade_id, relatorio_id=None):
        """Lista os exercícios realmente oferecidos para uma entidade."""

        relatorio_id = relatorio_id or self.RELATORIO_PESSOAL
        valores_relatorio = {
            self.TIPO: "1",
            self.MUNICIPIO: str(municipio_id),
            self.ENTIDADE: str(entidade_id),
            self.RELATORIO: str(relatorio_id),
        }
        self._carregar_pagina()
        self._postback(self.TIPO, {self.TIPO: "1"})
        self._postback(self.MUNICIPIO, {self.TIPO: "1", self.MUNICIPIO: str(municipio_id)})
        self._postback(
            self.ENTIDADE,
            {self.TIPO: "1", self.MUNICIPIO: str(municipio_id), self.ENTIDADE: str(entidade_id)},
        )
        self._validar_relatorio_disponivel(relatorio_id)
        self._postback(self.RELATORIO, valores_relatorio)
        parser = self._parser(self.html_atual)
        return self._opcoes_validas(parser.selects.get(self.SELECT_ANO, []))

    def listar_relatorios(self, municipio_id, entidade_id):
        self._carregar_pagina()
        self._postback(self.TIPO, {self.TIPO: "1"})
        self._postback(self.MUNICIPIO, {self.TIPO: "1", self.MUNICIPIO: str(municipio_id)})
        self._postback(
            self.ENTIDADE,
            {self.TIPO: "1", self.MUNICIPIO: str(municipio_id), self.ENTIDADE: str(entidade_id)},
        )
        parser = self._parser(self.html_atual)
        return self._opcoes_validas(parser.selects.get(self.SELECT_RELATORIO, []))

    def listar_periodos(self, municipio_id, entidade_id, relatorio_id, ano):
        valores_relatorio = {
            self.TIPO: "1",
            self.MUNICIPIO: str(municipio_id),
            self.ENTIDADE: str(entidade_id),
            self.RELATORIO: str(relatorio_id),
        }
        valores_ano = {**valores_relatorio, self.ANO: str(ano)}
        self._carregar_pagina()
        self._postback(self.TIPO, {self.TIPO: "1"})
        self._postback(self.MUNICIPIO, {self.TIPO: "1", self.MUNICIPIO: str(municipio_id)})
        self._postback(
            self.ENTIDADE,
            {self.TIPO: "1", self.MUNICIPIO: str(municipio_id), self.ENTIDADE: str(entidade_id)},
        )
        self._validar_relatorio_disponivel(relatorio_id)
        self._postback(self.RELATORIO, valores_relatorio)
        self._postback(self.ANO, valores_ano)
        parser = self._parser(self.html_atual)
        return self._opcoes_validas(parser.selects.get(self.SELECT_PERIODO, []))

    def coletar_relatorio_csv(
        self,
        municipio_id,
        entidade_id,
        relatorio_id,
        ano,
        periodo_id=None,
    ):
        """Executa as seleções do portal e devolve o relatório como texto CSV."""

        valores_relatorio = {
            self.TIPO: "1",
            self.MUNICIPIO: str(municipio_id),
            self.ENTIDADE: str(entidade_id),
            self.RELATORIO: str(relatorio_id),
        }
        valores_ano = {
            **valores_relatorio,
            self.ANO: str(ano),
        }
        valores_consulta = dict(valores_ano)
        if periodo_id is not None:
            valores_consulta[self.PERIODO] = str(periodo_id)

        self._carregar_pagina()
        self._postback(self.TIPO, {self.TIPO: "1"})
        self._postback(self.MUNICIPIO, {self.TIPO: "1", self.MUNICIPIO: str(municipio_id)})
        self._postback(
            self.ENTIDADE,
            {self.TIPO: "1", self.MUNICIPIO: str(municipio_id), self.ENTIDADE: str(entidade_id)},
        )
        # Cada campo só é enviado depois que o portal o habilita. Mandar o ano
        # antes do postback do relatório faz o servidor antigo responder 500.
        self._validar_relatorio_disponivel(relatorio_id)
        self._postback(self.RELATORIO, valores_relatorio)
        self._postback(self.ANO, valores_ano)
        if periodo_id is not None:
            self._postback(self.PERIODO, valores_consulta)
        self._postback(self.CONSULTAR, valores_consulta)

        correspondencia = re.search(r'"ExportUrlBase":"([^"]+)"', self.html_atual)
        if not correspondencia:
            raise TCEError("O portal não disponibilizou o endereço de exportação do relatório.")

        try:
            caminho_exportacao = json.loads(f'"{correspondencia.group(1)}"')
        except json.JSONDecodeError as erro:
            raise TCEError("Não foi possível interpretar o endereço de exportação do relatório.") from erro

        url_csv = urljoin(self.ORIGIN, caminho_exportacao.replace("&amp;", "&") + "CSV")
        conteudo = self._requisicao("GET", url_csv).content
        return conteudo.decode("utf-8-sig", errors="replace")
