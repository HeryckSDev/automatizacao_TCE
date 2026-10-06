/* Ações completas: selecionar, gerar e receber. Revisão só quando necessária. */
const el = id => document.getElementById(id);
let municipios = [], tabelas = [], preparacao = null, usandoDocumento = false;
const resultados = {};
const normalizar = texto => String(texto).normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();

async function api(url, opcoes = {}) {
  const resposta = await fetch(url, opcoes);
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const erro = new Error(dados.erro || 'Não foi possível concluir agora. Tente novamente.');
    erro.status = resposta.status;
    throw erro;
  }
  return dados;
}
const enviar = (url, dados) => api(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(dados)});
function mensagem(area, texto, erro = false) { el(`${area}-mensagem`).textContent=texto;el(`${area}-mensagem`).dataset.erro=String(erro); }
function ocupar(area, ocupado) {
  for (const campo of el(`form-${area}`).querySelectorAll('input,select,button')) {
    if (ocupado) { campo.dataset.desabilitadoAntes=String(campo.disabled);campo.disabled=true; }
    else if ('desabilitadoAntes' in campo.dataset) {campo.disabled=campo.dataset.desabilitadoAntes==='true';delete campo.dataset.desabilitadoAntes;}
  }
  el(`gerar-${area}`).dataset.ocupado=String(ocupado);
  el(`gerar-${area}`).textContent=ocupado?'Preparando seu Excel…':'Gerar Excel';
  el(`form-${area}`).setAttribute('aria-busy',String(ocupado));
}
function formatarTempo(segundos) { return segundos < 60 ? `${segundos} s` : `${Math.floor(segundos/60)} min ${String(segundos%60).padStart(2,'0')} s`; }
/* Mostra que o sistema está trabalhando: barra, tempo decorrido e textos que mudam devagar (leitores de tela não são avisados a cada segundo). */
function acompanhar(area, etapas) {
  const caixa = el(`progresso-${area}`), tempo = el(`tempo-${area}`), inicio = Date.now();
  let exibida = -1;
  const atualizar = () => {
    const segundos = Math.floor((Date.now()-inicio)/1000);
    tempo.textContent = formatarTempo(segundos);
    let atual = 0; etapas.forEach(([limite], indice) => { if (segundos >= limite) atual = indice; });
    if (atual !== exibida) { exibida = atual; mensagem(area, etapas[atual][1]); }
  };
  caixa.hidden = false; atualizar();
  const relogio = setInterval(atualizar, 1000);
  return () => { clearInterval(relogio); caixa.hidden = true; };
}
function baixar(arquivo) {
  const bytes=Uint8Array.from(atob(arquivo.conteudo_base64),c=>c.charCodeAt(0));
  const url=URL.createObjectURL(new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));
  const link=document.createElement('a');link.href=url;link.download=arquivo.nome;
  document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
}
function mostrarResultado(area, dados) {
  resultados[area]=dados;
  const box=el(`resultado-${area}`);box.replaceChildren();box.hidden=false;
  const titulo=document.createElement('h3');titulo.textContent=dados.exemplo?'Exemplo pronto':'Seu Excel está pronto';
  const resumo=document.createElement('p');resumo.textContent=`${dados.titulo} · ${dados.periodo}`;
  const botao=document.createElement('button');botao.type='button';botao.textContent='Baixar Excel novamente';botao.addEventListener('click',()=>baixar(dados.arquivo));
  box.append(titulo,resumo,botao);
  if(dados.avisos?.length){const detalhes=document.createElement('details'),sum=document.createElement('summary'),lista=document.createElement('ul');sum.textContent='Observações incluídas na planilha';for(const aviso of dados.avisos){const li=document.createElement('li');li.textContent=aviso;lista.appendChild(li);}detalhes.append(sum,lista);box.appendChild(detalhes);}
  const nota=document.createElement('p');nota.className='nota';nota.textContent='O download foi solicitado. Se não aparecer, use o botão acima.';box.appendChild(nota);
  baixar(dados.arquivo);
}
function escolherAba(area) {
  for(const nome of ['financeiro','salarios']){el(`painel-${nome}`).hidden=nome!==area;el(`aba-${nome}`).setAttribute('aria-selected',String(nome===area));}
}
for(const area of ['financeiro','salarios'])el(`aba-${area}`).addEventListener('click',()=>escolherAba(area));

