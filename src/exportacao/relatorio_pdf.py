"""Relatório PDF da comparação salarial, inspirado no material de referência."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


AZUL = colors.HexColor("#10102E")
VERDE = colors.HexColor("#4A6123")
VERDE_CLARO = colors.HexColor("#DCE9BD")
ROXO = colors.HexColor("#403250")
ROXO_CLARO = colors.HexColor("#D8CBE5")
VERMELHO_CLARO = colors.HexColor("#F4CCCC")
VERDE_OK = colors.HexColor("#D9EAD3")
CINZA = colors.HexColor("#E5E5E5")


def _registrar_fontes():
    pasta = Path(__file__).resolve().parents[2] / "assets/fonts"
    normal = pasta / "DejaVuSans.ttf"
    negrito = pasta / "DejaVuSans-Bold.ttf"
    if normal.exists() and negrito.exists():
        pdfmetrics.registerFont(TTFont("JornadaSans", normal))
        pdfmetrics.registerFont(TTFont("JornadaSans-Bold", negrito))
        pdfmetrics.registerFontFamily(
            "JornadaSans",
            normal="JornadaSans",
            bold="JornadaSans-Bold",
            italic="JornadaSans",
            boldItalic="JornadaSans-Bold",
        )
        return "JornadaSans", "JornadaSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONTE_NORMAL, FONTE_NEGRITO = _registrar_fontes()


def _moeda(valor, sinal=False, casas=2):
    numero = float(valor or 0)
    prefixo = "+" if sinal and numero > 0 else ""
    texto = f"{abs(numero):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if numero < 0:
        prefixo = "-"
    return f"{prefixo}R$ {texto}"


def _percentual(valor):
    return f"{float(valor or 0):.4f}%".replace(".", ",")


def _regra_vertical(nivel):
    regra = nivel.get("regra_vertical")
    if isinstance(regra, dict):
        return regra
    if nivel.get("acrescimo_valor_fixo") is not None:
        return {
            "tipo": "valor_fixo",
            "valor": nivel.get("acrescimo_valor_fixo", 0),
            "nivel_referencia": None,
        }
    return {
        "tipo": "percentual",
        "valor": nivel.get("acrescimo_percentual", 0) or 0,
        "nivel_referencia": None,
    }


def _rotulo_regra(nivel):
    regra = _regra_vertical(nivel)
    if regra.get("tipo") == "base":
        return "Base da carreira"
    referencia = f" sobre {regra.get('nivel_referencia')}" if regra.get("nivel_referencia") else ""
    if regra.get("tipo") == "valor_fixo":
        return f"+ {_moeda(regra.get('valor'))}{referencia}"
    valor = f"{float(regra.get('valor') or 0):.4f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"+ {valor}%{referencia}"


def _rotulo_progressoes(parametros):
    progressoes = parametros.get("progressoes_classes_percentuais") or []
    if not progressoes and parametros.get("progressao_classes_percentual") is not None:
        return _percentual(parametros.get("progressao_classes_percentual"))
    if parametros.get("progressao_classes_uniforme", True) and progressoes:
        return _percentual(progressoes[0])
    return "; ".join(
        f"{indice}→{indice + 1}: {_percentual(valor)}"
        for indice, valor in enumerate(progressoes, start=1)
    )


def _rodape(canvas, documento):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B9B9B9"))
    canvas.line(18 * mm, 12 * mm, 279 * mm, 12 * mm)
    canvas.setFont(FONTE_NORMAL, 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(18 * mm, 7.5 * mm, "Projeto Jornada de Aprendizagem - análise técnica")
    canvas.drawRightString(279 * mm, 7.5 * mm, f"Página {documento.page}")
    canvas.restoreState()


def _estilos():
    base = getSampleStyleSheet()
    return {
        "capa": ParagraphStyle(
            "Capa",
            parent=base["Title"],
            fontName=FONTE_NEGRITO,
            fontSize=27,
            leading=32,
            textColor=AZUL,
            alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "subcapa": ParagraphStyle(
            "Subcapa",
            parent=base["Normal"],
            fontName=FONTE_NORMAL,
            fontSize=14,
            leading=20,
            textColor=colors.HexColor("#4A4A4A"),
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=FONTE_NEGRITO,
            fontSize=17,
            leading=21,
            textColor=AZUL,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=FONTE_NEGRITO,
            fontSize=12,
            leading=15,
            textColor=AZUL,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "corpo": ParagraphStyle(
            "Corpo",
            parent=base["BodyText"],
            fontName=FONTE_NORMAL,
            fontSize=9.5,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=7,
        ),
        "pequeno": ParagraphStyle(
            "Pequeno",
            parent=base["BodyText"],
            fontName=FONTE_NORMAL,
            fontSize=8,
            leading=11,
        ),
        "centro": ParagraphStyle(
            "Centro",
            parent=base["BodyText"],
            fontName=FONTE_NEGRITO,
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
    }


def _tabela_salarios_bloco(tabela, classes, cor_titulo, cor_corpo, estilos, diferencas=False):
    cabecalho = ["Nível", "Descrição", "Regra vertical", *[str(item) for item in classes]]
    linhas = [cabecalho]
    for nivel in tabela:
        valores = [
            _moeda(valor, sinal=diferencas) if diferencas else _moeda(valor)
            for valor in nivel.get("valores", [])
        ]
        linhas.append(
            [
                nivel.get("codigo"),
                Paragraph(escape(str(nivel.get("descricao", ""))), estilos["pequeno"]),
                Paragraph(escape(_rotulo_regra(nivel)), estilos["pequeno"]),
                *valores,
            ]
        )

    quantidade_classes = len(classes)
    largura_disponivel = landscape(A4)[0] - 32 * mm
    larguras_fixas = 22 * mm + 39 * mm + 28 * mm
    largura_classe = (largura_disponivel - larguras_fixas) / max(quantidade_classes, 1)
    tabela_pdf = Table(
        linhas,
        colWidths=[22 * mm, 39 * mm, 28 * mm] + [largura_classe] * quantidade_classes,
        repeatRows=1,
        hAlign="LEFT",
    )
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), cor_titulo),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONTE_NEGRITO),
        ("FONTNAME", (0, 1), (0, -1), FONTE_NEGRITO),
        ("FONTSIZE", (0, 0), (-1, -1), 6.6),
        ("LEADING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, -1), cor_corpo),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#777777")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if diferencas:
        for linha_indice, nivel in enumerate(tabela, start=1):
            for coluna_indice, valor in enumerate(nivel.get("valores", []), start=3):
                cor = VERMELHO_CLARO if float(valor) < 0 else VERDE_OK
                estilo.append(("BACKGROUND", (coluna_indice, linha_indice), (coluna_indice, linha_indice), cor))
    tabela_pdf.setStyle(TableStyle(estilo))
    return tabela_pdf


def _tabela_salarios(tabela, classes, cor_titulo, cor_corpo, estilos, diferencas=False):
    blocos=[]
    for inicio in range(0,len(classes),12):
        fim=min(inicio+12,len(classes))
        recorte=[{**n,'valores':n.get('valores',[])[inicio:fim]} for n in tabela]
        blocos.append(Paragraph(f"Classes {escape(str(classes[inicio]))} a {escape(str(classes[fim-1]))}",estilos['pequeno']))
        blocos.append(_tabela_salarios_bloco(recorte,classes[inicio:fim],cor_titulo,cor_corpo,estilos,diferencas))
        blocos.append(Spacer(1,4*mm))
    return blocos


def gerar_relatorio_salarial_pdf(dados):
    """Retorna o relatório salarial em bytes."""

    atual = dados.get("tabela_atual") or []
    referencia = dados.get("tabela_referencia") or []
    diferencas = dados.get("diferencas") or []
    classes = dados.get("classes") or []
    if not atual or not referencia or not classes:
        raise ValueError("A análise salarial não possui dados suficientes para o PDF.")

    estilos = _estilos()
    arquivo = BytesIO()
    documento = SimpleDocTemplate(
        arquivo,
        pagesize=landscape(A4),
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Análise salarial - {dados.get('municipio', 'Município')}",
        author="Projeto Jornada de Aprendizagem",
    )

    resumo = dados.get("resumo") or {}
    parametros = dados.get("parametros") or {}
    ref = dados.get("referencia") or {}
    eh_pspn = ref.get("tipo", "pspn") == "pspn"
    rotulo_ref = "PSPN" if eh_pspn else str(ref.get("nome") or "Referência informada")
    municipio = escape(str(dados.get("municipio", "Município não informado")))
    lei = escape(str(dados.get("lei", "Lei não informada")))
    situacao = (
        "Tabela compatível com a referência calculada"
        if resumo.get("situacao") == "compativel"
        else "Há vencimentos abaixo da referência calculada"
    )

    historia = [
        Spacer(1, 18 * mm),
        Paragraph("RELATÓRIO TÉCNICO", estilos["subcapa"]),
        Spacer(1, 5 * mm),
        Paragraph("Análise Salarial Municipal — " + escape(str(dados.get("profissao") or "Magistério")), estilos["capa"]),
        Spacer(1, 5 * mm),
        Paragraph(f"{municipio} - {escape(str(dados.get('uf', 'PR')))}", estilos["subcapa"]),
        Paragraph(f"Tabela salarial: {lei}", estilos["subcapa"]),
        Spacer(1, 18 * mm),
    ]
    faixa = Table(
        [[Paragraph(escape(situacao), estilos["centro"])]],
        colWidths=[260 * mm],
        rowHeights=[16 * mm],
    )
    faixa.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AZUL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    historia.extend(
        [
            faixa,
            Spacer(1, 10 * mm),
            Paragraph(
                "Documento de apoio à análise. As premissas de jornada, centavos e enquadramento legal "
                "devem ser confirmadas por responsável humano antes do uso oficial.",
                estilos["corpo"],
            ),
            PageBreak(),
            Paragraph(f"1. Resumo da análise - {municipio}", estilos["h1"]),
        ]
    )

    linhas_resumo = [
        ["Indicador", "Resultado"],
        ["PSPN nacional de 40 horas" if eh_pspn else "Referência informada", _moeda(ref.get("valor", parametros.get("piso_nacional_40h")))],
        ["Jornada adotada", f"{parametros.get('jornada_semanal')} horas semanais"],
        ["Base proporcional exata", _moeda(parametros.get("piso_proporcional_exato"), casas=3)],
        ["Vencimento inicial atual", _moeda(resumo.get("vencimento_inicial_atual"))],
        ["Vencimento inicial de referência", _moeda(resumo.get("vencimento_inicial_referencia"))],
        ["Diferença inicial", _moeda(resumo.get("diferenca_inicial"), sinal=True)],
        ["Defasagem inicial", _percentual(resumo.get("defasagem_inicial_percentual"))],
        ["Células abaixo da referência", f"{resumo.get('celulas_abaixo_referencia', 0)} de {resumo.get('total_celulas', 0)}"],
        ["Divergências na estrutura", str(resumo.get("divergencias_estrutura", 0))],
        ["Progressão horizontal", _rotulo_progressoes(parametros)],
        ["Tratamento de centavos", str(parametros.get("modo_arredondamento", "não informado"))],
    ]
    tabela_resumo = Table(linhas_resumo, colWidths=[82 * mm, 105 * mm], hAlign="LEFT")
    tabela_resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONTE_NEGRITO),
                ("FONTNAME", (0, 1), (0, -1), FONTE_NEGRITO),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F4F4")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#888888")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    historia.extend(
        [
            tabela_resumo,
            Spacer(1, 8 * mm),
            Paragraph("Leitura do resultado", estilos["h2"]),
            Paragraph(
                f"A tabela possui {len(atual)} nível(is) e {len(classes)} classe(s). "
                f"O cálculo usa a progressão horizontal <b>{escape(_rotulo_progressoes(parametros))}</b> "
                f"e aplica o modo de centavos <b>{escape(str(parametros.get('modo_arredondamento')))}</b> em cada etapa.",
                estilos["corpo"],
            ),
            Paragraph(
                "A defasagem segue a expressão referência / valor atual - 1. Resultado positivo indica "
                "que o valor atual está abaixo da referência; resultado zero indica equivalência nos centavos exibidos.",
                estilos["corpo"],
            ),
            PageBreak(),
            Paragraph("2. Tabelas de vencimentos", estilos["h1"]),
            Paragraph("Tabela atual transcrita do documento municipal", estilos["h2"]),
            *_tabela_salarios(atual, classes, VERDE, VERDE_CLARO, estilos),
            Spacer(1, 7 * mm),
            Paragraph("Tabela de referência calculada a partir de " + escape(rotulo_ref), estilos["h2"]),
            *_tabela_salarios(referencia, classes, ROXO, ROXO_CLARO, estilos),
            PageBreak(),
            Paragraph("3 - Diferenças e premissas", estilos["h1"]),
            Paragraph(
                "Valores abaixo de zero indicam que a célula municipal está abaixo da referência; "
                "valores iguais ou superiores a zero são destacados em verde.",
                estilos["corpo"],
            ),
            *_tabela_salarios(diferencas, classes, AZUL, CINZA, estilos, diferencas=True),
            Spacer(1, 7 * mm),
            Paragraph("Avisos que acompanham esta análise", estilos["h2"]),
        ]
    )
    for aviso in dados.get("avisos") or []:
        historia.append(Paragraph(f"• {escape(str(aviso))}", estilos["corpo"]))
    fonte = ref.get("url") or ref.get("fonte") or parametros.get("url_fonte_piso")
    if fonte:
        historia.append(
            KeepTogether(
                [
                    Paragraph("Fonte da referência informada", estilos["h2"]),
                    Paragraph(escape(str(fonte)), estilos["pequeno"]),
                ]
            )
        )

    documento.build(historia, onFirstPage=_rodape, onLaterPages=_rodape)
    return arquivo.getvalue()
