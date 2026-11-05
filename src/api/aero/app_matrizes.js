/* Matrizes e gráfico: o mesmo cálculo do Assistente, mas para ENXERGAR.
 *
 *  - Dependências (A): mapa de calor; cada quadradinho é o peso que um ativo
 *    (coluna, a origem) passa para outro (linha, o destino): A[destino][origem].
 *  - I − A: a matriz que o sistema resolve, com o diagnóstico de invertibilidade.
 *  - Riscos: barras do risco próprio (b) e do risco efetivo (x) de cada ativo.
 *
 * Só desenha o que /api/risco/passos devolve (as mesmas funções do cálculo
 * oficial); não calcula nada por conta própria.
 */
const AppMatrizes = (() => {
  "use strict";
  const { el, num, api, faixa } = Nucleo;

  const ABAS = [
    ["A", "Dependências (A)"],
    ["IA", "Sistema (I − A)"],
    ["R", "Riscos (b e x)"],
  ];

  let ui = null;
  let dados = null;        // resposta de /api/risco/passos
  let erro = null;
  let aba = "A";
  let sel = null;          // { i, j } do quadradinho escolhido
  let pedido = 0;          // descarta respostas antigas

  const curto = (nome) => (nome.length > 11 ? nome.slice(0, 10) + "…" : nome);

  // ------------------------------------------------------------ cores
  /** Peso 0..1 em azul: quanto mais forte, mais risco passa. */
  function corA(v) {
    if (!v) return { fundo: "transparent", texto: "#8a98ad" };
    return { fundo: `rgba(30,110,230,${(0.14 + 0.78 * Math.min(1, v)).toFixed(2)})`, texto: v > 0.5 ? "#fff" : "#0a2a6b" };
  }

  /** I − A: diagonal verde (1), pesos negativos em laranja. */
  function corIA(v, diagonal) {
    if (diagonal) return { fundo: "rgba(70,175,60,.38)", texto: "#12400c" };
    if (!v) return { fundo: "transparent", texto: "#8a98ad" };
    const f = Math.min(1, Math.abs(v));
    return { fundo: `rgba(240,128,28,${(0.16 + 0.72 * f).toFixed(2)})`, texto: f > 0.55 ? "#fff" : "#4a2400" };
  }

  // ---------------------------------------------------------- mapa de calor
  function celula(i, j, valor, cor, rotulo) {
    const n = dados.ativos.length;
    const escolhida = sel && sel.i === i && sel.j === j;
    return el("button", {
      type: "button",
      class: `mat-cel${escolhida ? " escolhida" : ""}${valor ? "" : " vazia"}`,
      style: `background:${cor.fundo};color:${cor.texto}`,
      "data-i": i, "data-j": j, title: rotulo, "aria-label": rotulo,
      "aria-pressed": String(!!escolhida),
      on: {
        click: () => { sel = { i, j }; mostrar(); },
        pointerenter: (ev) => realcar(ev.currentTarget.closest(".mat-grade"), i, j, n),
        pointerleave: (ev) => realcar(ev.currentTarget.closest(".mat-grade"), null, null, n),
        focus: (ev) => realcar(ev.currentTarget.closest(".mat-grade"), i, j, n),
        blur: (ev) => realcar(ev.currentTarget.closest(".mat-grade"), null, null, n),
      },
    }, num(valor));
  }

  /** Destaca o cabeçalho da linha e da coluna sob o mouse. */
  function realcar(grade, i, j) {
    if (!grade) return;
    for (const c of grade.querySelectorAll(".mat-cab.no")) c.classList.remove("no");
    if (i === null) return;
    for (const c of grade.querySelectorAll(`[data-linha="${i}"],[data-coluna="${j}"]`)) c.classList.add("no");
  }

  function grade(matriz, { corDe, rotuloDe, somas }) {
    const ativos = dados.ativos, n = ativos.length;
    const colunas = `auto repeat(${n}, minmax(46px, 1fr))${somas ? " auto" : ""}`;
    const cab = (txt, atributos) => el("div", { class: "mat-cab", ...atributos }, txt);
    const filhos = [
      el("div", { class: "mat-canto", title: "linha = quem recebe · coluna = quem passa" }, "recebe ↓ · passa →"),
      ...ativos.map((a, j) => cab(curto(a.nome), { "data-coluna": j, title: `Origem: ${a.nome}` })),
      somas ? el("div", { class: "mat-cab soma", title: "Soma dos pesos que o ativo recebe. Precisa ser menor que 1." }, "Σ recebe") : null,
    ];
    for (let i = 0; i < n; i++) {
      filhos.push(cab(curto(ativos[i].nome), { "data-linha": i, class: "mat-cab lado", title: `Destino: ${ativos[i].nome}` }));
      for (let j = 0; j < n; j++) filhos.push(celula(i, j, matriz[i][j], corDe(matriz[i][j], i === j), rotuloDe(i, j, matriz[i][j])));
      if (somas) {
        const s = dados.somas_recebidas[i];
        filhos.push(el("div", { class: `mat-soma ${s < 1 ? "ok" : "ruim"}`, title: s < 1 ? "Menor que 1: a regra vale" : "Não é menor que 1: a regra falha" }, num(s)));
      }
    }
    return el("div", { class: "mat-grade", style: `grid-template-columns:${colunas}`, role: "group", "aria-label": "Matriz" }, filhos);
  }

  const legenda = (itens) => el("div", { class: "mat-legenda" }, itens.map(([cor, texto]) =>
    el("span", { style: `--c:${cor}` }, texto)));

  function vistaA() {
    return [
      grade(dados.A, {
        somas: true,
        corDe: (v) => corA(v),
        rotuloDe: (i, j, v) => v ? `${dados.ativos[j].nome} passa risco para ${dados.ativos[i].nome}: peso ${num(v)}` : `${dados.ativos[j].nome} não passa risco para ${dados.ativos[i].nome}`,
      }),
      legenda([["rgba(30,110,230,.2)", "peso pequeno"], ["rgba(30,110,230,.95)", "peso grande"], ["#d8dfe9", "vazio = sem dependência"]]),
    ];
  }

  function vistaIA() {
    return [
      grade(dados.I_menos_A, {
        corDe: (v, diag) => corIA(v, diag),
        rotuloDe: (i, j, v) => i === j ? `Diagonal de ${dados.ativos[i].nome}: 1` : `Linha ${dados.ativos[i].nome}, coluna ${dados.ativos[j].nome}: ${num(v)}`,
      }),
      legenda([["rgba(70,175,60,.55)", "diagonal = 1"], ["rgba(240,128,28,.8)", "−peso da dependência"], ["#d8dfe9", "vazio = 0"]]),
    ];
  }

  // ------------------------------------------------------------- gráfico
  function vistaRiscos() {
    const x = dados.x;
    const linhas = dados.ativos.map((a, i) => ({ nome: a.nome, b: dados.b[i], x: x ? x[i] : null }));
    linhas.sort((p, q) => (q.x ?? q.b) - (p.x ?? p.b));
    const maximo = Math.max(1e-9, ...linhas.map((l) => Math.max(l.b, l.x ?? 0)));
    const barra = (valor, classe, rotulo) => el("div", { class: "barra-linha" },
      el("span", { class: "barra-nome" }, rotulo),
      el("div", { class: "barra-trilho" }, el("i", { class: `barra ${classe}`, style: `width:${Math.max(valor > 0 ? 1.5 : 0, (100 * valor) / maximo).toFixed(1)}%` })),
      el("span", { class: "barra-valor" }, num(valor)));

    return [
      el("div", { class: "grafico", role: "img", "aria-label": "Gráfico de barras: risco próprio e risco efetivo de cada ativo" },
        linhas.map((l) => el("div", { class: "grafico-grupo" },
          el("b", { class: "grafico-ativo", title: l.nome }, l.nome),
          barra(l.b, "propria", "próprio (b)"),
          l.x === null ? el("p", { class: "dica" }, "x não calculado: I − A não é invertível.")
            : barra(l.x, faixa(l.x).classe, "efetivo (x)"),
          l.x !== null && l.x - l.b > 1e-9
            ? el("small", { class: "herdado" }, `+${num(l.x - l.b)} herdado das dependências`) : null))),
      legenda([["#6aa7f5", "risco próprio (b)"], ["#4fc23a", "efetivo baixo"], ["#f2cf2a", "médio"], ["#f08a24", "alto"], ["#e0392b", "crítico"]]),
    ];
  }

  // ----------------------------------------------------------------- painel
  function diagnostico() {
    const d = dados.diagnostico;
    if (!d) return [];
    return [
      el("h4", {}, "A matriz I − A tem solução?"),
      el("p", {}, d.invertivel
        ? Nucleo.rico("**Sim.** Tem solução única, então `np.linalg.solve` pode calcular x.")
        : Nucleo.rico("**Não.** Não há solução única, por isso o risco efetivo não é calculado.")),
      el("dl", { class: "numeros" },
        el("div", {}, el("dt", {}, "Posto"), el("dd", {}, `${d.posto} de ${d.ordem}`)),
        el("div", {}, el("dt", {}, "Condição"), el("dd", {}, num(d.condicao))),
        el("div", {}, el("dt", {}, "Determinante"), el("dd", {}, num(d.determinante, 4)))),
      dados.somas_recebidas.every((s) => s < 1)
        ? el("p", { class: "dica" }, "Todas as linhas de A somam menos de 1, então a regra de segurança vale.")
        : el("p", { class: "dica" }, "Alguma linha de A soma 1 ou mais: a regra de segurança falha."),
    ];
  }

  function detalhe() {
    const n = dados.ativos.length;
    if (!sel || sel.i >= n || sel.j >= n) return [];
    const { i, j } = sel;
    const destino = dados.ativos[i].nome, origem = dados.ativos[j].nome;
    const x = dados.x;
    if (aba === "R") return [];
    if (aba === "IA") {
      const v = dados.I_menos_A[i][j];
      return [el("h4", {}, "Quadradinho escolhido"),
        i === j
          ? el("p", {}, Nucleo.rico(`Diagonal de **${destino}**: vale **1**. É o \`I\` da conta; um ativo não passa risco para si mesmo.`))
          : el("p", {}, Nucleo.rico(`Linha **${destino}**, coluna **${origem}**: **${num(v)}**. É o peso da dependência com o sinal trocado: \`0 − A[${i}][${j}]\`.`))];
    }
    const v = dados.A[i][j];
    if (!v) return [el("h4", {}, "Quadradinho escolhido"), el("p", {}, `${origem} não passa risco para ${destino}.`)];
    return [el("h4", {}, "Quadradinho escolhido"),
      el("p", {}, Nucleo.rico(`**${origem}** passa risco para **${destino}** com peso **${num(v)}**.`)),
      x ? el("p", {}, Nucleo.rico(`Contribuição: \`${num(v)} × ${num(x[j])} = ${num(v * x[j])}\` do risco efetivo de ${destino}.`))
        : el("p", { class: "dica" }, "O risco efetivo não foi calculado, então não há contribuição para mostrar.")];
  }

  const COMO_LER = {
    A: "Cada linha é um ativo que **recebe** risco; cada coluna, um que **passa**. A cor mais forte é um peso maior. A última coluna soma o que cada ativo recebe e precisa dar menos que 1.",
    IA: "É a matriz do sistema `(I − A)x = b`: a identidade menos A. A diagonal vira 1 e os pesos mudam de sinal. Se ela tem solução única, o risco efetivo x existe.",
    R: "Cada ativo tem duas barras: o risco **próprio** (b, das falhas dele) e o **efetivo** (x, com o que ele herda das dependências). A diferença é o risco que veio da rede.",
  };

  function painel() {
    ui.info.replaceChildren(
      el("h3", {}, ABAS.find(([k]) => k === aba)[1]),
      el("p", {}, Nucleo.rico(COMO_LER[aba])),
      ...detalhe(),
      ...(aba === "R" ? [] : diagnostico()),
      el("div", { class: "acoes" },
        el("button", { type: "button", class: "botao gel", on: { click: () => AppAssistente.abrirCalculo() } }, "Como o risco é calculado?")));
  }

  // ------------------------------------------------------------------ tela
  function mostrar() {
    if (!ui) return;
    for (const [k, b] of ui.abas) b.setAttribute("aria-pressed", String(k === aba));
    if (erro) { ui.vista.replaceChildren(el("p", { class: "dica" }, `Não foi possível ler os dados: ${erro}`)); ui.info.replaceChildren(); return; }
    if (!dados) { ui.vista.replaceChildren(el("p", { class: "dica" }, "Carregando…")); return; }
    if (!dados.ativos.length) {
      ui.vista.replaceChildren(el("p", { class: "dica" }, "Sem ativos. Cadastre alguns no Gerenciador de Ativos para ver as matrizes."));
      ui.info.replaceChildren(el("div", { class: "acoes" },
        el("button", { type: "button", class: "botao gel", on: { click: () => AppAtivos.abrir() } }, "Abrir o Gerenciador")));
      return;
    }
    ui.vista.replaceChildren(...(aba === "A" ? vistaA() : aba === "IA" ? vistaIA() : vistaRiscos()));
    painel();
  }

  async function carregar() {
    const meu = ++pedido;
    try {
      const d = await api("/api/risco/passos");
      if (meu !== pedido) return;
      dados = d; erro = null;
    } catch (e) {
      if (meu !== pedido) return;
      erro = e.message;
    }
    mostrar();
  }

  function construir() {
    const abas = ABAS.map(([k, rotulo]) => [k, el("button", {
      type: "button", class: "mat-aba", "aria-pressed": String(k === aba),
      on: { click: () => { aba = k; sel = null; mostrar(); } },
    }, rotulo)]);
    const vista = el("div", { class: "mat-vista", "aria-live": "polite" });
    const info = el("div", { class: "mapa-info", "aria-live": "polite" });
    const raiz = el("div", { class: "mat-app" },
      el("div", { class: "mat-esq" }, el("div", { class: "mat-abas", role: "group", "aria-label": "Escolher a visão" }, abas.map(([, b]) => b)), vista),
      el("aside", { class: "mat-dir" }, info));
    ui = { raiz, vista, info, abas };
    return raiz;
  }

  function abrir(inicio) {
    if (inicio && ABAS.some(([k]) => k === inicio)) { aba = inicio; sel = null; }
    if (ui) { Janelas.focar("matrizes"); mostrar(); return; }
    const conteudo = construir();
    const desinscrever = Nucleo.assinar(() => carregar());
    Janelas.abrir({
      id: "matrizes", titulo: "Matrizes e Gráfico", icone: "matriz", largura: 960, altura: 580, minLargura: 520, minAltura: 360, conteudo,
      aoFechar: () => { desinscrever(); ui = null; dados = null; pedido++; },
    });
    mostrar();
    carregar();
  }

  return { abrir };
})();

window.AppMatrizes = AppMatrizes;
