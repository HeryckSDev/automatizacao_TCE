"""Teste manual parametrizável da integração real com o TCE-PR.

Este arquivo não faz parte dos testes rápidos porque depende da internet e da
disponibilidade de uma fonte externa.

Exemplos:
    python -m scripts.testar_tce --municipio "Cafezal do Sul" --ano 2024
    python -m scripts.testar_tce --municipio "Londrina" --ano 2024 --json resultado.json
"""

import json
from pathlib import Path

from src.coleta.tce_client import TCEClient
from src.services.analise_service import AnaliseService
from scripts.tce_cli import parser_com_selecao, resolver_municipio_entidade


def main():
    parser = parser_com_selecao("Consulta anual para validação manual do TCE-PR")
    parser.add_argument("--ano", type=int, default=2019)
    parser.add_argument("--sem-fundeb", action="store_true", help="Não consulta MDE/FUNDEB")
    parser.add_argument("--json", type=Path, help="Salva o resultado tratado em um arquivo JSON")
    opcoes = parser.parse_args()

    selecao = resolver_municipio_entidade(TCEClient(), opcoes)
    print(
        f"Consultando {selecao['municipio_nome']}/{opcoes.ano} em relatórios oficiais. "
        "A operação pode levar cerca de um minuto..."
    )
    resultado = AnaliseService().analisar(
        **selecao,
        ano=opcoes.ano,
        incluir_fundeb=not opcoes.sem_fundeb,
    ).to_dict()
    print("\nResultado:")
    for campo, valor in resultado.items():
        print(f"- {campo}: {valor}")
    if opcoes.json:
        opcoes.json.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nJSON salvo em: {opcoes.json.resolve()}")


if __name__ == "__main__":
    main()
