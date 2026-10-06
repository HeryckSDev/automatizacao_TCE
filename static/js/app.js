const ANOS_DEMO_CURITIBA = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  .map((ano) => ({ id: String(ano), nome: String(ano) }));

const elementos = {
  form: document.querySelector("#form-analise"),
  municipio: document.querySelector("#municipio"),
  entidade: document.querySelector("#entidade"),
  ano: document.querySelector("#ano"),
  anoInicial: document.querySelector("#ano-inicial"),
  anoFinal: document.querySelector("#ano-final"),
  campoAno: document.querySelector("#campo-ano-anual"),
  camposHistorico: document.querySelector("#campos-historico"),
  incluirFundeb: document.querySelector("#incluir-fundeb"),
  mensagem: document.querySelector("#mensagem-form"),
  fonteStatus: document.querySelector("#status-fonte-tce"),
  recarregar: document.querySelector("#botao-recarregar-tce"),
  analisar: document.querySelector("#botao-analisar"),
  amostra: document.querySelector("#botao-amostra"),
  exportar: document.querySelector("#botao-exportar"),
  inicial: document.querySelector("#estado-inicial"),
  carregamento: document.querySelector("#carregamento"),
  anual: document.querySelector("#resultado-anual"),
  historico: document.querySelector("#resultado-historico"),
  tempo: document.querySelector("#tempo-estimado"),
};

let ultimoResultado = null;
let entradaSalarial = null;
let ultimaAnaliseSalarial = null;

const salarioElementos = {
  form: document.querySelector("#form-salarial"),
  importarForm: document.querySelector("#form-importar-salarios"),
  municipio: document.querySelector("#salario-municipio"),
  ano: document.querySelector("#salario-ano"),
  jornada: document.querySelector("#salario-jornada"),
  piso: document.querySelector("#salario-piso"),
  arredondamento: document.querySelector("#salario-arredondamento"),
  amostra: document.querySelector("#botao-salario-amostra"),
  analisar: document.querySelector("#botao-salario-analisar"),
  mensagem: document.querySelector("#salario-mensagem"),
  inicial: document.querySelector("#salario-estado-inicial"),
  resultado: document.querySelector("#resultado-salarial"),
  excel: document.querySelector("#botao-salario-excel"),
  pdf: document.querySelector("#botao-salario-pdf"),
};

const dossieElementos = {
  form: document.querySelector("#form-dossie-salarial"),
  catalogo: document.querySelector("#dossie-fonte-catalogo"),
  detalhes: document.querySelector("#dossie-fonte-detalhes"),
  link: document.querySelector("#dossie-fonte-link"),
  municipio: document.querySelector("#dossie-municipio"),
  uf: document.querySelector("#dossie-uf"),
  ano: document.querySelector("#dossie-ano"),
  tipoFonte: document.querySelector("#dossie-tipo-fonte"),
  fonteUrl: document.querySelector("#dossie-fonte-url"),
  resultado: document.querySelector("#dossie-resultado"),
};

let fontesSalariais = [];

const moedaFormatador = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const moeda = (valor) => valor === null || valor === undefined ? "Não disponível" : moedaFormatador.format(Number(valor));
const percentual = (valor) => valor === null || valor === undefined ? "—" : `${Number(valor).toFixed(2).replace(".", ",")}%`;
const variacao = (valor) => {
  if (valor === null || valor === undefined) return "—";
  const numero = Number(valor);
  return `${numero > 0 ? "+" : ""}${numero.toFixed(2).replace(".", ",")}%`;
};
const nomeSelecionado = (select) => select.options[select.selectedIndex]?.text || "";
const modoAtual = () => document.querySelector('input[name="modo"]:checked').value;

async function requisicaoJson(url, opcoes = {}) {
  const resposta = await fetch(url, opcoes);
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(dados.erro || `Falha na requisição (${resposta.status})`);
  return dados;
}

function preencherSelect(select, opcoes, valorPreferido) {
  const valorAnterior = select.value;
  select.replaceChildren();
  for (const opcao of opcoes) {
    const item = document.createElement("option");
    item.value = opcao.id;
    item.textContent = opcao.nome;
    select.appendChild(item);
  }
  const alvo = opcoes.some((opcao) => opcao.id === valorPreferido)
    ? valorPreferido
    : opcoes.some((opcao) => opcao.id === valorAnterior) ? valorAnterior : opcoes[0]?.id;
  if (alvo) select.value = alvo;
}

