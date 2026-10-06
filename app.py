"""Ponto de entrada da aplicação web.

Execute com:
    python app.py
"""

from datetime import datetime
from base64 import b64encode
from functools import lru_cache
from src.coleta.cache_catalogo import cache_catalogo
from io import BytesIO
import json
import os
from pathlib import Path
from unicodedata import normalize

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.utils import secure_filename

from src.coleta.tce_client import TCEClient, TCEError, TCEConsultaIndisponivel
from src.exportacao.excel import gerar_excel
from src.exportacao.excel_salarial import gerar_excel_salarial
from src.exportacao.relatorio_pdf import gerar_relatorio_salarial_pdf
from src.materiais.planilha_service import inspecionar_planilha
from src.salarial.amostras import carregar_cafezal_2026
from src.salarial.analise_service import analisar_tabela_salarial
from src.salarial.aquisicao_service import registrar_dossie_salarial
from src.salarial.documento_service import importar_tabela_salarial
from src.salarial.fontes_service import listar_fontes_salariais
from src.salarial.pdf_service import inspecionar_pdf
from src.salarial.revisao_service import extrair_para_revisao
from src.exportacao.excel_modelo_salarial import normalizar_analise
from src.persistencia.dossie_salarial import DossieSalarialStore
from src.services.analise_service import AnaliseService
from src.services.automacao_financeira import gerar_analise_automatica
from src.salarial.automacao_service import AutomacaoSalarial


RAIZ_PROJETO = Path(__file__).resolve().parent
AMOSTRA_HISTORICA = RAIZ_PROJETO / "data/processed/amostra_curitiba_2019_2025.json"


def _opcoes_serializadas(opcoes):
    """Congela opções do catálogo para reutilizá-las sem nova consulta ao portal."""

    return tuple((str(item["id"]), str(item["nome"])) for item in opcoes)


def _priorizar_entidade_municipal(entidades):
    def prioridade(entidade):
        nome = normalize("NFKD", entidade["nome"]).encode("ascii", "ignore").decode().upper().strip()
        return 0 if nome.startswith(("MUNICIPIO ", "PREFEITURA ")) else 1

    # Mantém as demais entidades e a ordem relativa do catálogo oficial.
    return sorted(entidades, key=prioridade)


def _opcoes_json(opcoes):
    return [{"id": item_id, "nome": nome} for item_id, nome in opcoes]


@cache_catalogo(maxsize=1)
def _municipios_tce():
    return _opcoes_serializadas(TCEClient().listar_municipios())


@cache_catalogo(maxsize=512)
def _entidades_tce(municipio_id):
    return _opcoes_serializadas(TCEClient().listar_entidades(municipio_id))


@cache_catalogo(maxsize=512)
def _relatorios_tce(municipio_id, entidade_id):
    return _opcoes_serializadas(TCEClient().listar_relatorios(municipio_id, entidade_id))


@cache_catalogo(maxsize=512)
def _anos_tce(municipio_id, entidade_id):
    return _opcoes_serializadas(TCEClient().listar_anos(municipio_id, entidade_id))


@lru_cache(maxsize=1)
def _amostra_historica():
    if not AMOSTRA_HISTORICA.exists():
        raise FileNotFoundError("A amostra histórica ainda não foi gerada.")
    return json.loads(AMOSTRA_HISTORICA.read_text(encoding="utf-8"))


def _campos_base(dados):
    campos = ("municipio_id", "municipio_nome", "entidade_id", "entidade_nome")
    ausentes = [campo for campo in campos if not str(dados.get(campo, "")).strip()]
    if ausentes:
        raise ValueError(f"Campos obrigatórios ausentes: {', '.join(ausentes)}")
    return {
        "municipio_id": str(dados["municipio_id"]),
        "municipio_nome": str(dados["municipio_nome"]),
        "entidade_id": str(dados["entidade_id"]),
        "entidade_nome": str(dados["entidade_nome"]),
    }


