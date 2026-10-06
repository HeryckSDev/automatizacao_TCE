"""Prepara uma vez e reutiliza tabelas salariais sem exigir operação técnica."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from io import BytesIO
from pypdf import PdfReader
import json
from pathlib import Path
import re
from uuid import uuid4

from src.salarial.analise_service import analisar_tabela_salarial, _decimal, _validar_niveis
from src.salarial.revisao_service import extrair_para_revisao


VERSAO_EXTRACAO = "0.9.0"


def _moeda_br(valor):
    return "R$ " + f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sem_acento(texto):
    import unicodedata
    base = unicodedata.normalize("NFD", str(texto))
    return " ".join("".join(c for c in base if unicodedata.category(c) != "Mn").casefold().split())


def descrever_candidato(candidato, posicao):
    """Texto de exibição para a tela: título distinto, grupo e porte da tabela. Só apresenta dados já lidos."""
    titulo = str(candidato.get("profissao") or candidato.get("lei") or "").strip()
    fonte = str(candidato.get("arquivo_fonte") or "").strip()
    if not titulo:
        titulo = fonte.split(", ", 1)[1] if ", " in fonte else (fonte or f"Tabela {posicao + 1}")
    elif candidato.get("lei") and candidato.get("profissao"):
        a, b = _sem_acento(titulo), _sem_acento(candidato["lei"])
        if a in b:
            titulo = str(candidato["lei"]).strip()
        elif b not in a:
            titulo = f"{titulo} · {candidato['lei']}"
    niveis = candidato.get("niveis") or []
    classes = len(niveis[0]["valores"]) if niveis else 0
    inicial = niveis[0]["valores"][0] if niveis and classes else None
    partes = [f"{len(niveis)} {'nível' if len(niveis) == 1 else 'níveis'} × {classes} classes"]
    if inicial is not None:
        partes.append(f"a partir de {_moeda_br(inicial)}")
    if candidato.get("jornada_semanal"):
        partes.append(f"{candidato['jornada_semanal']:g} h/semana")
    return {"titulo": titulo, "grupo": candidato.get("grupo") or "Outras tabelas", "detalhe": " · ".join(partes)}


class AutomacaoSalarial:
    AMOSTRAS = {
        "cafezal-2026": "cafezal_do_sul_2026.json",
        "curitiba-administrativo-2026": "curitiba_administrativo_2026.json",
    }

    def __init__(self, amostras, diretorio):
        self.amostras = Path(amostras)
        self.diretorio = Path(diretorio)

    @staticmethod
    def _id(valor):
        if not re.fullmatch(r"[a-f0-9]{32}", str(valor)):
            raise ValueError("Essa preparação não foi encontrada. Envie o documento novamente.")
        return str(valor)

    def _ler_json(self, caminho):
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError("Essa tabela não foi encontrada. Envie o documento novamente.") from None

    def carregar(self, identificador):
        if identificador in self.AMOSTRAS:
            return self._ler_json(self.amostras / self.AMOSTRAS[identificador])
        return self._ler_json(self.diretorio / "tabelas" / f"{self._id(identificador)}.json")

    @staticmethod
    def descrever(identificador, dados):
        ref = dados.get("referencia") or {}
        nome_ref = ref.get("nome") or (f"Piso do magistério de {dados.get('ano')}" if dados.get("piso_nacional_40h") else "Referência a definir")
        nota = f"Jornada: {dados.get('jornada_semanal', '?')} h por semana. Referência: {nome_ref}."
        if dados.get("jornada_confirmada_no_documento") is not True:
            nota += " A jornada é uma premissa da preparação, ainda não confirmada no documento."
        if ref.get("tipo") == "cenario":
            nota += " Trata-se de uma simulação."
        return {"id": identificador, "municipio": dados.get("municipio", ""),
                "profissao": dados.get("profissao", ""), "ano": dados.get("ano"),
                "descricao": nota, "origem": "exemplo preparado" if identificador in AutomacaoSalarial.AMOSTRAS else "documento preparado por você"}

    def catalogo(self):
        itens = [self.descrever(i, self.carregar(i)) for i in self.AMOSTRAS]
        for caminho in sorted((self.diretorio / "tabelas").glob("*.json")):
            itens.append(self.descrever(caminho.stem, self._ler_json(caminho)))
        return itens

    def _preparacao_igual(self, impressao):
        """Mesmo arquivo, mesma versão da leitura: reaproveita em vez de reler (Curitiba leva ~30 s)."""
        raiz = self.diretorio / "documentos"
        if not raiz.is_dir():
            return None
        for pasta in raiz.iterdir():
            arquivo = pasta / "preparacao.json"
            if not arquivo.is_file():
                continue
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if dados.get("sha256") == impressao and dados.get("versao_extracao") == VERSAO_EXTRACAO and dados.get("candidatos"):
                omitir = {"nome_original", "sha256", "recebido_em", "versao_extracao"}
                return {"preparacao_id": pasta.name, "reaproveitada": True, **{k: v for k, v in dados.items() if k not in omitir}}
        return None

    def preparar(self, nome, conteudo):
        impressao = sha256(conteudo).hexdigest()
        existente = self._preparacao_igual(impressao)
        if existente:
            return existente
        extraido = extrair_para_revisao(nome, conteudo)
        validos, descartados = [], []
        for candidato in extraido["candidatos"]:
            if not isinstance(candidato, dict) or not isinstance(candidato.get("niveis"), list) or not candidato["niveis"]:
                raise ValueError("Esse arquivo não contém uma tabela salarial reconhecível.")
            try:
                _validar_niveis(candidato["niveis"])
                if len(candidato["niveis"]) > 100 or len(candidato["niveis"][0]["valores"]) > 200:
                    raise ValueError("A tabela é extensa. Envie somente a profissão que deseja comparar.")
            except ValueError as erro:
                # Uma tabela inválida não pode derrubar as demais do mesmo documento: registra e segue.
                descartados.append((str(candidato.get("profissao") or candidato.get("lei") or "tabela sem nome"), str(erro)))
                continue
            validos.append(candidato)
        if descartados and not validos:
            raise ValueError(descartados[0][1])
        if descartados:
            extraido["candidatos"] = validos
            extraido["pendencias"] = list(extraido.get("pendencias") or []) + [
                f"Tabela ignorada ({nome_tabela}): {motivo}" for nome_tabela, motivo in descartados
            ]
        for posicao, candidato in enumerate(extraido["candidatos"]):
            candidato["exibicao"] = descrever_candidato(candidato, posicao)
        extensao = Path(nome).suffix.lower()
        conferir = bool(extraido["pendencias"]) and extensao != ".pdf"
        if extensao == ".pdf":
            conferir = len(PdfReader(BytesIO(conteudo)).pages) > 1 or len(extraido["candidatos"]) > 1
        conferir = conferir or any(c.get("origem_ocr") for c in extraido["candidatos"])
        extraido["requer_conferencia_recorte"] = conferir
        identificador = uuid4().hex
        pasta = self.diretorio / "documentos" / identificador
        pasta.mkdir(parents=True, exist_ok=False)
        (pasta / ("original" + Path(nome).suffix.lower())).write_bytes(conteudo)
        manifest = {"nome_original": Path(nome).name, "sha256": impressao, "versao_extracao": VERSAO_EXTRACAO,
                    "recebido_em": datetime.now().isoformat(timespec="seconds"), **extraido}
        (pasta / "preparacao.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"preparacao_id": identificador, **extraido}

    def dados_preparados(self, identificador, indice, recorte_confirmado=False):
        pasta = self.diretorio / "documentos" / self._id(identificador)
        preparacao = self._ler_json(pasta / "preparacao.json")
        if preparacao.get("requer_conferencia_recorte") and recorte_confirmado is not True:
            raise ValueError("O documento contém mais de uma página ou tabela. Confirme que a tabela escolhida está completa.")
        try:
            if not str(indice).isdigit():
                raise ValueError
            dados = deepcopy(preparacao["candidatos"][int(indice)])
        except (ValueError, TypeError, IndexError, KeyError):
            raise ValueError("Escolha a tabela que deseja comparar.") from None
        dados["documento_sha256"] = preparacao["sha256"]
        dados["arquivo_fonte"] = dados.get("arquivo_fonte") or preparacao["nome_original"]
        return dados

    def analisar(self, pedido):
        if not isinstance(pedido, dict):
            raise ValueError("Escolha uma tabela ou envie um documento.")
        perfil = pedido.get("tabela_id")
        if perfil:
            dados = deepcopy(self.carregar(str(perfil)))
        else:
            dados = self.dados_preparados(pedido.get("preparacao_id"), pedido.get("candidato", 0), pedido.get("confirmar_recorte") is True)
            complementos = pedido.get("complementos") or {}
            if not isinstance(complementos, dict):
                raise ValueError("Confira as informações da tabela.")
            for chave in ("municipio", "profissao", "ano", "jornada_semanal"):
                if complementos.get(chave) not in (None, ""):
                    dados[chave] = complementos[chave]
            for chave, titulo in (("municipio", "município"), ("profissao", "profissão"),
                                   ("ano", "ano"), ("jornada_semanal", "jornada semanal")):
                if dados.get(chave) in (None, ""):
                    raise ValueError(f"Falta informar {titulo} para essa tabela.")
            if not str(dados["ano"]).isdigit() or not 2000 <= int(dados["ano"]) <= 2100:
                raise ValueError("Informe o ano da tabela com quatro dígitos.")
            dados["ano"] = int(dados["ano"])
            dados["jornada_semanal"] = float(_decimal(dados["jornada_semanal"], "Jornada semanal"))
            if "jornada_semanal" in complementos:
                # Informação do usuário não é convertida em fato extraído do documento.
                dados["jornada_confirmada_no_documento"] = False
            dados.setdefault("modo_arredondamento", "arredondar")
            escolha = pedido.get("comparacao") or {}
            if not isinstance(escolha, dict):
                raise ValueError("Escolha como deseja comparar os salários.")
            if escolha.get("tipo"):
                tipo = escolha["tipo"]
                if tipo == "percentual":
                    percentual = _decimal(escolha.get("valor"), "Reajuste desejado")
                    if not 0 <= percentual <= 100:
                        raise ValueError("Informe um reajuste entre 0% e 100%.")
                    base = _decimal(dados["niveis"][0]["valores"][0], "Vencimento inicial")
                    valor = (base * (1 + percentual / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    referencia = dict(tipo="cenario", nome=f"Simulação de reajuste de {percentual}%", valor=float(valor),
                                      fonte=f"Cenário escolhido pelo usuário: {percentual}% sobre o vencimento inicial.")
                elif tipo == "valor":
                    referencia = dict(tipo="consultoria", nome="Valor de referência informado", valor=float(_decimal(escolha.get("valor"), "Valor de referência")),
                                      fonte="Valor inicial informado pelo usuário para esta análise.")
                elif tipo == "pspn":
                    fonte = self.carregar("cafezal-2026")
                    if dados["ano"] != fonte["ano"]:
                        raise ValueError(f"O piso preparado é de {fonte['ano']}. Informe uma referência do ano da tabela.")
                    referencia = dict(tipo="pspn", nome=f"Piso do magistério de {fonte['ano']}", valor=fonte["piso_nacional_40h"],
                                      fonte=fonte["fonte_piso"], url=fonte["url_fonte_piso"], jornada=40, proporcional=True)
                else:
                    raise ValueError("Escolha como deseja comparar os salários.")
                referencia.setdefault("jornada", dados["jornada_semanal"])
                referencia.setdefault("proporcional", False)
                dados["referencia"] = {**referencia, "ano": dados["ano"]}
            if not dados.get("referencia") and not dados.get("piso_nacional_40h"):
                raise ValueError("Informe o reajuste desejado ou o valor que será usado na comparação.")
        analise = analisar_tabela_salarial(dados)
        if not perfil:
            pasta = self.diretorio / "tabelas"
            pasta.mkdir(parents=True, exist_ok=True)
            canonico = json.dumps(dados, ensure_ascii=False, sort_keys=True)
            perfil = sha256(canonico.encode()).hexdigest()[:32]
            caminho = pasta / f"{perfil}.json"
            if not caminho.exists():
                temporario = pasta / f"{perfil}-{uuid4().hex}.tmp"
                temporario.write_text(canonico, encoding="utf-8")
                temporario.replace(caminho)
        return analise, self.descrever(perfil, dados)
