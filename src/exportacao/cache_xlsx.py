"""Grava valores em cache nas células com fórmula de um XLSX gerado pelo openpyxl.

O openpyxl só escreve a fórmula, sem o último resultado calculado. Visualizadores que não
recalculam (pré-visualização de celular/e-mail, leitores de dados) mostram essas células em
branco até o arquivo ser aberto num programa de planilhas. Este módulo injeta o valor calculado
pelo Python ao lado da fórmula, que permanece viva: o Excel recalcula ao abrir.
"""

import re
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

_CELULA_FORMULA = re.compile(
    r'<c r="(?P<ref>[A-Z]+\d+)"(?P<attrs>[^>]*)>(?P<formula><f>.*?</f>)<v\s*(?:/>|></v>)</c>',
    re.DOTALL,
)


def _valor_xml(valor):
    if isinstance(valor, bool):
        return ' t="b"', "1" if valor else "0"
    if isinstance(valor, (int, float)):
        return "", repr(float(valor)) if isinstance(valor, float) else str(valor)
    return ' t="str"', escape("" if valor is None else str(valor))


def injetar_cache(conteudo, nomes_abas, caches):
    """Devolve o XLSX com `<v>` preenchido. `caches` = {nome_da_aba: {"B4": valor, ...}}.

    Células sem valor informado permanecem como estão. A ordem das abas segue `nomes_abas`
    (o openpyxl grava `sheet1.xml`, `sheet2.xml`... nessa ordem).
    """

    arquivos_alvo = {
        f"xl/worksheets/sheet{nomes_abas.index(aba) + 1}.xml": valores
        for aba, valores in caches.items()
        if aba in nomes_abas
    }
    saida = BytesIO()
    with zipfile.ZipFile(BytesIO(conteudo)) as origem, zipfile.ZipFile(
        saida, "w", zipfile.ZIP_DEFLATED
    ) as destino:
        for item in origem.infolist():
            dados = origem.read(item.filename)
            valores = arquivos_alvo.get(item.filename)
            if valores:
                def trocar(m):
                    ref = m.group("ref")
                    if ref not in valores:
                        return m.group(0)
                    atributo_tipo, texto = _valor_xml(valores[ref])
                    attrs = re.sub(r'\s+t="[^"]*"', "", m.group("attrs"))
                    return f'<c r="{ref}"{attrs}{atributo_tipo}>{m.group("formula")}<v>{texto}</v></c>'

                dados = _CELULA_FORMULA.sub(trocar, dados.decode("utf-8")).encode("utf-8")
            destino.writestr(item, dados)
    return saida.getvalue()
