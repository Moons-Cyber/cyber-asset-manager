/* Assistente: a Gota, uma gotinha de vidro no canto da tela.
 *
 * Fica quieta até ser chamada. Só fala sozinha uma vez: no primeiro acesso,
 * oferece um tour. Clicando nela, abre o menu de perguntas. As respostas
 * longas abrem num assistente no estilo do XP (Voltar / Avançar), com os
 * números reais de /api/risco/passos e a caixa "No código".
 */
const AppAssistente = (() => {
  "use strict";
  const { el, rico, api } = Nucleo;

  const CHAVE_OI = "aero-gota-oi";           // já ofereceu o tour?
  const CHAVE_OCULTA = "aero-gota-oculta";    // usuário escondeu a Gota?
  const ler = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  const gravar = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* sem armazenamento */ } };

  let gota = null, balao = null, holofote = null;

  // ------------------------------------------------------------ a Gota
  function montar() {
    if (gota) return;
    gota = el("button", {
      type: "button", id: "gota", title: "Assistente: clique para perguntar", "aria-label": "Assistente: o que você quer saber?",
      "aria-haspopup": "menu", "aria-expanded": "false",
      on: { click: (ev) => { ev.stopPropagation(); balao && !balao.hidden && balao.dataset.tipo === "menu" ? fecharBalao() : menu(); } },
    }, Icones.criar("gota"));
    balao = el("div", { id: "gota-balao", class: "gota-balao", role: "dialog", "aria-label": "Assistente", hidden: true });
    document.body.append(gota, balao);
    document.addEventListener("pointerdown", (ev) => {
      if (!balao.hidden && balao.dataset.tipo === "menu" && !balao.contains(ev.target) && !gota.contains(ev.target)) fecharBalao();
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "Escape" || balao.hidden) return;
      if (balao.dataset.tipo === "tour") encerrarTour(); else fecharBalao(true);
    });
    gota.hidden = ler(CHAVE_OCULTA) === "1";
    const marcar = () => document.body.classList.toggle("com-janela", Janelas.lista().some((j) => !j.minimizada));
    document.addEventListener("aero:janelas", marcar);
    marcar();
  }

  function mostrar() {
    montar();
    gota.hidden = false;
    gravar(CHAVE_OCULTA, null);
  }

  function esconder() {
    fecharBalao();
    gota.hidden = true;
    gravar(CHAVE_OCULTA, "1");
    Nucleo.balao("Assistente escondido", "Para chamar de volta, use o ícone Assistente na área de trabalho ou o menu iniciar.", "info");
  }

  function fecharBalao(devolverFoco = false) {
    if (!balao || balao.hidden) return;
    balao.hidden = true;
    gota.setAttribute("aria-expanded", "false");
    if (devolverFoco && !gota.hidden) gota.focus();
  }

  /** Mostra um balão de fala. `conteudo`: nós; `botoes`: [{ rotulo, primario, acao }]. */
  function falar(tipo, conteudo, botoes = []) {
    mostrar();
    balao.dataset.tipo = tipo;
    balao.replaceChildren(...[
      el("button", { type: "button", class: "fechar-balao", "aria-label": "Fechar", on: { click: () => (tipo === "tour" ? encerrarTour() : fecharBalao(true)) } }, "×"),
      ...conteudo,
      botoes.length ? el("div", { class: "gota-botoes" }, botoes.map((b) =>
        el("button", { type: "button", class: `botao${b.primario ? " gel" : ""} pequeno`, on: { click: b.acao } }, b.rotulo))) : null,
    ].filter(Boolean));          // replaceChildren escreveria "null" na tela
    balao.hidden = false;
    gota.setAttribute("aria-expanded", "true");
    const primeiro = balao.querySelector(".gota-botoes .botao, .gota-menu button");
    if (primeiro) primeiro.focus();
  }

  // ------------------------------------------------------------ menu
  const PERGUNTAS = [
    ["Como o risco é calculado?", () => abrirCalculo()],
    ["Por que um ativo tem esse risco?", () => escolherAtivo()],
    ["Como leio as matrizes e o gráfico?", () => AppMatrizes.abrir()],
    ["O que é uma falha e como prevenir?", () => escolherFalha()],
    ["O que é a verificação de invertibilidade?", () => abrirCalculo(Explicacoes.PASSO_INVERTIBILIDADE)],
    ["Como cadastro ativos, falhas e dependências?", () => abrirGuia("usar")],
    ["Onde fica cada parte no código?", () => abrirGuia("codigo")],
    ["Fazer o tour pela tela", () => tour()],
  ];

  function menu() {
    falar("menu", [
      el("p", { class: "gota-titulo" }, "O que você quer saber?"),
      el("div", { class: "gota-menu", role: "menu" }, PERGUNTAS.map(([texto, acao]) =>
        el("button", { type: "button", role: "menuitem", on: { click: () => { fecharBalao(); acao(); } } }, texto))),
      el("button", { type: "button", class: "link-discreto", on: { click: esconder } }, "Esconder o assistente"),
    ]);
  }

  function escolherAtivo() {
    const ativos = Nucleo.dados.ativos;
    if (!ativos.length) {
      falar("aviso", [el("p", {}, "Ainda não há ativos cadastrados. Cadastre alguns no Gerenciador de Ativos e me pergunte de novo.")],
        [{ rotulo: "Abrir o Gerenciador", primario: true, acao: () => { fecharBalao(); AppAtivos.abrir(); } }]);
      return;
    }
    falar("menu", [
      el("p", { class: "gota-titulo" }, "Qual ativo?"),
      el("div", { class: "gota-menu", role: "menu" }, ativos.slice(0, 10).map((a) =>
        el("button", { type: "button", role: "menuitem", on: { click: () => { fecharBalao(); explicarAtivo(a.id); } } }, a.nome))),
      ativos.length > 10 ? el("p", { class: "dica" }, "Para os outros, clique na esfera dele no Mapa da Rede.") : null,
    ]);
  }

  // ------------------------------------------------------- o assistente (wizard)
  async function carregar(url) {
    try {
      return await api(url);
    } catch (erro) {
      Nucleo.balao("Não foi possível explicar", erro.message, "erro");
      return null;
    }
  }

  /**
   * Janela no estilo dos assistentes do XP. `montarPassos(d)` recebe os dados
   * de `url` e devolve os passos; ao mudar algum dado, os números se atualizam.
   */
  function assistente({ id, titulo, montarPassos, inicio = 0, url = "/api/risco/passos" }) {
    let passos = [], atual = inicio, dados = null;
    const contador = el("span", { class: "contador" });
    const area = el("div", { class: "passo", tabindex: "-1" });
    const voltar = el("button", { type: "button", class: "botao", on: { click: () => ir(atual - 1) } }, "< Voltar");
    const avancar = el("button", { type: "button", class: "botao gel", on: { click: () => (atual < passos.length - 1 ? ir(atual + 1) : janela.fechar()) } }, "Avançar >");

    function caixaCodigo(lista) {
      if (!lista.length) return null;
      return el("details", { class: "no-codigo", open: true },
        el("summary", {}, Icones.criar("codigo"), "No código"),
        lista.map((c) => el("div", { class: "trecho" },
          el("div", { class: "onde" }, el("code", {}, c.arquivo), " › ", el("code", {}, `${c.funcao}()`)),
          el("pre", {}, c.trecho),
          el("p", {}, rico(c.texto)))));
    }

    function ir(i) {
      atual = Math.max(0, Math.min(passos.length - 1, i));
      const passo = passos[atual];
      area.replaceChildren(...[el("h3", {}, passo.titulo), ...passo.corpo, caixaCodigo(passo.codigo)].filter(Boolean));
      area.scrollTop = 0;
      contador.textContent = passos.length > 1 ? `Passo ${atual + 1} de ${passos.length}` : "";
      voltar.disabled = atual === 0;
      avancar.textContent = atual < passos.length - 1 ? "Avançar >" : "Concluir";
      area.focus({ preventScroll: true });
    }

    async function atualizar() {
      const d = await carregar(url);
      if (!d) return;
      dados = d;
      passos = montarPassos(d);
      ir(atual);
    }

    if (Janelas.aberta(id) || Janelas.lista().some((j) => j.id === id)) Janelas.fechar(id);
    const raiz = el("div", { class: "assistente" },
      el("div", { class: "assistente-faixa", "aria-hidden": "true" }, Icones.criar("gota"), el("span", {}, "Assistente")),
      el("div", { class: "assistente-meio" }, area,
        el("div", { class: "assistente-rodape" }, contador, el("span", { class: "espaco" }), voltar, avancar)));
    const desinscrever = Nucleo.assinar(() => { if (dados) atualizar(); });
    const janela = Janelas.abrir({
      id, titulo, icone: "gota", largura: 780, altura: 620, minLargura: 420, minAltura: 360, conteudo: raiz,
      aoFechar: desinscrever,
    });
    raiz.addEventListener("keydown", (ev) => {
      if (ev.target.closest("input, select, textarea, summary")) return;
      if (ev.key === "ArrowRight") { ev.preventDefault(); if (atual < passos.length - 1) ir(atual + 1); }
      if (ev.key === "ArrowLeft") { ev.preventDefault(); ir(atual - 1); }
    });
    area.replaceChildren(el("p", {}, "Carregando os seus dados…"));
    atualizar();
  }

  function abrirCalculo(inicio = 0) {
    assistente({ id: "calculo", titulo: "Assistente do Cálculo de Risco", montarPassos: Explicacoes.calculo, inicio });
  }

  function explicarAtivo(id) {
    const a = Nucleo.dados.ativos.find((x) => x.id === id);
    assistente({
      id: "ativo-explicado", titulo: `Por que esse risco? ${a ? a.nome : ""}`.trim(),
      montarPassos: (d) => Explicacoes.ativo(d, id),
    });
  }

  /** Explica uma falha: o que é, por que é perigosa, como prevenir e o que fazer agora. */
  function explicarFalha(ativoId, falhaId) {
    const a = Nucleo.dados.ativos.find((x) => x.id === ativoId);
    const url = `/api/ativos/${ativoId}/vulnerabilidades/${encodeURIComponent(falhaId)}/orientacao`;
    const mudarStatus = async (status) => {
      try {
        await Nucleo.alterar(() => api(`/api/ativos/${ativoId}/vulnerabilidades/${encodeURIComponent(falhaId)}`, Nucleo.json("PATCH", { status })));
        Nucleo.balao("Status atualizado", `${falhaId}: ${status}.`, "ok");
      } catch (erro) {
        Nucleo.balao("Não foi possível mudar o status", erro.message, "erro");
      }
    };
    assistente({
      id: "falha-explicada", titulo: `Assistente de Segurança${a ? `: ${a.nome}` : ""}`, url,
      montarPassos: (o) => Explicacoes.falha(o, { mudarStatus }),
    });
  }

  function escolherFalha() {
    const falhas = Nucleo.dados.ativos
      .flatMap((a) => a.vulnerabilidades.filter((v) => v.afeta_risco).map((v) => ({ a, v })))
      .sort((x, y) => y.v.severidade - x.v.severidade);
    if (!falhas.length) {
      falar("aviso", [el("p", {}, "Nenhuma falha aberta agora. Quando você registrar uma no Gerenciador de Ativos, eu explico o que ela é e como prevenir.")],
        [{ rotulo: "Abrir o Gerenciador", primario: true, acao: () => { fecharBalao(); AppAtivos.abrir(); } }]);
      return;
    }
    falar("menu", [
      el("p", { class: "gota-titulo" }, "Qual falha? (as mais graves primeiro)"),
      el("div", { class: "gota-menu", role: "menu" }, falhas.slice(0, 8).map(({ a, v }) =>
        el("button", { type: "button", role: "menuitem", on: { click: () => { fecharBalao(); explicarFalha(a.id, v.id); } } },
          `${Nucleo.num(v.severidade, 1)} · ${a.nome}: ${v.descricao_curta || v.categoria}`))),
      falhas.length > 8 ? el("p", { class: "dica" }, "As outras estão no Gerenciador de Ativos, no botão Explicar de cada falha.") : null,
    ]);
  }

  // ------------------------------------------------------------ guia
  function abrirGuia(aba = "usar") {
    if (Janelas.lista().some((j) => j.id === "guia")) Janelas.fechar("guia");
    const painel = el("div", { class: "painel-aba guia", role: "tabpanel" });
    const abas = [["usar", "Como usar"], ["codigo", "Onde está no código"]].map(([chave, rotulo]) =>
      el("button", { type: "button", class: "aba", role: "tab", "data-aba": chave, on: { click: () => mostrarAba(chave) } }, rotulo));

    function mostrarAba(chave) {
      abas.forEach((b) => b.setAttribute("aria-selected", String(b.dataset.aba === chave)));
      if (chave === "usar") {
        painel.replaceChildren(el("dl", { class: "guia-lista" }, Explicacoes.COMO_USAR.flatMap(([t, d]) => [el("dt", {}, t), el("dd", {}, rico(d))])),
          el("div", { class: "acoes" },
            el("button", { type: "button", class: "botao gel", on: { click: () => AppAtivos.abrir() } }, "Abrir o Gerenciador de Ativos")));
      } else {
        painel.replaceChildren(
          el("p", { class: "dica" }, "Os arquivos do projeto, na ordem em que os dados passam por eles: classes → JSON → regras → API → tela."),
          ...Explicacoes.CODIGO.map((g) => el("section", { class: "grupo" }, el("h3", {}, g.grupo),
            el("dl", { class: "guia-lista codigo" }, g.itens.flatMap(([arq, d]) => [el("dt", {}, el("code", {}, arq)), el("dd", {}, rico(d))])))));
      }
      painel.scrollTop = 0;
    }

    const raiz = el("div", { class: "app" }, el("div", { class: "abas", role: "tablist", "aria-label": "Guia" }, abas), painel);
    Janelas.abrir({ id: "guia", titulo: "Guia do Assistente", icone: "gota", largura: 720, altura: 520, conteudo: raiz });
    mostrarAba(aba);
  }

  // ------------------------------------------------------------- tour
  const PARADAS = [
    ["#icones", "Aqui ficam os programas. Um clique abre cada um."],
    ["#area-janelas .janela[aria-label='Mapa da Rede']", "O **Mapa da Rede**: cada esfera é um ativo, a cor é o risco efetivo e os canos são as dependências. Clique numa esfera para ver de onde vem o risco dela."],
    ["#btn-iniciar", "Tudo também está no **menu iniciar**, inclusive o passo a passo do cálculo."],
    ["#tray-saude", "Este escudo mostra se o serviço está no ar: **verde** é tudo certo. Clique nele para ver o diário das 24 horas."],
    ["#gota", "E eu fico aqui. Quando tiver uma dúvida, sobre a tela, a conta ou o código, é só clicar em mim."],
  ];
  let paradaAtual = 0;

  function tour() {
    if (!Janelas.aberta("mapa")) AppMapa.abrir();
    paradaAtual = 0;
    setTimeout(parada, 60);
  }

  function parada() {
    let alvo = null;
    const visivel = (n) => n && n.getClientRects().length > 0 && getComputedStyle(n).display !== "none";
    while (paradaAtual < PARADAS.length && !visivel(alvo = document.querySelector(PARADAS[paradaAtual][0]))) paradaAtual++;
    if (!visivel(alvo)) alvo = null;
    if (!alvo) { encerrarTour(); return; }
    const r = alvo.getBoundingClientRect();
    if (!holofote) { holofote = el("div", { class: "holofote", "aria-hidden": "true" }); document.body.append(holofote); }
    holofote.hidden = false;
    Object.assign(holofote.style, { left: `${r.left - 6}px`, top: `${r.top - 6}px`, width: `${r.width + 12}px`, height: `${r.height + 12}px` });
    const ultima = paradaAtual === PARADAS.length - 1;
    falar("tour", [el("p", { class: "gota-titulo" }, `Tour · ${paradaAtual + 1} de ${PARADAS.length}`), el("p", {}, rico(PARADAS[paradaAtual][1]))], [
      { rotulo: ultima ? "Concluir" : "Próximo", primario: true, acao: () => { if (ultima) encerrarTour(); else { paradaAtual++; parada(); } } },
      ...(ultima ? [] : [{ rotulo: "Pular tour", acao: encerrarTour }]),
    ]);
  }

  function encerrarTour() {
    if (holofote) holofote.hidden = true;
    fecharBalao(true);
  }

  // ----------------------------------------------------------- entrada
  /** Chamado pelo desktop depois da tela de entrada. Só fala na primeira visita. */
  function iniciar() {
    montar();
    if (ler(CHAVE_OI) === "1" || gota.hidden) return;
    setTimeout(() => {
      if (!balao.hidden) { gravar(CHAVE_OI, "1"); return; } // já está conversando com a Gota
      if (document.querySelector(".veu")) return;          // há um diálogo aberto: não interrompe
      if (getComputedStyle(gota).display === "none") return; // celular com janela aberta: fica para depois
      gravar(CHAVE_OI, "1");
      falar("oi", [
        el("p", { class: "gota-titulo" }, "Oi! Eu sou a Gota."),
        el("p", {}, "Explico a tela, a conta do risco e o código. Quer um tour rápido de 5 passos?"),
      ], [
        { rotulo: "Fazer o tour", primario: true, acao: () => tour() },
        { rotulo: "Agora não", acao: () => fecharBalao(true) },
      ]);
    }, 1200);
  }

  return { iniciar, menu: () => { menu(); }, abrirCalculo, explicarAtivo, explicarFalha, abrirGuia, tour, mostrar };
})();

window.AppAssistente = AppAssistente;
