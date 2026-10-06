"""Mostra relatórios, exercícios e períodos oferecidos pelo TCE-PR.

Uso:
    python -m scripts.mapear_tce --ano 2025
"""

import csv
from io import StringIO

from src.coleta.tce_client import TCEClient
from scripts.tce_cli import parser_com_selecao, resolver_municipio_entidade


def main():
    parser = parser_com_selecao("Mapeia relatórios e períodos disponíveis no TCE-PR")
    parser.add_argument("--ano", type=int, default=2019)
    opcoes = parser.parse_args()

    cliente = TCEClient()
    selecao = resolver_municipio_entidade(cliente, opcoes)
    municipio_id = selecao["municipio_id"]
    entidade_id = selecao["entidade_id"]
    print(f"## Relatórios disponíveis para {selecao['entidade_nome']}")
    for item in cliente.listar_relatorios(municipio_id, entidade_id):
        print(f"- {item['id']}: {item['nome']}")

    print("\n## Exercícios disponíveis no relatório de Pessoal")
    print(", ".join(item["id"] for item in cliente.listar_anos(municipio_id, entidade_id)))

    print(f"\n## Períodos do relatório MDE em {opcoes.ano}")
    periodos = cliente.listar_periodos(
        municipio_id, entidade_id, TCEClient.RELATORIO_MDE, opcoes.ano
    )
    for item in periodos:
        print(f"- {item['id']}: {item['nome']}")

    fechamento = next((item for item in periodos if "6º" in item["nome"]), None)
    if fechamento is None:
        print("O 6º bimestre não está disponível para o exercício informado.")
        return

    csv_mde = cliente.coletar_relatorio_csv(
        municipio_id,
        entidade_id,
        TCEClient.RELATORIO_MDE,
        opcoes.ano,
        periodo_id=fechamento["id"],
    )
    print(f"\n## Indicadores principais do FUNDEB em {opcoes.ano}")
    for linha in csv.reader(StringIO(csv_mde)):
        preenchidas = [celula.strip() for celula in linha if celula.strip()]
        if not preenchidas:
            continue
        rotulo = preenchidas[0].casefold()
        if any(
            termo in rotulo
            for termo in (
                "receitas recebidas do fundeb",
                "resultado líquido das transferências do fundeb",
            )
        ):
            print(" | ".join(preenchidas))


if __name__ == "__main__":
    main()
