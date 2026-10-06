import unittest
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from app import create_app
from src.coleta.tce_client import TCEClient, TCEError, TCEConsultaIndisponivel
from src.services.analise_service import AnaliseService


class DisponibilidadeTCETestCase(unittest.TestCase):
    def cliente_simulado(self, opcoes):
        cliente = TCEClient()
        self.addCleanup(cliente.session.close)
        cliente.html_atual = (
            f'<select id="{cliente.SELECT_RELATORIO}">{opcoes}</select>'
        )
        cliente._carregar_pagina = Mock()
        cliente._postback = Mock()
        return cliente

    def test_nao_envia_relatorio_que_entidade_nao_oferece(self):
        casos = [
            ("listar_anos", ("284", "14731"), '<option value="">Nenhum relatório encontrado</option>'),
            ("listar_periodos", ("1467", "9777", "10", 2025), '<option value="20">Pessoal</option>'),
            ("coletar_relatorio_csv", ("1467", "9777", "10", 2025), '<option value="20">Pessoal</option>'),
        ]
        for metodo, argumentos, opcoes in casos:
            with self.subTest(metodo=metodo):
                cliente = self.cliente_simulado(opcoes)
                with self.assertRaises(TCEConsultaIndisponivel):
                    getattr(cliente, metodo)(*argumentos)
                alvos = [chamada.args[0] for chamada in cliente._postback.call_args_list]
                self.assertNotIn(cliente.RELATORIO, alvos)
                self.assertNotIn(cliente.CONSULTAR, alvos)

    def test_relatorio_disponivel_permite_consultar_exercicios(self):
        cliente = self.cliente_simulado('<option value="20">Pessoal</option>')

        def postback(alvo, valores):
            if alvo == cliente.RELATORIO:
                cliente.html_atual = (
                    f'<select id="{cliente.SELECT_ANO}">'
                    '<option value="2025">2025</option></select>'
                )

        cliente._postback.side_effect = postback
        self.assertEqual(cliente.listar_anos("1", "2"), [{"id": "2025", "nome": "2025"}])

    def test_resposta_sem_catalogo_nao_e_classificada_como_entidade_sem_relatorio(self):
        cliente = self.cliente_simulado("")
        cliente.html_atual = "<html>Página inesperada</html>"
        with self.assertRaises(TCEError) as contexto:
            cliente.listar_anos("1", "2")
        self.assertNotIsInstance(contexto.exception, TCEConsultaIndisponivel)
        self.assertIn("identificar o catálogo", str(contexto.exception))

    def test_catalogo_prioriza_municipio_sem_remover_as_demais_entidades(self):
        with TemporaryDirectory() as tmp:
            client = create_app(dossie_diretorio=tmp).test_client()
            for nome in ("MUNICÍPIO DE TESTE", "Prefeitura Municipal de Teste"):
                with self.subTest(nome=nome):
                    entidades = (("1", "AUTARQUIA DE TESTE"), ("2", "CÂMARA DE TESTE"), ("3", nome))
                    with patch("app._entidades_tce", return_value=entidades):
                        resposta = client.get("/api/entidades/999")
                    self.assertEqual(resposta.status_code, 200)
                    self.assertEqual([e["id"] for e in resposta.json], ["3", "1", "2"])

    def test_api_informa_indisponibilidade_sem_rotular_como_falha_502(self):
        with TemporaryDirectory() as tmp:
            app = create_app(dossie_diretorio=tmp)
            mensagem = "A entidade não oferece o relatório requerido."
            with patch("app._anos_tce", side_effect=TCEConsultaIndisponivel(mensagem)):
                with self.assertLogs(app.logger, level="WARNING"):
                    resposta = app.test_client().get("/api/anos/284/14731")
            self.assertEqual(resposta.status_code, 422)
            self.assertEqual(resposta.json["tipo"], "relatorio_indisponivel")
            self.assertEqual(resposta.json["erro"], mensagem)

    def test_historico_interrompe_se_relatorio_inexistente_para_entidade(self):
        servico = AnaliseService(salvar_brutos=False)
        servico.analisar = Mock(side_effect=TCEConsultaIndisponivel("Relatório não oferecido."))
        with self.assertRaises(TCEConsultaIndisponivel):
            servico.analisar_historico("1", "Teste", "2", "Câmara", 2019, 2025)
        self.assertEqual(servico.analisar.call_count, 1)


if __name__ == "__main__":
    unittest.main()
