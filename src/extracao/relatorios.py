"""Funções pequenas para extrair os valores dos relatórios do TCE-PR."""

import csv
from io import StringIO
import re

from src.coleta.tce_client import TCEError


def numero_brasileiro(texto):
    """Converte ``7.361.430.652,73`` ou ``37,85%`` para ``float``."""

    if texto is None:
        raise ValueError("Valor vazio")
    limpo = str(texto).strip().replace("R$", "").replace("%", "").replace(" ", "")
    if not limpo or limpo == "-":
        raise ValueError("Valor vazio")
    negativo = limpo.startswith("(") and limpo.endswith(")")
    limpo = limpo.strip("()")
    limpo = limpo.replace(".", "").replace(",", ".")
    valor = float(limpo)
    return -valor if negativo else valor


def _linhas(csv_texto):
    return list(csv.reader(StringIO(csv_texto)))


def _celulas_preenchidas(linha):
    return [celula.strip() for celula in linha if celula and celula.strip()]


def _resumo_por_inicio(linhas, inicio):
    inicio_normalizado = inicio.casefold()
    for linha in linhas:
        # As tabelas mensais repetem alguns rótulos depois de várias colunas
        # vazias. No resumo anual o rótulo fica realmente na primeira coluna.
        primeira_celula = linha[0].strip() if linha else ""
        if primeira_celula.casefold().startswith(inicio_normalizado):
            return _celulas_preenchidas(linha)
    raise TCEError(f"A linha '{inicio}' não foi encontrada no relatório.")


def extrair_rcl_rreo(csv_texto):
    """Extrai o total anual atualizado da linha de RCL do RREO.

    O CSV apresenta os meses e, ao final, dois totais anuais. O penúltimo valor
    é o total atualizado usado na validação do protótipo.
    """

    for linha in _linhas(csv_texto):
        if any("RECEITA CORRENTE LÍQUIDA (III)" in celula for celula in linha):
            numeros = []
            for celula in linha:
                if re.search(r"\d", celula or ""):
                    try:
                        numeros.append(numero_brasileiro(celula))
                    except ValueError:
                        pass
            if len(numeros) >= 2:
                return numeros[-2]
    raise TCEError("A Receita Corrente Líquida não foi encontrada no relatório RREO.")


def extrair_resumo_pessoal(csv_texto):
    linhas = _linhas(csv_texto)
    rcl = _resumo_por_inicio(linhas, "RECEITA CORRENTE LÍQUIDA - RCL")
    rcl_ajustada = _resumo_por_inicio(linhas, "RECEITA CORRENTE LÍQUIDA AJUSTADA")
    despesa = _resumo_por_inicio(linhas, "DESPESA TOTAL COM PESSOAL")
    limite_maximo = _resumo_por_inicio(linhas, "LIMITE MÁXIMO")
    limite_prudencial = _resumo_por_inicio(linhas, "LIMITE PRUDENCIAL")
    limite_alerta = _resumo_por_inicio(linhas, "LIMITE DE ALERTA")

    return {
        "rcl": numero_brasileiro(rcl[1]),
        "rcl_ajustada": numero_brasileiro(rcl_ajustada[1]),
        "despesa_total_pessoal": numero_brasileiro(despesa[1]),
        "percentual_oficial": numero_brasileiro(despesa[2]),
        "limite_maximo": numero_brasileiro(limite_maximo[-1]),
        "limite_prudencial": numero_brasileiro(limite_prudencial[-1]),
        "limite_alerta": numero_brasileiro(limite_alerta[-1]),
    }


def _primeira_linha_contendo(linhas, trecho):
    trecho_normalizado = trecho.casefold()
    for linha in linhas:
        primeira_celula = linha[0].strip() if linha else ""
        if trecho_normalizado in primeira_celula.casefold():
            return linha
    raise TCEError(f"A linha contendo '{trecho}' não foi encontrada no relatório.")


def _ultimo_valor_monetario(linha):
    for celula in reversed(linha[1:]):
        if not celula or "%" in celula:
            continue
        try:
            return numero_brasileiro(celula)
        except ValueError:
            continue
    raise TCEError("A linha localizada não possui um valor monetário reconhecível.")


def _percentual_aplicacao_mde(linhas):
    """Localiza o percentual constitucional de MDE quando o layout o publica."""

    rotulos = (
        "PERCENTUAL DE APLICAÇÃO EM MDE SOBRE A RECEITA LÍQUIDA DE IMPOSTOS",
        "PERCENTUAL DE APLICAÇÃO DAS RECEITAS DE IMPOSTOS",
        "PERCENTUAL DE APLICAÇÃO EM MDE",
    )
    for rotulo in rotulos:
        try:
            linha = _primeira_linha_contendo(linhas, rotulo)
        except TCEError:
            continue
        for celula in reversed(linha[1:]):
            if "%" not in (celula or ""):
                continue
            try:
                return numero_brasileiro(celula)
            except ValueError:
                continue
    return None


def extrair_resumo_fundeb(csv_texto):
    """Extrai campos estáveis do relatório MDE em layouts antigos e novos.

    O TCE alterou a numeração das linhas a partir de 2021. Por isso a extração
    usa o texto do indicador, e não números como ``11`` ou ``6``.
    """

    linhas = _linhas(csv_texto)
    receitas = _primeira_linha_contendo(linhas, "RECEITAS RECEBIDAS DO FUNDEB")
    resultado = _primeira_linha_contendo(
        linhas, "RESULTADO LÍQUIDO DAS TRANSFERÊNCIAS DO FUNDEB"
    )
    return {
        "receitas_recebidas": _ultimo_valor_monetario(receitas),
        "resultado_liquido_transferencias": _ultimo_valor_monetario(resultado),
        "percentual_aplicacao_mde": _percentual_aplicacao_mde(linhas),
    }
