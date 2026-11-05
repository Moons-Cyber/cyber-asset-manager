/* Mapa da Rede: os ativos como esferas (cor = risco efetivo) ligados por canos
 * (as dependências, com o peso). Clicar numa esfera mostra de onde vem o risco
 * dela; o Assistente explica a conta com os números.
 *
 * Só lê dados que o Nucleo já carregou (/api/ativos, /api/dependencias,
 * /api/risco); não calcula nada por conta própria.
 */
const AppMapa = (() => {
  "use strict";
  const { el, num, pilula, dados } = Nucleo;

  let ui = null;
  let selecionado = null;
  let sobre = null;            // id sob o mouse
  let geometria = [];          // [{ id, x, y, r }] do último desenho, para o clique

  const nomeDe = (id) => (dados.ativos.find((a) => a.id === id) || {}).nome || `#${id}`;
  const riscoDe = (id) => dados.risco.get(id);

  // --------------------------------------------------------------- desenho
  function desenhar() {
    if (!ui) return;
    const { g, L, A, dpr } = Desenho.preparar(ui.canvas);
    if (!L || !A) return;
    g.clearRect(0, 0, L, A);
    g.drawImage(Desenho.fundo(L, A, dpr), 0, 0, L, A);

    const ativos = dados.ativos;
    if (!ativos.length) {
      Desenho.etiqueta(g, dados.carregado ? "Sem ativos. Cadastre alguns no Gerenciador de Ativos." : "Carregando…",
        L / 2, A / 2, L, { fonte: "700 13px Tahoma, sans-serif" });
      geometria = [];
      return;
    }

    const pos = Desenho.posicoes(ativos.map((a) => a.id), dados.deps.map((d) => [d.o, d.d]));
    const mx = Math.min(70, L * 0.12), my = Math.min(56, A * 0.15);
    const r = Math.max(14, Math.min(24, Math.min(L, A) / 14));
    const ponto = (id) => {
      const p = pos[id] || { x: 0.5, y: 0.5 };
      return { x: mx + p.x * (L - 2 * mx), y: my + p.y * (A - 2 * my) };
    };
    const ligado = (d) => selecionado === null || d.o === selecionado || d.d === selecionado;

    for (const d of dados.deps) {
      const k = Desenho.curva(ponto(d.o), ponto(d.d));
      Desenho.cano(g, k, d.peso, selecionado !== null && d.d === selecionado, !ligado(d));
    }
    for (const d of dados.deps) {           // pesos por cima dos canos
      if (!ligado(d)) continue;
      const m = Desenho.curva(ponto(d.o), ponto(d.d)).ponto(0.5);
      Desenho.etiqueta(g, num(d.peso), m.x, m.y, L, { cor: "#0a3fb0", borda: "rgba(10,63,176,.6)", fonte: "700 10.5px Tahoma, sans-serif" });
    }

    geometria = [];
    for (const a of ativos) {
      const { x, y } = ponto(a.id);
      const risco = riscoDe(a.id);
      const vizinho = selecionado === null || a.id === selecionado
        || dados.deps.some((d) => (d.o === a.id && d.d === selecionado) || (d.d === a.id && d.o === selecionado));
      const raio = r * (a.id === sobre ? 1.08 : 1);
      if (a.id === selecionado) {
        g.save();
        g.strokeStyle = "#ffd23f"; g.lineWidth = 4; g.shadowColor = "rgba(255,190,40,.9)"; g.shadowBlur = 12;
        g.beginPath(); g.arc(x, y, raio + 5, 0, Math.PI * 2); g.stroke();
        g.restore();
      }
      Desenho.esfera(g, x, y, raio, Desenho.corDoRisco(risco ? risco.risco_efetivo : null), vizinho ? 1 : 0.35);
      if (risco) {
        g.save();
        g.font = "700 10.5px Tahoma, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
        g.fillStyle = "#fff"; g.shadowColor = "rgba(0,0,0,.6)"; g.shadowBlur = 2;
        g.globalAlpha = vizinho ? 1 : 0.4;
        g.fillText(num(risco.risco_efetivo, 1), x, y + 1);
        g.restore();
      }
      const nome = a.nome.length > 18 ? a.nome.slice(0, 17) + "…" : a.nome;
      Desenho.etiqueta(g, nome, x, y + raio + 13, L);
      geometria.push({ id: a.id, x, y, r: raio });
    }
  }

  function noPonto(ev) {
    const caixa = ui.canvas.getBoundingClientRect();
    const x = ev.clientX - caixa.left, y = ev.clientY - caixa.top;
    const alvo = geometria.find((p) => Math.hypot(p.x - x, p.y - y) <= p.r + 6);
    return alvo ? alvo.id : null;
  }

  // ---------------------------------------------------------------- painel
  function painel() {
    if (!ui) return;
    ui.escolha.replaceChildren(
      el("option", { value: "" }, "Visão geral da rede"),
      ...dados.ativos.map((a) => el("option", { value: a.id, selected: a.id === selecionado }, `${a.id} - ${a.nome}`)));

    const a = dados.ativos.find((x) => x.id === selecionado);
    if (!a) { selecionado = null; ui.info.replaceChildren(...resumo()); return; }

    const r = riscoDe(a.id);
    const recebe = dados.deps.filter((d) => d.d === a.id);
    const passa = dados.deps.filter((d) => d.o === a.id);
    const abertas = a.vulnerabilidades.filter((v) => v.afeta_risco);

    ui.info.replaceChildren(
      el("h3", {}, a.nome),
      el("p", { class: "dica" }, `${a.tipo_nome} · fator de exposição ${r ? num(r.fator_exposicao, 1) : "--"}`),
      el("dl", { class: "numeros" },
        el("div", {}, el("dt", {}, "Risco próprio (b)"), el("dd", {}, r ? pilula(r.risco_proprio) : "--")),
        el("div", {}, el("dt", {}, "Risco efetivo (x)"), el("dd", {}, r ? pilula(r.risco_efetivo) : "--"))),
      el("h4", {}, `Falhas abertas (${abertas.length})`),
      abertas.length
        ? el("ul", { class: "fluxo" }, abertas.map((v) => el("li", {}, `${v.descricao_curta || v.id}: nota ${num(v.severidade, 1)} `,
            el("button", { type: "button", class: "link-falha", on: { click: () => AppAssistente.explicarFalha(a.id, v.id) } }, "o que é?"))))
        : el("p", { class: "dica" }, "Nenhuma: o risco próprio é zero."),
      el("h4", {}, "Recebe risco de"),
      recebe.length
        ? el("ul", { class: "fluxo" }, recebe.map((d) => {
            const xo = riscoDe(d.o);
            return el("li", {}, `${nomeDe(d.o)}: ${num(d.peso)} × ${xo ? num(xo.risco_efetivo) : "--"} = `,
              el("b", {}, xo ? num(d.peso * xo.risco_efetivo) : "--"));
          }))
        : el("p", { class: "dica" }, "Ninguém: o risco efetivo é igual ao próprio."),
      el("h4", {}, "Passa risco para"),
      passa.length
        ? el("ul", { class: "fluxo" }, passa.map((d) => el("li", {}, `${nomeDe(d.d)} (peso ${num(d.peso)})`)))
        : el("p", { class: "dica" }, "Ninguém."),
      el("div", { class: "acoes" },
        el("button", { type: "button", class: "botao gel", on: { click: () => AppAssistente.explicarAtivo(a.id) } }, "Por que esse valor?"),
        el("button", { type: "button", class: "botao", on: { click: () => AppAtivos.abrir(a.id) } }, "Editar ativo")));
  }

  function resumo() {
    const lista = [...dados.risco.values()];
    if (!dados.ativos.length) {
      return [el("h3", {}, "Rede vazia"),
        el("p", {}, "Cadastre ativos e dependências no Gerenciador de Ativos para ver a rede aqui."),
        el("div", { class: "acoes" }, el("button", { type: "button", class: "botao gel", on: { click: () => AppAtivos.abrir() } }, "Abrir o Gerenciador"))];
    }
    if (!lista.length) {
      return [el("h3", {}, "Risco não calculado"),
        el("p", {}, "Com os dados atuais, I − A não pôde ser resolvida. O Assistente explica o motivo."),
        el("div", { class: "acoes" }, el("button", { type: "button", class: "botao gel", on: { click: () => AppAssistente.abrirCalculo() } }, "Ver o diagnóstico"))];
    }
    const global = lista.reduce((s, r) => s + r.risco_efetivo, 0);
    const pior = lista.reduce((m, r) => (r.risco_efetivo > m.risco_efetivo ? r : m));
    return [
      el("h3", {}, "Visão geral"),
      el("div", { class: "global" }, el("span", {}, "Risco global da rede"), el("strong", {}, num(global)), el("small", {}, "soma dos riscos efetivos")),
      el("dl", { class: "numeros" },
        el("div", {}, el("dt", {}, "Ativos"), el("dd", {}, dados.ativos.length)),
        el("div", {}, el("dt", {}, "Dependências"), el("dd", {}, dados.deps.length))),
      el("p", {}, "Maior risco efetivo: ", el("b", {}, pior.nome), " ", pilula(pior.risco_efetivo)),
      el("p", { class: "dica" }, "Clique numa esfera para ver de onde vem o risco dela."),
      el("div", { class: "acoes" }, el("button", { type: "button", class: "botao gel", on: { click: () => AppAssistente.abrirCalculo() } }, "Como o risco é calculado?")),
    ];
  }

  function selecionar(id) {
    selecionado = id;
    painel();
    desenhar();
  }

  // ----------------------------------------------------------------- janela
  function construir() {
    const canvas = el("canvas", { class: "mapa", role: "img", "aria-label": "Mapa da rede: ativos e dependências" });
    canvas.addEventListener("click", (ev) => selecionar(noPonto(ev)));
    canvas.addEventListener("pointermove", (ev) => {
      const id = noPonto(ev);
      canvas.style.cursor = id === null ? "default" : "pointer";
      if (id !== sobre) { sobre = id; desenhar(); }
    });
    canvas.addEventListener("pointerleave", () => { if (sobre !== null) { sobre = null; desenhar(); } });

    const escolha = el("select", {
      "aria-label": "Escolher ativo",
      on: { change: (e) => selecionar(e.target.value === "" ? null : Number(e.target.value)) },
    });
    const info = el("div", { class: "mapa-info", "aria-live": "polite" });
    const legenda = el("div", { class: "legenda-risco", "aria-label": "Legenda de cores" },
      [["verde", "baixo (<4)"], ["amarelo", "médio (<8)"], ["laranja", "alto (<15)"], ["vermelho", "crítico (≥15)"]].map(([c, t]) =>
        el("span", { style: `--c:${Desenho.COR[c]}` }, t)));

    const raiz = el("div", { class: "mapa-app" },
      el("div", { class: "mapa-esq" }, el("div", { class: "mapa-wrap" }, canvas), legenda),
      el("aside", { class: "mapa-dir" }, el("label", { class: "campo" }, el("span", {}, "Ativo"), escolha), info));
    ui = { raiz, canvas, escolha, info };
    return raiz;
  }

  function abrir(id) {
    if (ui) {
      Janelas.focar("mapa");
      if (id !== undefined) selecionar(id);
      return;
    }
    const conteudo = construir();
    const desinscrever = Nucleo.assinar(() => { painel(); desenhar(); });
    Janelas.abrir({
      id: "mapa", titulo: "Mapa da Rede", icone: "rede", largura: 1000, altura: 600, minLargura: 560, minAltura: 380, conteudo,
      aoRedimensionar: desenhar,
      aoFechar: () => { desinscrever(); ui = null; },
    });
    selecionado = id === undefined ? null : id;
    painel();
    desenhar();
  }

  return { abrir, selecionar: (id) => abrir(id) };
})();

window.AppMapa = AppMapa;
