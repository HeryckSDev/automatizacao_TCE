"""Leitura de estruturas tabulares, sem condicionamento por município."""
from decimal import Decimal, InvalidOperation
import re,unicodedata
from src.salarial.tabelas_coordenadas import candidato_registros,registro


def chave(v):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(v or '')) if not unicodedata.combining(c)).lower().strip()

EIXOS={'nivel','classe','referencia','padrao','codigo','faixa'}
MOEDA=re.compile(r'(?:R\$\s*)?\d[\d.]*,\d{2}(?!\d|\s*%)')
ALIASES={'vencimento':'valor','vencimento base':'valor','salario':'valor','salario base':'valor','remuneracao':'valor','cargo':'profissao','jornada semanal':'jornada','jornada_semanal':'jornada','nivel':'nivel','referencia':'classe','padrao':'classe'}


def numero(v):
    if isinstance(v,bool) or v is None:raise ValueError('valor ausente')
    s=str(v).strip().replace('R$','').replace(' ','')
    if '%' in s:raise ValueError('percentual não é vencimento')
    if ',' in s:
        if not re.fullmatch(r'(?:\d{1,3}(?:\.\d{3})+|\d+),\d+',s):raise ValueError('formato monetário ambíguo')
        s=s.replace('.','').replace(',','.')
    try:d=Decimal(s)
    except InvalidOperation:raise ValueError('valor ilegível')
    if not d.is_finite() or d<=0:raise ValueError('vencimento deve ser positivo')
    return format(d,'f')


def metadados(texto):
    d={};s=str(texto)
    m=re.search(r'(?:Munic[ií]pio\s*:\s*|Prefeitura Municipal de\s+)([^\n;]+)',s,re.I)
    if not m:m=re.search(r'MAGIST[EÉ]RIO DE\s+([^\n]+?)\s*[-–—]',s,re.I)
    if m:d['municipio']=m.group(1).strip()
    grupos=re.findall(r'^CLASSE\s*[-–—]\s*([^\n]+)$',s,re.M|re.I)
    if grupos:d['grupo']='Classe '+grupos[-1].strip()
    linhas_ano=[l for l in s.splitlines() if not MOEDA.search(l) and re.search(r'ano|vig[eê]ncia|compet[eê]ncia|tabela.*salari|janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro',l,re.I)]
    anos=set(re.findall(r'\b20\d{2}\b','\n'.join(linhas_ano)))
    if len(anos)==1:d['ano']=int(next(iter(anos)))
    horas=set(re.findall(r'\b(\d{1,2})\s*(?:horas|h/semana)\b',s,re.I))
    if len(horas)==1 and 0<float(next(iter(horas)))<=60:d['jornada_semanal']=float(next(iter(horas)))
    m=re.search(r'(?:Cargo|Profiss[aã]o)\s*:\s*([^\n;]+)',s,re.I)
    if m:d['profissao']=m.group(1).strip()
    elif 'magisterio' in chave(s):d['profissao']='Magistério'
    return d


def montar(rows,nome,organizar,meta):
    # registro accepts Brazilian text; prevent decimal-dot text from being interpreted as thousands.
    for r in rows:
        r['vencimento']=format(Decimal(r['vencimento']),'.12f').rstrip('0').rstrip('.').replace('.',',')
    d=candidato_registros(rows,nome,organizar,meta)
    d['avisos_importacao'].append('Leitor geral: eixos e progressões reconhecidos por estrutura. Confirme os nomes e a regra legal na revisão.')
    return d


