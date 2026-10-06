"""Cria respostas reais das rotas para os testes de interação com DOM simulado."""
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from app import create_app


def preparar(destino):
    raiz = Path(__file__).resolve().parents[1]
    with TemporaryDirectory() as temp:
        client = create_app(dossie_diretorio=temp).test_client()
        def post(url, **kwargs):
            resposta = client.post(url, **kwargs)
            assert resposta.status_code == 200, resposta.json
            return resposta.json
        csv = (raiz / 'data/modelos/curitiba_administrativo_2026.csv').read_bytes()
        longo = post('/api/automacao/preparar-tabela', data={'arquivo': (BytesIO(csv), 'curitiba.csv')})
        matriz = post('/api/automacao/preparar-tabela', data={'arquivo': (BytesIO(b'Nivel;1;2\nA;2000;2100\n'), 'matriz.csv')})
        catalogo = client.get('/api/automacao/tabelas').json
        salvo = post('/api/automacao/salarios', json={'preparacao_id': longo['preparacao_id'], 'comparacao': {'tipo': 'percentual', 'valor': 5}})
        fixtures = {'html': client.get('/').get_data(as_text=True),
                    'javascript': (raiz / 'static/js/simples.js').read_text(encoding='utf-8'),
                    'tabelas': catalogo, 'longo': longo, 'matriz': matriz, 'salvo': salvo,
                    'financeiro': client.get('/api/automacao/exemplo-financeiro').json,
                    'salarios': post('/api/automacao/salarios', json={'tabela_id': 'cafezal-2026'})}
    Path(destino).write_text(json.dumps(fixtures, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    preparar(sys.argv[1])
