/* Gerenciador de janelas do desktop Aero.
 *
 *   Janelas.abrir({ id, titulo, icone, largura, altura, conteudo, aoFechar, aoRedimensionar })
 *   Janelas.dialogo({ titulo, icone, texto, corpo, botoes })  -> Promise com o valor do botão
 *
 * Janelas abrem, arrastam (pela barra de título), redimensionam (pelo canto),
 * minimizam (vão para a barra de tarefas), maximizam (duplo clique no título)
 * e fecham. No celular, ficam sempre em tela cheia.
 */
const Janelas = (() => {
  "use strict";
  const { el } = Nucleo;

  const abertas = new Map();      // id -> estado
  let zTopo = 20;
  let ativaId = null;
  let cascata = 0;

  const area = () => document.getElementById("area-janelas");
  const celular = () => window.matchMedia("(max-width: 760px)").matches;
  const avisar = () => document.dispatchEvent(new CustomEvent("aero:janelas"));

  // -------------------------------------------------------------- foco
  function focar(id) {
    const j = abertas.get(id);
    if (!j) return;
    if (j.minimizada) j.el.classList.remove("minimizada"), (j.minimizada = false);
    j.el.style.zIndex = String(++zTopo);
    for (const outra of abertas.values()) outra.el.classList.toggle("ativa", outra === j);
    ativaId = id;
    avisar();
  }

  function minimizar(id) {
    const j = abertas.get(id);
    if (!j || j.minimizada) return;
    j.minimizada = true;
    j.el.classList.add("minimizada");
    j.el.classList.remove("ativa");
    if (ativaId === id) {
      ativaId = null;
      const proxima = [...abertas.values()].filter((x) => !x.minimizada).sort((a, b) => Number(b.el.style.zIndex) - Number(a.el.style.zIndex))[0];
      if (proxima) focar(proxima.id); else avisar();
    } else avisar();
  }

  function alternarMaximizada(id) {
    const j = abertas.get(id);
    if (!j || celular()) return;
    j.el.classList.toggle("max");
    focar(id);
    if (j.opc.aoRedimensionar) j.opc.aoRedimensionar();
  }

  function fechar(id) {
    const j = abertas.get(id);
    if (!j) return;
    if (j.observador) j.observador.disconnect();
    if (j.opc.aoFechar) j.opc.aoFechar();
    j.el.remove();
    abertas.delete(id);
    if (ativaId === id) {
      ativaId = null;
      const proxima = [...abertas.values()].filter((x) => !x.minimizada).sort((a, b) => Number(b.el.style.zIndex) - Number(a.el.style.zIndex))[0];
      if (proxima) { focar(proxima.id); return; }
    }
    avisar();
  }

  /** Clique na barra de tarefas: restaura, minimiza ou traz para a frente. */
  function alternar(id) {
    const j = abertas.get(id);
    if (!j) return;
    if (j.minimizada) focar(id);
    else if (ativaId === id) minimizar(id);
    else focar(id);
  }

  // ------------------------------------------------------ arrastar/redimensionar
  function permitirArrasto(janela, titulo) {
    titulo.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0 || ev.target.closest(".ctl") || janela.classList.contains("max") || celular()) return;
      const caixa = janela.getBoundingClientRect();
      const base = area().getBoundingClientRect();
      const dx = ev.clientX - caixa.left, dy = ev.clientY - caixa.top;
      titulo.setPointerCapture(ev.pointerId);
      const mover = (e) => {
        const x = Math.min(Math.max(e.clientX - dx - base.left, 80 - caixa.width), base.width - 80);
        const y = Math.min(Math.max(e.clientY - dy - base.top, 0), base.height - 32);
        janela.style.left = `${x}px`;
        janela.style.top = `${y}px`;
      };
      const soltar = () => {
        titulo.removeEventListener("pointermove", mover);
        titulo.removeEventListener("pointerup", soltar);
        titulo.removeEventListener("pointercancel", soltar);
      };
      titulo.addEventListener("pointermove", mover);
      titulo.addEventListener("pointerup", soltar);
      titulo.addEventListener("pointercancel", soltar);
    });
  }

  function permitirRedimensionar(janela, grip, minimo) {
    grip.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      ev.preventDefault();
      const caixa = janela.getBoundingClientRect();
      const base = area().getBoundingClientRect();
      const x0 = ev.clientX, y0 = ev.clientY;
      grip.setPointerCapture(ev.pointerId);
      const mover = (e) => {
        janela.style.width = `${Math.min(Math.max(minimo.l, caixa.width + e.clientX - x0), base.width - (caixa.left - base.left))}px`;
        janela.style.height = `${Math.min(Math.max(minimo.a, caixa.height + e.clientY - y0), base.height - (caixa.top - base.top))}px`;
      };
      const soltar = () => {
        grip.removeEventListener("pointermove", mover);
        grip.removeEventListener("pointerup", soltar);
        grip.removeEventListener("pointercancel", soltar);
      };
      grip.addEventListener("pointermove", mover);
      grip.addEventListener("pointerup", soltar);
      grip.addEventListener("pointercancel", soltar);
    });
  }

  function botaoControle(classe, rotulo, aoClicar) {
    return el("button", { type: "button", class: classe, "aria-label": rotulo, title: rotulo, on: { click: aoClicar } });
  }

  // -------------------------------------------------------------- abrir
  function abrir(opc) {
    const { id } = opc;
    if (abertas.has(id)) { focar(id); return abertas.get(id).api; }

    const base = area().getBoundingClientRect();
    const largura = Math.min(opc.largura || 640, base.width - 16);
    const altura = Math.min(opc.altura || 460, base.height - 16);
    const x = opc.x ?? Math.max(8, Math.min(120 + cascata * 28, base.width - largura - 8));
    const y = opc.y ?? Math.max(8, Math.min(24 + cascata * 28, base.height - altura - 8));
    cascata = (cascata + 1) % 8;

    const titulo = el("h2", {}, opc.titulo);
    const barra = el("header", { class: "janela-titulo" }, Icones.criar(opc.icone || "info"), titulo,
      el("div", { class: "ctl" },
        botaoControle("min", "Minimizar", () => minimizar(id)),
        botaoControle("maxi", "Maximizar ou restaurar", () => alternarMaximizada(id)),
        botaoControle("fechar", "Fechar", () => fechar(id))));
    const corpo = el("div", { class: "janela-corpo" }, opc.conteudo);
    const grip = el("span", { class: "grip", "aria-hidden": "true" });
    const janela = el("section", {
      class: "janela", role: "dialog", "aria-label": opc.titulo, tabindex: "-1",
      style: `left:${x}px;top:${y}px;width:${largura}px;height:${altura}px`,
    }, barra, corpo, grip);

    janela.addEventListener("pointerdown", () => { if (ativaId !== id) focar(id); }, true);
    barra.addEventListener("dblclick", (ev) => { if (!ev.target.closest(".ctl")) alternarMaximizada(id); });
    permitirArrasto(janela, barra);
    permitirRedimensionar(janela, grip, { l: opc.minLargura || 340, a: opc.minAltura || 220 });

    area().append(janela);
    const estado = { id, el: janela, corpo, opc, minimizada: false, observador: null };
    estado.api = {
      id, el: janela, corpo,
      fechar: () => fechar(id),
      focar: () => focar(id),
      titulo: (t) => { titulo.textContent = t; janela.setAttribute("aria-label", t); },
    };
    if (opc.aoRedimensionar) {
      estado.observador = new ResizeObserver(() => opc.aoRedimensionar());
      estado.observador.observe(corpo);
    }
    abertas.set(id, estado);
    focar(id);
    return estado.api;
  }

  // ------------------------------------------------------------ diálogos
  /**
   * Janela modal no estilo do XP. Cada botão: { rotulo, valor, primario, perigo, aoClicar }.
   * Se aoClicar devolver false ou lançar erro, o diálogo continua aberto (o erro aparece nele).
   */
  function dialogo({ titulo, icone = "info", texto, corpo, botoes }) {
    return new Promise((resolver) => {
      const anterior = document.activeElement;
      const erro = el("p", { class: "erro-inline", role: "alert", hidden: true });
      const lista = (botoes && botoes.length ? botoes : [{ rotulo: "OK", primario: true }]).map((b) => ({ ...b, valor: b.valor ?? b.rotulo }));
      const elementosBotao = [];

      let veu;
      const encerrar = (valor) => {
        document.removeEventListener("keydown", teclas, true);
        veu.remove();
        if (anterior && anterior.isConnected) anterior.focus();
        resolver(valor);
      };

      const ocupado = (sim) => elementosBotao.forEach((b) => { b.disabled = sim; });
      async function clicou(b) {
        erro.hidden = true;
        if (!b.aoClicar) { encerrar(b.valor); return; }
        ocupado(true);
        try {
          const r = await b.aoClicar();
          if (r === false) { ocupado(false); return; }
          encerrar(b.valor);
        } catch (e) {
          erro.textContent = e.message || String(e);
          if (e.dica) erro.textContent += ` ${e.dica}`;
          erro.hidden = false;
          ocupado(false);
        }
      }

      for (const b of lista) {
        const botao = el("button", {
          type: "button", class: `botao${b.primario ? " gel" : ""}${b.perigo ? " perigo" : ""}`,
          on: { click: () => clicou(b) },
        }, b.rotulo);
        elementosBotao.push(botao);
      }
      // `foco` escolhe quem começa focado (ex.: "Cancelar" numa exclusão); senão, o botão principal.
      const primario = elementosBotao[Math.max(0, lista.findIndex((b) => b.foco || b.primario))] || elementosBotao[0];

      const fecharX = botaoControle("fechar", "Fechar", () => encerrar(null));
      const janela = el("section", { class: "janela dialogo ativa", role: "alertdialog", "aria-modal": "true", "aria-label": titulo, tabindex: "-1" },
        el("header", { class: "janela-titulo" }, el("h2", {}, titulo), el("div", { class: "ctl" }, fecharX)),
        el("div", { class: "dialogo-corpo" }, Icones.criar(icone),
          el("div", { class: "conteudo" }, texto ? el("p", {}, texto) : null, corpo || null)),
        erro,
        el("div", { class: "dialogo-rodape" }, ...elementosBotao));

      // Enter confirma pelo botão principal (menos dentro de áreas de texto); Tab não sai do diálogo.
      function teclas(ev) {
        if (ev.key === "Escape") { ev.preventDefault(); encerrar(null); return; }
        if (ev.key === "Tab") {
          const alvos = [...janela.querySelectorAll("button, input, select, textarea, a[href]")].filter((n) => !n.disabled && n.offsetParent !== null);
          if (!alvos.length) return;
          const primeiro = alvos[0], ultimo = alvos[alvos.length - 1];
          if (ev.shiftKey && document.activeElement === primeiro) { ev.preventDefault(); ultimo.focus(); }
          else if (!ev.shiftKey && document.activeElement === ultimo) { ev.preventDefault(); primeiro.focus(); }
        }
      }
      document.addEventListener("keydown", teclas, true);

      veu = el("div", { class: "veu" }, janela);
      document.body.append(veu);
      const caixa = janela.getBoundingClientRect();
      janela.style.left = `${Math.max(8, (window.innerWidth - caixa.width) / 2)}px`;
      janela.style.top = `${Math.max(8, (window.innerHeight - caixa.height) / 3)}px`;
      permitirArrasto(janela, janela.querySelector(".janela-titulo"));
      janela.style.position = "fixed";
      const primeiroCampo = janela.querySelector("input, select, textarea");
      (primeiroCampo || primario).focus();
    });
  }

  function lista() {
    return [...abertas.values()].map((j) => ({
      id: j.id, titulo: j.opc.titulo, icone: j.opc.icone || "info", minimizada: j.minimizada, ativa: ativaId === j.id,
    }));
  }

  return {
    abrir, dialogo, fechar, focar, minimizar, alternar, lista,
    fecharTodas: () => [...abertas.keys()].forEach(fechar),
    aberta: (id) => abertas.has(id) && !abertas.get(id).minimizada,
    ativa: () => ativaId,
  };
})();

window.Janelas = Janelas;
