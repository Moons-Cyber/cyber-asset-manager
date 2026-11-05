/* Monitor do Serviço: saúde da API e diário das últimas 24 horas.
 * O servidor calcula o risco uma vez por hora e anota em diario.json; aqui cada hora
 * vira um bloco verde (houve registro), vermelho (faltou) ou listrado
 * (antes do primeiro registro).
 */
const AppMonitor = (() => {
  "use strict";
  const { el, num, api } = Nucleo;
  let ui = null, ultimo = null, ciclo = null;

  async function carregar() {
    if (!ui) return;
    await Nucleo.checarSaude();
    desenharSaude();
    let d;
    try {
      d = await api("/api/diario");
    } catch (erro) {
      ultimo = null;
      ui.resumo.textContent = erro.status === 404
        ? "O diário está desligado neste servidor. Ele liga com o servidor.py (variável DIARIO_INTERVALO_S, padrão: 1 hora)."
        : `Não foi possível ler o diário: ${erro.message}`;
      ui.blocos.replaceChildren(...Array.from({ length: 24 }, () => el("i", { class: "antes" })));
      ui.tabela.replaceChildren();
      desenharGrafico([], Date.now() / 1000);
      return;
    }
    ultimo = d;
    const e = d.entradas;
    const intervalo = d.intervalo_s > 0 ? d.intervalo_s : 3600;
    const inicio = d.agora - 24 * 3600;
    const janela = e.filter((x) => x.t >= inicio);
    const primeira = janela.length ? janela[0].t : null;
    const horas = Array.from({ length: 24 }, (_, h) => {
      const a = inicio + h * 3600, b = a + 3600;
      if (janela.some((x) => x.t >= a && x.t < b)) return "ok";
      if (primeira === null || b <= primeira) return "antes";
      return a < d.agora - intervalo ? "falha" : "antes";
    });
    const comRegistro = horas.filter((h) => h === "ok").length;
    const comErro = janela.filter((x) => x.erro).length;
    ui.resumo.textContent = e.length
      ? `${e.length} anotações desde ${new Date(e[0].t * 1000).toLocaleString("pt-BR")}. Nas últimas 24 horas, ${comRegistro} de 24 horas têm registro`
        + (comErro ? ` e ${comErro} anotação(ões) não conseguiram calcular o risco.` : " e o cálculo funcionou em todas.")
      : "Nenhuma anotação ainda. A primeira é feita quando o servidor liga.";
    ui.blocos.replaceChildren(...horas.map((estado, h) => {
      const quando = new Date((inicio + h * 3600) * 1000).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
      return el("i", { class: estado, title: `${quando}: ${estado === "ok" ? "com registro" : estado === "falha" ? "sem registro" : "antes do primeiro registro"}` });
    }));
    const rot = (h) => new Date((inicio + h * 3600) * 1000).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    ui.eixo.replaceChildren(el("span", {}, rot(0)), el("span", {}, rot(6)), el("span", {}, rot(12)), el("span", {}, rot(18)), el("span", {}, "agora"));
    ui.tabela.replaceChildren(
      el("thead", {}, el("tr", {}, ["Quando", "Motivo", "Ativos", "Dependências", "Risco global", "I − A invertível"].map((t, k) =>
        el("th", { scope: "col", class: k >= 2 ? "num" : null }, t)))),
      el("tbody", {}, e.slice(-48).reverse().map((x) => el("tr", {},
        el("td", {}, new Date(x.t * 1000).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })),
        el("td", {}, x.erro ? `${x.motivo} (erro: ${x.erro})` : x.motivo),
        el("td", { class: "num" }, x.ativos),
        el("td", { class: "num" }, x.dependencias ?? "--"),
        el("td", { class: "num" }, num(x.risco_global)),
        el("td", { class: "num" }, x.invertivel === true ? "sim" : x.invertivel === false ? "não" : "--")))));
    desenharGrafico(e, d.agora);
  }

  function desenharSaude() {
    const s = Nucleo.saude;
    ui.painel.classList.toggle("falha", s.ok === false);
    ui.icone.replaceChildren(Icones.criar("escudo", s.ok === null ? "neutro" : s.ok ? "ok" : "falha"));
    ui.titulo.textContent = s.ok === null ? "Verificando…" : s.ok ? "Serviço no ar" : "Serviço sem resposta";
    ui.detalhe.textContent = s.ok === null ? "" : s.ok
      ? `${s.ativos ?? 0} ativo(s) cadastrados. Verificado às ${s.quando.toLocaleTimeString("pt-BR")}.`
      : `${s.motivo}. Verificado às ${s.quando.toLocaleTimeString("pt-BR")}.`;
  }

  function desenharGrafico(entradas, agora) {
    const c = ui.grafico, dpr = Math.min(2, window.devicePixelRatio || 1);
    const L = c.clientWidth, A = c.clientHeight;
    if (!L || !A) return;
    c.width = Math.round(L * dpr); c.height = Math.round(A * dpr);
    const g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const x0 = 8, x1 = L - 8, y0 = 10, y1 = A - 18;
    const inicio = agora - 24 * 3600;
    const px = (t) => x0 + ((t - inicio) / (24 * 3600)) * (x1 - x0);
    const janela = entradas.filter((x) => x.t >= inicio);
    const topo = Math.max(1, ...janela.map((x) => x.risco_global || 0)) * 1.15;
    const py = (v) => y1 - (v / topo) * (y1 - y0);
    g.strokeStyle = "#cfd8e6"; g.beginPath(); g.moveTo(x0, y1 + 0.5); g.lineTo(x1, y1 + 0.5); g.stroke();
    g.font = "10.5px Tahoma, sans-serif"; g.fillStyle = "#5a6a85";
    for (let h = 0; h <= 24; h += 6) {
      const t = inicio + h * 3600;
      g.textAlign = h === 0 ? "left" : h === 24 ? "right" : "center";
      g.fillText(new Date(t * 1000).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }), px(t), A - 4);
    }
    for (const x of janela) {
      if (x.risco_global !== null && x.risco_global !== undefined) {
        const gr = g.createLinearGradient(0, py(x.risco_global), 0, y1);
        gr.addColorStop(0, "#6db8ff"); gr.addColorStop(1, "#1a58d8");
        g.fillStyle = gr; g.fillRect(px(x.t) - 2, py(x.risco_global), 4, y1 - py(x.risco_global));
      }
      if (x.erro) {
        g.fillStyle = "#e5513f"; g.beginPath(); g.arc(px(x.t), y1 - 4, 3.5, 0, Math.PI * 2); g.fill();
      }
    }
    if (!janela.length) { g.fillStyle = "#5a6a85"; g.textAlign = "center"; g.fillText("Sem anotações nas últimas 24 horas", L / 2, A / 2 - 4); }
  }

  async function copiar() {
    const s = Nucleo.saude;
    const linhas = [
      `Resumo do serviço (${new Date().toLocaleString("pt-BR")})`,
      `Saúde: ${s.ok ? "no ar" : "sem resposta"}; ativos: ${s.ativos ?? "?"}`,
      ui.resumo.textContent,
    ];
    try {
      await navigator.clipboard.writeText(linhas.join("\n"));
      Nucleo.balao("Resumo copiado", "Cole no relatório ou no e-mail da entrega.", "ok");
    } catch {
      Nucleo.balao("Não foi possível copiar", "Selecione o texto do resumo e copie manualmente.", "aviso");
    }
  }

  function construir() {
    const icone = el("span", {}), titulo = el("h3", {}, "Verificando…"), detalhe = el("p", {}, "");
    const painel = el("section", { class: "painel-saude", "aria-live": "polite" }, icone, el("div", {}, titulo, detalhe));
    const resumo = el("p", {}, "Carregando…");
    const blocos = el("div", { class: "blocos24", role: "img", "aria-label": "Uma marca por hora nas últimas 24 horas" });
    const eixo = el("div", { class: "eixo24" });
    const grafico = el("canvas", { class: "grafico-diario", role: "img", "aria-label": "Risco global por hora" });
    const tabela = el("table", { class: "lista" });
    const raiz = el("div", { class: "app" },
      el("div", { class: "ferramentas" },
        el("button", { type: "button", class: "botao gel", on: { click: carregar } }, "Atualizar"),
        el("button", { type: "button", class: "botao", on: { click: copiar } }, "Copiar resumo")),
      el("div", { class: "painel-aba", style: "overflow:auto" }, el("div", { class: "monitor" },
        painel,
        el("section", { class: "grupo" }, el("h3", {}, "Últimas 24 horas"), resumo, blocos, eixo,
          el("div", { class: "legenda-diario" },
            el("span", { style: "--c:#44c331" }, "com registro"), el("span", { style: "--c:#e5513f" }, "sem registro"),
            el("span", { style: "--c:#e6e3d3" }, "antes do primeiro registro"))),
        el("section", { class: "grupo" }, el("h3", {}, "Risco global, hora a hora"), grafico,
          el("div", { class: "legenda-diario" }, el("span", { style: "--c:#1a58d8" }, "risco global calculado"), el("span", { style: "--c:#e5513f" }, "cálculo falhou"))),
        el("section", { class: "grupo" }, el("h3", {}, "Últimas 48 anotações"), el("div", { class: "rolagem-curta", style: "max-height:240px" }, tabela)))));
    ui = { raiz, icone, titulo, detalhe, painel, resumo, blocos, eixo, grafico, tabela };
    return raiz;
  }

  function abrir() {
    if (ui) { Janelas.focar("monitor"); return; }
    const conteudo = construir();
    Janelas.abrir({
      id: "monitor", titulo: "Monitor do Serviço", icone: "monitor", largura: 760, altura: 600, conteudo,
      aoRedimensionar: () => { if (ui && ultimo) desenharGrafico(ultimo.entradas, ultimo.agora); },
      aoFechar: () => { clearInterval(ciclo); ui = null; ultimo = null; },
    });
    carregar();
    ciclo = setInterval(carregar, 30000);
  }

  return { abrir };
})();

window.AppMonitor = AppMonitor;
