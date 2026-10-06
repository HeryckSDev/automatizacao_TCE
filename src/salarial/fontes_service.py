"""Catálogo inicial de pontos oficiais para obter documentos salariais.

As páginas abaixo são pontos de partida, não uma promessa de que o primeiro
arquivo exibido esteja vigente. A conferência de competência, jornada e ato
legal continua sendo parte obrigatória do dossiê municipal.
"""


FONTES_SALARIAIS = (
    {
        "id": "cafezal-do-sul-pr",
        "municipio": "Cafezal do Sul",
        "uf": "PR",
        "tipo_fonte": "legislacao_municipal",
        "pagina_oficial": "https://www.cafezaldosul.pr.gov.br/index.php?novo_cliente=12145&pagina=20&sessao=b054603368xsb0",
        "orientacao": "Pesquisar o plano da profissão escolhida e o ato mais recente que altera sua tabela salarial.",
        "formatos_observados": ["página de legislação", "DOC/PDF em anexos"],
        "observacao": "O Anexo A de 2026 recebido do professor é a referência de layout, não um padrão universal.",
    },
    {
        "id": "curitiba-pr",
        "municipio": "Curitiba",
        "uf": "PR",
        "tipo_fonte": "portal_transparencia",
        "pagina_oficial": "https://www.transparencia.curitiba.pr.gov.br/conteudo/gestaodepessoal.aspx",
        "orientacao": "Abrir Tabela Salarial, escolher o ano e localizar a profissão ou cargo escolhido no compilado.",
        "formatos_observados": ["PDF compilado por ano"],
        "observacao": "Um único PDF pode reunir dezenas de carreiras e mais de uma parte da tabela.",
    },
    {
        "id": "londrina-pr",
        "municipio": "Londrina",
        "uf": "PR",
        "tipo_fonte": "recursos_humanos",
        "pagina_oficial": "https://portal.londrina.pr.gov.br/menu-oculto-recursos-humanos/legislacao-rh-portal-servidor/plano-de-cargos-carreiras-e-salarios-do-magisterio-publico-municipal-do-poder-executivo-do-municipio-de-londrina",
        "orientacao": "Baixar o Anexo III de vencimentos e conferir na página de Pessoal a revisão anual mais recente.",
        "formatos_observados": ["PDF por anexo", "página de revisão anual"],
        "observacao": "A carreira usa muitas referências e não tem a mesma matriz de Cafezal do Sul.",
    },
    {
        "id": "maringa-pr",
        "municipio": "Maringá",
        "uf": "PR",
        "tipo_fonte": "portal_transparencia",
        "pagina_oficial": "https://transparencia.maringa.pr.gov.br/portaltransparencia/1/publicacoes/4383",
        "orientacao": "Localizar a tabela do Quadro Geral ou do Magistério, conforme o cargo, e baixar o documento da competência desejada.",
        "formatos_observados": ["PDF", "DOCX", "portal com JavaScript"],
        "observacao": "A página pode exigir JavaScript; registre a URL do arquivo e a data da consulta.",
    },
    {
        "id": "ponta-grossa-pr",
        "municipio": "Ponta Grossa",
        "uf": "PR",
        "tipo_fonte": "portal_servidor",
        "pagina_oficial": "https://rh.pontagrossa.pr.gov.br/estatisticas/salarios",
        "orientacao": "Identificar no quadro web os códigos ligados ao cargo escolhido e salvar a página oficial como HTML/PDF.",
        "formatos_observados": ["tabela HTML"],
        "observacao": "A fonte organiza classe, nível e valor em linhas, em vez de uma matriz como Cafezal.",
    },
    {
        "id": "siqueira-campos-pr",
        "municipio": "Siqueira Campos",
        "uf": "PR",
        "tipo_fonte": "pagina_educacao",
        "pagina_oficial": "https://siqueiracampos.pr.gov.br/pagina/37/educacao/sub-pagina/48/",
        "orientacao": "Baixar a tabela e o Estatuto do Magistério; confirmar se há publicação posterior à exibida na página.",
        "formatos_observados": ["documentos anexos em página municipal"],
        "observacao": "É uma fonte útil para amostragem, mas a vigência do documento deve ser confirmada.",
    },
)


def listar_fontes_salariais():
    """Retorna cópias serializáveis para impedir alteração do catálogo global."""

    return [
        {
            **fonte,
            "formatos_observados": list(fonte["formatos_observados"]),
            "ultima_verificacao": "2026-08-31",
            "coleta_automatica": False,
        }
        for fonte in FONTES_SALARIAIS
    ]
