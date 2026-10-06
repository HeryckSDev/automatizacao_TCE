import unittest

from src.calculos.indicadores import (
    classificar_percentual,
    diferenca_pontos_percentuais,
    percentual_comprometimento,
    variacao_percentual,
)
from src.modelos.analise import LimitesPessoal


class CalculosTestCase(unittest.TestCase):
    def setUp(self):
        self.limites = LimitesPessoal(alerta=48.6, prudencial=51.3, maximo=54.0)

    def test_percentual_comprometimento(self):
        valor = percentual_comprometimento(2786074714.14, 7359872310.73)
        self.assertAlmostEqual(valor, 37.855, places=3)

    def test_classificacoes(self):
        self.assertEqual(classificar_percentual(37.85, self.limites), "normal")
        self.assertEqual(classificar_percentual(49, self.limites), "alerta")
        self.assertEqual(classificar_percentual(52, self.limites), "prudencial")
        self.assertEqual(classificar_percentual(54, self.limites), "limite_excedido")

    def test_receita_zero_nao_e_aceita(self):
        with self.assertRaises(ValueError):
            percentual_comprometimento(10, 0)

    def test_variacao_percentual(self):
        self.assertAlmostEqual(variacao_percentual(120, 100), 20)
        self.assertAlmostEqual(variacao_percentual(80, 100), -20)
        self.assertIsNone(variacao_percentual(100, 0))
        self.assertIsNone(variacao_percentual(100, None))

    def test_diferenca_em_pontos_percentuais(self):
        self.assertAlmostEqual(diferenca_pontos_percentuais(41.25, 39.5), 1.75)


if __name__ == "__main__":
    unittest.main()
