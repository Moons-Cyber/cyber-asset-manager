/* Núcleo do tema Aero: chamadas à API, formatação, dados compartilhados e
 * saúde do serviço. Todos os aplicativos usam isto.
 *
 * Regra de segurança: nada que vem do servidor entra por innerHTML. Tudo é
 * montado com createElement + textContent, então um nome com <tags> aparece
 * como texto e não executa nada.
 */
const Nucleo = (() => {
  "use strict";

  // ----------------------------------------------------------------- API
  async function api(url, opcoes) {
    const resposta = await fetch(url, opcoes);
    let corpo = null;
    try { corpo = await resposta.json(); } catch { /* resposta sem JSON */ }
    if (!resposta.ok) {
      const erro = new Error((corpo && corpo.erro) || `Erro HTTP ${resposta.status}`);
      erro.status = resposta.status;
      erro.dica = corpo && corpo.dica;
      throw erro;
    }
    return corpo;
  }

  const json = (metodo, corpo) => ({
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });

  // ------------------------------------------------------- formatação
  function num(v, casas = 2) {
    if (v === null || v === undefined || !Number.isFinite(v)) return "--";
    if (Math.abs(v) >= 1e5) return v.toExponential(1).replace(".", ",");
    return v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  }

  function el(tag, atributos = {}, ...filhos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(atributos)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "on") for (const [ev, fn] of Object.entries(v)) e.addEventListener(ev, fn);
      else if (k === "style") e.style.cssText = v;
      else if (k in e && k !== "list") e[k] = v;
      else e.setAttribute(k, v);
    }
    for (const f of filhos.flat()) {
      if (f === null || f === undefined || f === false) continue;
      e.append(typeof f === "object" ? f : document.createTextNode(String(f)));
    }
    return e;
  }

  /** Texto com **negrito** e `código`, sem innerHTML. */
  function rico(texto) {
    const frag = document.createDocumentFragment();
    for (const parte of String(texto).split(/(\*\*[^*]+\*\*|`[^`]+`)/)) {
      if (!parte) continue;
      if (parte.startsWith("**")) frag.append(el("b", {}, parte.slice(2, -2)));
      else if (parte.startsWith("`")) frag.append(el("code", {}, parte.slice(1, -1)));
      else frag.append(document.createTextNode(parte));
    }
    return frag;
  }

  /** Faixa de cor do risco: verde, amarelo, laranja, vermelho. */
  function faixa(x) {
    if (x === null || x === undefined || !Number.isFinite(x)) return { classe: "neutro", rotulo: "sem dado" };
    if (x < 4) return { classe: "verde", rotulo: "baixo" };
    if (x < 8) return { classe: "amarelo", rotulo: "médio" };
    if (x < 15) return { classe: "laranja", rotulo: "alto" };
    return { classe: "vermelho", rotulo: "crítico" };
  }

  function pilula(x, casas = 2) {
    return el("span", { class: `pilula ${faixa(x).classe}`, title: `Risco ${faixa(x).rotulo}` }, num(x, casas));
  }

  // -------------------------------------------------- dados compartilhados
  const dados = { ativos: [], deps: [], risco: new Map(), tipos: [], status: [], carregado: false };
  const ouvintes = new Set();

  function assinar(fn) {
    ouvintes.add(fn);
    return () => ouvintes.delete(fn);
  }

  async function recarregar() {
    if (!dados.tipos.length) dados.tipos = await api("/api/tipos");
    if (!dados.status.length) dados.status = await api("/api/status");
    const [ativos, deps, risco] = await Promise.all([
      api("/api/ativos"),
      api("/api/dependencias"),
      api("/api/risco").catch(() => null),
    ]);
    dados.ativos = ativos;
    dados.deps = deps.map((d) => ({ o: d.ativo_origem_id, d: d.ativo_destino_id, peso: d.peso }));
    dados.risco = new Map(((risco && risco.resultados) || []).map((r) => [r.id, r]));
    dados.carregado = true;
    ouvintes.forEach((fn) => fn(dados));
  }

  /** Roda uma alteração na API e depois relê tudo, avisando os aplicativos. */
  async function alterar(acao) {
    const resultado = await acao();
    await recarregar();
    return resultado;
  }

  // ---------------------------------------------------------------- saúde
  const saude = { ok: null, ativos: null, quando: null, motivo: null };
  const ouvintesSaude = new Set();

  async function checarSaude() {
    const antes = saude.ok;
    try {
      const resposta = await fetch("/api/saude", { cache: "no-store" });
      const corpo = await resposta.json().catch(() => ({}));
      saude.ok = resposta.ok && corpo.status === "ok";
      saude.ativos = corpo.ativos ?? null;
      saude.motivo = saude.ok ? null : (corpo.detalhe || `HTTP ${resposta.status}`);
    } catch (erro) {
      saude.ok = false;
      saude.motivo = "sem resposta do servidor";
    }
    saude.quando = new Date();
    ouvintesSaude.forEach((fn) => fn(saude, antes));
    return saude;
  }

  function assinarSaude(fn) {
    ouvintesSaude.add(fn);
    return () => ouvintesSaude.delete(fn);
  }

  /** Balão de notificação (a bandeja do sistema mostra). tipo: info | ok | erro | aviso. */
  function balao(titulo, texto, tipo = "info") {
    document.dispatchEvent(new CustomEvent("aero:balao", { detail: { titulo, texto, tipo } }));
  }

  return { api, json, num, el, rico, faixa, pilula, dados, assinar, recarregar, alterar, saude, checarSaude, assinarSaude, balao };
})();

window.Nucleo = Nucleo;   // "const" de topo não vira propriedade de window
