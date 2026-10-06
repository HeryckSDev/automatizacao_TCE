"""Adaptadores de tabelas oficiais por coordenadas; extração exige revisão."""
from io import BytesIO
from html.parser import HTMLParser
import re
import pdfplumber



def limpar_numero(v):
    return re.sub(r'\s+','',str(v or '')).replace('R$','')


def separar_colunas(tabela):
    """Páginas de piso salarial trazem dois níveis lado a lado (Referência, Valor, vazio, Referência, Valor).
    Sem separar, esses níveis eram ignorados em silêncio e a tabela saía incompleta."""
    if tabela and all(len(r) == 5 for r in tabela):
        cabecalho = [str(c or '').strip() for r in tabela for c in r[:5] if str(r[0] or '').strip() == 'Referência']
        if cabecalho[:5] == ['Referência', 'Valor', '', 'Referência', 'Valor']:
            return [[[r[0], r[1]] for r in tabela], [[r[3], r[4]] for r in tabela]]
    return [tabela]


def candidato_registros(rows,nome,organizar,metadata=None):
    if rows and all(str(r['classe']).isdigit() for r in rows):
        rows=sorted(rows,key=lambda r:int(r['classe']))
    d=organizar(rows,nome)[0]
    for i,n in enumerate(d['niveis']):
        if i:
            anterior=d['niveis'][i-1]
            n['regra_vertical']={'tipo':'percentual','valor':round((n['valores'][0]/anterior['valores'][0]-1)*100,4),'nivel_referencia':anterior['codigo']}

    for k in ['municipio','profissao','ano','jornada_semanal']:d.pop(k,None)
    d.update(metadata or {})
    d['jornada_confirmada_no_documento']=bool((metadata or {}).get('jornada_semanal'))
    d['avisos_importacao'].append('Extração de tabela oficial por coordenadas/células: confirme recorte, jornada, vigência e regras antes de comparar.')
    return d


def registro(nivel,classe,valor,descricao=''):
    return dict(municipio='A informar',profissao='A informar',ano=2000,jornada=1,nivel=nivel,classe=classe,vencimento=limpar_numero(valor),descricao=descricao or nivel)


def extrair_pdf(nome,conteudo,organizar):
    candidates=[];pendencias=[];textos=[]
    with pdfplumber.open(BytesIO(conteudo)) as doc:
        if len(doc.pages)>300:raise ValueError('PDF extenso: envie o recorte de até 300 páginas.')
        for i,page in enumerate(doc.pages,1):
            text=page.extract_text() or '';textos.append(f'PÁGINA {i}\n{text}')
            # Only layouts with explicitly recognized axes are considered.
            curitiba='PREFEITURA MUNICIPAL DE CURITIBA' in text and 'Parte' in text and 'Referência' in text and 'Valor' in text
            londrina=bool(re.search(r'TABELA\s+\d+:\s*PROFESSOR',text)) and 'Interstício' in text
            if not(curitiba or londrina):continue
            tables=page.extract_tables();antes=len(candidates)
            if curitiba:
                groups={};special=[];jornadas=set()
                for t0 in tables:
                    for row in t0:
                        for cell in row:
                            if re.fullmatch(r'\d+\s*horas',str(cell or '').strip()):jornadas.add(float(re.search(r'\d+',cell).group()))
                for t in [parte for t0 in tables for parte in separar_colunas(t0)]:
                    header=next((j for j,r in enumerate(t) if len(r)==2 and str(r[0]).strip()=='Referência' and str(r[1]).strip()=='Valor'),None)
                    if header is None:continue
                    description=' '.join(str(c or '') for r in t[:header] for c in r).replace('\n',' ')
                    match=re.search(r'Parte Permanente\s+Nível\s+([IVXLCDM]+)',description)
                    rows=t[header+1:]
                    if not rows or any(len(r)!=2 or not re.fullmatch(r'[IVXLCDM]+',str(r[0] or '')) or not re.fullmatch(r'\d[\d.]*,\d{2}',limpar_numero(r[1])) for r in rows):
                        pendencias.append(f'{nome}, página {i}: coluna salarial incompleta; nenhuma linha dessa coluna foi incorporada.');continue
                    if match:groups[match.group(1)]=(description,rows)
                    elif 'Parte Especial' in description:special.append((description,rows))
                identity=re.search(r'ANEXO\s*-?\s*([\w-]+)',text)
                label='Anexo '+identity.group(1) if identity else f'página {i}'
                metadata={'municipio':'Curitiba','arquivo_fonte':f'{nome}, página {i}, {label}'}
                grupo=re.search(r'GRUPO OCUPACIONAL\s+([^\n]+)',text)
                if grupo:metadata['grupo']='Grupo '+grupo.group(1).strip().capitalize()
                else:
                    linhas=[l.strip() for l in text.split('\n')]
                    cargo=next((linhas[k+1] for k,l in enumerate(linhas) if 'Piso Salarial' in l and k+1<len(linhas) and linhas[k+1]),None)
                    if cargo:metadata['grupo']='Piso salarial';metadata['profissao']=cargo  # cargo escrito no título da própria página
                year=re.search(r'TABELA SALARIAL[^\n]*(20\d{2})',text)
                if year:metadata['ano']=int(year.group(1))
                if len(jornadas)==1:metadata['jornada_semanal']=next(iter(jornadas))
                esperados=set(re.findall(r'Parte Permanente\s+Nível\s+([IVXLCDM]+)',text))
                if groups and esperados-set(groups):
                    pendencias.append(f'{nome}, página {i}: a página indica os níveis {", ".join(sorted(esperados))}, mas só foram lidos {", ".join(sorted(groups))}; a tabela não foi incorporada para não sair incompleta.');groups={}
                if groups:
                    refs=[tuple(r[0] for r in rows) for _,rows in groups.values()]
                    if len(set(refs))!=1:pendencias.append(f'{nome}, página {i}: níveis com referências diferentes; revise a continuação.');continue
                    rs=[registro(k,r[0],r[1],desc) for k,(desc,rows) in groups.items() for r in rows]
                    d=candidato_registros(rs,nome,organizar,metadata)
                    d['lei']=label+' — parte permanente'
                    d['avisos_importacao'].append('Parte especial separada da parte permanente. O cargo deve ser escolhido conforme o enquadramento do documento; não foi presumido.')
                    candidates.append(d)
                for desc,rows in special:
                    d=candidato_registros([registro('Especial',r[0],r[1],desc) for r in rows],nome,organizar,metadata);d['lei']=label+' — parte especial';candidates.append(d)
            if londrina:
                title=re.search(r'TABELA\s+\d+:\s*PROFESSOR[^\n]*',text).group()
                for t in tables:
                    header=next((j for j,r in enumerate(t) if r and r[0] is None and any(str(v)=='I' for v in r)),None)
                    if header is None:continue
                    axes=t[header];blocks=[j for j,v in enumerate(axes) if v is None]
                    rs=[];seen=set();invalid=False
                    for row in t[header+1:]:
                        if not row or not str(row[0] or '').isdigit():continue
                        for start in blocks:
                            level=str(row[start] or '')
                            end=next((b for b in blocks if b>start),len(axes))
                            if not level.isdigit():invalid=True;break
                            for col in range(start+1,end):
                                ref=str(axes[col] or '').strip();val=row[col] if col<len(row) else None
                                if not ref or not re.fullmatch(r'\d[\d.]*,\d{2}',limpar_numero(val)):invalid=True;break
                                key=(ref,level)
                                if key in seen:invalid=True;break
                                seen.add(key);rs.append(registro(ref,level,val,'Referência '+ref))
                    if invalid or not rs:pendencias.append(f'{nome}, página {i}: matriz incompleta; revisão necessária.');continue
                    meta={'municipio':'Londrina','profissao':title.split(':',1)[1].strip(),'arquivo_fonte':f'{nome}, página {i}','lei':title}
                    year=re.search(r'Atualizada[^\n]*(20\d{2})',text);hours=re.search(r'(\d+)\s*HORAS',title)
                    if year:meta['ano']=int(year.group(1))
                    if hours:meta['jornada_semanal']=float(hours.group(1))
                    d=candidato_registros(rs,nome,organizar,meta)
                    d['avisos_importacao'].append('Eixos transpostos para preservar todos os valores: referências do documento nas linhas; níveis numéricos nas colunas. Não presumir equivalência legal entre eixos.')
                    candidates.append(d)
            if len(candidates)==antes:pendencias.append(f'{nome}, página {i}: layout reconhecido, mas não há matriz completa extraível.')
    return candidates,'\n'.join(textos),pendencias