function mostrarFonteSalarial() {
  const identificador = dossieElementos.catalogo.value;
  const fonte = fontesSalariais.find((item) => item.id === identificador);
  dossieElementos.detalhes.replaceChildren();
  if (!fonte) {
    dossieElementos.detalhes.textContent = identificador === "outro"
      ? "Informe manualmente o município e a URL de uma página oficial. Priorize prefeitura, portal da transparência ou diário oficial."
      : "Selecione uma fonte para ver onde procurar e o que baixar.";
    dossieElementos.link.hidden = true;
    if (identificador === "outro") {
      dossieElementos.municipio.value = "";
      dossieElementos.fonteUrl.value = "";
      dossieElementos.municipio.focus();
    }
    return;
  }

  const titulo = document.createElement("strong");
  titulo.textContent = `${fonte.municipio}/${fonte.uf}`;
  const orientacao = document.createElement("div");
  orientacao.textContent = fonte.orientacao;
  const formatos = document.createElement("span");
  formatos.textContent = `Formato observado: ${fonte.formatos_observados.join(", ")}. ${fonte.observacao}`;
  dossieElementos.detalhes.append(titulo, orientacao, formatos);
  dossieElementos.link.href = fonte.pagina_oficial;
  dossieElementos.link.hidden = false;
  dossieElementos.municipio.value = fonte.municipio;
  dossieElementos.uf.value = fonte.uf;
  dossieElementos.tipoFonte.value = "portal_prefeitura";
  dossieElementos.fonteUrl.value = fonte.pagina_oficial;
}

async function carregarFontesSalariais() {
  try {
    fontesSalariais = await requisicaoJson("/api/salarios/fontes");
    dossieElementos.catalogo.replaceChildren(new Option("Selecione um município…", ""));
    for (const fonte of fontesSalariais) {
      dossieElementos.catalogo.appendChild(new Option(`${fonte.municipio}/${fonte.uf}`, fonte.id));
    }
    dossieElementos.catalogo.appendChild(new Option("Outro município (informar manualmente)", "outro"));
    dossieElementos.catalogo.disabled = false;
  } catch (erro) {
    dossieElementos.catalogo.replaceChildren(new Option("Catálogo indisponível", ""));
    dossieElementos.detalhes.textContent = `${erro.message} Ainda é possível informar a URL oficial manualmente.`;
    dossieElementos.municipio.disabled = false;
    dossieElementos.fonteUrl.disabled = false;
  }
}

function mostrarDossieRegistrado(dados) {
  dossieElementos.resultado.replaceChildren();
  const titulo = document.createElement("strong");
  titulo.textContent = `Dossiê ${dados.status === "completo_para_triagem" ? "completo" : "parcial"} registrado.`;
  const local = document.createElement("p");
  local.textContent = `Originais preservados em ${dados.localizacao_relativa}.`;
  const lista = document.createElement("ul");
  for (const arquivo of dados.arquivos) {
    const item = document.createElement("li");
    const alertas = [];
    if (arquivo.requer_ocr) alertas.push("requer OCR");
    if (arquivo.requer_conversao) alertas.push("requer conversão");
    item.textContent = `${arquivo.categoria_descricao}: ${arquivo.nome_original} · SHA-256 ${arquivo.sha256.slice(0, 12)}…${alertas.length ? ` · ${alertas.join(", ")}` : ""}`;
    lista.appendChild(item);
  }
  dossieElementos.resultado.append(titulo, local, lista);
  if (dados.itens_recomendados_ausentes.length) {
    const pendencia = document.createElement("p");
    pendencia.textContent = `Ainda recomendado: ${dados.itens_recomendados_ausentes.join(", ").replaceAll("_", " ")}.`;
    dossieElementos.resultado.appendChild(pendencia);
  }
}

function preencherAnos(opcoes) {
  const ordenadas = [...opcoes].sort((a, b) => Number(b.id) - Number(a.id));
  preencherSelect(elementos.ano, ordenadas, null);
  preencherSelect(elementos.anoInicial, ordenadas, "2019");
  preencherSelect(elementos.anoFinal, ordenadas, ordenadas[0]?.id);
}

function atualizarEstadoFonte(estado, mensagem) {
  elementos.fonteStatus.dataset.estado = estado;
  elementos.fonteStatus.textContent = mensagem;
}

function bloquearConsultaAoVivo(bloqueada) {
  elementos.analisar.disabled = bloqueada;
  elementos.recarregar.hidden = !bloqueada;
}

