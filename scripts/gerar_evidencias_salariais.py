"""Regenera as evidências salariais oficiais da versão atual."""

from pathlib import Path

from src.exportacao.excel_salarial import gerar_excel_salarial
from src.exportacao.relatorio_pdf import gerar_relatorio_salarial_pdf
from src.salarial.amostras import carregar_cafezal_2026
from src.salarial.analise_service import analisar_tabela_salarial


def main():
    destino = Path(__file__).resolve().parents[1] / "docs/evidencias"
    destino.mkdir(parents=True, exist_ok=True)
    analise = analisar_tabela_salarial(carregar_cafezal_2026())
    excel = destino / "Analise_Salarial_Cafezal_do_Sul_2026.xlsx"
    pdf = destino / "Relatorio_Salarial_Cafezal_do_Sul_2026.pdf"
    excel.write_bytes(gerar_excel_salarial(analise))
    pdf.write_bytes(gerar_relatorio_salarial_pdf(analise))
    print(excel)
    print(pdf)


if __name__ == "__main__":
    main()