def ler_matrizes(tabelas,nome,organizar,contexto=''):
    saida=[];pendencias=[]
    for ti,t in enumerate(tabelas,1):
        if not t:continue
        for pos,h in enumerate(t):
            if not h:continue
            heads=[ALIASES.get(chave(c),chave(c)) for c in h]
            if {'profissao','valor'}.issubset(heads) and not ({'nivel','classe'} & set(heads)):
                completos=[]
                try:
                    for ri,row in enumerate(t[pos+1:],pos+2):
                        if not any(str(x or '').strip() for x in row):continue
                        if len(row)!=len(h):raise ValueError(f'linha {ri}: lista incompleta')
                        obj=dict(zip(heads,row));prof=str(obj['profissao'] or '').strip()
                        if not prof:raise ValueError(f'linha {ri}: cargo ausente')
                        meta=metadados(contexto);meta.update(profissao=prof,arquivo_fonte=f'{nome}, tabela {ti}, linha {ri}')
                        r=dict(registro('Único','Inicial','1,00'),vencimento=numero(obj['valor']))
                        d=montar([r],nome,organizar,meta)
                        d['avisos_importacao'].append('Lista de cargos com um valor por cargo: estrutura sem progressão; nomes Único/Inicial são rótulos de apresentação, não níveis legais.')
                        completos.append(d)
                    saida.extend(completos)
                except (ValueError,TypeError) as e:pendencias.append(f'{nome}, tabela {ti}: {e}; lista não incorporada.')
                break
            if {'nivel','classe','valor'}.issubset(heads):
                rs=[];meta=metadados(contexto)
                try:
                    grupos={}
                    for ri,row in enumerate(t[pos+1:],pos+2):
                        if not any(str(x or '').strip() for x in row):continue
                        if len(row)!=len(h):raise ValueError(f'linha {ri}: quantidade de colunas diferente')
                        d=dict(zip(heads,row));v=numero(d['valor'])
                        ident=tuple(str(d.get(k) or meta.get(k) or '') for k in ('municipio','profissao','ano','jornada'))
                        gm={k:d[k] for k in ('municipio','profissao','ano') if d.get(k)}
                        if d.get('jornada'):gm['jornada_semanal']=float(numero(d['jornada']))
                        rows,md=grupos.setdefault(ident,([],dict(meta,**gm)))
                        rows.append(dict(registro(str(d['nivel']),str(d['classe']),'1,00'),vencimento=v))
                    completos=[]
                    for rows,md in grupos.values():
                        md['arquivo_fonte']=f'{nome}, tabela {ti}';completos.append(montar(rows,nome,organizar,md))
                    saida.extend(completos)
                except (ValueError,TypeError) as e:pendencias.append(f'{nome}, tabela {ti}: {e}; bloco não incorporado.')
                break
            if chave(h[0]) not in EIXOS or len(h)<2:continue
            descritiva=len(h)>1 and chave(h[1]) in {'descricao','titulacao','cargo'}
            inicio=2 if descritiva else 1
            headers=[str(v or '').strip() for v in h[inicio:]]
            if any(MOEDA.search(v) for v in headers):continue
            if any(not v for v in headers) or len(set(headers))!=len(headers):
                pendencias.append(f'{nome}, tabela {ti}: cabeçalho ausente/duplicado.');break
            rows=[];meta=metadados(contexto);meta['arquivo_fonte']=f'{nome}, tabela {ti}'
            try:
                for ri,row in enumerate(t[pos+1:],pos+2):
                    if not any(str(x or '').strip() for x in row):continue
                    if chave(row[0]) in EIXOS:break
                    if len(row)!=len(h):raise ValueError(f'linha {ri}: matriz incompleta')
                    label=re.sub(r'^(?:N[ií]vel|Classe|Refer[eê]ncia|Padr[aã]o)\s*[-–—:]?\s*','',str(row[0] or ''),flags=re.I).strip()
                    if not label:raise ValueError(f'linha {ri}: falta identificação')
                    for cl,v in zip(headers,row[inicio:]):
                        nivel,classe=(cl,label) if chave(h[0]) in {'classe','referencia'} else (label,cl)
                        rows.append(dict(registro(nivel,classe,'1,00'),vencimento=numero(v)))
                if rows:saida.append(montar(rows,nome,organizar,meta))
            except (ValueError,TypeError) as e:pendencias.append(f'{nome}, tabela {ti}: {e}; bloco não incorporado.')
            # Continue procurando outras matrizes na mesma aba/tabela.
    return saida,pendencias


def ler_texto(texto,nome,organizar):
    """Reconhece cabeçalho de eixo + valores monetários, incluindo linhas quebradas."""
    linhas=str(texto).splitlines();tabelas=[];contextos=[];atual=None;ctx=[];pend=[]
    for linha in linhas:
        s=linha.strip()
        header=re.match(r'^(N[ií]vel|Classe|Refer[eê]ncia|Padr[aã]o|Faixa)\s+(.+)$',s,re.I)
        if header and not MOEDA.search(s) and not re.match(r'^[-–—:]\s*',header.group(2)):
            colunas=header.group(2).split()
            if len(colunas)>=2 and len(set(colunas))==len(colunas):
                atual=[[header.group(1)]+colunas];tabelas.append(atual);contextos.append('\n'.join(linhas[:min(4,len(linhas))]+ctx[-10:]));continue
        vals=MOEDA.findall(s)
        if atual is not None and vals:
            prefix=s[:MOEDA.search(s).start()].strip()
            prefix=re.sub(r'^(?:N[ií]vel|Classe|Refer[eê]ncia)\s*[-–—:]?\s*','',prefix,flags=re.I).strip()
            if prefix:atual.append([prefix]+vals)
            elif len(atual)>1:atual[-1].extend(vals)
        else:
            if re.match(r'^(?:CLASSE|TABELA|ANEXO)\s*[-–—:]',s,re.I):atual=None
            if atual is not None and re.match(r'^(?:N[ií]vel\s*[-–—:]\s*[IVXLCDM]+|[IVXLCDM]+|[A-Z]|\d+)\s+',s):
                atual.append([s])  # Linha salarial sem valores: rejeitar, nunca omitir.
            if s.startswith(('Fonte:','Obs.','Observação')):atual=None
            ctx.append(s)
    out=[]
    for i,(t,c) in enumerate(zip(tabelas,contextos),1):
        d,p=ler_matrizes([t],f'{nome}, bloco {i}',organizar,c);out.extend(d);pend.extend(p)
    return out,pend
