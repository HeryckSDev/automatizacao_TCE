/* Revisão explícita dos dados antes da comparação. Usa somente DOM seguro. */
const campoSalario = (id) => document.getElementById(id);
let candidatosSalariais = [];
function limparSelecaoImportada() {
  candidatosSalariais=[];campoSalario('salario-candidatos').replaceChildren();
  campoSalario('salario-candidatos').hidden=true;campoSalario('salario-texto-extraido').textContent='';
}

function camposReferenciaProfissao() {
  return {
    profissao: campoSalario('salario-profissao').value.trim(),
    lei: campoSalario('salario-lei').value.trim(),
    url_fonte_tabela: campoSalario('salario-tabela-url').value.trim(),
    jornada_confirmada_no_documento: campoSalario('salario-jornada-confirmada').checked,
    referencia: {
      tipo: campoSalario('salario-ref-tipo').value,
      nome: campoSalario('salario-ref-nome').value.trim(),
      valor: Number(salarioElementos.piso.value),
      jornada: Number(campoSalario('salario-ref-jornada').value),
      ano: Number(campoSalario('salario-ref-ano').value),
      proporcional: campoSalario('salario-proporcional').checked,
      fonte: campoSalario('salario-ref-fonte').value.trim(),
      url: campoSalario('salario-ref-url').value.trim(),
    },
  };
}

function invalidarSalario() {
  ultimaAnaliseSalarial = null;
  salarioElementos.resultado.hidden = true;
  campoSalario('salario-revisado').checked = false;
  salarioElementos.analisar.disabled = !entradaSalarial;
}

function carregarRevisao(dados) {
  entradaSalarial = structuredClone(dados);
  const d = entradaSalarial;
  const ref = d.referencia || (d.piso_nacional_40h ? {
    tipo: 'pspn', nome: `PSPN ${d.ano}`, valor: d.piso_nacional_40h, jornada: 40,
    ano: d.ano, proporcional: true, fonte: d.fonte_piso || '', url: d.url_fonte_piso || '',
  } : {tipo: 'cenario', nome: '', valor: '', jornada: d.jornada_semanal ?? '', ano: d.ano ?? '', fonte: '', url: ''});
  const values = {
    'salario-municipio': d.municipio || '', 'salario-profissao': d.profissao || '',
    'salario-ano': d.ano ?? '', 'salario-jornada': d.jornada_semanal ?? '',
    'salario-piso': ref.valor, 'salario-ref-tipo': ref.tipo, 'salario-ref-nome': ref.nome,
    'salario-ref-jornada': ref.jornada, 'salario-ref-ano': ref.ano,
    'salario-ref-fonte': ref.fonte, 'salario-ref-url': ref.url,
    'salario-lei': d.lei || '', 'salario-tabela-url': d.url_fonte_tabela || '',
    'salario-arredondamento': d.modo_arredondamento || 'arredondar',
  };
  for (const [id,value] of Object.entries(values)) campoSalario(id).value = value ?? '';
  campoSalario('salario-proporcional').checked = ref.proporcional === true;
  campoSalario('salario-jornada-confirmada').checked = d.jornada_confirmada_no_documento === true;
  d.classes ||= d.niveis[0].valores.map((_, i) => i + 1);
  d.progressoes_classes_percentuais ||= d.classes.slice(1).map(() => d.progressao_classes_percentual || 0);
  for (const [i,n] of d.niveis.entries()) n.regra_vertical ||= {tipo: i ? 'percentual' : 'base', valor: n.acrescimo_percentual || 0, nivel_referencia: i ? d.niveis[0].codigo : null};
  campoSalario('salario-importacao-avisos').textContent = (d.avisos_importacao || []).join(' ');
  campoSalario('salario-editor').hidden = false;
  salarioElementos.inicial.hidden = true;
  invalidarSalario();renderizarGradeSalarial();
  salarioElementos.mensagem.textContent = 'Tabela carregada. Revise a grade, defina a referência e clique em Recalcular referência.';
}

