"""Gera a amostra histórica oficial usada quando o TCE estiver indisponível."""

import json
from pathlib import Path

from src.services.analise_service import AnaliseService


DESTINO = Path("data/processed/amostra_curitiba_2019_2025.json")


def main():
    print("Consultando Curitiba de 2019 a 2025. Esta operação pode levar alguns minutos...")
    historico = AnaliseService().analisar_historico(
        municipio_id="1490",
        municipio_nome="Curitiba",
        entidade_id="12268",
        entidade_nome="Município de Curitiba",
        ano_inicial=2019,
        ano_final=2025,
        incluir_fundeb=True,
    )
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(
        json.dumps(historico.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Amostra salva em {DESTINO}")
    print(f"Exercícios analisados: {historico.resumo.anos_analisados}")
    print(f"Exercícios com erro: {historico.resumo.anos_com_erro}")
    for item in historico.resultados:
        fundeb = item.fundeb.receitas_recebidas if item.fundeb else None
        print(
            f"{item.ano}: RCL ajustada={item.receita_corrente_liquida_ajustada:.2f}; "
            f"DTP={item.despesa_total_pessoal:.2f}; FUNDEB={fundeb}; "
            f"comprometimento={item.percentual_calculado:.4f}%"
        )


if __name__ == "__main__":
    main()
