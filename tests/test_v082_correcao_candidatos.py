"""Uma tabela inválida não pode derrubar as demais do mesmo documento (achado da revisão da v0.8.2)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.salarial import automacao_service
from src.salarial.automacao_service import AutomacaoSalarial

RAIZ = Path(__file__).resolve().parents[1]


def candidato(nome, a1, b1, vertical=None):
    base = {
        "profissao": nome, "municipio": "Teste", "ano": 2026, "jornada_semanal": 40, "classes": ["1", "2"],
        "niveis": [
            {"codigo": "A", "valores": [a1, round(a1 * 1.02, 2)]},
            {"codigo": "B", "valores": [b1, round(b1 * 1.02, 2)]},
        ],
    }
    if vertical is not None:
        base["niveis"][0]["regra_vertical"] = {"tipo": "base", "valor": 0.0, "nivel_referencia": None}
        base["niveis"][1]["regra_vertical"] = vertical
    return base


class CandidatoInvalidoNaoDerrubaODocumentoTest(unittest.TestCase):
    def preparar(self, candidatos):
        extraido = {"candidatos": candidatos, "pendencias": [], "revisao_obrigatoria": True, "texto_extraido": "", "texto_truncado": False}
        with tempfile.TemporaryDirectory() as pasta, mock.patch.object(automacao_service, "extrair_para_revisao", return_value=extraido):
            return AutomacaoSalarial(RAIZ / "data" / "processed", pasta).preparar("doc.html", b"<html></html>")

    def test_mantem_os_validos_e_registra_o_descartado(self):
        r = self.preparar([candidato("Valida 1", 100.0, 112.0), candidato("Invalida", 100.0, 90.0, {"tipo": "percentual", "valor": -10.0, "nivel_referencia": "A"}), candidato("Valida 2", 200.0, 224.0)])
        self.assertEqual([c["profissao"] for c in r["candidatos"]], ["Valida 1", "Valida 2"])
        self.assertTrue(any("Tabela ignorada (Invalida)" in p and "negativo" in p for p in r["pendencias"]))

    def test_documento_so_com_tabela_invalida_continua_falhando_com_mensagem(self):
        with self.assertRaisesRegex(ValueError, "negativo"):
            self.preparar([candidato("Invalida", 100.0, 90.0, {"tipo": "percentual", "valor": -10.0, "nivel_referencia": "A"})])

    def test_documento_sem_problema_nao_ganha_pendencia_nova(self):
        r = self.preparar([candidato("Valida", 100.0, 112.0)])
        self.assertEqual(r["pendencias"], [])

    def test_ponta_grossa_real_agora_e_preparado(self):
        fonte = RAIZ / "referencias/fontes_salariais_2026_09_07/ponta-grossa.html"
        if not fonte.exists():
            self.skipTest("fonte real ausente")
        with tempfile.TemporaryDirectory() as pasta:
            r = AutomacaoSalarial(RAIZ / "data" / "processed", pasta).preparar("ponta-grossa.html", fonte.read_bytes())
        self.assertEqual(len(r["candidatos"]), 58)
        self.assertTrue(any("Agentes Manut" in p for p in r["pendencias"]))


if __name__ == "__main__":
    unittest.main()