function renderizarGradeSalarial() {
  const d=entradaSalarial, table=document.createElement('table');
  function input(value,label,change,type='text') {
    const el=document.createElement('input');el.type=type;el.value=value ?? '';el.setAttribute('aria-label',label);
    if(type==='number'){el.step='0.0001';el.min='0';}
    el.addEventListener('change',()=>{change(type==='number' ? Number(el.value) : el.value.trim());invalidarSalario();});return el;
  }
  function td(row,element,header=false){const c=document.createElement(header?'th':'td');if(typeof element==='string')c.textContent=element;else c.append(element);row.append(c);}
  const head=table.createTHead().insertRow();
  for(const label of ['Nível','Descrição','Tipo de regra','Acréscimo','Sobre o nível'])td(head,label,true);
  d.classes.forEach((cl,j)=>td(head,input(cl,`Nome da classe ${j+1}`,v=>{d.classes[j]=v;}),true));
  const body=table.createTBody();
  const pro=body.insertRow();td(pro,'Progressão (%)');for(let i=0;i<4;i++)td(pro,'');
  d.classes.forEach((_,j)=>td(pro,j===0?'Entrada':input(d.progressoes_classes_percentuais[j-1],`Progressão para classe ${j+1}`,v=>{d.progressoes_classes_percentuais[j-1]=v;d.progressao_classes_origem='revisada';},'number')));
  d.niveis.forEach((n,i)=>{
    const row=body.insertRow();
    td(row,input(n.codigo,`Código do nível ${i+1}`,v=>{
      const anterior=n.codigo;n.codigo=v.toUpperCase();
      for(const level of d.niveis)if(level.regra_vertical.nivel_referencia===anterior)level.regra_vertical.nivel_referencia=n.codigo;
      renderizarGradeSalarial();
    }));
    td(row,input(n.descricao,`Descrição do nível ${i+1}`,v=>{n.descricao=v;}));
    if(i===0){td(row,'Base');td(row,'—');td(row,'—');}
    else{
      const sel=document.createElement('select');for(const [v,t] of [['percentual','Percentual (%)'],['valor_fixo','Valor fixo (R$)']])sel.add(new Option(t,v));
      sel.value=n.regra_vertical.tipo;sel.setAttribute('aria-label',`Regra do nível ${n.codigo}`);
      sel.addEventListener('change',()=>{n.regra_vertical.tipo=sel.value;invalidarSalario();});td(row,sel);
      td(row,input(n.regra_vertical.valor,`Acréscimo do nível ${n.codigo}`,v=>{n.regra_vertical.valor=v;},'number'));
      const sobre=document.createElement('select');for(const prev of d.niveis.slice(0,i))sobre.add(new Option(prev.codigo,prev.codigo));
      sobre.value=n.regra_vertical.nivel_referencia;sobre.setAttribute('aria-label',`Base do nível ${n.codigo}`);
      sobre.addEventListener('change',()=>{n.regra_vertical.nivel_referencia=sobre.value;invalidarSalario();});td(row,sobre);
    }
    n.valores.forEach((v,j)=>td(row,input(v,`Vencimento nível ${n.codigo}, classe ${d.classes[j]}`,value=>{n.valores[j]=value;},'number')));
  });
  campoSalario('salario-grade').replaceChildren(table);
}

salarioElementos.form.addEventListener('input',invalidarSalario);
salarioElementos.amostra.addEventListener('click',async()=>{
  try{limparSelecaoImportada();carregarRevisao(await requisicaoJson('/api/salarios/amostras/cafezal-do-sul-2026'));}
  catch(e){salarioElementos.mensagem.textContent=e.message;}
});
campoSalario('botao-salario-curitiba').addEventListener('click',async()=>{
  try{limparSelecaoImportada();carregarRevisao(await requisicaoJson('/api/salarios/amostras/curitiba-administrativo-2026'));}
  catch(e){salarioElementos.mensagem.textContent=e.message;}
});
campoSalario('botao-salario-novo').addEventListener('click',()=>{limparSelecaoImportada();carregarRevisao({niveis:[{codigo:'A',descricao:'Inicial',valores:[0]}],classes:['1'],arquivo_fonte:'Transcrição manual',avisos_importacao:['Preencha os valores a partir da tabela municipal. Nenhum salário foi presumido.']});});
for(const [id,action] of Object.entries({
  'salario-add-nivel':()=>{if(entradaSalarial.niveis.length>=100)return;let i=entradaSalarial.niveis.length+1;while(entradaSalarial.niveis.some(n=>n.codigo===`N${i}`))i++;entradaSalarial.niveis.push({codigo:`N${i}`,descricao:'Novo nível',regra_vertical:{tipo:'percentual',valor:0,nivel_referencia:entradaSalarial.niveis[0].codigo},valores:entradaSalarial.classes.map(()=>0)});},
  'salario-add-classe':()=>{if(entradaSalarial.classes.length>=200)return;let label=entradaSalarial.classes.length+1;while(entradaSalarial.classes.some(c=>String(c)===String(label)))label++;entradaSalarial.classes.push(String(label));entradaSalarial.progressoes_classes_percentuais.push(0);entradaSalarial.niveis.forEach(n=>n.valores.push(0));},
  'salario-rem-nivel':()=>{if(entradaSalarial.niveis.length>1)entradaSalarial.niveis.pop();},
  'salario-rem-classe':()=>{if(entradaSalarial.classes.length>1){entradaSalarial.classes.pop();entradaSalarial.progressoes_classes_percentuais.pop();entradaSalarial.niveis.forEach(n=>n.valores.pop());}},
}))campoSalario(id).addEventListener('click',()=>{if(!entradaSalarial)return;action();invalidarSalario();renderizarGradeSalarial();});

