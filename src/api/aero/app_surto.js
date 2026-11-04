/* Varredura de Contágio: o risco se espalhando pela rede.
 *
 * Mostra o grafo de ativos como esferas de vidro ligadas por canos. A cada
 * "epidemia" sorteada no navegador (classe Epidemia, a mesma regra do
 * servidor), bolhas de infecção correm pelos canos. Ao lado: o R0, a
 * comparação sorteio x álgebra e o ranking de defesa (o que corrigir primeiro).
 */
const AppSurto = (() => {
  "use strict";
  const { el, num, api, json, dados: nucleoDados } = Nucleo;

  const RODADAS_SERVIDOR = 2000;
  const VELOCIDADES = [["1×", 3], ["10×", 30], ["100×", 300]];
  const COR = { verde: "#4fc23a", amarelo: "#f2cf2a", laranja: "#f08a24", vermelho: "#e0392b", neutro: "#9aa8bb" };
  const corDoRisco = (x) => COR[Nucleo.faixa(x).classe];
  const calmo = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const est = {
    dados: null, epi: null, rodando: false, vel: 30, escala: 1, acumulado: 0,
    particulas: [], flashes: new Map(), ondas: [], pos: {}, explodiuEm: null,
    ultimaCorrecao: null, erro: null, ultimoVisual: 0, ultimoQuadro: 0, raf: 0,
  };
  let ui = null, janela = null, pedido = 0, tempoEscala = null;

  // ------------------------------------------------------------ layout
  // Molas determinísticas, normalizadas para [0,1] x [0,1]; o desenho aplica a margem.
  const layouts = new Map();
  function layout(ids, deps) {
    const chave = ids.join(",") + "|" + deps.map((d) => `${d.ativo_origem_id}>${d.ativo_destino_id}`).sort().join(",");
    if (layouts.has(chave)) return layouts.get(chave);
    const n = ids.length, pos = {};
    if (!n) return pos;
    if (n === 1) { pos[ids[0]] = { x: 0.5, y: 0.5 }; return pos; }
    const P = ids.map((id, i) => {
      const a = (2 * Math.PI * i) / n + Math.sin(id * 12.9898) * 0.3;
      return { id, x: Math.cos(a), y: Math.sin(a) * 0.6, dx: 0, dy: 0 };
    });
    const indice = new Map(P.map((p, i) => [p.id, i]));
    const arestas = deps.map((d) => [indice.get(d.ativo_origem_id), indice.get(d.ativo_destino_id)]).filter(([a, b]) => a !== undefined && b !== undefined);
    const k = 0.9;
    for (let it = 0; it < 360; it++) {
      const temp = 0.12 * (1 - it / 360) + 0.003;
      for (const p of P) { p.dx = 0; p.dy = 0; }
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
        let dx = P[i].x - P[j].x, dy = (P[i].y - P[j].y) * 1.6;
        const d = Math.max(0.02, Math.hypot(dx, dy)), f = (k * k) / d;
        dx /= d; dy /= d;
        P[i].dx += dx * f; P[i].dy += dy * f; P[j].dx -= dx * f; P[j].dy -= dy * f;
      }
      for (const [a, b] of arestas) {
        let dx = P[a].x - P[b].x, dy = P[a].y - P[b].y;
        const d = Math.max(0.02, Math.hypot(dx, dy)), f = (d * d) / k;
        dx /= d; dy /= d;
        P[a].dx -= dx * f; P[a].dy -= dy * f; P[b].dx += dx * f; P[b].dy += dy * f;
      }
      for (const p of P) {
        p.dx -= p.x * 0.3; p.dy -= p.y * 0.3;
        const m = Math.max(1e-4, Math.hypot(p.dx, p.dy));
        p.x += (p.dx / m) * Math.min(m, temp);
        p.y += (p.dy / m) * Math.min(m, temp);
      }
    }
    const xs = P.map((p) => p.x), ys = P.map((p) => p.y);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    for (const p of P) {
      pos[p.id] = { x: (p.x - x0) / Math.max(1e-3, x1 - x0), y: (p.y - y0) / Math.max(1e-3, y1 - y0) };
    }
    layouts.set(chave, pos);
    return pos;
  }

  // ------------------------------------------------------------- dados
  async function carregar() {
    const meu = ++pedido;
    try {
      const d = await api(`/api/surto?escala=${est.escala}&rodadas=${RODADAS_SERVIDOR}`);
      if (meu !== pedido || !ui) return;
      est.dados = d;
      est.erro = null;
      est.epi = new Epidemia(d.A, d.b);
      est.rodando = false;
      est.particulas = []; est.ondas = []; est.flashes.clear();
      est.explodiuEm = null;
      est.pos = layout(d.ativos.map((a) => a.id), d.dependencias);
      montarPainel();
      montarRanking();
      atualizarBotoes();
      pedirQuadro();
    } catch (erro) {
      if (!ui) return;
      est.erro = erro.message;
      ui.veredito.texto.textContent = erro.message;
      ui.veredito.r0.textContent = "--";
    }
  }

  // ------------------------------------------------------------ desenho
  const cvs = document.createElement("canvas");   // só para medir
  void cvs;

  function geometria() {
    const c = ui.mapa;
    const L = c.clientWidth, A = c.clientHeight;
    const mx = Math.min(70, L * 0.12), my = Math.min(60, A * 0.16);
    const ponto = (id) => {
      const p = est.pos[id] || { x: 0.5, y: 0.5 };
      return { x: mx + p.x * (L - 2 * mx), y: my + p.y * (A - 2 * my) };
    };
    return { L, A, ponto, raio: Math.max(14, Math.min(24, Math.min(L, A) / 14)) };
  }

  /** Fundo com céu, sol e colinas, desenhado uma vez por tamanho. */
  let fundoCache = { L: 0, A: 0, img: null };
  function fundo(L, A, dpr) {
    if (fundoCache.img && fundoCache.L === L && fundoCache.A === A && fundoCache.dpr === dpr) return fundoCache.img;
    const f = document.createElement("canvas");
    f.width = Math.round(L * dpr); f.height = Math.round(A * dpr);
    const g = f.getContext("2d");
    g.scale(dpr, dpr);
    const ceu = g.createLinearGradient(0, 0, 0, A);
    ceu.addColorStop(0, "#2d86e8"); ceu.addColorStop(0.6, "#8fd0ff"); ceu.addColorStop(1, "#d8f1ff");
    g.fillStyle = ceu; g.fillRect(0, 0, L, A);
    const sol = g.createRadialGradient(L * 0.82, A * 0.18, 2, L * 0.82, A * 0.18, A * 0.5);
    sol.addColorStop(0, "rgba(255,255,255,.95)"); sol.addColorStop(0.25, "rgba(255,255,255,.35)"); sol.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = sol; g.fillRect(0, 0, L, A);
    const nuvem = (x, y, s) => {
      g.fillStyle = "rgba(255,255,255,.85)";
      for (const [dx, dy, r] of [[0, 0, 18], [20, -8, 22], [44, 0, 18], [22, 6, 20]]) {
        g.beginPath(); g.arc(x + dx * s, y + dy * s, r * s, 0, Math.PI * 2); g.fill();
      }
    };
    nuvem(L * 0.12, A * 0.2, 0.9); nuvem(L * 0.55, A * 0.12, 0.7); nuvem(L * 0.35, A * 0.34, 0.55);
    const colina = (topo, c1, c2, fase) => {
      const gr = g.createLinearGradient(0, A * topo, 0, A);
      gr.addColorStop(0, c1); gr.addColorStop(1, c2);
      g.fillStyle = gr;
      g.beginPath(); g.moveTo(0, A);
      for (let x = 0; x <= L; x += 8) g.lineTo(x, A * topo + Math.sin(x / L * Math.PI * 2 + fase) * A * 0.05);
      g.lineTo(L, A); g.closePath(); g.fill();
    };
    colina(0.72, "#8ee06a", "#3f9d2c", 0.5);
    colina(0.82, "#62c744", "#2a7d1d", 2.4);
    fundoCache = { L, A, dpr, img: f };
    return f;
  }

  function esfera(g, x, y, r, cor, brilho = 0) {
    const sombra = g.createRadialGradient(x, y + r * 1.05, 1, x, y + r * 1.05, r * 1.1);
    sombra.addColorStop(0, "rgba(0,40,0,.28)"); sombra.addColorStop(1, "rgba(0,40,0,0)");
    g.fillStyle = sombra; g.beginPath(); g.ellipse(x, y + r * 1.05, r * 1.1, r * 0.32, 0, 0, Math.PI * 2); g.fill();
    if (brilho > 0) {
      const halo = g.createRadialGradient(x, y, r * 0.8, x, y, r * (1.8 + brilho));
      halo.addColorStop(0, `rgba(255,255,255,${0.6 * brilho})`); halo.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = halo; g.beginPath(); g.arc(x, y, r * (1.8 + brilho), 0, Math.PI * 2); g.fill();
    }
    const gr = g.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
    gr.addColorStop(0, "#fff"); gr.addColorStop(0.3, cor); gr.addColorStop(1, "rgba(0,0,0,.55)");
    g.fillStyle = cor; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    g.fillStyle = gr; g.globalAlpha = 0.9; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); g.globalAlpha = 1;
    g.strokeStyle = "rgba(0,30,90,.75)"; g.lineWidth = 1.2; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.stroke();
    g.fillStyle = "rgba(255,255,255,.65)";
    g.beginPath(); g.ellipse(x - r * 0.18, y - r * 0.52, r * 0.55, r * 0.28, -0.3, 0, Math.PI * 2); g.fill();
  }

  function curva(g, a, b, r) {
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
    const c = { x: mx - (dy / d) * d * 0.12, y: my + (dx / d) * d * 0.12 };
    return { a, b, c, d, ponto: (t) => ({
      x: (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * c.x + t * t * b.x,
      y: (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * c.y + t * t * b.y,
    }), r };
  }

  function quadro(agora) {
    est.raf = 0;
    if (!ui || !janelaVisivel()) return;
    const t = agora / 1000;
    const dt = est.ultimoQuadro ? Math.min(0.1, t - est.ultimoQuadro) : 0.016;
    est.ultimoQuadro = t;
    passo(t, dt);
    desenhar(t);
    if (est.rodando || est.particulas.length || est.ondas.length || (est.explodiuEm !== null && t - est.explodiuEm < 1.4)) pedirQuadro();
    else est.ultimoQuadro = 0;
  }

  function pedirQuadro() {
    if (!est.raf && ui) est.raf = requestAnimationFrame(quadro);
  }

  function janelaVisivel() {
    return janela && janela.el.isConnected && !janela.el.classList.contains("minimizada");
  }

  function passo(t, dt) {
    if (est.rodando && est.epi) {
      est.acumulado += dt * est.vel;
      const duracao = est.vel <= 3 ? 0.7 : est.vel <= 30 ? 0.5 : 0.35;
      const intervalo = est.vel <= 3 ? 0 : est.vel <= 30 ? 0.12 : 0.22;
      let feitas = 0;
      while (est.acumulado >= 1 && feitas < 400) {
        est.acumulado -= 1; feitas++;
        const saltos = est.epi.rodada();
        if (est.epi.explodiu) { explodir(t); break; }
        const mostrar = t - est.ultimoVisual >= intervalo && est.particulas.length < 140;
        if (mostrar && saltos.length) {
          est.ultimoVisual = t;
          for (const s of saltos.slice(0, 60)) {
            est.particulas.push({ de: s.de, para: s.para, t0: t + s.geracao * duracao, dur: duracao });
          }
          est.epi.b.forEach((v, i) => { if (v > 0 && est.dados.ativos[i]) est.flashes.set(est.dados.ativos[i].id, t); });
        }
      }
      atualizarPlacar();
    }
    // chegadas: gera ondinhas
    for (const p of est.particulas) {
      if (!p.chegou && t >= p.t0 + p.dur) {
        p.chegou = true;
        const a = est.dados && est.dados.ativos[p.para];
        if (a) est.ondas.push({ id: a.id, t0: t });
      }
    }
    est.particulas = est.particulas.filter((p) => t < p.t0 + p.dur + 0.05);
    est.ondas = est.ondas.filter((o) => t - o.t0 < 0.7);
  }

  function explodir(t) {
    est.rodando = false;
    est.explodiuEm = t;
    atualizarBotoes();
    Nucleo.balao("O surto explodiu", "Os pesos fizeram a infecção crescer sem parar: não existe risco finito.", "erro");
    if (!est.dados.convergente) {
      Janelas.dialogo({
        titulo: "Surto fora de controle", icone: "erro",
        texto: "Cada infecção gera, em média, uma ou mais novas (R0 ≥ 1). A soma b + A·b + A²·b + … não termina, então (I − A)x = b não tem resposta finita. Reduza os pesos ou corrija falhas.",
      });
    }
  }

  function desenhar(t) {
    const c = ui.mapa, dpr = Math.min(2, window.devicePixelRatio || 1);
    const { L, A, ponto, raio } = geometria();
    if (!L || !A) return;
    if (c.width !== Math.round(L * dpr) || c.height !== Math.round(A * dpr)) { c.width = Math.round(L * dpr); c.height = Math.round(A * dpr); }
    const g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, L, A);

    let tremor = 0;
    if (est.explodiuEm !== null && !calmo) tremor = Math.max(0, 1 - (t - est.explodiuEm) / 1.2) * 6;
    g.save();
    if (tremor > 0) g.translate((Math.random() - 0.5) * tremor, (Math.random() - 0.5) * tremor);
    g.drawImage(fundo(L, A, dpr), 0, 0, L, A);

    const d = est.dados;
    if (!d || !d.ativos.length) {
      g.fillStyle = "rgba(255,255,255,.85)";
      g.font = "600 14px Tahoma, sans-serif"; g.textAlign = "center";
      g.fillText(est.erro || (d ? "Sem ativos. Cadastre alguns no Gerenciador de Ativos." : "Carregando…"), L / 2, A / 2);
      g.restore();
      return;
    }

    // canos
    const canos = d.dependencias.map((dep) => {
      const a = ponto(dep.ativo_origem_id), b = ponto(dep.ativo_destino_id);
      return { ...curva(g, a, b, raio), peso: dep.peso, o: dep.ativo_origem_id, d: dep.ativo_destino_id };
    });
    for (const k of canos) {
      const larg = 3 + Math.min(5, k.peso * 8);
      g.lineCap = "round";
      g.strokeStyle = "rgba(0,50,120,.55)"; g.lineWidth = larg + 2;
      g.beginPath(); g.moveTo(k.a.x, k.a.y); g.quadraticCurveTo(k.c.x, k.c.y, k.b.x, k.b.y); g.stroke();
      g.strokeStyle = "rgba(170,225,255,.9)"; g.lineWidth = larg;
      g.beginPath(); g.moveTo(k.a.x, k.a.y); g.quadraticCurveTo(k.c.x, k.c.y, k.b.x, k.b.y); g.stroke();
      g.strokeStyle = "rgba(255,255,255,.7)"; g.lineWidth = Math.max(1, larg / 3);
      g.beginPath(); g.moveTo(k.a.x, k.a.y - 1); g.quadraticCurveTo(k.c.x, k.c.y - 1, k.b.x, k.b.y - 1); g.stroke();
      // seta perto do destino
      const p1 = k.ponto(0.82), p2 = k.ponto(0.9);
      const ang = Math.atan2(p2.y - p1.y, p2.x - p1.x);
      g.fillStyle = "#0a3fb0";
      g.save(); g.translate(p2.x, p2.y); g.rotate(ang);
      g.beginPath(); g.moveTo(5, 0); g.lineTo(-5, -4.5); g.lineTo(-5, 4.5); g.closePath(); g.fill(); g.restore();
      // peso
      const m = k.ponto(0.5);
      const txt = num(k.peso);
      g.font = "700 10.5px Tahoma, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
      const w = g.measureText(txt).width + 10;
      g.fillStyle = "rgba(255,255,255,.92)"; g.strokeStyle = "rgba(10,63,176,.6)"; g.lineWidth = 1;
      g.beginPath(); g.roundRect(m.x - w / 2, m.y - 8, w, 16, 8); g.fill(); g.stroke();
      g.fillStyle = "#0a3fb0"; g.fillText(txt, m.x, m.y + 0.5);
    }

    // bolhas de infecção
    const idx = new Map(d.ativos.map((a, i) => [i, a.id]));
    for (const p of est.particulas) {
      const u = (t - p.t0) / p.dur;
      if (u < 0 || u > 1) continue;
      const a = ponto(idx.get(p.de)), b = ponto(idx.get(p.para));
      const k = curva(g, a, b, raio), q = k.ponto(u);
      const gr = g.createRadialGradient(q.x - 1.5, q.y - 1.5, 0.5, q.x, q.y, 6);
      gr.addColorStop(0, "#fff"); gr.addColorStop(0.5, "#ff7a5c"); gr.addColorStop(1, "#c4260f");
      g.fillStyle = gr; g.beginPath(); g.arc(q.x, q.y, 5, 0, Math.PI * 2); g.fill();
      g.strokeStyle = "rgba(120,20,5,.7)"; g.lineWidth = 0.8; g.stroke();
    }

    // esferas
    const estimativa = est.epi && est.epi.rodadas ? est.epi.estimativa() : null;
    d.ativos.forEach((a, i) => {
      const { x, y } = ponto(a.id);
      const valor = estimativa ? estimativa[i] : (d.x ? d.x[i] : null);
      const flash = est.flashes.has(a.id) ? Math.max(0, 1 - (t - est.flashes.get(a.id)) / 0.5) : 0;
      esfera(g, x, y, raio, est.explodiuEm !== null && !d.convergente ? COR.vermelho : corDoRisco(valor), flash);
      for (const o of est.ondas) {
        if (o.id !== a.id) continue;
        const u = (t - o.t0) / 0.7;
        g.strokeStyle = `rgba(255,255,255,${0.8 * (1 - u)})`; g.lineWidth = 2;
        g.beginPath(); g.arc(x, y, raio * (1 + u * 0.9), 0, Math.PI * 2); g.stroke();
      }
      g.font = "700 11px Tahoma, sans-serif"; g.textAlign = "center"; g.textBaseline = "top";
      const nome = a.nome.length > 16 ? a.nome.slice(0, 15) + "…" : a.nome;
      const w = g.measureText(nome).width + 10;
      g.fillStyle = "rgba(255,255,255,.88)"; g.strokeStyle = "rgba(10,63,176,.45)"; g.lineWidth = 1;
      const lx = Math.min(L - 3 - w / 2, Math.max(3 + w / 2, x));   // rótulo nunca sai do mapa
      g.beginPath(); g.roundRect(lx - w / 2, y + raio + 5, w, 17, 8); g.fill(); g.stroke();
      g.fillStyle = "#12315f"; g.fillText(nome, lx, y + raio + 8);
      g.textBaseline = "middle"; g.font = "700 10.5px Tahoma, sans-serif"; g.fillStyle = "#fff";
      if (valor !== null && valor !== undefined) {
        g.save(); g.shadowColor = "rgba(0,0,0,.6)"; g.shadowBlur = 2;
        g.fillText(num(valor, 1), x, y + 1); g.restore();
      }
    });
    g.restore();

    if (tremor > 0) {
      g.fillStyle = `rgba(220,40,30,${0.25 * (tremor / 6)})`; g.fillRect(0, 0, L, A);
    }
  }

  // ---------------------------------------------------------- gráfico
  function desenharGrafico() {
    const c = ui.grafico, dpr = Math.min(2, window.devicePixelRatio || 1);
    const L = c.clientWidth, A = c.clientHeight;
    if (!L || !A) return;
    if (c.width !== Math.round(L * dpr) || c.height !== Math.round(A * dpr)) { c.width = Math.round(L * dpr); c.height = Math.round(A * dpr); }
    const g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, L, A);
    const d = est.dados, epi = est.epi;
    const x0 = 8, x1 = L - 8, y0 = 16, y1 = A - 18;
    g.strokeStyle = "#cfd8e6"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x0, y1 + 0.5); g.lineTo(x1, y1 + 0.5); g.stroke();
    g.font = "10.5px Tahoma, sans-serif"; g.fillStyle = "#5a6a85";
    g.textAlign = "left"; g.fillText("0", x0, y1 + 13);
    if (!d || !epi) return;
    const exato = d.risco_global;
    const base = exato ? exato * 0.5 : 0;
    const topo = exato ? exato * 1.5 : Math.max(1, ...epi.curva.map((p) => p[1]));
    const maxR = Math.max(50, epi.rodadas);
    const px = (r) => x0 + (r / maxR) * (x1 - x0);
    const py = (v) => y1 - Math.max(0, Math.min(1, (v - base) / ((topo - base) || 1))) * (y1 - y0);
    g.textAlign = "right"; g.fillText(`${maxR.toLocaleString("pt-BR")} epidemias`, x1, y1 + 13);
    if (exato) {
      g.setLineDash([5, 4]); g.strokeStyle = "#1a8f2c"; g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(x0, py(exato)); g.lineTo(x1, py(exato)); g.stroke(); g.setLineDash([]);
      g.fillStyle = "#1a8f2c"; g.textAlign = "right"; g.fillText(`álgebra ${num(exato)}`, x1, py(exato) - 4);
      g.fillStyle = "#8a97ad"; g.textAlign = "left"; g.fillText("+50%", x0, y0 - 4); g.fillText("−50%", x0, y1 - 4);
    } else {
      g.fillStyle = "#c46a10"; g.textAlign = "center"; g.fillText("sem solução finita", L / 2, y0);
    }
    if (epi.curva.length) {
      g.strokeStyle = "#e0701a"; g.lineWidth = 2; g.lineJoin = "round";
      g.beginPath();
      epi.curva.forEach(([r, v], k) => (k ? g.lineTo(px(r), py(v)) : g.moveTo(px(r), py(v))));
      g.stroke();
      const [r, v] = epi.curva[epi.curva.length - 1];
      g.fillStyle = "#e0701a"; g.beginPath(); g.arc(px(r), py(v), 3.5, 0, Math.PI * 2); g.fill();
    }
  }

  // ------------------------------------------------------------- painéis
  function montarPainel() {
    const d = est.dados;
    ui.veredito.card.classList.toggle("explodiu", !d.convergente);
    ui.veredito.r0.textContent = num(d.rho, 3);
    let texto;
    if (!d.n) texto = "Sem ativos, sem surto. Cadastre ativos no Gerenciador de Ativos.";
    else if (!d.convergente) texto = "Maior ou igual a 1: o surto explode. A série b + A·b + A²·b + … não termina e não existe risco finito.";
    else if (!d.regra_do_projeto) texto = "Menor que 1: ainda converge. Mas algum ativo recebe pesos que somam 1 ou mais, e o cadastro recusaria. A regra é mais exigente que o R0.";
    else texto = "Menor que 1: cada infecção gera menos de uma nova, o surto morre sozinho e I − A tem solução.";
    ui.veredito.texto.textContent = texto;

    ui.tabela.replaceChildren(
      el("thead", {}, el("tr", {},
        el("th", { scope: "col" }, "Ativo"),
        el("th", { scope: "col", class: "num", title: "Risco próprio" }, "b"),
        el("th", { scope: "col", class: "num", title: "Álgebra: (I − A)x = b" }, "x álgebra"),
        el("th", { scope: "col", class: "num", title: "Média das epidemias sorteadas" }, "x sorteio"),
        el("th", { scope: "col", class: "num", title: "Quanto 1 ponto de risco aqui vira na rede" }, "mult."))),
      el("tbody", {}, d.ativos.map((a, i) => el("tr", {},
        el("th", { scope: "row" }, el("span", { class: "bolinha", style: `background:${corDoRisco(d.x ? d.x[i] : null)}` }), a.nome),
        el("td", { class: "num" }, num(d.b[i])),
        el("td", { class: "num" }, d.x ? num(d.x[i]) : "--"),
        el("td", { class: "num mc", "data-i": i }, "--"),
        el("td", { class: "num" }, d.multiplicadores ? num(d.multiplicadores[i]) : "--")))));

    const ids = d.ativos.map((a) => a.id);
    ui.matriz.replaceChildren(d.n ? el("table", { class: "matriz" },
      el("caption", { class: "dica", style: "text-align:left;caption-side:top;margin-bottom:6px" }, "A[linha][coluna] = quanto do risco da coluna chega na linha"),
      el("thead", {}, el("tr", {}, el("th", {}, ""), ids.map((id) => el("th", { scope: "col" }, id)))),
      el("tbody", {}, d.A.map((linha, i) => el("tr", {},
        el("th", { scope: "row" }, ids[i]),
        linha.map((v) => el("td", { style: v > 0 ? `background:rgba(240,138,36,${Math.min(0.8, 0.2 + v)});font-weight:700` : "color:#8a97ad" }, v > 0 ? num(v) : "0")))))) : el("p", { class: "vazio" }, "Sem ativos."));

    const g = d.diagnostico;
    ui.diag.replaceChildren(...(g ? [
      ["Posto de I − A", `${g.posto} de ${g.ordem}`],
      ["Determinante", num(g.determinante, 4)],
      ["Número de condição κ", g.condicao === null ? "infinito" : num(g.condicao, 2)],
      ["Invertível", g.invertivel ? "sim" : "não"],
      ["Regra do cadastro (somas < 1)", d.regra_do_projeto ? "respeitada" : "violada"],
      ["Sorteio no servidor (NumPy)", d.erro_relativo === null || d.erro_relativo === undefined
        ? (d.convergente ? "parou (R0 perto de 1)" : "explodiu")
        : `${d.monte_carlo.rodadas} epidemias, diferença ${num(d.erro_relativo * 100)}%`],
    ].flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]) : []));
    atualizarPlacar();
  }

  function atualizarPlacar() {
    const d = est.dados;
    if (!d || !est.epi || !ui) return;
    const exato = d.risco_global, mc = est.epi.global();
    ui.placar.exato.textContent = num(exato);
    ui.placar.mc.textContent = est.epi.rodadas ? (est.epi.explodiu ? (d.convergente ? "parou" : "explodiu") : num(mc)) : "--";
    ui.placar.erro.textContent = est.epi.rodadas && exato ? `${num(Math.abs(mc - exato) / exato * 100)}%` : "--";
    ui.placar.rodadas.textContent = est.epi.rodadas.toLocaleString("pt-BR");
    const e = est.epi.estimativa();
    ui.tabela.querySelectorAll(".mc").forEach((td) => { td.textContent = est.epi.rodadas ? num(e[Number(td.dataset.i)]) : "--"; });
    ui.progresso.value = Math.min(RODADAS_SERVIDOR, est.epi.rodadas);
    ui.progressoTxt.textContent = `${Math.min(RODADAS_SERVIDOR, est.epi.rodadas).toLocaleString("pt-BR")} de ${RODADAS_SERVIDOR.toLocaleString("pt-BR")} epidemias`;
    desenharGrafico();
  }

  function montarRanking() {
    const d = est.dados;
    if (!d.ranking.length) {
      ui.ranking.replaceChildren(el("li", { class: "vazio" }, d.n ? "Nenhuma falha aberta. Rede limpa." : "Sem ativos cadastrados."));
      return;
    }
    const maior = d.ranking[0].queda_global || 1;
    const itens = d.ranking.slice(0, 8).map((r, k) => el("li", {},
      el("span", { class: "posicao" }, `${k + 1}º`),
      el("div", { class: "alvo" },
        el("b", {}, `${r.vulnerabilidade_id} em ${r.ativo_nome}`),
        el("span", {}, `nota ${num(r.nota, 1)} × fator ${num(r.fator, 2)} × multiplicador ${num(r.multiplicador)}`),
        el("div", { class: "barra", style: `width:${Math.max(4, (r.queda_global / maior) * 100)}%` })),
      el("span", { class: "queda" }, `−${num(r.queda_global)}` + (d.risco_global ? ` (${num(r.queda_global / d.risco_global * 100, 1)}%)` : "")),
      el("button", { type: "button", class: "botao pequeno gel", on: { click: () => corrigir(r) } }, "Corrigir")));
    const desfazer = est.ultimaCorrecao
      ? el("li", {}, el("span", {}), el("span", { class: "dica" }, `Última correção: ${est.ultimaCorrecao.vulnerabilidade_id} em ${est.ultimaCorrecao.ativo_nome}.`),
          el("button", { type: "button", class: "botao pequeno", on: { click: desfazerCorrecao } }, "Desfazer"))
      : null;
    ui.ranking.replaceChildren(...itens, ...(desfazer ? [desfazer] : []));
  }

  async function mudarStatus(item, status) {
    await api(`/api/ativos/${item.ativo_id}/vulnerabilidades/${encodeURIComponent(item.vulnerabilidade_id)}`, json("PATCH", { status }));
  }

  async function corrigir(item) {
    const antes = est.dados.risco_global;
    try {
      await mudarStatus(item, "Corrigida");
      est.ultimaCorrecao = item;
      await Nucleo.recarregar();          // avisa as outras janelas; nossa própria assinatura recarrega o surto
      await carregar();
      Nucleo.balao("Falha corrigida", `${item.vulnerabilidade_id}: risco global ${num(antes)} → ${num(est.dados.risco_global)}.`, "ok");
    } catch (erro) {
      Nucleo.balao("Não foi possível corrigir", erro.message, "erro");
    }
  }

  async function desfazerCorrecao() {
    const item = est.ultimaCorrecao;
    if (!item) return;
    try {
      await mudarStatus(item, "Aberta");
      est.ultimaCorrecao = null;
      await Nucleo.recarregar();
      await carregar();
      Nucleo.balao("Falha reaberta", `${item.vulnerabilidade_id} voltou para Aberta em ${item.ativo_nome}.`, "info");
    } catch (erro) {
      Nucleo.balao("Não foi possível desfazer", erro.message, "erro");
    }
  }

  // ---------------------------------------------------------- controles
  function atualizarBotoes() {
    if (!ui) return;
    const acabou = est.epi && est.epi.explodiu;
    ui.btnIniciar.textContent = est.rodando ? "Pausar" : acabou ? "Explodiu (zere)" : est.epi && est.epi.rodadas ? "Continuar" : "Iniciar surto";
    ui.btnIniciar.disabled = !est.epi || !est.dados || !est.dados.n || acabou;
    ui.btnZerar.disabled = !est.epi;
    ui.velocidades.forEach(([b, v]) => b.setAttribute("aria-checked", String(v === est.vel)));
  }

  function alternar() {
    if (!est.epi || est.epi.explodiu || !est.dados.n) return;
    est.rodando = !est.rodando;
    if (est.rodando && est.epi.rodadas >= RODADAS_SERVIDOR * 50) est.rodando = false;
    atualizarBotoes();
    pedirQuadro();
  }

  function zerar() {
    if (!est.epi) return;
    est.epi.zerar();
    est.rodando = false; est.particulas = []; est.ondas = []; est.flashes.clear(); est.explodiuEm = null; est.acumulado = 0;
    atualizarBotoes(); atualizarPlacar(); pedirQuadro();
  }

  function construir() {
    const mapa = el("canvas", { class: "mapa", role: "img", "aria-label": "Mapa da rede de ativos com o risco se espalhando" });
    const btnIniciar = el("button", { type: "button", class: "botao gel", on: { click: alternar } }, "Iniciar surto");
    const btnZerar = el("button", { type: "button", class: "botao", on: { click: zerar } }, "Zerar");
    const velocidades = VELOCIDADES.map(([rot, v]) => [el("button", {
      type: "button", class: "botao pequeno", role: "radio", "aria-label": `Velocidade ${rot}`,
      on: { click: () => { est.vel = v; atualizarBotoes(); } },
    }, rot), v]);

    const saida = el("output", {}, "1,0×");
    const escala = el("input", {
      type: "range", min: 0.5, max: 6, step: 0.1, value: 1, "aria-label": "Multiplicador dos pesos das dependências",
      on: {
        input: (e) => {
          est.escala = Number(e.target.value);
          saida.textContent = `${num(est.escala, 1)}×`;
          clearTimeout(tempoEscala);
          tempoEscala = setTimeout(carregar, 300);
        },
      },
    });
    const progresso = el("progress", { max: RODADAS_SERVIDOR, value: 0, class: "progresso" });
    const progressoTxt = el("small", {}, "");

    const legenda = el("div", { class: "legenda-risco", "aria-label": "Legenda de cores" },
      [["verde", "baixo (<4)"], ["amarelo", "médio (<8)"], ["laranja", "alto (<15)"], ["vermelho", "crítico"]].map(([c, t]) =>
        el("span", { style: `--c:${COR[c]}` }, t)));

    const mapaWrap = el("div", { class: "mapa-wrap" }, mapa);
    const esq = el("div", { class: "surto-esq" }, mapaWrap,
      el("div", { class: "controles" }, btnIniciar, btnZerar,
        el("span", { class: "grupo-vel", role: "radiogroup", "aria-label": "Velocidade" }, velocidades.map(([b]) => b)),
        el("label", { class: "escala" }, el("span", {}, "Pesos"), escala, saida),
        el("div", { class: "carga-surto" }, progressoTxt, progresso)),
      legenda);

    const r0 = el("div", { class: "r0" }, "--");
    const texto = el("p", { class: "texto" }, "Carregando…");
    const card = el("section", { class: "grupo veredito", "aria-live": "polite" },
      el("p", { class: "rotulo" }, "R0: infecções novas geradas por cada infecção"), r0, texto);

    const grafico = el("canvas", { class: "grafico", role: "img", "aria-label": "Média do sorteio aproximando-se do resultado da álgebra" });
    const placar = {
      exato: el("dd", {}, "--"), mc: el("dd", {}, "--"), erro: el("dd", {}, "--"), rodadas: el("dd", {}, "0"),
    };
    const secaoGrafico = el("section", { class: "grupo" }, el("h3", {}, "Sorteio × álgebra"), grafico,
      el("dl", { class: "placar" },
        el("div", {}, el("dt", {}, "Risco global (álgebra)"), placar.exato),
        el("div", {}, el("dt", {}, "Média do sorteio"), placar.mc),
        el("div", {}, el("dt", {}, "Diferença"), placar.erro),
        el("div", {}, el("dt", {}, "Epidemias"), placar.rodadas)));

    const ranking = el("ol", { class: "ranking" });
    const secaoDefesa = el("section", { class: "grupo" }, el("h3", {}, "Defesa: o que corrigir primeiro"),
      el("p", { class: "dica" }, "Quanto o risco global cai se cada falha for corrigida."), ranking);

    const tabela = el("table", { class: "lista" });
    const matriz = el("div", { class: "rolagem-curta" });
    const diag = el("dl", { class: "diagnostico" });
    const detalhes = el("details", { class: "grupo" }, el("summary", {}, "Ativo por ativo e matriz A"),
      el("div", { class: "rolagem-curta" }, tabela), el("h3", { style: "margin-top:10px" }, "Matriz A"), matriz, diag);

    const dir = el("div", { class: "surto-dir" }, card, secaoGrafico, secaoDefesa, detalhes);
    const raiz = el("div", { class: "surto" }, esq, dir);

    ui = {
      raiz, mapa, grafico, tabela, matriz, diag, ranking, placar, progresso, progressoTxt,
      btnIniciar, btnZerar, velocidades,
      veredito: { card, r0, texto },
    };
    return raiz;
  }

  function aoTeclar(ev) {
    if (ev.code !== "Space" || !ui || Janelas.ativa() !== "surto") return;
    const alvo = ev.target;
    if (alvo.closest && alvo.closest("button, input, select, textarea, summary, a")) return;
    if (document.querySelector(".veu")) return;
    ev.preventDefault();
    alternar();
  }

  function abrir() {
    if (ui) { Janelas.focar("surto"); return; }
    const conteudo = construir();
    document.addEventListener("keydown", aoTeclar);
    const aoMudar = () => {
      // outra janela mexeu nos dados: o surto se recalcula
      if (ui && !est.rodando) carregar();
    };
    const desinscrever = Nucleo.assinar(aoMudar);
    const aoJanelas = () => { if (ui && janelaVisivel()) pedirQuadro(); };
    document.addEventListener("aero:janelas", aoJanelas);

    janela = Janelas.abrir({
      id: "surto", titulo: "Varredura de Contágio", icone: "surto", largura: 1040, altura: 640, minLargura: 640, minAltura: 420, conteudo,
      aoRedimensionar: () => { pedirQuadro(); if (ui) desenharGrafico(); },
      aoFechar: () => {
        desinscrever();
        document.removeEventListener("keydown", aoTeclar);
        document.removeEventListener("aero:janelas", aoJanelas);
        if (est.raf) cancelAnimationFrame(est.raf);
        est.raf = 0; est.rodando = false; ui = null; janela = null;
      },
    });
    atualizarBotoes();
    carregar();
  }

  void nucleoDados;
  return { abrir };
})();

window.AppSurto = AppSurto;
