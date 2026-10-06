"""v0.8.3: escolha de tabelas legível, reaproveitamento de leitura e piso salarial com dois níveis lado a lado."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.salarial import automacao_service
from src.salarial.automacao_service import AutomacaoSalarial, VERSAO_EXTRACAO, descrever_candidato
from src.salarial.tabelas_coordenadas import separar_colunas

RAIZ = Path(__file__).resolve().parents[1]
FONTES = RAIZ / "referencias/fontes_salariais_2026_09_07"


def candidato(**extra):
    base = {"niveis": [{"codigo": "I", "valores": [2180.44, 2241.49]}, {"codigo": "II", "valores": [2507.51, 2577.72]}],
            "classes": ["I", "II"], "jornada_semanal": 40.0}
    base.update(extra)
    return base


class DescreverCandidatoTest(unittest.TestCase):
    def test_titulo_porte_e_valor_inicial_em_formato_brasileiro(self):
        e = descrever_candidato(candidato(lei="Anexo B1 — parte permanente", grupo="Grupo Básico"), 0)
        self.assertEqual(e["titulo"], "Anexo B1 — parte permanente")
        self.assertEqual(e["grupo"], "Grupo Básico")
        self.assertEqual(e["detalhe"], "2 níveis × 2 classes · a partir de R$ 2.180,44 · 40 h/semana")

    def test_singular_para_um_nivel(self):
        e = descrever_candidato(candidato(niveis=[{"codigo": "ESPECIAL", "valores": [2076.61]}], lei="Anexo B1 — parte especial"), 1)
        self.assertTrue(e["detalhe"].startswith("1 nível × 1 classes"))

    def test_nao_repete_texto_quando_profissao_ja_esta_na_lei(self):
        e = descrever_candidato(candidato(profissao="PROFESSOR - CLASSE A - 20 HORAS", lei="TABELA 11: PROFESSOR - CLASSE A - 20 HORAS"), 0)
        self.assertEqual(e["titulo"], "TABELA 11: PROFESSOR - CLASSE A - 20 HORAS")

    def test_junta_profissao_e_lei_quando_sao_diferentes(self):
        e = descrever_candidato(candidato(profissao="Agente Comunitário de Saúde", lei="Anexo TABELA"), 0)
        self.assertEqual(e["titulo"], "Agente Comunitário de Saúde · Anexo TABELA")

    def test_sem_nenhum_nome_usa_a_fonte_ou_a_posicao(self):
        self.assertEqual(descrever_candidato(candidato(arquivo_fonte="x.pdf, página 3, Anexo B2"), 0)["titulo"], "página 3, Anexo B2")
        self.assertEqual(descrever_candidato(candidato(), 4)["titulo"], "Tabela 5")
        self.assertEqual(descrever_candidato(candidato(), 0)["grupo"], "Outras tabelas")


class SepararColunasTest(unittest.TestCase):
    def test_divide_dois_niveis_lado_a_lado(self):
        t = [["Parte Permanente\nNível I", None, None, "Parte Permanente\nNível II", None], ["Padrão 4113", None, None, "Padrão 4114", None],
             ["Referência", "Valor", None, "Referência", "Valor"], ["I", "R$ 3.242,00", None, "I", "R$ 3.728,30"], ["II", "R$ 3.332,78", "2,8%", "II", "R$ 3.832,69"]]
        a, b = separar_colunas(t)
        self.assertEqual(a[3], ["I", "R$ 3.242,00"])
        self.assertEqual(b[4], ["II", "R$ 3.832,69"])
        self.assertIn("Nível II", b[0][0])

    def test_tabela_de_duas_colunas_nao_muda(self):
        t = [["Referência", "Valor"], ["I", "R$ 1,00"]]
        self.assertEqual(separar_colunas(t), [t])

    def test_cinco_colunas_sem_o_cabecalho_esperado_nao_e_dividida(self):
        t = [["a", "b", "c", "d", "e"], ["1", "2", "3", "4", "5"]]
        self.assertEqual(separar_colunas(t), [t])


class ReaproveitarLeituraTest(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.chamadas = 0

        def extrair(nome, conteudo):
            self.chamadas += 1
            return {"candidatos": [candidato(lei="Anexo B1 — parte permanente")], "pendencias": [], "revisao_obrigatoria": True,
                    "texto_extraido": "", "texto_truncado": False}

        patcher = mock.patch.object(automacao_service, "extrair_para_revisao", side_effect=extrair)
        patcher.start(); self.addCleanup(patcher.stop)
        self.servico = AutomacaoSalarial(RAIZ / "data" / "processed", self.pasta.name)

    def test_mesmo_arquivo_nao_e_lido_duas_vezes(self):
        a = self.servico.preparar("t.html", b"<html>1</html>")
        b = self.servico.preparar("t.html", b"<html>1</html>")
        self.assertEqual(self.chamadas, 1)
        self.assertEqual(a["preparacao_id"], b["preparacao_id"])
        self.assertTrue(b["reaproveitada"])
        self.assertNotIn("sha256", b)
        self.assertEqual(b["candidatos"][0]["exibicao"]["titulo"], "Anexo B1 — parte permanente")

    def test_arquivo_diferente_e_lido_de_novo(self):
        self.servico.preparar("t.html", b"<html>1</html>")
        self.servico.preparar("t.html", b"<html>2</html>")
        self.assertEqual(self.chamadas, 2)

    def test_versao_antiga_da_leitura_nao_e_reaproveitada(self):
        a = self.servico.preparar("t.html", b"<html>1</html>")
        arquivo = Path(self.pasta.name) / "documentos" / a["preparacao_id"] / "preparacao.json"
        dados = json.loads(arquivo.read_text(encoding="utf-8")); dados["versao_extracao"] = "0.0.1"
        arquivo.write_text(json.dumps(dados), encoding="utf-8")
        self.servico.preparar("t.html", b"<html>1</html>")
        self.assertEqual(self.chamadas, 2)

    def test_preparacao_reaproveitada_gera_excel_normalmente(self):
        self.servico.preparar("t.html", b"<html>1</html>")
        b = self.servico.preparar("t.html", b"<html>1</html>")
        dados = self.servico.dados_preparados(b["preparacao_id"], 0, True)
        self.assertEqual(dados["niveis"][0]["codigo"], "I")
        self.assertTrue(VERSAO_EXTRACAO)


@unittest.skipUnless(os.environ.get("TESTES_LENTOS") == "1" and (FONTES / "curitiba.pdf").exists(), "defina TESTES_LENTOS=1 (leva cerca de 25 s)")
class CuritibaRealTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.salarial.revisao_service import extrair_para_revisao
        cls.r = extrair_para_revisao("curitiba.pdf", (FONTES / "curitiba.pdf").read_bytes())

    def test_tabelas_com_titulos_distintos(self):
        c = self.r["candidatos"]
        self.assertEqual(len(c), 68)
        rotulos = {(x.get("grupo"), x.get("profissao"), x["lei"], x["niveis"][0]["valores"][0]) for x in c}
        self.assertEqual(len(rotulos), 68)

    def test_pisos_de_agentes_de_saude_tem_os_tres_niveis(self):
        pisos = [x for x in self.r["candidatos"] if x.get("grupo") == "Piso salarial"]
        self.assertEqual(len(pisos), 2)
        for x in pisos:
            self.assertEqual([n["codigo"] for n in x["niveis"]], ["I", "II", "III"])
            self.assertEqual([n["valores"][0] for n in x["niveis"]], [3242.0, 3728.3, 4287.55])
            self.assertTrue(all(len(n["valores"]) == 36 for n in x["niveis"]))


if __name__ == "__main__":
    unittest.main()
