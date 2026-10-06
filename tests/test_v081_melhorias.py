"""Testes das melhorias da v0.8.1: aviso de vigência, ano obrigatório e Excel com valores em cache."""
import copy
import io
import json
import unittest
import zipfile
from pathlib import Path

from openpyxl import load_workbook

from src.exportacao.cache_xlsx import injetar_cache
from src.exportacao.excel import gerar_excel
from src.salarial.analise_service import analisar_tabela_salarial
from src.salarial.documento_service import extrair_tabela_salarial_texto

RAIZ = Path(__file__).resolve().parents[1]
BASE = (
    "Nível A - Magistério 2.565,31 2.616,61 2.668,94\n"
    "Nível B - Licenciatura 2.873,14 2.930,60 2.989,21\n"
    "Percentual entre classes = 2,00%\n"
    "Nível B = Nível A acrescido de 12,00%\n"
)


class AvisoDeVigenciaTest(unittest.TestCase):
    def test_texto_sem_revogacao_nao_gera_aviso(self):
        avisos = extrair_tabela_salarial_texto(BASE)["avisos_importacao"]
        self.assertFalse([a for a in avisos if "revogação" in a])

    def test_revogacao_gera_aviso_com_o_trecho(self):
        texto = BASE + "Fica revogado o art. 5º da Lei 10/2020.\n"
        avisos = extrair_tabela_salarial_texto(texto)["avisos_importacao"]
        aviso = next(a for a in avisos if "revogação" in a)
        self.assertIn("revogado o art. 5º", aviso)
        self.assertIn("não decide", aviso)

    def test_nova_redacao_e_alteracao_tambem_sinalizam(self):
        for frase in ("O art. 3º passa a vigorar com nova redação.", "Ficam alterados os valores do Anexo II."):
            with self.subTest(frase=frase):
                avisos = extrair_tabela_salarial_texto(BASE + frase + "\n")["avisos_importacao"]
                self.assertTrue([a for a in avisos if "revogação ou alteração" in a])

    def test_aviso_nao_altera_os_valores_extraidos(self):
        sem = extrair_tabela_salarial_texto(BASE)
        com = extrair_tabela_salarial_texto(BASE + "Fica revogado o art. 5º.\n")
        self.assertEqual(sem["niveis"], com["niveis"])

    def test_regras_conflitantes_continuam_interrompendo(self):
        texto = BASE + "Nível B = Nível A acrescido de 15,00%\n"
        with self.assertRaises(ValueError):
            extrair_tabela_salarial_texto(texto)

    def test_percentual_em_nota_nao_vira_classe(self):
        resultado = extrair_tabela_salarial_texto(BASE + "(reajuste anual de 5,00%)\n")
        self.assertEqual([n["codigo"] for n in resultado["niveis"]], ["A", "B"])


class AnoObrigatorioTest(unittest.TestCase):
    def setUp(self):
        self.amostra = json.loads((RAIZ / "data/processed/cafezal_do_sul_2026.json").read_text(encoding="utf-8"))

    def test_ano_invalido_e_rejeitado(self):
        for ano in ("dois mil", "1999", "2101", "20x6", "2026.5"):
            with self.subTest(ano=ano):
                dados = copy.deepcopy(self.amostra)
                dados["ano"] = ano
                with self.assertRaises(ValueError):
                    analisar_tabela_salarial(dados)

    def test_ano_valido_continua_funcionando(self):
        self.assertEqual(analisar_tabela_salarial(copy.deepcopy(self.amostra))["ano"], 2026)


class ExcelFinanceiroComCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        historico = json.loads((RAIZ / "data/processed/amostra_curitiba_2019_2025.json").read_text(encoding="utf-8"))
        cls.conteudo = gerar_excel(historico)
        cls.historico = historico

    def test_formulas_continuam_vivas(self):
        painel = load_workbook(io.BytesIO(self.conteudo))["Painel financeiro"]
        self.assertTrue(str(painel["B12"].value).startswith("=IFERROR("))
        self.assertTrue(str(painel["B17"].value).startswith("=IF("))

    def test_todas_as_formulas_tem_valor_em_cache(self):
        wb = load_workbook(io.BytesIO(self.conteudo))
        wbv = load_workbook(io.BytesIO(self.conteudo), data_only=True)
        for ws in wb.worksheets:
            for linha in ws.iter_rows():
                for celula in linha:
                    if isinstance(celula.value, str) and celula.value.startswith("="):
                        valor = wbv[ws.title][celula.coordinate].value
                        # MDE (linha 12) não é automatizado: o resultado "" volta como None
                        if not (ws.title == "Painel financeiro" and celula.row == 16):
                            self.assertIsNotNone(valor, f"{ws.title}!{celula.coordinate} sem valor em cache")

    def test_cache_confere_com_o_dado_bruto(self):
        painel = load_workbook(io.BytesIO(self.conteudo), data_only=True)["Painel financeiro"]
        for coluna, resultado in enumerate(self.historico["resultados"], start=2):
            rcl = resultado["receita_corrente_liquida_ajustada"]
            dtp = resultado["despesa_total_pessoal"]
            self.assertAlmostEqual(painel.cell(6, coluna).value, rcl, places=2)
            self.assertAlmostEqual(painel.cell(9, coluna).value, dtp, places=2)
            self.assertAlmostEqual(painel.cell(12, coluna).value * 100, dtp / rcl * 100, places=6)
            self.assertAlmostEqual(painel.cell(12, coluna).value * 100, resultado["percentual_calculado"], places=2)
        self.assertEqual(painel["B17"].value, "Normal")

    def test_evolucao_anual_no_cache(self):
        painel = load_workbook(io.BytesIO(self.conteudo), data_only=True)["Painel financeiro"]
        r = self.historico["resultados"]
        esperado = r[1]["receita_corrente_liquida_ajustada"] / r[0]["receita_corrente_liquida_ajustada"] - 1
        self.assertAlmostEqual(painel["C8"].value, esperado, places=9)

    def test_graficos_sem_suavizacao(self):
        with zipfile.ZipFile(io.BytesIO(self.conteudo)) as z:
            graficos = [z.read(n).decode() for n in z.namelist() if n.startswith("xl/charts/chart")]
        self.assertTrue(graficos)
        for xml in graficos:
            self.assertNotIn('<c:smooth val="1"', xml)

    def test_injetar_cache_nao_mexe_em_celula_sem_valor_informado(self):
        saida = injetar_cache(self.conteudo, ["Resumo histórico", "Histórico", "Painel financeiro", "Erros e pendências"], {})
        self.assertEqual(saida and load_workbook(io.BytesIO(saida)).sheetnames, load_workbook(io.BytesIO(self.conteudo)).sheetnames)


class ModeloDoProfessorTest(unittest.TestCase):
    """Reproduz os números do relatório-modelo do professor (Jornada_Relatorio_Referencia.pdf, p. 10 e 11).

    Município XYZ anonimizado: base atual R$ 2.119,32 e referência PSPN R$ 2.433,89 (20 h);
    primeira diferença -R$ 314,57 e defasagem de 14,84%. O sentido é atual menos referência
    para a diferença e referência dividida por atual menos um para o percentual.
    """

    def test_primeira_classe_do_nivel_a_bate_com_o_pdf_do_professor(self):
        dados = json.loads((RAIZ / "data/processed/cafezal_do_sul_2026.json").read_text(encoding="utf-8"))
        dados.update(
            municipio="Município XYZ", ano=2025, jornada_semanal=20, piso_nacional_40h=4867.78,
            modo_arredondamento="arredondar", classes=[1, 2],
            progressao_classes_percentual=3.2, progressoes_classes_percentuais=[3.2],
            progressao_classes_uniforme=True,
            niveis=[{"codigo": "A", "descricao": "Magistério", "regra_vertical": {"tipo": "base"}, "valores": [2119.32, 2187.14]}],
        )
        r = analisar_tabela_salarial(dados)
        self.assertEqual(r["tabela_referencia"][0]["valores"][:2], [2433.89, 2511.77])
        self.assertEqual(r["diferencas"][0]["valores"][0], -314.57)
        self.assertEqual(r["defasagens_percentuais"][0]["valores"][0], 14.84)


if __name__ == "__main__":
    unittest.main()