async function carregarMunicipios() {
  el('financeiro-municipio').disabled=true;el('gerar-financeiro').disabled=true;el('repetir-municipios').hidden=true;
  for(let tentativa=0;tentativa<2;tentativa++){
    try{
      municipios=await api('/api/municipios');if(!municipios.length)throw new Error('A lista de municípios ainda não está disponível.');
      const lista=el('lista-municipios');lista.replaceChildren();for(const m of municipios){const opcao=document.createElement('option');opcao.value=m.nome;lista.appendChild(opcao);}
      try{const anterior=localStorage.getItem('jornada-municipio');if(municipios.some(m=>m.nome===anterior))el('financeiro-municipio').value=anterior;}catch{}
      el('financeiro-municipio').disabled=false;el('gerar-financeiro').disabled=false;mensagem('financeiro','Escolha o município e clique em Gerar Excel.');return;
    }catch(erro){
      if(tentativa===0){mensagem('financeiro','A lista demorou a responder. Estamos tentando novamente…');continue;}
      mensagem('financeiro','Não conseguimos carregar os municípios agora. Você pode tentar novamente ou abrir o exemplo pronto.',true);el('repetir-municipios').hidden=false;
    }
  }
}
el('repetir-municipios').addEventListener('click',carregarMunicipios);
el('financeiro-periodo').addEventListener('change',()=>{const custom=el('financeiro-periodo').value==='intervalo';el('financeiro-intervalo').hidden=!custom;for(const id of ['financeiro-inicio','financeiro-fim']){el(id).required=custom;el(id).disabled=!custom;}});
el('financeiro-periodo').dispatchEvent(new Event('change'));
el('form-financeiro').addEventListener('submit',async evento=>{
  evento.preventDefault();
  const municipio=municipios.find(m=>normalizar(m.nome)===normalizar(el('financeiro-municipio').value));
  if(!municipio){mensagem('financeiro','Escolha um município da lista que aparece enquanto você digita.',true);return;}
  const pedido={municipio_id:municipio.id,periodo:el('financeiro-periodo').value};
  if(pedido.periodo==='intervalo'){pedido.ano_inicial=el('financeiro-inicio').value;pedido.ano_final=el('financeiro-fim').value;}
  try{localStorage.setItem('jornada-municipio',municipio.nome);}catch{}
  ocupar('financeiro',true);el('resultado-financeiro').hidden=true;
  const parar=acompanhar('financeiro',[[0,'Buscando os dados no TCE-PR e organizando a planilha…'],[20,'A consulta continua. O histórico completo pode levar alguns minutos.'],[120,'Ainda consultando. Você pode aguardar nesta tela; o Excel será baixado quando terminar.']]);
  try{const dados=await enviar('/api/automacao/financeiro',pedido);parar();mostrarResultado('financeiro',dados);mensagem('financeiro','Pronto. A planilha foi gerada.');}
  catch(erro){parar();mensagem('financeiro',erro.message,true);}
  finally{ocupar('financeiro',false);}
});
el('exemplo-financeiro').addEventListener('click',async()=>{
  el('exemplo-financeiro').disabled=true;
  try{mostrarResultado('financeiro',await api('/api/automacao/exemplo-financeiro'));mensagem('financeiro','Exemplo de Curitiba com dados preservados.');}
  catch(erro){mensagem('financeiro',erro.message,true);}finally{el('exemplo-financeiro').disabled=false;}
});