async function carregarMunicipios() {
  elementos.municipio.disabled = true;
  elementos.entidade.disabled = true;
  bloquearConsultaAoVivo(true);
  atualizarEstadoFonte("carregando", "Conectando ao catálogo do TCE-PR…");
  elementos.mensagem.textContent = "A lista oficial pode levar alguns segundos. A demonstração de Curitiba continua disponível offline.";
  try {
    const municipios = await requisicaoJson("/api/municipios");
    if (!municipios.length) throw new Error("O TCE-PR não retornou municípios.");
    preencherSelect(elementos.municipio, municipios, "1490");
    elementos.municipio.disabled = false;
    atualizarEstadoFonte("carregando", `${municipios.length} municípios encontrados; carregando entidades…`);
    const carregado = await carregarEntidades();
    if (!carregado) return;
    atualizarEstadoFonte("pronto", `${municipios.length} municípios disponíveis para consulta ao vivo.`);
    elementos.mensagem.textContent = "Catálogo oficial pronto. Escolha município, entidade e período; Curitiba é apenas a demonstração offline.";
  } catch (erro) {
    preencherSelect(elementos.municipio, [{ id: "", nome: "Consulta ao vivo indisponível" }], null);
    preencherSelect(elementos.entidade, [{ id: "", nome: "Tente carregar novamente" }], null);
    elementos.municipio.disabled = true;
    elementos.entidade.disabled = true;
    bloquearConsultaAoVivo(true);
    atualizarEstadoFonte("erro", "TCE-PR indisponível agora; nenhuma consulta ao vivo foi simulada.");
    elementos.mensagem.textContent = `${erro.message} Use a demonstração offline ou tente carregar a fonte novamente.`;
    preencherAnos(ANOS_DEMO_CURITIBA);
  }
}

async function carregarEntidades() {
  bloquearConsultaAoVivo(true);
  atualizarEstadoFonte("carregando", "Carregando entidades do município selecionado…");
  elementos.entidade.disabled = true;
  elementos.entidade.replaceChildren(new Option("Carregando entidades…", ""));
  try {
    const entidades = await requisicaoJson(`/api/entidades/${elementos.municipio.value}`);
    preencherSelect(elementos.entidade, entidades, elementos.municipio.value === "1490" ? "12268" : null);
    const carregado = await carregarAnos();
    if (!carregado) return false;
    bloquearConsultaAoVivo(false);
    return true;
  } catch (erro) {
    elementos.entidade.replaceChildren(new Option("Não foi possível carregar", ""));
    elementos.mensagem.textContent = `${erro.message} Tente carregar a fonte novamente.`;
    atualizarEstadoFonte("erro", "Falha ao obter as entidades do município selecionado.");
    bloquearConsultaAoVivo(true);
    return false;
  } finally {
    elementos.entidade.disabled = false;
  }
}

async function carregarAnos() {
  bloquearConsultaAoVivo(true);
  atualizarEstadoFonte("carregando", "Carregando exercícios fechados da entidade…");
  try {
    const anos = await requisicaoJson(`/api/anos/${elementos.municipio.value}/${elementos.entidade.value}`);
    if (!anos.length) throw new Error("Nenhum exercício fechado foi encontrado.");
    preencherAnos(anos);
    bloquearConsultaAoVivo(false);
    atualizarEstadoFonte("pronto", "Município, entidade e exercícios prontos para consulta ao vivo.");
    return true;
  } catch (erro) {
    elementos.mensagem.textContent = `${erro.message} A consulta ao vivo foi bloqueada para evitar usar anos inventados.`;
    atualizarEstadoFonte("erro", "Falha ao obter os exercícios fechados dessa entidade.");
    bloquearConsultaAoVivo(true);
    return false;
  }
}

function atualizarModo() {
  const historico = modoAtual() === "historico";
  elementos.campoAno.hidden = historico;
  elementos.camposHistorico.hidden = !historico;
  elementos.analisar.textContent = historico ? "Consultar histórico no TCE-PR" : "Consultar exercício no TCE-PR";
  elementos.amostra.textContent = historico
    ? "Abrir demo Curitiba 2019–2025"
    : `Abrir demo Curitiba/${elementos.ano.value || "2025"}`;
  elementos.tempo.textContent = historico
    ? "O histórico consulta três relatórios por exercício. De 2019 a 2025 pode levar alguns minutos."
    : "A consulta anual gera três relatórios e normalmente leva menos de um minuto.";
}

