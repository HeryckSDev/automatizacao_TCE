"""CSV/TSV mantêm linhas e células, incluindo codificação brasileira."""
import csv
from io import StringIO

def extrair_csv(conteudo, tsv=False):
    try: texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError: texto = conteudo.decode("cp1252")
    try: dialect = csv.Sniffer().sniff(texto[:8192], delimiters=";,\t")
    except csv.Error: dialect = csv.excel_tab if tsv else csv.excel
    matriz = list(csv.reader(StringIO(texto), dialect))
    if len(matriz)>20000 or any(len(l)>220 for l in matriz):
        raise ValueError("Tabela extensa: envie um recorte.")
    return [matriz], texto
