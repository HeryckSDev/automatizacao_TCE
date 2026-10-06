import unittest
from types import SimpleNamespace

from scripts.tce_cli import resolver_municipio_entidade


class ClienteFalso:
    def listar_municipios(self):
        return [
            {"id": "1490", "nome": "Curitiba"},
            {"id": "290", "nome": "Cafezal do Sul"},
        ]

    def listar_entidades(self, municipio_id):
        if municipio_id == "290":
            return [{"id": "9001", "nome": "Município de Cafezal do Sul"}]
        return [{"id": "12268", "nome": "Município de Curitiba"}]


class TceCliTestCase(unittest.TestCase):
    def test_resolve_municipio_por_nome_sem_acentos(self):
        opcoes = SimpleNamespace(
            municipio="cafezal do sul",
            municipio_id=None,
            entidade=None,
            entidade_id=None,
        )
        resultado = resolver_municipio_entidade(ClienteFalso(), opcoes)
        self.assertEqual(resultado["municipio_id"], "290")
        self.assertEqual(resultado["entidade_id"], "9001")

    def test_aceita_ids_parametrizados(self):
        opcoes = SimpleNamespace(
            municipio="Cafezal do Sul",
            municipio_id="290",
            entidade="Município de Cafezal do Sul",
            entidade_id="9001",
        )
        resultado = resolver_municipio_entidade(ClienteFalso(), opcoes)
        self.assertEqual(resultado["municipio_nome"], "Cafezal do Sul")
        self.assertEqual(resultado["entidade_nome"], "Município de Cafezal do Sul")


if __name__ == "__main__":
    unittest.main()
