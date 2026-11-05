/* O desktop: tela de entrada, ícones, menu iniciar, barra de tarefas,
 * bandeja (saúde do serviço, relógio) e balões de aviso.
 */
(() => {
  "use strict";
  const { el } = Nucleo;
  const $ = (id) => document.getElementById(id);
  const calmo = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const PROGRAMAS = [
    { id: "mapa", titulo: "Mapa da Rede", curto: "Mapa da Rede", sub: "Ativos, dependências e risco", icone: "rede", abrir: () => AppMapa.abrir() },
    { id: "ativos", titulo: "Gerenciador de Ativos", curto: "Ativos", sub: "Cadastro, falhas e dependências", icone: "ativos", abrir: () => AppAtivos.abrir() },
    { id: "monitor", titulo: "Monitor do Serviço", curto: "Monitor 24h", sub: "Saúde e diário do container", icone: "monitor", abrir: () => AppMonitor.abrir() },
    { id: "assistente", titulo: "Assistente", curto: "Assistente", sub: "Explica a tela, a conta e o código", icone: "gota", abrir: () => AppAssistente.menu() },
  ];

  // ----------------------------------------------------------- papel de parede
  function criarBolhas() {
    if (calmo) return;
    const caixa = $("bolhas");
    for (let i = 0; i < 16; i++) {
      const tam = 18 + Math.round(Math.random() * 56);
      caixa.append(el("span", {
        class: "bolha",
        style: `left:${Math.round(Math.random() * 100)}%;width:${tam}px;height:${tam}px;`
          + `animation-duration:${26 + Math.round(Math.random() * 30)}s;animation-delay:-${Math.round(Math.random() * 40)}s`,
      }));
    }
  }

  // ------------------------------------------------------------------ ícones
  function montarIcones() {
    $("icones").replaceChildren(...PROGRAMAS.map((p) =>
      el("button", { type: "button", class: "icone", title: p.titulo, on: { click: () => p.abrir() } },
        Icones.criar(p.icone), el("span", {}, p.curto))));
  }

  // ------------------------------------------------------------ menu iniciar
  const menu = $("menu-iniciar");
  const botaoIniciar = $("btn-iniciar");

  function itemMenu(icone, titulo, sub, aoClicar, classe = "") {
    return el("button", { type: "button", role: "menuitem", class: `menu-item ${classe}`, on: { click: () => { fecharMenu(); aoClicar(); } } },
      Icones.criar(icone), el("span", {}, el("b", {}, titulo), sub ? el("small", {}, sub) : null));
  }

  function montarMenu() {
    menu.replaceChildren(
      el("div", { class: "menu-topo" }, Icones.criar("orbe"),
        el("div", {}, "Inventário de Ativos", el("small", {}, "Trabalho 2 · Sprints 3 a 5"))),
      el("div", { class: "menu-colunas" },
        el("div", { class: "menu-esq" }, PROGRAMAS.map((p) => itemMenu(p.icone, p.titulo, p.sub, p.abrir))),
        el("div", { class: "menu-dir" },
          itemMenu("pergunta", "Como o risco é calculado", null, () => AppAssistente.abrirCalculo()),
          itemMenu("codigo", "Onde está no código", null, () => AppAssistente.abrirGuia("codigo")),
          itemMenu("gota", "Fazer o tour", null, () => AppAssistente.tour()),
          itemMenu("info", "Sobre o projeto", null, sobre),
          itemMenu("janelas", "Fechar janelas", null, () => Janelas.fecharTodas()))),
      el("div", { class: "menu-pe" },
        itemMenu("gota", "Assistente: o que você quer saber?", null, () => AppAssistente.menu())));
  }

  function abrirMenu() {
    menu.hidden = false;
    botaoIniciar.setAttribute("aria-expanded", "true");
    const primeiro = menu.querySelector(".menu-item");
    if (primeiro) primeiro.focus();
  }
  function fecharMenu(devolverFoco = false) {
    if (menu.hidden) return;
    menu.hidden = true;
    botaoIniciar.setAttribute("aria-expanded", "false");
    if (devolverFoco) botaoIniciar.focus();
  }
  botaoIniciar.addEventListener("click", (ev) => { ev.stopPropagation(); menu.hidden ? abrirMenu() : fecharMenu(); });
  document.addEventListener("pointerdown", (ev) => {
    if (!menu.hidden && !menu.contains(ev.target) && !botaoIniciar.contains(ev.target)) fecharMenu();
  });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !menu.hidden) fecharMenu(true); });

  function sobre() {
    Janelas.dialogo({
      titulo: "Sobre o projeto", icone: "info",
      texto: "Inventário de Ativos de TI: cadastra ativos e falhas, e calcula o risco efetivo resolvendo (I − A)x = b. "
        + "O servidor é uma API Flask que roda em um container Docker; esta tela é só mais uma forma de usá-la.",
      botoes: [{ rotulo: "OK", primario: true }],
    });
  }

  // -------------------------------------------------------- barra de tarefas
  function atualizarTarefas() {
    $("tarefas").replaceChildren(...Janelas.lista().map((j) =>
      el("button", {
        type: "button", class: "tarefa", "aria-pressed": String(j.ativa), title: j.titulo,
        on: { click: () => Janelas.alternar(j.id) },
      }, Icones.criar(j.icone), el("span", {}, j.titulo))));
  }
  document.addEventListener("aero:janelas", atualizarTarefas);

  // ---------------------------------------------------------------- bandeja
  const tray = $("tray-saude");
  function atualizarTray() {
    const s = Nucleo.saude;
    const estado = s.ok === null ? "neutro" : s.ok ? "ok" : "falha";
    tray.replaceChildren(Icones.criar("escudo", estado));
    tray.className = `tray ${s.ok === false ? "falha" : ""}`;
    const texto = s.ok === null ? "Verificando o serviço…"
      : s.ok ? `Serviço no ar · ${s.ativos ?? 0} ativo(s) · verificado às ${s.quando.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
        : `Serviço sem resposta (${s.motivo}).`;
    tray.title = texto;
    tray.setAttribute("aria-label", texto);
  }
  tray.addEventListener("click", () => AppMonitor.abrir());

  Nucleo.assinarSaude((s, antes) => {
    atualizarTray();
    if (antes === true && s.ok === false) Nucleo.balao("Serviço sem resposta", `O servidor parou de responder: ${s.motivo}.`, "erro");
    else if (antes === false && s.ok === true) Nucleo.balao("Serviço restabelecido", "O servidor voltou a responder.", "ok");
  });

  function relogio() {
    $("relogio").textContent = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  // ---------------------------------------------------------------- balões
  document.addEventListener("aero:balao", (ev) => {
    const { titulo, texto, tipo } = ev.detail;
    const icone = { ok: "ok", erro: "erro", aviso: "aviso", info: "info" }[tipo] || "info";
    const balao = el("div", { class: "balao", role: "status", title: "Clique para fechar" },
      el("strong", {}, Icones.criar(icone), titulo), el("span", {}, texto));
    const remover = () => balao.remove();
    balao.addEventListener("click", remover);
    $("baloes").append(balao);
    while ($("baloes").children.length > 3) $("baloes").firstChild.remove();
    setTimeout(remover, tipo === "erro" ? 9000 : 6000);
  });

  // ---------------------------------------------------------------- entrada
  async function entrar() {
    $("boot-logo").append(Icones.criar("rede"));
    let jaViu = false;
    try { jaViu = sessionStorage.getItem("aero-boot") === "1"; } catch { /* sem armazenamento */ }
    const minimo = calmo || jaViu ? 0 : 1900;

    let pular;
    const espera = new Promise((resolver) => { pular = resolver; setTimeout(resolver, minimo); });
    $("boot").addEventListener("pointerdown", () => pular());
    document.addEventListener("keydown", () => pular(), { once: true });

    const [saude] = await Promise.allSettled([Nucleo.checarSaude(), Nucleo.recarregar(), espera]);
    await espera;
    try { sessionStorage.setItem("aero-boot", "1"); } catch { /* sem armazenamento */ }

    $("boot").classList.add("some");
    setTimeout(() => { $("boot").hidden = true; }, calmo ? 0 : 600);

    if (!Nucleo.saude.ok) {
      Janelas.dialogo({
        titulo: "Sem conexão com o serviço", icone: "erro",
        texto: `Não foi possível falar com a API (${Nucleo.saude.motivo || "sem detalhes"}). `
          + "Confira se o container está no ar. Esta tela tenta de novo a cada 15 segundos.",
      });
    } else {
      setTimeout(() => Nucleo.balao("Bem-vindo", `Serviço no ar com ${Nucleo.saude.ativos ?? 0} ativo(s). Use os ícones ou o menu iniciar.`, "info"), 500);
    }
    PROGRAMAS[0].abrir();
    AppAssistente.iniciar();
    void saude;
  }

  criarBolhas();
  montarIcones();
  montarMenu();
  $("orbe-iniciar").append(Icones.criar("orbe"));
  atualizarTray();
  relogio();
  setInterval(relogio, 15000);
  setInterval(() => Nucleo.checarSaude(), 15000);
  entrar();
})();