function descreverTabela() { const tabela=tabelas.find(t=>t.id===el('salarios-tabela').value);el('salarios-descricao').textContent=tabela?`${tabela.descricao} Origem: ${tabela.origem}.`:'';el('gerar-salarios').disabled=usandoDocumento?!preparacao?.candidatos.length:!tabela; }
async function carregarTabelas(preferida) {
  try{tabelas=await api('/api/automacao/tabelas');const select=el('salarios-tabela');select.replaceChildren();for(const t of tabelas)select.add(new Option(`${t.municipio} · ${t.profissao} · ${t.ano}`,t.id));if(preferida)select.value=preferida;select.disabled=usandoDocumento;descreverTabela();}
  catch(erro){mensagem('salarios','Não conseguimos abrir as tabelas preparadas. Você ainda pode enviar um documento.',true);}
}
function modoDocumento(ativo) {
  usandoDocumento=ativo;el('tabela-salva').hidden=ativo;el('nova-tabela').hidden=!ativo;el('salarios-tabela').disabled=ativo;
  for(const controle of el('nova-tabela').querySelectorAll('input,select'))controle.disabled=!ativo;
  if(ativo&&preparacao?.candidatos.length)mostrarCandidato();
  else if(ativo){el('gerar-salarios').disabled=true;mensagem('salarios','Escolha o arquivo. Vamos identificar a tabela para você.');}
  else{el('gerar-salarios').disabled=!tabelas.length;mensagem('salarios','');}
}
el('usar-documento').addEventListener('click',()=>modoDocumento(true));
el('usar-tabela-salva').addEventListener('click',()=>modoDocumento(false));
el('salarios-tabela').addEventListener('change',descreverTabela);
const LIMITE_FILTRO = 8;
function rotuloCandidato(c, i) {
  const e = c.exibicao;
  if (e) return `${e.titulo} · ${e.detalhe}`;
  return [c.profissao, c.municipio, c.jornada_semanal ? `${c.jornada_semanal} h` : null, c.arquivo_fonte].filter(Boolean).join(' · ') || `Tabela ${i+1}`;
}
function montarLista(filtro = '') {
  const select = el('salarios-candidato'), total = preparacao.candidatos.length, termo = normalizar(filtro);
  const anterior = select.value;
  select.replaceChildren();
  const grupos = new Map();
  preparacao.candidatos.forEach((c, i) => {
    const rotulo = rotuloCandidato(c, i);
    const grupo = c.exibicao?.grupo || '';
    if (termo && !normalizar(`${grupo} ${rotulo}`).includes(termo)) return;
    if (!grupos.has(grupo)) grupos.set(grupo, []);
    grupos.get(grupo).push(new Option(rotulo, String(i)));
  });
  const comGrupos = [...grupos.keys()].filter(Boolean).length > 1;
  for (const [grupo, opcoes] of grupos) {
    if (comGrupos && grupo) { const bloco = document.createElement('optgroup'); bloco.label = grupo; bloco.append(...opcoes); select.appendChild(bloco); }
    else select.append(...opcoes);
  }
  const mostradas = select.options.length;
  el('contagem-candidato').textContent = !termo ? `${total} tabelas encontradas no documento.` : (mostradas ? `${mostradas} de ${total} tabelas.` : 'Nenhuma tabela com esse texto. Apague o filtro para ver todas.');
  if (mostradas) { select.value = [...select.options].some(o => o.value === anterior) ? anterior : select.options[0].value; if (select.value !== anterior) mostrarCandidato(); }
  else { el('gerar-salarios').disabled = true; }
}
el('filtro-candidato').addEventListener('input', () => montarLista(el('filtro-candidato').value));
function candidatoAtual(){return preparacao?.candidatos[Number(el('salarios-candidato').value||0)];}
function ajustarComparacao(){const precisa=usandoDocumento&&!el('definir-comparacao').hidden;const tipo=el('comparacao-tipo').value;const valor=precisa&&['valor','percentual'].includes(tipo);el('comparacao-tipo').required=precisa;el('comparacao-tipo').disabled=!precisa;el('comparacao-valor-campo').hidden=!valor;el('comparacao-valor').disabled=!valor;el('comparacao-valor').required=valor;el('comparacao-valor').min=tipo==='percentual'?'0':'0.01';if(tipo==='percentual')el('comparacao-valor').max='100';else el('comparacao-valor').removeAttribute('max');el('comparacao-valor-rotulo').textContent=tipo==='percentual'?'Reajuste desejado (%)':'Valor inicial de referência (R$)';}
el('comparacao-tipo').addEventListener('change',ajustarComparacao);
function mostrarAvisos(avisos) {
  const area = el('avisos-leitura'); area.replaceChildren();
  const unicos = [...new Set(avisos.filter(Boolean))];
  if (!unicos.length) return;
  const lista = document.createElement('ul'); lista.className = 'avisos';
  for (const aviso of unicos.slice(0, 3)) { const item = document.createElement('li'); item.textContent = aviso; lista.appendChild(item); }
  area.appendChild(lista);
  if (unicos.length > 3) {
    const mais = document.createElement('details'), titulo = document.createElement('summary'), resto = document.createElement('ul');
    titulo.textContent = `Mais ${unicos.length-3} observações`; resto.className = 'avisos';
    for (const aviso of unicos.slice(3)) { const item = document.createElement('li'); item.textContent = aviso; resto.appendChild(item); }
    mais.append(titulo, resto); area.appendChild(mais);
  }
}
function mostrarCandidato(){
  const dados=candidatoAtual();if(!dados)return;
  el('preparacao-tabela').hidden=false;el('gerar-salarios').disabled=false;
  for(const container of document.querySelectorAll('[data-complemento]')){const chave=container.dataset.complemento;const falta=dados[chave]===undefined||dados[chave]===null||dados[chave]==='';container.hidden=!falta;const input=container.querySelector('input');input.value='';input.required=falta;input.disabled=!falta;}
  const partes=[dados.municipio,dados.profissao,dados.ano,dados.jornada_semanal?`${dados.jornada_semanal} h/semana`:null].filter(Boolean);
  const escolhida=dados.exibicao?`Tabela escolhida: ${dados.exibicao.titulo}${dados.exibicao.grupo&&dados.exibicao.grupo!=='Outras tabelas'?` (${dados.exibicao.grupo})`:''} — ${dados.exibicao.detalhe}.`:'';
  const lido=partes.length?`Identificado no arquivo: ${partes.join(' · ')}`:'A tabela foi lida. Complete apenas as informações que não apareceram no documento.';
  el('dados-encontrados').textContent=[escolhida,lido].filter(Boolean).join('\n');
  el('definir-comparacao').hidden=Boolean(dados.referencia||dados.piso_nacional_40h);
  el('comparacao-tipo').value='';el('comparacao-valor').value='';ajustarComparacao();
  el('conferir-recorte').hidden=!preparacao.requer_conferencia_recorte;el('recorte-confirmado').required=Boolean(preparacao.requer_conferencia_recorte);el('recorte-confirmado').checked=false;
  const tabela=document.createElement('table'),cabecalho=tabela.createTHead().insertRow();
  const classes=dados.classes||dados.niveis[0].valores.map((_,i)=>i+1);
  for(const titulo of ['Nível',...classes]){const c=document.createElement('th');c.textContent=titulo;cabecalho.appendChild(c);}
  const corpo=tabela.createTBody();for(const nivel of dados.niveis){const linha=corpo.insertRow();for(const valor of [nivel.codigo,...nivel.valores]){const c=linha.insertCell();c.textContent=typeof valor==='number'?valor.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}):valor;}}
  el('preview-tabela').replaceChildren(tabela);mostrarAvisos([...(preparacao.pendencias||[]),...(dados.avisos_importacao||[])]);
}
el('salarios-candidato').addEventListener('change',mostrarCandidato);
el('salarios-arquivo').addEventListener('change',async()=>{
  const arquivo=el('salarios-arquivo').files[0];if(!arquivo)return;
  preparacao=null;el('preparacao-tabela').hidden=true;el('resultado-salarios').hidden=true;el('gerar-salarios').disabled=true;
  ocupar('salarios',true);
  const grande=arquivo.size>1024*1024;
  const parar=acompanhar('salarios',[[0,grande?'Lendo o documento. Arquivos grandes podem levar cerca de 30 segundos.':'Lendo o documento e procurando as tabelas…'],[30,'Ainda lendo. Documentos com muitas páginas podem levar mais de 1 minuto.']]);
  try{
    const dados=new FormData();dados.append('arquivo',arquivo);preparacao=await api('/api/automacao/preparar-tabela',{method:'POST',body:dados});
    parar();
    el('filtro-candidato').value='';el('filtro-candidato-campo').hidden=preparacao.candidatos.length<LIMITE_FILTRO;
    montarLista();
    el('escolha-candidato').hidden=preparacao.candidatos.length<2;
    mensagem('salarios',preparacao.candidatos.length?'Tabela encontrada. Complete somente o que faltar e gere o Excel.':'Não conseguimos identificar uma tabela completa. Abra a revisão detalhada para montar ou corrigir a tabela; também pode enviar Excel/CSV.',!preparacao.candidatos.length);
  }catch(erro){parar();mensagem('salarios',erro.message,true);}finally{ocupar('salarios',false);if(preparacao?.candidatos.length)mostrarCandidato();else el('gerar-salarios').disabled=true;}
});
function complementos(){const dados={};for(const container of document.querySelectorAll('[data-complemento]'))if(!container.hidden)dados[container.dataset.complemento]=container.querySelector('input').value.trim();return dados;}
el('revisar-detalhes').addEventListener('click',()=>{try{sessionStorage.setItem('jornada-revisao',JSON.stringify({...candidatoAtual(),...complementos()}));}catch{}});
el('form-salarios').addEventListener('submit',async evento=>{
  evento.preventDefault();let pedido;
  if(usandoDocumento){
    if(!preparacao?.candidatos.length){mensagem('salarios','Escolha um documento para começar.',true);return;}
    pedido={preparacao_id:preparacao.preparacao_id,candidato:Number(el('salarios-candidato').value||0),complementos:complementos(),confirmar_recorte:el('recorte-confirmado').checked};
    if(!el('definir-comparacao').hidden)pedido.comparacao={tipo:el('comparacao-tipo').value,valor:el('comparacao-valor').value};
  }else pedido={tabela_id:el('salarios-tabela').value};
  ocupar('salarios',true);el('resultado-salarios').hidden=true;
  const parar=acompanhar('salarios',[[0,'Comparando os salários e montando o Excel…'],[15,'Tabelas grandes levam mais tempo. Continuamos trabalhando.']]);
  let concluido=null;
  try{concluido=await enviar('/api/automacao/salarios',pedido);parar();mostrarResultado('salarios',concluido);mensagem('salarios',usandoDocumento?'Pronto. Essa preparação também ficou salva para as próximas consultas.':'Pronto. A comparação foi gerada.');}
  catch(erro){parar();mensagem('salarios',erro.message,true);}finally{ocupar('salarios',false);}
  if(concluido)await carregarTabelas(concluido.tabela.id);
});
modoDocumento(false);carregarMunicipios();carregarTabelas();
