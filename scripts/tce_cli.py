"""Utilitários de linha de comando para selecionar município e entidade no TCE."""

import argparse
import unicodedata


def _normalizar(texto):
    sem_acentos = unicodedata.normalize("NFKD", str(texto))
    return " ".join(
        "".join(caractere for caractere in sem_acentos if not unicodedata.combining(caractere))
        .casefold()
        .split()
    )


def _localizar(opcoes, nome, tipo):
    procurado = _normalizar(nome)
    exatos = [item for item in opcoes if _normalizar(item.get("nome")) == procurado]
    if len(exatos) == 1:
        return exatos[0]
    parciais = [item for item in opcoes if procurado in _normalizar(item.get("nome"))]
    if len(parciais) == 1:
        return parciais[0]
    sugestoes = ", ".join(item.get("nome", "") for item in parciais[:5])
    complemento = f" Correspondências: {sugestoes}." if sugestoes else ""
    raise ValueError(f"Não foi possível identificar {tipo} '{nome}'.{complemento}")


def adicionar_argumentos_selecao(parser):
    parser.add_argument("--municipio", default="Curitiba", help="Nome do município no TCE-PR")
    parser.add_argument("--municipio-id", help="ID do município; evita a busca pelo nome")
    parser.add_argument("--entidade", help="Nome da entidade; por padrão procura 'Município de ...'")
    parser.add_argument("--entidade-id", help="ID da entidade; evita a busca pelo nome")


def resolver_municipio_entidade(cliente, opcoes):
    municipios = cliente.listar_municipios()
    if opcoes.municipio_id:
        municipio = next(
            (item for item in municipios if str(item.get("id")) == str(opcoes.municipio_id)),
            {"id": str(opcoes.municipio_id), "nome": opcoes.municipio},
        )
    else:
        municipio = _localizar(municipios, opcoes.municipio, "o município")

    entidades = cliente.listar_entidades(str(municipio["id"]))
    if opcoes.entidade_id:
        entidade = next(
            (item for item in entidades if str(item.get("id")) == str(opcoes.entidade_id)),
            {"id": str(opcoes.entidade_id), "nome": opcoes.entidade or "Entidade informada"},
        )
    else:
        nome_entidade = opcoes.entidade or f"Município de {municipio['nome']}"
        try:
            entidade = _localizar(entidades, nome_entidade, "a entidade")
        except ValueError:
            if len(entidades) != 1:
                raise
            entidade = entidades[0]

    return {
        "municipio_id": str(municipio["id"]),
        "municipio_nome": str(municipio["nome"]),
        "entidade_id": str(entidade["id"]),
        "entidade_nome": str(entidade["nome"]),
    }


def parser_com_selecao(descricao):
    parser = argparse.ArgumentParser(description=descricao)
    adicionar_argumentos_selecao(parser)
    return parser
