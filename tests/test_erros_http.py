import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import create_app
from src.coleta.tce_client import TCEError


class ErrosHTTPTestCase(unittest.TestCase):
    def setUp(self):
        self.diretorio = TemporaryDirectory()
        self.addCleanup(self.diretorio.cleanup)
        self.app = create_app(dossie_diretorio=self.diretorio.name)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_url_ausente_mantem_404_sem_traceback_de_erro_interno(self):
        for caminho in ("/pagina-inexistente", "/api/rota-inexistente", "/static/arquivo-inexistente.css"):
            with self.subTest(caminho=caminho):
                with self.assertNoLogs(self.app.logger, level="ERROR"):
                    resposta = self.client.get(caminho)
                self.assertEqual(resposta.status_code, 404)
                self.assertEqual(resposta.json["codigo"], 404)
                self.assertEqual(resposta.json["caminho"], caminho)
                self.assertEqual(resposta.json["metodo"], "GET")

    def test_metodo_incorreto_mantem_405_e_allow(self):
        with self.assertNoLogs(self.app.logger, level="ERROR"):
            resposta = self.client.get("/api/analisar")
        self.assertEqual(resposta.status_code, 405)
        self.assertIn("POST", resposta.headers["Allow"])
        self.assertEqual(resposta.json["codigo"], 405)

    def test_upload_grande_preserva_tratamento_especifico(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 32
        resposta = self.client.post("/api/analisar", json={"conteudo": "x" * 100})
        self.assertEqual(resposta.status_code, 413)
        self.assertEqual(resposta.json["tipo"], "validacao")
        self.assertIn("48 MB", resposta.json["erro"])

    def test_falha_interna_continua_500_e_registrada(self):
        def falhar():
            raise RuntimeError("detalhe interno de teste")

        self.app.add_url_rule("/teste-falha-interna", view_func=falhar)
        with self.assertLogs(self.app.logger, level="ERROR") as logs:
            resposta = self.client.get("/teste-falha-interna")
        self.assertEqual(resposta.status_code, 500)
        self.assertNotIn("detalhe interno", resposta.get_data(as_text=True))
        self.assertIn("GET /teste-falha-interna", "\n".join(logs.output))
        self.assertIn("RuntimeError", "\n".join(logs.output))

    def test_502_preserva_motivo_e_identifica_rota_no_terminal(self):
        mensagem = "O TCE-PR respondeu com erro HTTP 500."
        with patch("app._anos_tce", side_effect=TCEError(mensagem)):
            with self.assertLogs(self.app.logger, level="WARNING") as logs:
                resposta = self.client.get("/api/anos/284/14731")
        self.assertEqual(resposta.status_code, 502)
        self.assertEqual(resposta.json["erro"], mensagem)
        self.assertEqual(resposta.json["caminho"], "/api/anos/284/14731")
        self.assertIn(mensagem, "\n".join(logs.output))
        self.assertIn("GET /api/anos/284/14731", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
