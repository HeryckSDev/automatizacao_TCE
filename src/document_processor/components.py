"""Tabelas de remuneração com células mescladas e componentes explícitos."""
import re
from src.salarial.leitor_geral import chave,numero,montar,metadados
from src.salarial.tabelas_coordenadas import registro


def ler_componentes(tabelas,nome,organizar,texto):
 out=[];pend=[]
 for ti,t in enumerate(tabelas,1):
  h=next((i for i,r in enumerate(t) if any(chave(x)=='nivel' for x in r) and any('basico' in chave(x) or chave(x)=='vb' for x in r)),None)
  if h is None:continue
  header=t[h];n=next(i for i,x in enumerate(header) if chave(x)=='nivel')
  cl=next((i for i,x in enumerate(header) if chave(x)=='classe'),None)
  cargo=next((i for i,x in enumerate(header) if chave(x)=='cargo'),None)
  cols=[(i,'Vencimento básico') for i,x in enumerate(header) if 'basico' in chave(x) or chave(x)=='vb']
  start=h+1
  if start<len(t) and any(chave(x)=='total' for x in t[start]):
   grupo='';sub=t[start]
   for i,x in enumerate(header):
    if x:grupo=str(x).replace('\n',' ').strip()
    if i<len(sub) and chave(sub[i])=='total':cols.append((i,'Total — '+grupo))
   start+=1
  else:
   cols.extend((i,'Total') for i,x in enumerate(header) if chave(x)=='total')
  try:
   records=[];last='';job='';seen=set()
   for row in t[start:]:
    if not any(row):continue
    if len(row)!=len(header):raise ValueError('linha incompleta')
    if cl is not None and row[cl]:last=str(row[cl])
    if cargo is not None and row[cargo]:job=str(row[cargo]).replace('\n',' ')
    lev=str(row[n] or '').strip()
    if not lev or (cl is not None and not last):raise ValueError('classe/nível ausente')
    label=(last+'-'+lev) if cl is not None else lev
    if label in seen:raise ValueError('classe/nível duplicado')
    seen.add(label);records.append((label,[numero(row[i]) for i,_ in cols]))
   # Carreira em ordem inicial -> final; não confundir titulação com classes legais.
   if cl is not None:records.sort(key=lambda r:(r[0].split('-')[0],int(r[0].split('-')[-1])))
   completos=[]
   for ci,(_,label) in enumerate(cols):
    meta=metadados(texto);meta.update(arquivo_fonte=f'{nome}, tabela {ti}',lei=label,grupo=label,pspn_inaplicavel=("magisterio superior" in chave(texto) or label.startswith("Total")))
    if job:meta['profissao']=job
    elif 'magisterio superior' in chave(texto):meta['profissao']='Professor do magistério superior'
    if 'dedicacao exclusiva' in chave(texto):meta.pop('jornada_semanal',None)
    rs=[dict(registro('Série salarial',ref,'1,00'),vencimento=vals[ci]) for ref,vals in records]
    if not rs:raise ValueError('nenhum vencimento')
    d=montar(rs,nome,organizar,meta)
    d['avisos_importacao'].append('Componentes separados: vencimento básico não inclui RT; total inclui titulação. Classe-nível foi preservada como referência composta. PSPN da educação básica não se aplica automaticamente. Dedicação exclusiva não foi convertida em horas.')
    completos.append(d)
   out.extend(completos)
  except (ValueError,TypeError) as e:pend.append(f'{nome}, tabela {ti}: {e}; componentes exigem revisão.')
 return out,pend