function alternarCarregamento(ativo) {
  elementos.inicial.hidden = true;
  elementos.anual.hidden = true;
  elementos.historico.hidden = true;
  elementos.carregamento.hidden = !ativo;
  elementos.analisar.disabled = ativo;
  elementos.amostra.disabled = ativo;
  if (ativo) {
    const historico = modoAtual() === "historico";
    document.querySelector("#carregamento-titulo").textContent = historico ? "Montando a série histórica" : "Coletando relatórios oficiais";
    document.querySelector("#carregamento-texto").textContent = historico
      ? "Cada exercício é processado separadamente; falhas isoladas serão registradas."
      : "RCL, Pessoal e MDE/FUNDEB são processados em sequência.";
  }
}

function mostrarErro(erro) {
  elementos.carregamento.hidden = true;
  elementos.inicial.hidden = false;
  elementos.mensagem.textContent = erro.message;
}

function classificacaoLegivel(valor) {
  return {
    normal: "Situação normal",
    alerta: "Faixa de alerta",
    prudencial: "Limite prudencial",
    limite_excedido: "Limite excedido",
  }[valor] || valor;
}

function preencherAvisos(container, avisos) {
  container.replaceChildren();
  container.hidden = !avisos.length;
  for (const aviso of avisos) {
    const item = document.createElement("p");
    item.textContent = aviso;
    container.appendChild(item);
  }
}

function mostrarResultadoAnual(dados) {
  ultimoResultado = dados;
  elementos.inicial.hidden = true;
  elementos.carregamento.hidden = true;
  elementos.historico.hidden = true;
  elementos.anual.hidden = false;
  elementos.exportar.disabled = false;
  document.querySelector("#titulo-resultado").textContent = "Resumo financeiro";

  document.querySelector("#resultado-identificacao").textContent = `${dados.municipio} · ${dados.entidade} · ${dados.ano}`;
  document.querySelector("#resultado-coleta").textContent = dados.coletado_em;
  document.querySelector("#resultado-origem").textContent = dados.origem_dados || "Consulta ao vivo ao TCE-PR";
  document.querySelector("#valor-rcl").textContent = moeda(dados.receita_corrente_liquida);
  document.querySelector("#valor-rcl-ajustada").textContent = moeda(dados.receita_corrente_liquida_ajustada);
  document.querySelector("#valor-dtp").textContent = moeda(dados.despesa_total_pessoal);
  document.querySelector("#valor-percentual").textContent = percentual(dados.percentual_oficial);
  document.querySelector("#valor-fundeb").textContent = moeda(dados.fundeb?.receitas_recebidas);
  document.querySelector("#valor-fundeb-liquido").textContent = moeda(dados.fundeb?.resultado_liquido_transferencias);
  const status = document.querySelector("#classificacao");
  status.textContent = classificacaoLegivel(dados.classificacao);
  status.dataset.status = dados.classificacao;
  document.querySelector("#fonte-receita").textContent = dados.fonte_receita;
  document.querySelector("#fonte-pessoal").textContent = dados.fonte_pessoal;
  document.querySelector("#fonte-fundeb").textContent = dados.fundeb ? `${dados.fundeb.fonte} · ${dados.fundeb.periodo}` : "Não disponível nesta consulta.";
  document.querySelector("#validacao-rcl").textContent = Number(dados.diferenca_validacao_rcl) === 0
    ? "Os valores de RCL encontrados nos dois relatórios conferem."
    : `Diferença encontrada: ${moeda(dados.diferenca_validacao_rcl)}.`;

  document.querySelector("#limite-alerta").textContent = `Alerta ${percentual(dados.limites.alerta)}`;
  document.querySelector("#limite-prudencial").textContent = `Prudencial ${percentual(dados.limites.prudencial)}`;
  document.querySelector("#limite-maximo").textContent = `Máximo ${percentual(dados.limites.maximo)}`;
  document.querySelector("#marker-label").textContent = percentual(dados.percentual_oficial);
  document.querySelector("#current-marker").style.left = `${Math.min(Number(dados.percentual_oficial) / 0.6, 100)}%`;
  preencherAvisos(document.querySelector("#avisos-anual"), dados.avisos || []);
}

function svgElemento(nome, atributos = {}) {
  const elemento = document.createElementNS("http://www.w3.org/2000/svg", nome);
  for (const [chave, valor] of Object.entries(atributos)) elemento.setAttribute(chave, valor);
  return elemento;
}

