from src.modelos.analise import LimitesPessoal


def percentual_comprometimento(despesa_total_pessoal, receita_corrente_liquida_ajustada):
    if receita_corrente_liquida_ajustada <= 0:
        raise ValueError("A Receita Corrente Líquida Ajustada deve ser maior que zero.")
    return (despesa_total_pessoal / receita_corrente_liquida_ajustada) * 100


def classificar_percentual(percentual, limites: LimitesPessoal):
    if percentual >= limites.maximo:
        return "limite_excedido"
    if percentual >= limites.prudencial:
        return "prudencial"
    if percentual >= limites.alerta:
        return "alerta"
    return "normal"


def variacao_percentual(valor_atual, valor_anterior):
    """Calcula a variação entre dois exercícios sem mascarar base zero."""

    if valor_anterior is None or valor_atual is None or valor_anterior == 0:
        return None
    return ((valor_atual / valor_anterior) - 1) * 100


def diferenca_pontos_percentuais(valor_atual, valor_anterior):
    if valor_anterior is None or valor_atual is None:
        return None
    return valor_atual - valor_anterior
