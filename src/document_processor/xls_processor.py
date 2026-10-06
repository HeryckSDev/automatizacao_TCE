def ler_xls(conteudo):
    import xlrd
    try:book=xlrd.open_workbook(file_contents=conteudo)
    except xlrd.XLRDError as erro:raise ValueError('Arquivo XLS inválido ou protegido; envie XLSX/CSV.') from erro
    tables=[]
    for sheet in book.sheets():
        if sheet.nrows>20000 or sheet.ncols>220:raise ValueError('Planilha extensa: envie recorte.')
        tables.append([sheet.row_values(i) for i in range(sheet.nrows)])
    return tables

