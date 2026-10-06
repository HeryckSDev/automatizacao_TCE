/* Integração DOM; não substitui uma inspeção visual em navegador. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require(process.env.JSDOM_PATH || 'jsdom');
const fixtures = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const dom = new JSDOM(fixtures.html, {url:'http://127.0.0.1:5000', runScripts:'outside-only'});
const {window:w} = dom, doc = w.document, calls = [], downloads = [], errors = [];
const el = id => doc.getElementById(id);
const tick = () => new Promise(resolve=>setTimeout(resolve,0));
let catalogo = fixtures.tabelas, proximaLeitura = fixtures.longo, falharFinanceiro = false, resolverFinanceiro;
w.addEventListener('error', e=>errors.push(e.error));
w.URL.createObjectURL = ()=>'blob:teste'; w.URL.revokeObjectURL = ()=>{};
w.HTMLAnchorElement.prototype.click = function(){if(this.download)downloads.push(this.download);};
w.fetch = async (url, options={})=>{
  const body = typeof options.body==='string'?JSON.parse(options.body):options.body;
  calls.push({url, body});
  const responder = (dados, status=200)=>({ok:status<400,status,json:async()=>structuredClone(dados)});
  if(url==='/api/municipios')return responder([{id:'1467',nome:'CRUZEIRO DO SUL'}]);
  if(url==='/api/automacao/tabelas')return responder(catalogo);
  if(url==='/api/automacao/exemplo-financeiro')return responder(fixtures.financeiro);
  if(url==='/api/automacao/financeiro'){
    await new Promise(resolve=>{resolverFinanceiro=resolve;});
    return falharFinanceiro?responder({erro:'A fonte não respondeu como esperado. Tente novamente em alguns instantes.'},502):responder(fixtures.financeiro);
  }
  if(url==='/api/automacao/preparar-tabela')return responder(proximaLeitura);
  if(url==='/api/automacao/salarios'){
    if(body.preparacao_id){catalogo=[...fixtures.tabelas,fixtures.salvo.tabela];return responder(fixtures.salvo);}
    return responder(fixtures.salarios);
  }
  throw new Error(`Chamada inesperada: ${url}`);
};
function change(id,value){el(id).value=value;el(id).dispatchEvent(new w.Event('change'));}
async function upload(){
  Object.defineProperty(el('salarios-arquivo'),'files',{configurable:true,value:[new w.File(['dados'],'tabela.csv',{type:'text/csv'})]});
  el('salarios-arquivo').dispatchEvent(new w.Event('change'));await tick();await tick();
}
async function main(){
  w.eval(fixtures.javascript);await tick();await tick();
  assert.equal(el('gerar-financeiro').disabled,false);
  assert.equal(el('financeiro-municipio').value,'');
  assert.equal(el('financeiro-inicio').disabled,true);
  el('financeiro-municipio').value='cruzeiro do sul';change('financeiro-periodo','ultimo');
  assert.equal(el('form-financeiro').checkValidity(),true);
  el('gerar-financeiro').click();await tick();
  assert.equal(el('gerar-financeiro').disabled,true);
  const pedido = calls.find(c=>c.url==='/api/automacao/financeiro').body;
  assert.deepEqual(pedido,{municipio_id:'1467',periodo:'ultimo'});
  resolverFinanceiro();await tick();await tick();
  assert.equal(downloads.length,1);assert.equal(el('gerar-financeiro').disabled,false);
  assert.equal(el('resultado-financeiro').hidden,false);
  el('resultado-financeiro').querySelector('button').click();assert.equal(downloads.length,2);
  falharFinanceiro=true;el('gerar-financeiro').click();await tick();resolverFinanceiro();await tick();
  assert.equal(downloads.length,2);assert.equal(el('resultado-financeiro').hidden,true);
  assert.match(el('financeiro-mensagem').textContent,/Tente novamente/);
  assert.equal(el('gerar-financeiro').disabled,false);

  el('aba-salarios').click();assert.equal(el('painel-financeiro').hidden,true);
  assert.equal(el('form-salarios').checkValidity(),true);
  el('gerar-salarios').click();await tick();await tick();
  assert.equal(downloads.length,3);
  assert.deepEqual(calls.find(c=>c.url==='/api/automacao/salarios').body,{tabela_id:'cafezal-2026'});
  el('usar-documento').click();await upload();
  assert.equal(el('preparacao-tabela').hidden,false);
  for(const div of doc.querySelectorAll('[data-complemento]')){assert.equal(div.hidden,true);assert.equal(div.querySelector('input').disabled,true);}
  assert.equal(el('form-salarios').checkValidity(),false);
  change('comparacao-tipo','percentual');el('comparacao-valor').value='5';
  assert.equal(el('form-salarios').checkValidity(),true);
  el('gerar-salarios').click();await tick();await tick();
  assert.equal(downloads.length,4);
  const uploadPedido=calls.filter(c=>c.url==='/api/automacao/salarios').at(-1).body;
  assert.deepEqual(uploadPedido.complementos,{});
  assert.deepEqual(uploadPedido.comparacao,{tipo:'percentual',valor:'5'});
  el('usar-tabela-salva').click();
  assert.equal(el('salarios-tabela').value,fixtures.salvo.tabela.id);
  assert.equal(el('form-salarios').checkValidity(),true);
  el('gerar-salarios').click();await tick();await tick();
  assert.equal(downloads.length,5);

  el('usar-documento').click();proximaLeitura=fixtures.matriz;await upload();
  for(const div of doc.querySelectorAll('[data-complemento]'))assert.equal(div.hidden,false);
  assert.equal(el('form-salarios').checkValidity(),false);
  const campos={municipio:'Cidade Teste',profissao:'Técnico',ano:'2026',jornada_semanal:'40'};
  for(const [k,v] of Object.entries(campos))el(`complemento-${k}`).value=v;
  change('comparacao-tipo','valor');el('comparacao-valor').value='2400';
  assert.equal(el('form-salarios').checkValidity(),true);
  proximaLeitura={...fixtures.longo,requer_conferencia_recorte:true};await upload();
  change('comparacao-tipo','percentual');el('comparacao-valor').value='5';
  assert.equal(el('conferir-recorte').hidden,false);
  assert.equal(el('form-salarios').checkValidity(),false);
  el('recorte-confirmado').checked=true;assert.equal(el('form-salarios').checkValidity(),true);
  assert.equal(errors.length,0);
  console.log('DOM aprovado: pedido financeiro mínimo, download automático, repetição, falha recuperável, salário preparado, leitura automática, preenchimento mínimo, reutilização e confirmação de recorte.');
}
main().then(()=>dom.window.close()).catch(e=>{console.error(e);dom.window.close();process.exitCode=1;});
