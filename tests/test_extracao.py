import unittest

from src.extracao.relatorios import (
    extrair_rcl_rreo,
    extrair_resumo_fundeb,
    extrair_resumo_pessoal,
    numero_brasileiro,
)


CSV_RCL = '''Mes1,Mes2,Descricao,Total atualizado,Total anterior
Set/2018,Out/2018,RECEITA CORRENTE LÍQUIDA (III) = (I - II)," 7.361.430.652,73"," 7.267.318.676,66"
'''

CSV_PESSOAL = '''Descricao,Valor,Percentual
,,DESPESA TOTAL COM PESSOAL - DTP (IV),"208.117.992,99","208.293.387,24"
RECEITA CORRENTE LÍQUIDA - RCL (V),"7.361.430.652,73",-
RECEITA CORRENTE LÍQUIDA AJUSTADA - RCL (VI),"7.359.872.310,73",-
DESPESA TOTAL COM PESSOAL - DTP (IV),"2.786.074.714,14","37,85%"
LIMITE MÁXIMO - 54%,"3.974.331.574,04","54%"
LIMITE PRUDENCIAL - 51,3%,"3.775.614.995,33","51,3%"
LIMITE DE ALERTA - 48,6%,"3.576.898.416,64","48,6%"
'''

CSV_FUNDEB_ANTIGO = '''Descrição,Previsão inicial,Previsão atualizada,Receitas realizadas,%
"11- RECEITAS RECEBIDAS DO FUNDEB","604.200.000,00","604.200.000,00","600.162.934,45","99,33%"
"12- RESULTADO LÍQUIDO DAS TRANSFERÊNCIAS DO FUNDEB (11.1 – 10)","274.514.000,00","274.514.000,00","275.212.940,29","100,25%"
'''

CSV_FUNDEB_NOVO = '''Descrição,Previsão atualizada,Receitas realizadas
"6 - RECEITAS RECEBIDAS DO FUNDEB","860.000.000,00","863.804.576,18"
"7 - RESULTADO LÍQUIDO DAS TRANSFERÊNCIAS DO FUNDEB (6.1.1–4)","436.537.200,00","408.889.476,88"
"PERCENTUAL DE APLICAÇÃO EM MDE SOBRE A RECEITA LÍQUIDA DE IMPOSTOS",,"27,35%"
'''


class ExtracaoTestCase(unittest.TestCase):
    def test_converte_numero_brasileiro(self):
        self.assertEqual(numero_brasileiro(" 7.361.430.652,73"), 7361430652.73)
        self.assertEqual(numero_brasileiro("37,85%"), 37.85)
        self.assertEqual(numero_brasileiro("(1.234,50)"), -1234.50)

    def test_extrai_rcl_do_rreo(self):
        self.assertEqual(extrair_rcl_rreo(CSV_RCL), 7361430652.73)

    def test_extrai_resumo_de_pessoal(self):
        resumo = extrair_resumo_pessoal(CSV_PESSOAL)
        self.assertEqual(resumo["rcl_ajustada"], 7359872310.73)
        self.assertEqual(resumo["despesa_total_pessoal"], 2786074714.14)
        self.assertEqual(resumo["percentual_oficial"], 37.85)
        self.assertEqual(resumo["limite_alerta"], 48.6)
        self.assertEqual(resumo["limite_prudencial"], 51.3)
        self.assertEqual(resumo["limite_maximo"], 54.0)

    def test_extrai_fundeb_em_layout_antigo(self):
        resumo = extrair_resumo_fundeb(CSV_FUNDEB_ANTIGO)
        self.assertEqual(resumo["receitas_recebidas"], 600162934.45)
        self.assertEqual(resumo["resultado_liquido_transferencias"], 275212940.29)

    def test_extrai_fundeb_em_layout_novo(self):
        resumo = extrair_resumo_fundeb(CSV_FUNDEB_NOVO)
        self.assertEqual(resumo["receitas_recebidas"], 863804576.18)
        self.assertEqual(resumo["resultado_liquido_transferencias"], 408889476.88)
        self.assertEqual(resumo["percentual_aplicacao_mde"], 27.35)


if __name__ == "__main__":
    unittest.main()
