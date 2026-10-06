import unittest
from io import BytesIO

from openpyxl import load_workbook

from src.exportacao.excel import gerar_excel


class ExcelTestCase(unittest.TestCase):
    def setUp(self):
        self.anual = {
            "municipio_id": "1490",
            "municipio": "Curitiba",
            "entidade_id": "12268",
            "entidade": "Município de Curitiba",
            "ano": 2019,
            "receita_corrente_liquida": 7361430652.73,
            "receita_corrente_liquida_ajustada": 7359872310.73,
            "despesa_total_pessoal": 2786074714.14,
            "percentual_oficial": 37.85,
            "percentual_calculado": 37.8549,
            "classificacao": "normal",
            "fonte_receita": "RREO",
            "fonte_pessoal": "RGF",
            "fundeb": {
                "receitas_recebidas": 600162934.45,
                "resultado_liquido_transferencias": 275212940.29,
                "fonte": "MDE",
                "periodo": "6º Bimestre",
            },
            "avisos": [],
        }

    def test_gera_planilha_anual_que_pode_ser_aberta(self):
        conteudo = gerar_excel(self.anual)
        workbook = load_workbook(BytesIO(conteudo), data_only=False)
        self.assertIn("Resumo", workbook.sheetnames)
        self.assertIn("Fontes e validação", workbook.sheetnames)
        self.assertEqual(workbook["Resumo"]["B2"].value, "Curitiba")
        self.assertEqual(workbook["Resumo"]["B8"].value, 0.3785)
        self.assertEqual(workbook["Resumo"]["B11"].value, 600162934.45)

    def test_gera_planilha_historica(self):
        segundo = dict(self.anual)
        segundo.update(
            ano=2020,
            receita_corrente_liquida_ajustada=8000000000,
            despesa_total_pessoal=3000000000,
            evolucao={
                "rcl_ajustada_percentual": 8.7,
                "despesa_pessoal_percentual": 7.67,
                "receitas_fundeb_percentual": -4.69,
                "comprometimento_pontos_percentuais": -0.35,
            },
        )
        primeiro = dict(self.anual)
        primeiro["evolucao"] = {
            "rcl_ajustada_percentual": None,
            "despesa_pessoal_percentual": None,
            "receitas_fundeb_percentual": None,
            "comprometimento_pontos_percentuais": None,
        }
        historico = {
            "municipio": "Curitiba",
            "entidade": "Município de Curitiba",
            "ano_inicial": 2019,
            "ano_final": 2020,
            "coletado_em": "2026-08-15T12:00:00-03:00",
            "resultados": [primeiro, segundo],
            "erros": [],
            "resumo": {
                "anos_analisados": 2,
                "anos_com_erro": 0,
                "evolucao_acumulada_rcl_ajustada": 8.7,
                "evolucao_acumulada_despesa_pessoal": 7.67,
                "evolucao_acumulada_receitas_fundeb": -4.69,
                "media_comprometimento": 37.67,
                "maior_comprometimento": 37.85,
                "ano_maior_comprometimento": 2019,
            },
        }
        conteudo = gerar_excel(historico)
        workbook = load_workbook(BytesIO(conteudo), data_only=False)
        self.assertIn("Resumo histórico", workbook.sheetnames)
        self.assertIn("Histórico", workbook.sheetnames)
        self.assertIn("Painel financeiro", workbook.sheetnames)
        self.assertIn("Erros e pendências", workbook.sheetnames)
        self.assertEqual(workbook["Histórico"]["A3"].value, 2020)
        self.assertEqual(workbook["Histórico"]["H2"].value, 600162934.45)
        self.assertEqual(workbook["Painel financeiro"]["B6"].value, '=IF(\'Histórico\'!C2="","",\'Histórico\'!C2)')
        self.assertEqual(workbook["Painel financeiro"]["C8"].value, '=IFERROR(IF(OR(C6="",B6=""),"",(C6/B6)-1),"")')
        self.assertEqual(len(workbook["Painel financeiro"]._charts), 1)


if __name__ == "__main__":
    unittest.main()
