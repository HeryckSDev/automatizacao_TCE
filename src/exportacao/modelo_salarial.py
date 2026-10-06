"""Modelo único de conteúdo e aparência, derivado das páginas 9–11 do professor.

O mesmo esquema alimenta a exportação Python e a verificação visual do Excel.
Valores calculados permanecem fórmulas; caches só tornam a primeira abertura legível.
"""
from decimal import Decimal

VERDE, VERDE_CLARO = "#4F6228", "#C4D79B"
ROXO, ROXO_CLARO = "#403152", "#B1A0C7"
VERMELHO, ROSA = "#FF0000", "#E6B8B7"
MOEDA = '"R$" #,##0.00;-"R$" #,##0.00;"R$" 0.00'


def coluna(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def criar_modelo(analise):
    a = analise
    p, ref = a["parametros"], a["referencia"]
    niveis, classes = a["tabela_atual"], a["classes"]
    n, m = len(niveis), len(classes)
    if n > 100 or m > 200:
        raise ValueError("Divida a análise em até 100 níveis e 200 classes por arquivo.")
    specs = []

    def sheet(name, widths):
        s = {"name": name, "cells": [], "merges": [], "formats": [], "widths": widths,
             "heights": {}, "conditional": [], "freeze": 3, "print": None}
        specs.append(s)
        return s

    def cell(s, r, c, v=None, f=None, cache=None, fmt=None):
        item = {"address": f"{coluna(c)}{r}", "value": v}
        if f:
            item.update(formula=f, cache=cache)
        if fmt:
            item["numberFormat"] = fmt
        s["cells"].append(item)

    def band(s, row, last, title, color, size=12, height=26):
        rng = f"A{row}:{coluna(last)}{row}"
        s["merges"].append(rng)
        cell(s, row, 1, title)
        s["formats"].append({"range": rng, "fill": color, "fontColor": "#FFFFFF", "bold": True, "size": size, "align": "center"})
        s["heights"][str(row)] = height

    def note(s, row, last, text=None, formula=None, cache=None, height=30):
        rng = f"A{row}:{coluna(last)}{row}"
        s["merges"].append(rng)
        cell(s, row, 1, text, formula, cache)
        s["formats"].append({"range": rng, "wrap": True, "align": "left"})
        s["heights"][str(row)] = height

    params = sheet("Parâmetros", [33, 29, 25, 23, 19, 24])
    band(params, 1, 6, "PARÂMETROS DA COMPARAÇÃO", ROXO)
    entradas = [
        ("Município", a["municipio"]), ("Profissão/cargo", a["profissao"]), ("Ano", a["ano"]),
        ("Jornada do cargo (h/semana)", p["jornada_semanal"]), ("Tipo da referência", ref["tipo"]),
        ("Nome da referência", ref["nome"]), ("Valor da referência", ref["valor"]),
        ("Jornada da referência", ref["jornada"]), ("Proporcionalidade autorizada", "sim" if ref["proporcional"] else "não"),
        ("Tratamento dos centavos", p["modo_arredondamento"]), ("Referência proporcional", None),
        ("Ano da referência", ref["ano"]), ("Tolerância estrutural (R$)", .01),
    ]
    for r, (label, value) in enumerate(entradas, 3):
        cell(params, r, 1, label)
        cell(params, r, 2, value)
    # B13: arredondamento/truncamento decidido e auditável no próprio Excel.
    params["cells"] = [c for c in params["cells"] if c["address"] != "B13"]
    expression='IF(B11="sim",B9*B6/B10,B9)'
    cell(params, 13, 2, f=f'=IF(B12="truncar",ROUNDDOWN({expression},2),ROUND({expression},2))', cache=a["resumo"]["vencimento_inicial_referencia"], fmt=MOEDA)
    cell(params,16,1,"Coerência de ano/jornada")
    cell(params,16,2,f='=IF(AND(B5=B14,OR(B11="sim",B6=B10)),"OK","REVISAR ANO/JORNADA")',cache='OK')
    params["formats"].append({"range": "B3:B15", "fill": "#FFF2CC", "fontColor": "#0000FF", "wrap": True})
    for r in [4, 7, 8, 11, 12]: params["heights"][str(r)] = 32
    cell(params, 18, 1, "Nível"); cell(params, 18, 2, "Descrição"); cell(params, 18, 3, "Regra vertical")
    cell(params, 18, 4, "Valor (% ou R$)"); cell(params, 18, 5, "Sobre o nível")
    for i, nivel in enumerate(niveis):
        r = 19 + i; reg = nivel["regra_vertical"]
        for c, value in enumerate([nivel["codigo"], nivel["descricao"], reg["tipo"], reg["valor"], reg["nivel_referencia"] or ""], 1): cell(params, r, c, value)
    start_progress = 22 + n
    for c,v in enumerate(["Classe de origem", "Classe de destino", "Progressão (%)"],1): cell(params,start_progress,c,v)
    for j,v in enumerate(p["progressoes_classes_percentuais"]):
        for c,value in enumerate([str(classes[j]),str(classes[j+1]),v],1):cell(params,start_progress+j+1,c,value)
    note(params, start_progress+m+2, 6, "Cenário/consultoria é uma referência analítica. PSPN é exclusivo do magistério. Alterar profissão, ano ou jornada exige revisar a referência e sua fonte.", height=45)

    raw = sheet("Dados originais", [15, 35, 28] + [16]*m)
    band(raw, 1, min(18,max(4,m+3)), "TABELA MUNICIPAL TRANSCRITA — VALORES DE ENTRADA", VERDE)
    for j,v in enumerate(["Nível", "Descrição", "Regra vertical"]+[str(c) for c in classes],1): cell(raw,3,j,v)
    for i, nivel in enumerate(niveis):
        for j,v in enumerate([nivel["codigo"],nivel["descricao"],nivel["regra_vertical"]["tipo"]]+nivel["valores"],1): cell(raw,4+i,j,v,fmt=MOEDA if j>=4 else None)
    raw["formats"].append({"range":f"D4:{coluna(m+3)}{n+3}","fontColor":"#0000FF"})

    main = sheet("Comparação salarial", [10, 10, 16]+[16]*min(15,m))
    # Primeiro na ordem de abertura, como o relatório do professor.
    specs.remove(main); specs.insert(0, main)
    last = 3 + min(15,m)
    band(main, 1, last, f"ANÁLISE SALARIAL — {a['municipio'].upper()} / {a['uf']}", VERDE, 14, 30)
    note(main, 2, last, f"{a['profissao']} · {a['ano']} · {p['jornada_semanal']:g} horas semanais · {a['lei']}", height=30)
    note(main, 3, last, f"Referência: {ref['nome']} ({ref['tipo']}). Fonte, competência e decisões: aba Fontes e premissas.")
    main['merges'].append('A4:C4')
    cell(main,4,1,'Base da referência:')
    cell(main,4,4,f="='Parâmetros'!B13",cache=a['resumo']['vencimento_inicial_referencia'],fmt=MOEDA)
    # Mantém grupos largos legíveis, repetindo o MESMO conjunto de tabelas.
    positions = {}
    row = 5
    for offset in range(0,m,15):
        indices = list(range(offset,min(offset+15,m)))
        end = 3+len(indices)
        if m > 15:
            note(main,row,last,f"Continuação das classes/referências: {classes[indices[0]]} a {classes[indices[-1]]}. Nenhuma classe foi descartada."); row += 2
        sections = [("estrutura","ESTRUTURA DE PROMOÇÃO / PROGRESSÃO",VERDE,VERDE_CLARO),
                    ("atual",f"• TABELA DE VENCIMENTOS {a['ano']} •",VERDE,VERDE_CLARO),
                    ("referencia",f"• TABELA DE VENCIMENTOS — REFERÊNCIA {ref['nome']} •",ROXO,ROXO_CLARO),
                    ("conformidades","NÃO CONFORMIDADES EM RELAÇÃO À REFERÊNCIA",VERDE,VERDE_CLARO),
                    ("diferencas","• DEFASAGEM SALARIAL MENSAL •",VERMELHO,ROSA)]
        for key,title,dark,light in sections:
            if key == "conformidades":
                actual_range=f"{positions[('atual',0,indices[0])]}:{positions[('atual',n-1,indices[-1])]}"
                ref_range=f"{positions[('referencia',0,indices[0])]}:{positions[('referencia',n-1,indices[-1])]}"
                below=sum(nv['valores'][k] < a['tabela_referencia'][i]['valores'][k] for i,nv in enumerate(niveis) for k in indices)
                count_base=sum(nv['valores'][k] < a['resumo']['vencimento_inicial_referencia'] for nv in niveis for k in indices)
                formula=f'="Neste bloco: "&SUMPRODUCT(--({actual_range}<{ref_range}))&" vencimentos abaixo da referência de carreira; "&COUNTIF({actual_range},"<"&$D$4)&" abaixo da base inicial (em vermelho)."'
                note(main,row,last,formula=formula,cache=f'Neste bloco: {below} vencimentos abaixo da referência de carreira; {count_base} abaixo da base inicial (em vermelho).',height=35)
                row+=2
            band(main,row,last,title,dark,12,28)
            band(main,row+1,last,f"{a['profissao'].upper()} — {p['jornada_semanal']:g} HORAS",dark,11,24)
            for j,v in enumerate(["Classes →","Nível","Regra vertical"]+[str(classes[k]) for k in indices],1):cell(main,row+2,j,v)
            main["formats"].append({"range":f"A{row+2}:{coluna(last)}{row+2}","fill":light,"bold":True,"align":"center"})
            main["heights"][str(row+2)]=28
            if n>1: main["merges"].append(f"A{row+3}:A{row+n+2}")
            cell(main,row+3,1,"Níveis ↓")
            for i,nivel in enumerate(niveis):
                r=row+3+i; reg=nivel["regra_vertical"]
                cell(main,r,2,nivel["codigo"])
                regtext="Base" if i==0 else (f"+{reg['valor']:g}{'%' if reg['tipo']=='percentual' else ' R$'} / {reg['nivel_referencia']}")
                if i==0:cell(main,r,3,regtext)
                else:
                    regformula=f'= "+"&TEXT(\'Parâmetros\'!D{19+i},"0.00")&IF(\'Parâmetros\'!C{19+i}="valor_fixo"," R$ / ","% / ")&\'Parâmetros\'!E{19+i}'
                    cell(main,r,3,f=regformula,cache=f"+{reg['valor']:.2f}{'%' if reg['tipo']=='percentual' else ' R$'} / {reg['nivel_referencia']}")
                main["heights"][str(r)]=26
                if i%2:main["formats"].append({"range":f"B{r}:{coluna(last)}{r}","fill":light})
                for j,k in enumerate(indices,4):
                    addr=f"{coluna(j)}{r}"; original=f"'Dados originais'!{coluna(4+k)}{4+i}"
                    formula=None; value=None; cached=None; fmt=MOEDA
                    if key=="estrutura":
                        fmt="0.00%"
                        if k==0: value="Entrada"
                        else:formula=f"='Parâmetros'!C{start_progress+k}/100";cached=p["progressoes_classes_percentuais"][k-1]/100
                    elif key in {"atual","conformidades"}:
                        formula=f"={original}";cached=nivel["valores"][k]
                    elif key=="referencia":
                        if k==0 and i==0:formula="='Parâmetros'!B13"
                        else:
                            if k==0:
                                refi=next(idx for idx,nv in enumerate(niveis) if nv['codigo']==reg['nivel_referencia'])
                                base=f"SUMIF('Parâmetros'!$A$19:$A${18+i},'Parâmetros'!E{19+i},$D${row+3}:$D${r-1})"
                                expression=f'IF(\'Parâmetros\'!C{19+i}="valor_fixo",{base}+\'Parâmetros\'!D{19+i},{base}*(1+\'Parâmetros\'!D{19+i}/100))'
                            else:expression=f"{positions[('referencia',i,k-1)]}*(1+'Parâmetros'!C{start_progress+k}/100)"
                            formula=f'=IF(\'Parâmetros\'!$B$12="truncar",ROUNDDOWN({expression},2),ROUND({expression},2))'
                        cached=a['tabela_referencia'][i]['valores'][k]
                    else:
                        formula=f"={positions[('atual',i,k)]}-{positions[('referencia',i,k)]}"
                        cached=a['diferencas'][i]['valores'][k]
                    cell(main,r,j,value,formula,cached,fmt)
                    positions[(key,i,k)]=addr
                if key in {"atual","conformidades"}:
                    main["conditional"].append({"range":f"D{r}:{coluna(end)}{r}","type":"expression","formula":f"=D{r}<$D$4","fill":VERMELHO,"color":"#000000"})
            main["formats"].append({"range":f"A{row+n+2}:{coluna(last)}{row+n+2}","bottom":dark})
            row+=n+5
        note(main,row,last,"Defasagem = referência ÷ atual − 1. Diferença mensal = atual − referência; negativa indica valor abaixo da referência.");row+=2
        split=max(4,last-3)
        main['merges'].extend([f"A{row}:{coluna(split-1)}{row+1}",f"{coluna(split)}{row}:{coluna(last)}{row+1}"])
        cell(main,row,1,"DEFASAGEM SALARIAL EM RELAÇÃO À REFERÊNCIA")
        cell(main,row,split,f=f"={positions[('referencia',0,0)]}/{positions[('atual',0,0)]}-1",cache=a['resumo']['defasagem_inicial_percentual']/100,fmt="0.00%")
        main['formats'].append({"range":f"A{row}:{coluna(last)}{row+1}","fill":VERMELHO,"fontColor":"#FFFFFF","bold":True,"size":16,"align":"center","wrap":True})
        main['heights'][str(row)]=30;main['heights'][str(row+1)]=24
        row+=5
    # Nomes completos sem ampliar as colunas monetárias do modelo.
    note(main,row,last,"Níveis: "+"; ".join(nv['codigo']+' — '+nv['descricao'] for nv in niveis),height=max(32,18*((n+3)//4)))
    main["print"] = f"A1:{coluna(last)}{row}"
    sources=sheet("Fontes e premissas",[32,90,25])
    band(sources,1,3,"FONTES E DECISÕES ADOTADAS",ROXO)
    notes=[("Organização", "Jornada (2).pdf, páginas impressas 9–11: estrutura, atual verde, referência roxa, não conformidades, diferenças e defasagem em vermelho."),
           ("Tabela municipal",a['arquivo_fonte']), ("URL tabela",a.get('url_fonte_tabela','')),
           ("Referência",ref['fonte']), ("URL referência",ref.get('url','')),
           ("Centavos",p['modo_arredondamento']+" em cada etapa. Padrão geral: arredondar. Cafezal: truncar para reproduzir o anexo."),
           ("Vigência",str(a['ano'])+"; não pressupõe que a tabela histórica seja a mais recente."),
           ("Regra da defasagem","(referência / atual - 1) × 100; o destaque usa a classe inicial, conforme o exemplo."),
           ("Valores atuais","Transcritos do documento. Permanecem preservados; somente referências são calculadas."),
           ("Uso da referência",ref['tipo']+": "+ref['nome']),
           ("Cores de alerta","Vermelho na tabela atual: vencimento abaixo da base de referência. Diferenças da carreira: atual menos referência."),
           ("Edição posterior","Ajuste valores, modo e progressões em Parâmetros/Dados originais. Mudança de fonte, profissão, vigência ou quantidade de classes: regenere pelo sistema.")]
    notes += [("Observação ao gerar",v) for v in a['avisos']]
    for r,(label,value) in enumerate(notes,3):
        cell(sources,r,1,label);cell(sources,r,2,value);sources['heights'][str(r)]=48
    sources['formats'].append({"range":f"A3:C{len(notes)+2}","wrap":True})
    return {"sheets":specs,"analysis":a}