function renderizarGrafico(resultados) {
  const svg = document.querySelector("#grafico-historico");
  svg.replaceChildren();
  const largura = 840;
  const altura = 330;
  const margem = { esquerda: 82, direita: 25, topo: 24, base: 48 };
  const series = [
    { chave: "rcl", cor: "#1e6b53", valor: (item) => item.receita_corrente_liquida_ajustada },
    { chave: "despesa", cor: "#d98d42", valor: (item) => item.despesa_total_pessoal },
    { chave: "fundeb", cor: "#597aa5", valor: (item) => item.fundeb?.receitas_recebidas ?? null },
  ];
  const valores = series.flatMap((serie) => resultados.map(serie.valor)).filter((valor) => valor !== null);
  const maximo = Math.max(...valores, 1);
  const x = (indice) => margem.esquerda + (resultados.length === 1 ? 0 : indice * (largura - margem.esquerda - margem.direita) / (resultados.length - 1));
  const y = (valor) => altura - margem.base - (Number(valor) / maximo) * (altura - margem.topo - margem.base);

  for (let nivel = 0; nivel <= 4; nivel += 1) {
    const valor = maximo * nivel / 4;
    const posicao = y(valor);
    svg.appendChild(svgElemento("line", { x1: margem.esquerda, y1: posicao, x2: largura - margem.direita, y2: posicao, class: "chart-grid-line" }));
    const rotulo = svgElemento("text", { x: margem.esquerda - 12, y: posicao + 4, "text-anchor": "end", class: "chart-label" });
    rotulo.textContent = `R$ ${(valor / 1e9).toFixed(1).replace(".", ",")} bi`;
    svg.appendChild(rotulo);
  }

  resultados.forEach((item, indice) => {
    const rotulo = svgElemento("text", { x: x(indice), y: altura - 18, "text-anchor": "middle", class: "chart-label" });
    rotulo.textContent = item.ano;
    svg.appendChild(rotulo);
  });

  for (const serie of series) {
    const pontos = resultados
      .map((item, indice) => ({ indice, valor: serie.valor(item) }))
      .filter((ponto) => ponto.valor !== null);
    if (!pontos.length) continue;
    svg.appendChild(svgElemento("polyline", {
      points: pontos.map((ponto) => `${x(ponto.indice)},${y(ponto.valor)}`).join(" "),
      fill: "none",
      stroke: serie.cor,
      "stroke-width": 4,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    }));
    for (const ponto of pontos) {
      svg.appendChild(svgElemento("circle", { cx: x(ponto.indice), cy: y(ponto.valor), r: 5, fill: "#fffdf8", stroke: serie.cor, "stroke-width": 3 }));
    }
  }
}

function mostrarResultadoHistorico(dados) {
  ultimoResultado = dados;
  elementos.inicial.hidden = true;
  elementos.carregamento.hidden = true;
  elementos.anual.hidden = true;
  elementos.historico.hidden = false;
  elementos.exportar.disabled = false;
  document.querySelector("#titulo-resultado").textContent = "Histórico financeiro";
  document.querySelector("#historico-identificacao").textContent = `${dados.municipio} · ${dados.entidade} · ${dados.ano_inicial}–${dados.ano_final}`;
  document.querySelector("#historico-coleta").textContent = dados.coletado_em;
  document.querySelector("#historico-origem").textContent = dados.origem_dados || "Consulta ao vivo ao TCE-PR";
  document.querySelector("#evolucao-rcl").textContent = variacao(dados.resumo.evolucao_acumulada_rcl_ajustada);
  document.querySelector("#evolucao-despesa").textContent = variacao(dados.resumo.evolucao_acumulada_despesa_pessoal);
  document.querySelector("#evolucao-fundeb").textContent = variacao(dados.resumo.evolucao_acumulada_receitas_fundeb);
  document.querySelector("#maior-comprometimento").textContent = `${percentual(dados.resumo.maior_comprometimento)} · ${dados.resumo.ano_maior_comprometimento}`;

  const corpo = document.querySelector("#tabela-historico");
  corpo.replaceChildren();
  for (const item of dados.resultados) {
    const linha = document.createElement("tr");
    const valores = [
      item.ano,
      moeda(item.receita_corrente_liquida_ajustada),
      moeda(item.despesa_total_pessoal),
      moeda(item.fundeb?.receitas_recebidas),
      percentual(item.percentual_calculado),
      classificacaoLegivel(item.classificacao),
      variacao(item.evolucao?.despesa_pessoal_percentual),
    ];
    valores.forEach((valor, indice) => {
      const celula = document.createElement("td");
      celula.textContent = valor;
      if (indice === 5) celula.dataset.status = item.classificacao;
      linha.appendChild(celula);
    });
    corpo.appendChild(linha);
  }
  renderizarGrafico(dados.resultados);
  const avisos = [];
  for (const erro of dados.erros || []) avisos.push(`${erro.ano}: ${erro.mensagem}`);
  for (const item of dados.resultados) for (const aviso of item.avisos || []) avisos.push(`${item.ano}: ${aviso}`);
  preencherAvisos(document.querySelector("#avisos-historico"), avisos);
}

