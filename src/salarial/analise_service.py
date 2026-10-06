"""Regras auditáveis para comparar uma tabela salarial com o PSPN."""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
from zoneinfo import ZoneInfo


CENTAVO = Decimal("0.01")
MODOS_ARREDONDAMENTO = {
    "truncar": ROUND_DOWN,
    "arredondar": ROUND_HALF_UP,
}
TIPOS_REGRA_VERTICAL = {"base", "percentual", "valor_fixo"}


def _decimal(valor, nome):
    if isinstance(valor, bool) or valor is None:
        raise ValueError(f"{nome} deve ser numérico.")
    texto = str(valor).strip().replace("R$", "").replace("%", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    if texto.startswith("(") and texto.endswith(")"):
        texto = f"-{texto[1:-1]}"
    try:
        numero = Decimal(texto)
        if not numero.is_finite():
            raise ValueError(f"{nome} deve ser finito.")
        return numero
    except InvalidOperation as erro:
        raise ValueError(f"{nome} deve ser numérico.") from erro


def _centavos(valor, modo):
    return valor.quantize(CENTAVO, rounding=MODOS_ARREDONDAMENTO[modo])


def _float(valor, casas=2):
    if valor is None:
        return None
    quantizador = Decimal("1").scaleb(-casas)
    return float(valor.quantize(quantizador, rounding=ROUND_HALF_UP))


def _normalizar_regra_vertical(nivel, indice, codigo_base, codigos_anteriores):
    if indice == 1:
        return {"tipo": "base", "valor": Decimal("0"), "nivel_referencia": None}

    regra_informada = nivel.get("regra_vertical")
    if isinstance(regra_informada, dict):
        tipo = str(regra_informada.get("tipo", "percentual")).strip().lower()
        valor_bruto = regra_informada.get("valor", 0)
        referencia = str(
            regra_informada.get("nivel_referencia") or codigo_base
        ).strip().upper()
    elif str(nivel.get("acrescimo_tipo", "")).strip().lower() == "valor_fixo" or nivel.get(
        "acrescimo_valor_fixo"
    ) not in (None, ""):
        tipo = "valor_fixo"
        valor_bruto = nivel.get("acrescimo_valor_fixo", nivel.get("acrescimo_valor", 0))
        referencia = str(nivel.get("nivel_referencia") or codigo_base).strip().upper()
    else:
        tipo = "percentual"
        valor_bruto = nivel.get("acrescimo_percentual", 0)
        referencia = str(nivel.get("nivel_referencia") or codigo_base).strip().upper()

    if tipo not in TIPOS_REGRA_VERTICAL - {"base"}:
        raise ValueError("A regra vertical deve ser 'percentual' ou 'valor_fixo'.")
    valor = _decimal(valor_bruto, f"Regra vertical do nível {nivel.get('codigo', indice)}")
    if valor < 0:
        raise ValueError("A regra vertical não pode possuir acréscimo negativo.")
    if tipo == "percentual" and valor > 100:
        raise ValueError("O acréscimo percentual entre níveis deve estar entre 0% e 100%.")
    if referencia not in codigos_anteriores:
        raise ValueError(
            f"O nível {nivel.get('codigo', indice)} referencia um nível inexistente ou posterior."
        )
    return {"tipo": tipo, "valor": valor, "nivel_referencia": referencia}


def _validar_niveis(niveis):
    if not isinstance(niveis, list) or not niveis:
        raise ValueError("Informe ao menos um nível salarial.")

    normalizados = []
    quantidade_classes = None
    codigos = set()
    for indice, nivel in enumerate(niveis, start=1):
        if not isinstance(nivel, dict):
            raise ValueError(f"O nível {indice} possui formato inválido.")
        codigo = str(nivel.get("codigo", "")).strip().upper()
        descricao = str(nivel.get("descricao", "")).strip()
        if not codigo or codigo in codigos:
            raise ValueError("Cada nível deve possuir um código único.")
        codigos.add(codigo)
        valores = nivel.get("valores")
        if not isinstance(valores, list) or not valores:
            raise ValueError(f"O nível {codigo} não possui classes salariais.")
        if quantidade_classes is None:
            quantidade_classes = len(valores)
        elif len(valores) != quantidade_classes:
            raise ValueError("Todos os níveis devem possuir a mesma quantidade de classes.")
        valores_decimais = []
        for classe, valor in enumerate(valores, start=1):
            convertido = _decimal(valor, f"Valor do nível {codigo}, classe {classe}")
            if convertido <= 0:
                raise ValueError("Os vencimentos devem ser maiores que zero.")
            valores_decimais.append(convertido.quantize(CENTAVO, rounding=ROUND_HALF_UP))
        codigo_base = normalizados[0]["codigo"] if normalizados else codigo
        regra = _normalizar_regra_vertical(
            nivel,
            indice,
            codigo_base,
            {item["codigo"] for item in normalizados},
        )
        normalizados.append(
            {
                "codigo": codigo,
                "descricao": descricao or f"Nível {codigo}",
                "regra_vertical": regra,
                "acrescimo_percentual": (
                    regra["valor"] if regra["tipo"] in {"base", "percentual"} else None
                ),
                "acrescimo_valor_fixo": (
                    regra["valor"] if regra["tipo"] == "valor_fixo" else None
                ),
                "valores": valores_decimais,
            }
        )
    return normalizados, quantidade_classes


def _normalizar_progressoes(dados, quantidade_classes):
    quantidade_transicoes = max(quantidade_classes - 1, 0)
    lista_informada = dados.get("progressoes_classes_percentuais")
    if lista_informada is not None:
        if not isinstance(lista_informada, (list, tuple)):
            raise ValueError("As progressões por classe devem ser informadas em uma lista.")
        if len(lista_informada) != quantidade_transicoes:
            raise ValueError(
                "A lista de progressões deve possuir exatamente "
                f"{quantidade_transicoes} valor(es), um para cada transição de classe."
            )
        progressoes = [
            _decimal(valor, f"Progressão da transição {indice} para {indice + 1}")
            for indice, valor in enumerate(lista_informada, start=1)
        ]
    elif quantidade_transicoes == 0:
        progressoes = []
    else:
        progressao = _decimal(
            dados.get("progressao_classes_percentual"), "Progressão entre classes"
        )
        progressoes = [progressao] * quantidade_transicoes

    if any(valor < 0 or valor > 100 for valor in progressoes):
        raise ValueError("Cada progressão entre classes deve estar entre 0% e 100%.")
    uniforme = not progressoes or all(valor == progressoes[0] for valor in progressoes)
    progressao_uniforme = progressoes[0] if uniforme and progressoes else Decimal("0")
    return progressoes, progressao_uniforme, uniforme


def _aplicar_regra_vertical(valor_referencia, regra, modo):
    if regra["tipo"] == "percentual":
        fator = Decimal("1") + regra["valor"] / Decimal("100")
        return _centavos(valor_referencia * fator, modo)
    if regra["tipo"] == "valor_fixo":
        return _centavos(valor_referencia + regra["valor"], modo)
    return _centavos(valor_referencia, modo)


def _tabela_referencia(piso_40h, jornada, progressoes, niveis, modo, jornada_referencia=Decimal("40")):
    base_exata = piso_40h * jornada / jornada_referencia
    base = _centavos(base_exata, modo)

    referencia = []
    por_codigo = {}
    for indice, nivel in enumerate(niveis):
        if indice == 0:
            primeiro_valor = base
        else:
            regra = nivel["regra_vertical"]
            nivel_referencia = por_codigo[regra["nivel_referencia"]]
            primeiro_valor = _aplicar_regra_vertical(
                nivel_referencia["valores"][0], regra, modo
            )
        valores = [primeiro_valor]
        for progressao in progressoes:
            fator_progressao = Decimal("1") + progressao / Decimal("100")
            valores.append(_centavos(valores[-1] * fator_progressao, modo))
        item = {**nivel, "valores": valores}
        referencia.append(item)
        por_codigo[nivel["codigo"]] = item
    return base_exata, referencia


def _inconsistencias_estrutura(niveis, progressoes, modo):
    inconsistencias = []
    tolerancia = Decimal("0.01")
    for nivel in niveis:
        for indice in range(1, len(nivel["valores"])):
            progressao = progressoes[indice - 1]
            fator_progressao = Decimal("1") + progressao / Decimal("100")
            esperado = _centavos(nivel["valores"][indice - 1] * fator_progressao, modo)
            atual = nivel["valores"][indice]
            if abs(atual - esperado) > tolerancia:
                inconsistencias.append(
                    {
                        "tipo": "progressao_horizontal",
                        "nivel": nivel["codigo"],
                        "classe": indice + 1,
                        "atual": _float(atual),
                        "esperado": _float(esperado),
                        "diferenca": _float(atual - esperado),
                        "progressao_percentual": _float(progressao, 4),
                    }
                )

    por_codigo = {nivel["codigo"]: nivel for nivel in niveis}
    for nivel in niveis[1:]:
        regra = nivel["regra_vertical"]
        referencia = por_codigo[regra["nivel_referencia"]]["valores"][0]
        atual = nivel["valores"][0]
        esperado = _aplicar_regra_vertical(referencia, regra, modo)
        if abs(atual - esperado) > tolerancia:
            inconsistencias.append(
                {
                    "tipo": "progressao_vertical",
                    "nivel": nivel["codigo"],
                    "classe": 1,
                    "atual": _float(atual),
                    "esperado": _float(esperado),
                    "diferenca": _float(atual - esperado),
                    "regra_vertical": _serializar_regra(regra),
                }
            )
    return inconsistencias


def _serializar_regra(regra):
    return {
        "tipo": regra["tipo"],
        "valor": _float(regra["valor"], 4),
        "nivel_referencia": regra["nivel_referencia"],
    }


def _serializar_tabela(tabela):
    return [
        {
            "codigo": nivel["codigo"],
            "descricao": nivel["descricao"],
            "acrescimo_percentual": _float(nivel["acrescimo_percentual"], 4),
            "acrescimo_valor_fixo": _float(nivel["acrescimo_valor_fixo"]),
            "regra_vertical": _serializar_regra(nivel["regra_vertical"]),
            "valores": [_float(valor) for valor in nivel["valores"]],
        }
        for nivel in tabela
    ]


def analisar_tabela_salarial(dados):
    """Compara a tabela informada com uma referência calculada a partir do PSPN.

    O primeiro nível é tratado como base da carreira. As transições de classe
    podem ter percentuais uniformes ou diferentes, e as regras entre níveis
    podem usar percentual ou acréscimo fixo em reais.
    """

    if not isinstance(dados, dict):
        raise ValueError("Os dados salariais possuem formato inválido.")

    ano_informado = str(dados.get("ano") if dados.get("ano") is not None else "").strip()
    if ano_informado and (not ano_informado.isdigit() or not 2000 <= int(ano_informado) <= 2100):
        # ano ausente continua tolerado (fixtures e importação sem ano); ano preenchido errado não.
        raise ValueError("Informe o ano da tabela com quatro dígitos (entre 2000 e 2100).")

    modo = str(dados.get("modo_arredondamento", "arredondar")).strip().lower()
    if modo not in MODOS_ARREDONDAMENTO:
        raise ValueError("O modo de arredondamento deve ser 'truncar' ou 'arredondar'.")

    profissao = str(dados.get("profissao") or "Magistério").strip()
    ref = dados.get("referencia")
    if ref is not None and not isinstance(ref, dict):
        raise ValueError("A referência salarial deve ser um objeto.")
    if ref is None:
        if profissao.casefold() not in {"magistério", "magisterio", "professor", "professora", "professor/a"}:
            raise ValueError("Informe a referência específica da profissão; o PSPN é exclusivo do magistério.")
        ref = {"tipo": "pspn", "nome": f"PSPN {dados.get('ano', '')}",
               "valor": dados.get("piso_nacional_40h"), "jornada": 40,
               "proporcional": True, "fonte": dados.get("fonte_piso", "Não informada"),
               "url": dados.get("url_fonte_piso", ""), "ano": dados.get("ano")}
    if ref.get("tipo") not in {"pspn", "piso_profissional", "consultoria", "cenario"}:
        raise ValueError("Selecione PSPN, piso profissional, consultoria ou cenário.")
    if ref.get("tipo") == "pspn" and not any(x in profissao.casefold() for x in ("professor", "magist")):
        raise ValueError("O PSPN não pode ser aplicado a esta profissão.")
    if not str(ref.get("nome", "")).strip() or not str(ref.get("fonte", "")).strip():
        raise ValueError("Informe o nome e a fonte da referência.")
    if str(ref.get("ano")) != str(dados.get("ano")):
        raise ValueError("O ano da referência deve coincidir com o ano analisado.")
    piso_40h = _decimal(ref.get("valor"), "Valor de referência")
    jornada = _decimal(dados.get("jornada_semanal"), "Jornada semanal")
    jornada_referencia = _decimal(ref.get("jornada"), "Jornada da referência")
    if jornada_referencia <= 0 or jornada_referencia > 60:
        raise ValueError("A jornada da referência deve estar entre 1 e 60 horas.")
    proporcional = ref.get("proporcional") is True
    if not proporcional and jornada != jornada_referencia:
        raise ValueError("Jornadas diferentes: informe a referência para a jornada do cargo ou habilite a proporcionalidade expressamente.")
    if ref.get("tipo") == "pspn" and jornada_referencia != 40:
        raise ValueError("O PSPN nacional deve ser informado para 40 horas.")
    if piso_40h <= 0:
        raise ValueError("A referência deve ser maior que zero.")
    if jornada <= 0 or jornada > 60:
        raise ValueError("A jornada semanal deve estar entre 1 e 60 horas.")

    niveis, quantidade_classes = _validar_niveis(dados.get("niveis"))
    progressoes, progressao_uniforme, uniforme = _normalizar_progressoes(
        dados, quantidade_classes
    )
    base_exata, referencia = _tabela_referencia(
        piso_40h, jornada, progressoes, niveis, modo, jornada_referencia
    )

    diferencas = []
    defasagens = []
    celulas_abaixo = 0
    maior_defasagem = Decimal("0")
    for atual, esperado in zip(niveis, referencia):
        diferencas_nivel = []
        defasagens_nivel = []
        for valor_atual, valor_referencia in zip(atual["valores"], esperado["valores"]):
            diferenca = valor_atual - valor_referencia
            defasagem = (valor_referencia / valor_atual - Decimal("1")) * Decimal("100")
            diferencas_nivel.append(diferenca)
            defasagens_nivel.append(defasagem)
            if diferenca < 0:
                celulas_abaixo += 1
            maior_defasagem = max(maior_defasagem, defasagem)
        diferencas.append({**atual, "valores": diferencas_nivel})
        defasagens.append({**atual, "valores": defasagens_nivel})

    atual_inicial = niveis[0]["valores"][0]
    referencia_inicial = referencia[0]["valores"][0]
    diferenca_inicial = atual_inicial - referencia_inicial
    defasagem_inicial = (referencia_inicial / atual_inicial - Decimal("1")) * Decimal("100")
    total_celulas = len(niveis) * quantidade_classes
    inconsistencias = _inconsistencias_estrutura(niveis, progressoes, modo)

    avisos_importacao = [str(aviso) for aviso in dados.get("avisos_importacao") or []]
    avisos = list(avisos_importacao)
    if modo == "truncar":
        avisos.append(
            "O truncamento foi aplicado em cada etapa para reproduzir o anexo municipal; "
            "confirme essa regra com o responsável antes de emitir parecer."
        )
    else:
        avisos.append(
            "O arredondamento comercial foi aplicado em cada etapa; ele pode divergir em "
            "centavos de tabelas municipais que usam truncamento."
        )
    if dados.get("jornada_confirmada_no_documento") is not True:
        avisos.append(
            "A carga horária não está declarada no anexo analisado; a jornada informada deve "
            "ser confirmada na lei completa."
        )
    origem_progressao = str(
        dados.get("progressao_classes_origem", "informada")
    ).strip().lower()
    if origem_progressao == "inferida" and not any(
        "progressões entre classes foram inferidas" in aviso for aviso in avisos
    ):
        avisos.append(
            "As progressões entre classes foram inferidas matematicamente; confirme cada "
            "percentual na lei municipal."
        )
    if not uniforme:
        lista = ", ".join(f"{_float(valor, 4):g}%" for valor in progressoes)
        avisos.append(
            f"A carreira utiliza progressão horizontal não uniforme ({lista}); "
            "cada transição foi validada separadamente."
        )
    if any(nivel["regra_vertical"]["tipo"] == "valor_fixo" for nivel in niveis[1:]):
        avisos.append(
            "Há acréscimo vertical em valor fixo; o cálculo aplicou o valor em reais "
            "ao nível de referência indicado."
        )
    if inconsistencias:
        avisos.append(
            f"Foram encontradas {len(inconsistencias)} divergência(s) em relação às regras "
            "de progressão informadas ou extraídas."
        )
    if ref["tipo"] in {"consultoria", "cenario"}:
        avisos.append("Referência de consultoria/cenário: diferenças não representam descumprimento de piso legal.")
    avisos.append("A referência aplica as regras de carreira informadas; divergências numéricas não constituem parecer jurídico.")

    horario_brasilia = datetime.now(ZoneInfo("America/Sao_Paulo"))
    classes = dados.get("classes") or list(range(1, quantidade_classes + 1))
    if not isinstance(classes, list) or len(classes) != quantidade_classes or len(set(map(str, classes))) != len(classes):
        raise ValueError("Informe um rótulo único para cada classe.")

    return {
        "municipio": str(dados.get("municipio", "Município não informado")).strip(),
        "profissao": profissao,
        "url_fonte_tabela": str(dados.get("url_fonte_tabela", "")),
        "referencia": {**ref, "valor": _float(piso_40h), "jornada": _float(jornada_referencia), "proporcional": proporcional},
        "entrada": dados,
        "uf": str(dados.get("uf", "PR")).strip().upper(),
        "ano": int(dados.get("ano")) if str(dados.get("ano", "")).isdigit() else None,
        "lei": str(dados.get("lei", "Não informada")).strip(),
        "arquivo_fonte": str(dados.get("arquivo_fonte", "Não informado")).strip(),
        "classes": classes,
        "tabela_atual": _serializar_tabela(niveis),
        "tabela_referencia": _serializar_tabela(referencia),
        "diferencas": _serializar_tabela(diferencas),
        "defasagens_percentuais": _serializar_tabela(defasagens),
        "inconsistencias_estrutura": inconsistencias,
        "parametros": {
            "piso_nacional_40h": _float(piso_40h),
            "jornada_referencia": _float(jornada_referencia),
            "piso_proporcional_exato": _float(base_exata, 4),
            "jornada_semanal": _float(jornada, 2),
            "progressao_classes_percentual": (
                _float(progressao_uniforme, 4) if uniforme else None
            ),
            "progressoes_classes_percentuais": [
                _float(valor, 4) for valor in progressoes
            ],
            "progressao_classes_uniforme": uniforme,
            "progressao_classes_origem": origem_progressao,
            "modo_arredondamento": modo,
            "fonte_piso": str(ref.get("fonte", "Não informada")).strip(),
            "url_fonte_piso": str(ref.get("url", "")).strip(),
        },
        "resumo": {
            "situacao": "compativel" if celulas_abaixo == 0 else "abaixo_referencia",
            "vencimento_inicial_atual": _float(atual_inicial),
            "vencimento_inicial_referencia": _float(referencia_inicial),
            "diferenca_inicial": _float(diferenca_inicial),
            "defasagem_inicial_percentual": _float(defasagem_inicial, 4),
            "maior_defasagem_percentual": _float(max(maior_defasagem, Decimal("0")), 4),
            "celulas_abaixo_referencia": celulas_abaixo,
            "celulas_abaixo_base": sum(v < referencia_inicial for n in niveis for v in n["valores"]),
            "total_celulas": total_celulas,
            "divergencias_estrutura": len(inconsistencias),
        },
        "avisos": avisos,
        "avisos_importacao": avisos_importacao,
        "gerado_em": horario_brasilia.isoformat(timespec="seconds"),
    }
