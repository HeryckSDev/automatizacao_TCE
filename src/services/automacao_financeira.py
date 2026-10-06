"""Resolve as escolhas de coleta e entrega a análise a partir do pedido do usuário."""
from datetime import datetime
from unicodedata import normalize

from src.coleta.tce_client import TCEError, TCEConsultaIndisponivel


def _nome(texto):
    return normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().upper().strip()


def gerar_analise_automatica(pedido, servico, municipios, entidades, relatorios, anos):
    if not isinstance(pedido, dict):
        raise ValueError("Escolha o município e o período da análise.")
    municipio_id = str(pedido.get("municipio_id", "")).strip()
    municipio = next((m for m in municipios() if m["id"] == municipio_id), None)
    if municipio is None:
        raise ValueError("Escolha um município da lista.")
    candidatas = [e for e in entidades(municipio_id)
                  if _nome(e["nome"]).startswith(("MUNICIPIO ", "PREFEITURA "))]
    contexto = None
    ultimo_erro = None
    limite = datetime.now().year - 1
    for entidade in candidatas:
        try:
            catalogo = relatorios(municipio_id, entidade["id"])
            if not {"10", "20"}.issubset({str(r["id"]) for r in catalogo}):
                continue
            publicados = sorted({int(a["id"]) for a in anos(municipio_id, entidade["id"])
                                 if str(a["id"]).isdigit() and 2019 <= int(a["id"]) <= limite})
            if publicados:
                contexto = entidade, publicados
                break
        except TCEError as erro:
            ultimo_erro = erro
    if contexto is None:
        if ultimo_erro:
            raise TCEError(f"Não conseguimos consultar os dados deste município agora. Detalhe: {ultimo_erro}") from ultimo_erro
        raise TCEConsultaIndisponivel("Ainda não encontramos os relatórios necessários para este município.")
    entidade, publicados = contexto
    base = dict(municipio_id=municipio_id, municipio_nome=municipio["nome"],
                entidade_id=entidade["id"], entidade_nome=entidade["nome"], incluir_fundeb=True)
    periodo = pedido.get("periodo", "historico")
    if periodo == "ultimo":
        return servico.analisar(**base, ano=publicados[-1]).to_dict()
    if periodo == "historico":
        fim = publicados[-1]
        inicio = max(publicados[0], fim - 9)
    elif periodo == "intervalo":
        try:
            inicio, fim = int(pedido["ano_inicial"]), int(pedido["ano_final"])
        except (ValueError, TypeError, KeyError):
            raise ValueError("Informe os anos inicial e final.") from None
        if inicio < 2019 or fim > limite or inicio > fim or fim - inicio > 9:
            raise ValueError(f"Escolha até dez anos entre 2019 e {limite}.")
        if not any(inicio <= a <= fim for a in publicados):
            raise ValueError("Não encontramos dados publicados para esse período.")
    else:
        raise ValueError("Escolha uma das opções de período.")
    return servico.analisar_historico(**base, ano_inicial=inicio, ano_final=fim,
                                     anos_disponiveis=publicados).to_dict()