elementos.municipio.addEventListener("change", carregarEntidades);
elementos.entidade.addEventListener("change", carregarAnos);
elementos.ano.addEventListener("change", atualizarModo);
elementos.recarregar.addEventListener("click", carregarMunicipios);
document.querySelectorAll('input[name="modo"]').forEach((radio) => radio.addEventListener("change", atualizarModo));

elementos.form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  elementos.mensagem.textContent = "";
  alternarCarregamento(true);
  const base = {
    municipio_id: elementos.municipio.value,
    municipio_nome: nomeSelecionado(elementos.municipio),
    entidade_id: elementos.entidade.value,
    entidade_nome: nomeSelecionado(elementos.entidade),
    incluir_fundeb: elementos.incluirFundeb.checked,
  };
  const historico = modoAtual() === "historico";
  try {
    const dados = await requisicaoJson(historico ? "/api/analisar-historico" : "/api/analisar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(historico
        ? { ...base, ano_inicial: elementos.anoInicial.value, ano_final: elementos.anoFinal.value }
        : { ...base, ano: elementos.ano.value }),
    });
    if (historico) mostrarResultadoHistorico(dados); else mostrarResultadoAnual(dados);
    elementos.mensagem.textContent = "Consulta concluída. Confira fontes, avisos e anos processados.";
  } catch (erro) {
    mostrarErro(erro);
  } finally {
    elementos.analisar.disabled = false;
    elementos.amostra.disabled = false;
    atualizarModo();
  }
});

elementos.amostra.addEventListener("click", async () => {
  try {
    if (modoAtual() === "historico") {
      mostrarResultadoHistorico(await requisicaoJson("/api/amostras/curitiba-historico"));
      elementos.mensagem.textContent = "Demonstração preservada de Curitiba/2019–2025 carregada sem consultar a internet.";
    } else {
      const ano = elementos.ano.value || "2025";
      mostrarResultadoAnual(await requisicaoJson(`/api/amostras/curitiba/${ano}`));
      elementos.mensagem.textContent = `Demonstração preservada de Curitiba/${ano} carregada sem consultar a internet.`;
    }
  } catch (erro) {
    mostrarErro(erro);
  }
});

elementos.exportar.addEventListener("click", async () => {
  if (!ultimoResultado) return;
  elementos.exportar.disabled = true;
  elementos.exportar.textContent = "Gerando Excel…";
  try {
    const resposta = await fetch("/api/exportar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimoResultado),
    });
    if (!resposta.ok) throw new Error("Não foi possível gerar o Excel.");
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const periodo = ultimoResultado.resultados ? `${ultimoResultado.ano_inicial}-${ultimoResultado.ano_final}` : ultimoResultado.ano;
    link.href = url;
    link.download = `analise-${ultimoResultado.municipio}-${periodo}.xlsx`.toLowerCase().replaceAll(" ", "-");
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (erro) {
    elementos.mensagem.textContent = erro.message;
  } finally {
    elementos.exportar.disabled = false;
    elementos.exportar.textContent = "Baixar Excel";
  }
});

async function enviarArquivo(form, rota, destino, renderizar) {
  const botao = form.querySelector("button");
  botao.disabled = true;
  destino.textContent = "Inspecionando arquivo…";
  try {
    const dados = await requisicaoJson(rota, { method: "POST", body: new FormData(form) });
    renderizar(destino, dados);
  } catch (erro) {
    destino.textContent = erro.message;
  } finally {
    botao.disabled = false;
  }
}

document.querySelector("#form-pdf").addEventListener("submit", (evento) => {
  evento.preventDefault();
  enviarArquivo(evento.currentTarget, "/api/salarios/inspecionar-pdf", document.querySelector("#resultado-pdf"), (destino, dados) => {
    destino.replaceChildren();
    const resumo = document.createElement("strong");
    resumo.textContent = `${dados.quantidade_paginas} página(s) · ${dados.paginas_com_texto} com texto`;
    const detalhe = document.createElement("p");
    detalhe.textContent = dados.provavelmente_escaneado
      ? "O PDF parece escaneado e provavelmente exigirá OCR."
      : `${dados.quantidade_caracteres} caracteres foram extraídos para o futuro mapeamento.`;
    destino.append(resumo, detalhe);
  });
});

