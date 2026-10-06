"""Layout matricial do magistério de Araucária, sem presumir jornada."""
import re


def extrair(texto, nome, pagina, organizar, candidato, registro):
    texto = texto.replace('–', '-').replace('—', '-')
    blocos = list(re.finditer(r'^CLASSE\s*-\s*([IVX]+)\s*$', texto, re.M))
    if not blocos:
        raise ValueError('Araucária: não foram encontrados os blocos de classes.')
    ano = re.search(r'MAGISTÉRIO DE ARAUCÁRIA[^\n]*(20\d{2})', texto)
    saida = []
    for i, bloco in enumerate(blocos):
        parte = texto[bloco.end():blocos[i+1].start() if i+1<len(blocos) else len(texto)]
        cabecalho = re.search(r'^NÍVEL\s+((?:[A-Z]\s+)+[A-Z])\s*$', parte, re.M)
        if not cabecalho:
            raise ValueError('Araucária: cabeçalho de referências incompleto.')
        classes = cabecalho.group(1).split()
        linhas = list(re.finditer(r'^NÍVEL\s*-\s*([IVX]+)\s+', parte, re.M))
        if not linhas:
            raise ValueError('Araucária: bloco sem níveis.')
        rows = []; vistos = set()
        for j, linha in enumerate(linhas):
            trecho = parte[linha.end():linhas[j+1].start() if j+1<len(linhas) else len(parte)].split('Fonte:')[0]
            valores = re.findall(r'\d[\d.]*,\d{2}', trecho)
            nivel = linha.group(1)
            if len(valores)!=len(classes) or nivel in vistos:
                raise ValueError('Araucária: nível incompleto ou duplicado; nenhuma tabela da página foi incorporada.')
            vistos.add(nivel)
            rows.extend(registro(nivel,cl,v) for cl,v in zip(classes,valores))
        meta = {'municipio':'Araucária', 'profissao':'Magistério', 'grupo':'Classe '+bloco.group(1),
                'arquivo_fonte':f'{nome}, página {pagina}', 'lei':'Não informada no documento'}
        if ano:meta['ano']=int(ano.group(1))
        d = candidato(rows,nome,organizar,meta)
        d['avisos_importacao'].extend(['A classe de enquadramento do documento identifica cada bloco separado; A–T são as referências horizontais.',
            'Jornada não informada no PDF: confirme no plano de carreira antes de comparar com o piso.',
            'Progressões inferidas célula a célula; o reajuste de 4,11% no título não é a progressão da carreira.',
            'Documento elaborado pelo DIEESE/ER-PR com fonte declarada Prefeitura; vigência e origem devem ser conferidas.'])
        saida.append(d)
    return saida
