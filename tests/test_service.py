import tempfile
import unittest
from unittest.mock import Mock

from src.coleta.tce_client import TCEClient, TCEError
from src.persistencia.arquivos import ArquivoBrutoStore
from src.services.analise_service import AnaliseService


def brasileiro(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ClienteFalso:
    chamadas = []

    def coletar_relatorio_csv(
        self, municipio_id, entidade_id, relatorio_id, ano, periodo_id=None
    ):
        self.chamadas.append((relatorio_id, ano, periodo_id))
        fator = 1 if ano == 2019 else 1.1
        rcl = 1000 * fator
        despesa = 400 * fator
        fundeb = 600 * fator
        if relatorio_id == TCEClient.RELATORIO_RCL:
            return (
                "Mes,Descricao,Total atualizado,Total anterior\n"
                f"Dez,RECEITA CORRENTE LÍQUIDA (III),\"{brasileiro(rcl)}\",\"{brasileiro(rcl - 10)}\"\n"
            )
        if relatorio_id == TCEClient.RELATORIO_PESSOAL:
            return (
                "Descricao,Valor,Percentual\n"
                f"RECEITA CORRENTE LÍQUIDA - RCL (V),\"{brasileiro(rcl)}\",-\n"
                f"RECEITA CORRENTE LÍQUIDA AJUSTADA - RCL (VI),\"{brasileiro(rcl)}\",-\n"
                f"DESPESA TOTAL COM PESSOAL - DTP (IV),\"{brasileiro(despesa)}\",\"40,00%\"\n"
                "LIMITE MÁXIMO - 54%,\"540,00\",\"54%\"\n"
                "LIMITE PRUDENCIAL - 51,3%,\"513,00\",\"51,3%\"\n"
                "LIMITE DE ALERTA - 48,6%,\"486,00\",\"48,6%\"\n"
            )
        if relatorio_id == TCEClient.RELATORIO_MDE:
            return (
                "Descricao,Previsto,Realizado\n"
                f"RECEITAS RECEBIDAS DO FUNDEB,\"{brasileiro(fundeb - 5)}\",\"{brasileiro(fundeb)}\"\n"
                f"RESULTADO LÍQUIDO DAS TRANSFERÊNCIAS DO FUNDEB,\"100,00\",\"{brasileiro(200 * fator)}\"\n"
            )
        raise AssertionError("Relatório inesperado")


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        ClienteFalso.chamadas = []

    def test_analise_anual_inclui_fundeb_e_preserva_csv(self):
        with tempfile.TemporaryDirectory() as diretorio:
            servico = AnaliseService(
                ClienteFalso,
                raw_store=ArquivoBrutoStore(diretorio),
                salvar_brutos=True,
            )
            resultado = servico.analisar(
                "1490", "Curitiba", "12268", "Município de Curitiba", 2019
            )
            self.assertEqual(resultado.percentual_calculado, 40)
            self.assertEqual(resultado.fundeb.receitas_recebidas, 600)
            self.assertEqual(ClienteFalso.chamadas[-1], ("15", 2019, "32"))
            arquivos = [p for p in ArquivoBrutoStore(diretorio).diretorio.rglob("*.csv") if p.parent.name != "versoes"]
            self.assertEqual(len(arquivos), 3)

    def test_historico_calcula_evolucao(self):
        servico = AnaliseService(ClienteFalso, salvar_brutos=False)
        historico = servico.analisar_historico(
            "1490", "Curitiba", "12268", "Município de Curitiba", 2019, 2020
        )
        self.assertEqual(len(historico.resultados), 2)
        self.assertAlmostEqual(
            historico.resultados[1].evolucao.rcl_ajustada_percentual, 10
        )
        self.assertAlmostEqual(
            historico.resumo.evolucao_acumulada_receitas_fundeb, 10
        )

    def test_historico_limita_intervalo(self):
        servico = AnaliseService(ClienteFalso, salvar_brutos=False)
        with self.assertRaises(ValueError):
            servico.analisar_historico(
                "1490", "Curitiba", "12268", "Município de Curitiba", 2013, 2025
            )

    def test_historico_sem_resultados_preserva_causas_por_ano(self):
        servico = AnaliseService(ClienteFalso, salvar_brutos=False)
        servico.analisar = Mock(side_effect=[
            TCEError("O TCE-PR respondeu com erro HTTP 500."),
            ValueError("RCL não encontrada no relatório."),
        ])
        with self.assertRaises(TCEError) as contexto:
            servico.analisar_historico(
                "1490", "Curitiba", "12268", "Município de Curitiba", 2019, 2020
            )
        mensagem = str(contexto.exception)
        self.assertIn("2019: O TCE-PR respondeu com erro HTTP 500.", mensagem)
        self.assertIn("2020: RCL não encontrada no relatório.", mensagem)


if __name__ == "__main__":
    unittest.main()