document.querySelector("#form-planilha").addEventListener("submit", (evento) => {
  evento.preventDefault();
  enviarArquivo(evento.currentTarget, "/api/materiais/inspecionar-planilha", document.querySelector("#resultado-planilha"), (destino, dados) => {
    destino.replaceChildren();
    const resumo = document.createElement("strong");
    resumo.textContent = `${dados.quantidade_abas} aba(s) · ${dados.total_formulas} fórmula(s)`;
    const lista = document.createElement("p");
    lista.textContent = dados.abas.map((aba) => `${aba.nome}: ${aba.linhas}×${aba.colunas}`).join(" · ");
    destino.append(resumo, lista);
  });
});

function parametrosSalarial(base) {
  return {
    ...base,
    ...camposReferenciaProfissao(),
    municipio: salarioElementos.municipio.value.trim(),
    ano: Number(salarioElementos.ano.value),
    jornada_semanal: Number(salarioElementos.jornada.value),
    piso_nacional_40h: Number(salarioElementos.piso.value),
    modo_arredondamento: salarioElementos.arredondamento.value,
  };
}

function moedaComSinal(valor) {
  const numero = Number(valor);
  if (numero > 0) return `+${moeda(numero)}`;
  return moeda(numero);
}

function regraVerticalLegivel(nivel) {
  const regra = nivel.regra_vertical || {};
  if (regra.tipo === "base") return "Base da carreira";
  const referencia = regra.nivel_referencia ? ` sobre ${regra.nivel_referencia}` : "";
  if (regra.tipo === "valor_fixo") return `+ ${moeda(regra.valor)}${referencia}`;
  const valor = regra.valor ?? nivel.acrescimo_percentual;
  return valor === null || valor === undefined ? "Não informada" : `+ ${percentual(valor)}${referencia}`;
}

function montarTabelaSalarial(destino, classes, niveis, diferenca = false) {
  destino.replaceChildren();
  const tabela = document.createElement("table");
  const cabecalho = document.createElement("thead");
  const linhaCabecalho = document.createElement("tr");
  ["Nível", "Descrição", "Regra vertical", ...classes.map((item) => `Classe ${item}`)].forEach((texto) => {
    const th = document.createElement("th");
    th.textContent = texto;
    linhaCabecalho.appendChild(th);
  });
  cabecalho.appendChild(linhaCabecalho);
  tabela.appendChild(cabecalho);

  const corpo = document.createElement("tbody");
  for (const nivel of niveis) {
    const linha = document.createElement("tr");
    const fixos = [nivel.codigo, nivel.descricao, regraVerticalLegivel(nivel)];
    for (const texto of fixos) {
      const celula = document.createElement("td");
      celula.textContent = texto;
      linha.appendChild(celula);
    }
    for (const valor of nivel.valores) {
      const celula = document.createElement("td");
      celula.textContent = diferenca ? moedaComSinal(valor) : moeda(valor);
      if (diferenca) celula.dataset.comparison = Number(valor) < 0 ? "negativo" : "ok";
      linha.appendChild(celula);
    }
    corpo.appendChild(linha);
  }
  tabela.appendChild(corpo);
  destino.appendChild(tabela);
}

function entradaAPartirDaAnalise(dados) {
  return {
    municipio: dados.municipio,
    uf: dados.uf,
    ano: dados.ano,
    lei: dados.lei,
    arquivo_fonte: dados.arquivo_fonte,
    jornada_semanal: dados.parametros.jornada_semanal,
    jornada_confirmada_no_documento: false,
    piso_nacional_40h: dados.parametros.piso_nacional_40h,
    fonte_piso: dados.parametros.fonte_piso,
    url_fonte_piso: dados.parametros.url_fonte_piso,
    modo_arredondamento: dados.parametros.modo_arredondamento,
    progressao_classes_percentual: dados.parametros.progressao_classes_percentual,
    progressoes_classes_percentuais: dados.parametros.progressoes_classes_percentuais,
    progressao_classes_uniforme: dados.parametros.progressao_classes_uniforme,
    progressao_classes_origem: dados.parametros.progressao_classes_origem,
    avisos_importacao: dados.avisos_importacao || [],
    classes: dados.classes,
    niveis: dados.tabela_atual,
  };
}