def _ano(valor, nome="exercício"):
    try:
        ano = int(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"O {nome} deve ser um número inteiro.") from erro
    if ano < 2013 or ano > datetime.now().year:
        raise ValueError(f"O {nome} está fora do intervalo aceito.")
    return ano


def create_app(analise_service=None, dossie_diretorio=None):
    """Cria a aplicação Flask e permite trocar o serviço durante os testes."""

    app = Flask(__name__)
    app.config.update(
        ANALISE_SERVICE=analise_service or AnaliseService(),
        DOSSIE_SALARIAL_STORE=DossieSalarialStore(
            dossie_diretorio or RAIZ_PROJETO / "data/raw/salarios"
        ),
        MAX_CONTENT_LENGTH=48 * 1024 * 1024,
    )

    app.config["AUTOMACAO_SALARIAL"] = AutomacaoSalarial(
        RAIZ_PROJETO / "data/processed",
        (Path(dossie_diretorio) / "automatico" if dossie_diretorio is not None else
         Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local/share") / "AnaliseMunicipal" / "tabelas_salariais"),
    )

    @app.get("/")
    def index():
        return render_template("inicio.html", ultimo_fechado=datetime.now().year - 1)

    @app.get("/avancado")
    def modo_avancado():
        return render_template("index.html")

    def pacote_excel(dados, salarial=False, exemplo=False):
        if salarial:
            conteudo = gerar_excel_salarial(dados)
            periodo = str(dados["ano"])
            sufixo = secure_filename(dados["profissao"])
            titulo = f"{dados['municipio']} · {dados['profissao']}"
            avisos = dados.get("avisos", [])
        else:
            conteudo = gerar_excel(dados)
            periodo = f"{dados['ano_inicial']}-{dados['ano_final']}" if "resultados" in dados else str(dados["ano"])
            sufixo = "financeiro"
            titulo = dados["municipio"]
            avisos = list(dados.get("avisos", []))
            for erro in dados.get("erros", []):
                avisos.append(f"{erro['ano']}: {erro['mensagem']}")
            for item in dados.get("resultados", []):
                avisos.extend(f"{item['ano']}: {aviso}" for aviso in item.get("avisos", []))
        nome = f"analise-{secure_filename(dados['municipio'])}-{sufixo}-{periodo}.xlsx".lower()
        return {"titulo": titulo, "periodo": periodo, "avisos": avisos,
                "exemplo": exemplo, "coletado_em": dados.get("coletado_em"),
                "arquivo": {"nome": nome, "conteudo_base64": b64encode(conteudo).decode("ascii")}}

    @app.post("/api/automacao/financeiro")
    def automacao_financeiro():
        resultado = gerar_analise_automatica(
            request.get_json(silent=True) or {}, app.config["ANALISE_SERVICE"],
            lambda: _opcoes_json(_municipios_tce()),
            lambda municipio: _priorizar_entidade_municipal(_opcoes_json(_entidades_tce(municipio))),
            lambda municipio, entidade: _opcoes_json(_relatorios_tce(municipio, entidade)),
            lambda municipio, entidade: _opcoes_json(_anos_tce(municipio, entidade)),
        )
        return jsonify(pacote_excel(resultado))

    @app.get("/api/automacao/exemplo-financeiro")
    def automacao_exemplo():
        return jsonify(pacote_excel(dict(_amostra_historica()), exemplo=True))

    @app.get("/api/automacao/tabelas")
    def automacao_tabelas():
        return jsonify(app.config["AUTOMACAO_SALARIAL"].catalogo())

    @app.post("/api/automacao/preparar-tabela")
    def automacao_preparar_tabela():
        arquivo = request.files.get("arquivo")
        if arquivo is None:
            raise ValueError("Escolha o documento com a tabela salarial.")
        return jsonify(app.config["AUTOMACAO_SALARIAL"].preparar(arquivo.filename, arquivo.read()))

    @app.post("/api/automacao/salarios")
    def automacao_salarios():
        analise, tabela = app.config["AUTOMACAO_SALARIAL"].analisar(request.get_json(silent=True) or {})
        return jsonify({**pacote_excel(analise, salarial=True), "tabela": tabela})

    @app.get("/favicon.ico")
    def favicon():
        return send_file(RAIZ_PROJETO / "static/favicon.svg", mimetype="image/svg+xml")

    @app.get("/api/municipios")
    def listar_municipios():
        return jsonify(_opcoes_json(_municipios_tce()))

    @app.get("/api/entidades/<municipio_id>")
    def listar_entidades(municipio_id):
        return jsonify(_priorizar_entidade_municipal(_opcoes_json(_entidades_tce(str(municipio_id)))))

    @app.get("/api/anos/<municipio_id>/<entidade_id>")
    def listar_anos(municipio_id, entidade_id):
        ultimo_fechado = datetime.now().year - 1
        anos = _opcoes_json(_anos_tce(str(municipio_id), str(entidade_id)))
        fechados = [
            item
            for item in anos
            if item["id"].isdigit() and 2019 <= int(item["id"]) <= ultimo_fechado
        ]
        return jsonify(fechados)

    @app.post("/api/analisar")
    def analisar():
        dados = request.get_json(silent=True) or {}
        parametros = _campos_base(dados)
        parametros["ano"] = _ano(dados.get("ano"))
        parametros["incluir_fundeb"] = dados.get("incluir_fundeb", True) is not False
        resultado = app.config["ANALISE_SERVICE"].analisar(**parametros)
        return jsonify(resultado.to_dict())

    @app.post("/api/analisar-historico")
    def analisar_historico():
        dados = request.get_json(silent=True) or {}
        parametros = _campos_base(dados)
        parametros["ano_inicial"] = _ano(dados.get("ano_inicial"), "exercício inicial")
        parametros["ano_final"] = _ano(dados.get("ano_final"), "exercício final")
        parametros["incluir_fundeb"] = dados.get("incluir_fundeb", True) is not False
        resultado = app.config["ANALISE_SERVICE"].analisar_historico(**parametros)
        return jsonify(resultado.to_dict())

    @app.get("/api/amostras/curitiba-historico")
    def amostra_curitiba_historico():
        try:
            dados = dict(_amostra_historica())
        except FileNotFoundError as erro:
            return jsonify({"erro": str(erro)}), 404
        dados["origem_dados"] = "Amostra preservada de Curitiba"
        return jsonify(dados)

    @app.get("/api/amostras/curitiba/<int:ano>")
    def amostra_curitiba_anual(ano):
        """Entrega qualquer exercício preservado da demonstração, não só 2019."""

        try:
            historico = _amostra_historica()
        except FileNotFoundError as erro:
            return jsonify({"erro": str(erro)}), 404
        resultado = next(
            (dict(item) for item in historico.get("resultados", []) if item.get("ano") == ano),
            None,
        )
        if resultado is None:
            disponiveis = [item.get("ano") for item in historico.get("resultados", [])]
            return jsonify(
                {
                    "erro": f"A demonstração offline não possui Curitiba/{ano}.",
                    "anos_disponiveis": disponiveis,
                }
            ), 404
        resultado["origem_dados"] = "Amostra preservada de Curitiba"
        return jsonify(resultado)

    @app.post("/api/exportar")
    def exportar():
        dados = request.get_json(silent=True) or {}
        conteudo = gerar_excel(dados)
        if "resultados" in dados:
            periodo = f"{dados.get('ano_inicial', 'inicio')}-{dados.get('ano_final', 'fim')}"
        else:
            periodo = str(dados.get("ano", "ano"))
        municipio = secure_filename(str(dados.get("municipio", "municipio"))) or "municipio"
        nome = f"analise-{municipio}-{periodo}.xlsx"
        return send_file(
            BytesIO(conteudo),
            as_attachment=True,
            download_name=nome.lower().replace(" ", "-"),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.post("/api/salarios/inspecionar-pdf")
    def inspecionar_pdf_salarios():
        arquivo = request.files.get("arquivo")
        if arquivo is None:
            raise ValueError("Envie o PDF no campo 'arquivo'.")
        return jsonify(inspecionar_pdf(arquivo.filename, arquivo.read()))

    @app.get("/api/salarios/amostras/cafezal-do-sul-2026")
    def amostra_salarial_cafezal():
        return jsonify(carregar_cafezal_2026())

    @app.get("/api/salarios/fontes")
    def fontes_salariais():
        return jsonify(listar_fontes_salariais())

    @app.get("/api/salarios/amostras/curitiba-administrativo-2026")
    def amostra_curitiba_administrativo():
        return jsonify(json.loads((RAIZ_PROJETO / 'data/processed/curitiba_administrativo_2026.json').read_text(encoding='utf-8')))

    @app.post("/api/salarios/extrair-revisao")
    def extrair_revisao_salarial():
        arquivo = request.files.get('arquivo')
        if arquivo is None:
            raise ValueError("Envie a tabela no campo arquivo.")
        return jsonify(extrair_para_revisao(arquivo.filename, arquivo.read()))

    @app.get("/api/salarios/modelo-importacao")
    def modelo_importacao_salarial():
        return send_file(RAIZ_PROJETO / 'data/modelos/importacao_profissoes.csv',as_attachment=True)

    @app.post("/api/salarios/dossies")
    def criar_dossie_salarial():
        arquivos = []
        for categoria in ("tabela_vigente", "plano_carreira", "ato_reajuste"):
            arquivo = request.files.get(categoria)
            if arquivo is not None and arquivo.filename:
                arquivos.append(
                    {
                        "categoria": categoria,
                        "nome_original": arquivo.filename,
                        "conteudo": arquivo.read(),
                    }
                )
        resultado = registrar_dossie_salarial(
            app.config["DOSSIE_SALARIAL_STORE"],
            {
                "municipio": request.form.get("municipio"),
                "uf": request.form.get("uf"),
                "ano": request.form.get("ano_referencia"),
                "fonte_url": request.form.get("fonte_url"),
                "tipo_fonte": request.form.get("tipo_fonte"),
                "observacoes": request.form.get("observacoes", ""),
            },
            arquivos,
        )
        return jsonify(resultado), 201

    @app.post("/api/salarios/analisar")
    def analisar_salarios():
        dados = request.get_json(silent=True) or {}
        return jsonify(analisar_tabela_salarial(dados))

    @app.post("/api/salarios/importar-documento")
    def importar_documento_salarial():
        arquivo = request.files.get("arquivo")
        if arquivo is None:
            raise ValueError("Envie o documento salarial no campo 'arquivo'.")
        importado = importar_tabela_salarial(arquivo.filename, arquivo.read())
        dados = {
            **importado,
            "municipio": request.form.get("municipio", "Município não informado"),
            "uf": request.form.get("uf", "PR"),
            "ano": request.form.get("ano"),
            "piso_nacional_40h": request.form.get("piso_nacional_40h"),
            "jornada_semanal": request.form.get("jornada_semanal"),
            "jornada_confirmada_no_documento": request.form.get(
                "jornada_confirmada_no_documento"
            )
            in ("1", "true", "on"),
            "modo_arredondamento": request.form.get("modo_arredondamento", "truncar"),
            "fonte_piso": request.form.get("fonte_piso", "Fonte não informada"),
            "url_fonte_piso": request.form.get("url_fonte_piso", ""),
        }
        resultado = analisar_tabela_salarial(dados)
        resultado["importacao"] = {
            "arquivo": arquivo.filename,
            "texto_extraido_caracteres": importado.get("texto_extraido_caracteres"),
        }
        return jsonify(resultado)

    @app.post("/api/salarios/exportar-excel")
    def exportar_salarios_excel():
        dados = request.get_json(silent=True) or {}
        conteudo = gerar_excel_salarial(dados)
        municipio = secure_filename(str(dados.get("municipio", "municipio"))) or "municipio"
        entrada = dados.get('entrada', dados)
        profissao = secure_filename(str(entrada.get('profissao','magisterio'))) or 'profissao'
        ano = secure_filename(str(entrada.get('ano','')))
        return send_file(
            BytesIO(conteudo),
            as_attachment=True,
            download_name=f"analise-salarial-{municipio.lower()}-{profissao.lower()}-{ano}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.post("/api/salarios/relatorio-pdf")
    def exportar_salarios_pdf():
        dados = request.get_json(silent=True) or {}
        dados = normalizar_analise(dados)
        conteudo = gerar_relatorio_salarial_pdf(dados)
        municipio = secure_filename(str(dados.get("municipio", "municipio"))) or "municipio"
        return send_file(
            BytesIO(conteudo),
            as_attachment=True,
            download_name=f"relatorio-salarial-{municipio.lower()}.pdf",
            mimetype="application/pdf",
        )

    @app.post("/api/materiais/inspecionar-planilha")
    def inspecionar_planilha_original():
        arquivo = request.files.get("arquivo")
        if arquivo is None:
            raise ValueError("Envie a planilha no campo 'arquivo'.")
        return jsonify(inspecionar_planilha(arquivo.filename, arquivo.read()))

    @app.errorhandler(ValueError)
    def tratar_erro_validacao(erro):
        return jsonify({"erro": str(erro), "tipo": "validacao"}), 400

    @app.errorhandler(TCEConsultaIndisponivel)
    def tratar_consulta_indisponivel(erro):
        app.logger.warning("Consulta indisponível em %s %s: %s", request.method, request.path, erro)
        mensagem = "Ainda não encontramos os dados necessários para esse município." if request.path.startswith("/api/automacao/") else str(erro)
        return jsonify({
            "erro": mensagem,
            "detalhe": str(erro),
            "tipo": "relatorio_indisponivel",
            "caminho": request.path,
            "metodo": request.method,
        }), 422

    @app.errorhandler(TCEError)
    def tratar_erro_tce(erro):
        app.logger.warning("Falha na consulta/coleta em %s %s: %s", request.method, request.path, erro)
        mensagem = "A fonte não respondeu como esperado. Tente novamente em alguns instantes." if request.path.startswith("/api/automacao/") else str(erro)
        return jsonify({
            "erro": mensagem,
            "detalhe": str(erro),
            "tipo": "fonte_externa",
            "caminho": request.path,
            "metodo": request.method,
        }), 502

    @app.errorhandler(RequestEntityTooLarge)
    def tratar_arquivo_grande(_erro):
        return jsonify({"erro": "O conjunto enviado excede o limite total de 48 MB.", "tipo": "validacao"}), 413

    @app.errorhandler(HTTPException)
    def tratar_erro_http(erro):
        # Mantém o status e os cabeçalhos originais (por exemplo, Allow no 405).
        # Uma URL ausente é 404; não é uma falha interna do servidor.
        resposta = erro.get_response()
        mensagens = {
            404: "Endereço não encontrado. Confira a URL solicitada.",
            405: "Método não permitido para este endereço.",
        }
        resposta.set_data(app.json.dumps({
            "erro": mensagens.get(erro.code, erro.description),
            "tipo": "http",
            "codigo": erro.code,
            "caminho": request.path,
            "metodo": request.method,
        }))
        resposta.content_type = "application/json"
        return resposta

    @app.errorhandler(Exception)
    def tratar_erro_inesperado(erro):
        app.logger.exception("Erro inesperado em %s %s", request.method, request.path, exc_info=erro)
        mensagem = ("Não conseguimos concluir a análise agora. Tente novamente."
                    if request.path.startswith("/api/automacao/") else
                    "Ocorreu um erro inesperado. Consulte o terminal para detalhes.")
        return jsonify({"erro": mensagem}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