salarioElementos.importarForm.addEventListener('submit',async(event)=>{
  event.preventDefault();const button=event.currentTarget.querySelector('button');button.disabled=true;
  invalidarSalario();salarioElementos.mensagem.textContent='Extraindo as tabelas para revisão…';
  try{
    const result=await requisicaoJson('/api/salarios/extrair-revisao',{method:'POST',body:new FormData(event.currentTarget)});
    candidatosSalariais=result.candidatos;
    const select=campoSalario('salario-candidatos');select.replaceChildren();
    candidatosSalariais.forEach((d,i)=>select.add(new Option(`${d.municipio || 'Município a informar'} · ${d.profissao || d.arquivo_fonte} · ${d.jornada_semanal || '?'} h · ${d.ano || '?'}`,String(i))));
    select.hidden=candidatosSalariais.length<2;
    if(candidatosSalariais.length)carregarRevisao(candidatosSalariais[0]);
    else{entradaSalarial=null;salarioElementos.analisar.disabled=true;campoSalario('salario-grade').replaceChildren();}
    campoSalario('salario-editor').hidden=false;
    campoSalario('salario-texto-extraido').textContent=result.texto_extraido || 'Consulte o arquivo original.';
    campoSalario('salario-importacao-avisos').textContent=[...result.pendencias,...(entradaSalarial?.avisos_importacao || [])].join(' ');
    salarioElementos.mensagem.textContent=`${candidatosSalariais.length} tabela(s) disponível(is). Revise antes de comparar.`;
  }catch(e){entradaSalarial=null;salarioElementos.analisar.disabled=true;salarioElementos.mensagem.textContent=e.message;}
  finally{button.disabled=false;}
});
campoSalario('salario-candidatos').addEventListener('change',e=>carregarRevisao(candidatosSalariais[Number(e.target.value)]));

// A revisão detalhada pode continuar uma leitura iniciada na tela simplificada.
try {
  const pendente = sessionStorage.getItem('jornada-revisao');
  if (pendente) {
    const dados = JSON.parse(pendente);
    if (dados && Array.isArray(dados.niveis) && dados.niveis.length) carregarRevisao(dados);
    sessionStorage.removeItem('jornada-revisao');
  }
} catch { /* A navegação continua normalmente se o navegador bloquear o armazenamento. */ }

// Saída assistida para layouts não reconhecidos: sem alteração de código.
campoSalario('salario-criar-manual').addEventListener('click',()=>{
  carregarRevisao({classes:['Inicial'],niveis:[{codigo:'N1',descricao:'Informe o nível',valores:[''],regra_vertical:{tipo:'base',valor:0,nivel_referencia:null}}],
    progressoes_classes_percentuais:[],progressao_classes_origem:'revisada',arquivo_fonte:'Transcrição manual: informe o documento original',
    avisos_importacao:['Tabela montada manualmente. Preencha os valores e nomes, acrescente classes/níveis e confira no documento antes de calcular.']});
  campoSalario('salario-editor').scrollIntoView({behavior:'smooth',block:'start'});
});
