"""Cada tabela escolhe sua estratégia sem ocultar outras tabelas do documento."""
from .components import ler_componentes
from src.salarial.leitor_geral import ler_matrizes

def ler_tabelas(tabelas, nome, organizar, texto=''):
    dados, pendencias = [], []
    for indice, tabela in enumerate(tabelas, 1):
        local = f'{nome}, bloco {indice}'
        d,p = ler_componentes([tabela], local, organizar, texto)
        if not d and not p:
            d,p = ler_matrizes([tabela], local, organizar, texto)
        dados.extend(d);pendencias.extend(p)
    return dados, pendencias