class HTMLComContexto(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.rows=None;self.row=None;self.cell=None;self.heading=None;self.label='';self.date=None
    def handle_starttag(self,t,a):
        if t in ('h1','h2','h3','h4'):self.heading=[]
        if t=='table':self.rows=[];self.context=self.label
        if t=='tr' and self.rows is not None:self.row=[]
        if t in ('td','th') and self.row is not None:self.cell=[]
    def handle_data(self,v):
        if self.heading is not None:self.heading.append(v)
        if self.cell is not None:self.cell.append(v)
    def handle_endtag(self,t):
        if t in ('h1','h2','h3','h4') and self.heading is not None:
            self.label=' '.join(' '.join(self.heading).split());self.heading=None
            m=re.search(r'Data Referência:\s*(\d{2}/\d{2}/\d{4})',self.label)
            if m:self.date=m.group(1)
        if t in ('td','th') and self.cell is not None:self.row.append(' '.join(self.cell).strip());self.cell=None
        if t=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
        if t=='table' and self.rows is not None:self.tables.append((self.context,self.rows));self.rows=None


def extrair_html(nome,conteudo,organizar):
    p=HTMLComContexto();p.feed(conteudo.decode('utf-8',errors='replace'));cs=[];ps=[]
    for idx,(context,table) in enumerate(p.tables,1):
        if not table or [str(c).strip() for c in table[0]]!=['Classe','Nível','Valor']:continue
        rows=table[1:]
        if not rows:ps.append(f'Tabela {idx} ({context}): vazia.');continue
        # Mixed symbolic salary codes are not an ordered career matrix.
        if any(len(r)!=3 or not r[0] or not re.fullmatch(r'\d+',str(r[1])) for r in rows):
            ps.append(f'Tabela {idx} ({context}): códigos/níveis sem matriz ordenada; revisão detalhada necessária.');continue
        rs=[registro(r[0],r[1],r[2],'Classe '+r[0]) for r in rows]
        try:d=candidato_registros(rs,nome,organizar,{'arquivo_fonte':f'{nome}, tabela {idx}: {context}'})
        except ValueError as e:ps.append(f'Tabela {idx} ({context}): {e}');continue
        d['lei']=context or 'Não informada'
        if p.date:d['ano']=int(p.date[-4:]);d['avisos_importacao'].append('Data de referência da página: '+p.date+'; confirme vigência da norma.')
        d['avisos_importacao'].append('Eixos transpostos: classe do documento nas linhas e nível numérico nas colunas. Cargo e jornada precisam ser informados; o cabeçalho de grupo não foi tratado como profissão.')
        cs.append(d)
    if not cs:ps.append('A página não contém matriz salarial reconhecida. Se for catálogo de leis/publicações, envie o anexo com os vencimentos.')
    return cs,ps