function mostrarAnaliseSalarial(dados) {
  ultimaAnaliseSalarial = dados;
  salarioElementos.inicial.hidden = true;
  salarioElementos.resultado.hidden = false;
  salarioElementos.analisar.disabled = false;
  document.querySelector("#salario-identificacao").textContent = `${dados.municipio} · ${dados.profissao} · ${dados.ano}`;
  salarioElementos.pdf.hidden = dados.referencia.tipo !== "pspn";
  document.querySelector("#salario-situacao").textContent = dados.resumo.situacao === "compativel"
    ? "Compatível com a referência"
    : "Há valores abaixo";
  document.querySelector("#salario-atual").textContent = moeda(dados.resumo.vencimento_inicial_atual);
  document.querySelector("#salario-referencia").textContent = moeda(dados.resumo.vencimento_inicial_referencia);
  document.querySelector("#salario-defasagem").textContent = `${Number(dados.resumo.defasagem_inicial_percentual).toFixed(4).replace(".", ",")}%`;
  document.querySelector("#salario-celulas").textContent = `${dados.resumo.celulas_abaixo_referencia} de ${dados.resumo.total_celulas}`;
  document.querySelector("#salario-divergencias").textContent = String(dados.resumo.divergencias_estrutura);
  montarTabelaSalarial(document.querySelector("#tabela-salario-atual"), dados.classes, dados.tabela_atual);
  montarTabelaSalarial(document.querySelector("#tabela-salario-referencia"), dados.classes, dados.tabela_referencia);
  montarTabelaSalarial(document.querySelector("#tabela-salario-diferencas"), dados.classes, dados.diferencas, true);
  preencherAvisos(document.querySelector("#avisos-salariais"), dados.avisos || []);
}

async function executarAnaliseSalarial() {
  if (!entradaSalarial) throw new Error("Carregue uma amostra ou importe uma tabela primeiro.");
  if (!document.querySelector("#salario-revisado").checked) throw new Error("Revise a tabela e marque a confirmação antes de comparar.");
  salarioElementos.analisar.disabled = true;
  salarioElementos.amostra.disabled = true;
  salarioElementos.mensagem.textContent = "Calculando a tabela de referência…";
  try {
    const dados = await requisicaoJson("/api/salarios/analisar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parametrosSalarial(entradaSalarial)),
    });
    mostrarAnaliseSalarial(dados);
    salarioElementos.mensagem.textContent = "Análise concluída. Confira os avisos e as premissas.";
  } finally {
    salarioElementos.amostra.disabled = false;
    salarioElementos.analisar.disabled = false;
  }
}

dossieElementos.catalogo.addEventListener("change", mostrarFonteSalarial);

dossieElementos.form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const botao = evento.currentTarget.querySelector('button[type="submit"]');
  botao.disabled = true;
  dossieElementos.resultado.textContent = "Inspecionando e registrando os documentos originais…";
  try {
    const dados = await requisicaoJson("/api/salarios/dossies", {
      method: "POST",
      body: new FormData(evento.currentTarget),
    });
    mostrarDossieRegistrado(dados);
    salarioElementos.municipio.value = dados.municipio;
    salarioElementos.ano.value = dados.ano_referencia;
    salarioElementos.mensagem.textContent = "Dossiê registrado. A comparação não foi executada automaticamente; confirme vigência e estrutura primeiro.";
  } catch (erro) {
    dossieElementos.resultado.textContent = erro.message;
  } finally {
    botao.disabled = false;
  }
});

salarioElementos.form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  try {
    await executarAnaliseSalarial();
  } catch (erro) {
    salarioElementos.mensagem.textContent = erro.message;
  }
});

async function baixarAnaliseSalarial(rota, extensao, botao) {
  if (!ultimaAnaliseSalarial) return;
  const textoOriginal = botao.textContent;
  botao.disabled = true;
  botao.textContent = "Gerando…";
  try {
    const resposta = await fetch(rota, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimaAnaliseSalarial.entrada),
    });
    if (!resposta.ok) {
      const erro = await resposta.json().catch(() => ({}));
      throw new Error(erro.erro || `Não foi possível gerar o ${extensao.toUpperCase()}.`);
    }
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `analise-salarial-${ultimaAnaliseSalarial.municipio}-${ultimaAnaliseSalarial.profissao}-${ultimaAnaliseSalarial.ano}.${extensao}`.toLowerCase().replaceAll(" ", "-");
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (erro) {
    salarioElementos.mensagem.textContent = erro.message;
  } finally {
    botao.disabled = false;
    botao.textContent = textoOriginal;
  }
}

salarioElementos.excel.addEventListener("click", () => baixarAnaliseSalarial(
  "/api/salarios/exportar-excel", "xlsx", salarioElementos.excel,
));
salarioElementos.pdf.addEventListener("click", () => baixarAnaliseSalarial(
  "/api/salarios/relatorio-pdf", "pdf", salarioElementos.pdf,
));

preencherAnos(ANOS_DEMO_CURITIBA);
atualizarModo();
carregarMunicipios();
carregarFontesSalariais();
