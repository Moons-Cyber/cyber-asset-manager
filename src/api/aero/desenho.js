/* Desenho do mapa da rede em canvas: posições, céu, esferas de vidro e canos.
 * Só desenha; quem decide o que mostrar é o app_mapa.js.
 */
const Desenho = (() => {
  "use strict";

  const COR = { verde: "#4fc23a", amarelo: "#f2cf2a", laranja: "#f08a24", vermelho: "#e0392b", neutro: "#9aa8bb" };
  const corDoRisco = (x) => COR[Nucleo.faixa(x).classe];

  // ------------------------------------------------------------ posições
  // Molas (force-directed): ativos se empurram, dependências puxam.
  // Determinístico (sem Math.random): o mesmo cadastro dá sempre o mesmo mapa.
  // Resultado normalizado em [0,1] x [0,1]; quem desenha aplica a margem.
  const memoria = new Map();
  function posicoes(ids, arestas) {
    const chave = ids.join(",") + "|" + arestas.map(([o, d]) => `${o}>${d}`).sort().join(",");
    if (memoria.has(chave)) return memoria.get(chave);
    const n = ids.length, pos = {};
    if (n === 1) pos[ids[0]] = { x: 0.5, y: 0.5 };
    if (n <= 1) return pos;

    const P = ids.map((id, i) => {
      const a = (2 * Math.PI * i) / n + Math.sin(id * 12.9898) * 0.3;
      return { id, x: Math.cos(a), y: Math.sin(a) * 0.6, dx: 0, dy: 0 };
    });
    const indice = new Map(P.map((p, i) => [p.id, i]));
    const pares = arestas.map(([o, d]) => [indice.get(o), indice.get(d)]).filter(([a, b]) => a !== undefined && b !== undefined);
    const k = 0.9;
    for (let it = 0; it < 360; it++) {
      const passo = 0.12 * (1 - it / 360) + 0.003;
      for (const p of P) { p.dx = 0; p.dy = 0; }
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {      // repulsão
        let dx = P[i].x - P[j].x, dy = (P[i].y - P[j].y) * 1.6;
        const d = Math.max(0.02, Math.hypot(dx, dy)), f = (k * k) / d;
        dx /= d; dy /= d;
        P[i].dx += dx * f; P[i].dy += dy * f; P[j].dx -= dx * f; P[j].dy -= dy * f;
      }
      for (const [a, b] of pares) {                                       // atração
        let dx = P[a].x - P[b].x, dy = P[a].y - P[b].y;
        const d = Math.max(0.02, Math.hypot(dx, dy)), f = (d * d) / k;
        dx /= d; dy /= d;
        P[a].dx -= dx * f; P[a].dy -= dy * f; P[b].dx += dx * f; P[b].dy += dy * f;
      }
      for (const p of P) {
        p.dx -= p.x * 0.3; p.dy -= p.y * 0.3;                             // puxa para o centro
        const m = Math.max(1e-4, Math.hypot(p.dx, p.dy));
        p.x += (p.dx / m) * Math.min(m, passo);
        p.y += (p.dy / m) * Math.min(m, passo);
      }
    }
    // Gira a rede para o eixo mais comprido ficar na horizontal (a janela é
    // mais larga que alta). Sem isso, uma corrente A→B→C→D podia sair em pé.
    const mx = P.reduce((t, p) => t + p.x, 0) / n, my = P.reduce((t, p) => t + p.y, 0) / n;
    let sxx = 0, syy = 0, sxy = 0;
    for (const p of P) { const dx = p.x - mx, dy = p.y - my; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; }
    const ang = 0.5 * Math.atan2(2 * sxy, sxx - syy);
    const [c, s] = [Math.cos(-ang), Math.sin(-ang)];
    for (const p of P) { const dx = p.x - mx, dy = p.y - my; p.x = dx * c - dy * s; p.y = dx * s + dy * c; }

    // Normaliza para [0,1]. Um lado muito estreito fica centralizado, em vez de
    // ser esticado (uma linha reta não pode virar uma faixa colada na borda).
    const xs = P.map((p) => p.x), ys = P.map((p) => p.y);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const maior = Math.max(x1 - x0, y1 - y0, 1e-6);
    const ex = Math.max(x1 - x0, 0.35 * maior), ey = Math.max(y1 - y0, 0.35 * maior);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    for (const p of P) pos[p.id] = { x: 0.5 + (p.x - cx) / ex, y: 0.5 + (p.y - cy) / ey };
    memoria.set(chave, pos);
    return pos;
  }

  // ----------------------------------------------------------------- fundo
  let fundoCache = null;
  function fundo(L, A, dpr) {
    if (fundoCache && fundoCache.L === L && fundoCache.A === A && fundoCache.dpr === dpr) return fundoCache.img;
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
      for (let x = 0; x <= L; x += 8) g.lineTo(x, A * topo + Math.sin((x / L) * Math.PI * 2 + fase) * A * 0.05);
      g.lineTo(L, A); g.closePath(); g.fill();
    };
    colina(0.72, "#8ee06a", "#3f9d2c", 0.5);
    colina(0.82, "#62c744", "#2a7d1d", 2.4);
    fundoCache = { L, A, dpr, img: f };
    return f;
  }

  // -------------------------------------------------------------- formas
  function esfera(g, x, y, r, cor, opacidade = 1) {
    g.save();
    g.globalAlpha = opacidade;
    const sombra = g.createRadialGradient(x, y + r * 1.05, 1, x, y + r * 1.05, r * 1.1);
    sombra.addColorStop(0, "rgba(0,40,0,.28)"); sombra.addColorStop(1, "rgba(0,40,0,0)");
    g.fillStyle = sombra; g.beginPath(); g.ellipse(x, y + r * 1.05, r * 1.1, r * 0.32, 0, 0, Math.PI * 2); g.fill();
    const gr = g.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
    gr.addColorStop(0, "#fff"); gr.addColorStop(0.3, cor); gr.addColorStop(1, "rgba(0,0,0,.55)");
    g.fillStyle = cor; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    g.globalAlpha = 0.9 * opacidade; g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    g.globalAlpha = opacidade;
    g.strokeStyle = "rgba(0,30,90,.75)"; g.lineWidth = 1.2; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.stroke();
    g.fillStyle = "rgba(255,255,255,.65)";
    g.beginPath(); g.ellipse(x - r * 0.18, y - r * 0.52, r * 0.55, r * 0.28, -0.3, 0, Math.PI * 2); g.fill();
    g.restore();
  }

  /** Curva suave de a até b (um pouco arqueada, para canos de ida e volta não se sobreporem). */
  function curva(a, b) {
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
    const c = { x: mx - (dy / d) * d * 0.12, y: my + (dx / d) * d * 0.12 };
    return {
      a, b, c,
      ponto: (t) => ({
        x: (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * c.x + t * t * b.x,
        y: (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * c.y + t * t * b.y,
      }),
    };
  }

  function cano(g, k, peso, destaque, apagado) {
    const larg = 3 + Math.min(5, peso * 8);
    const tracar = (cor, w, dy = 0) => {
      g.strokeStyle = cor; g.lineWidth = w; g.lineCap = "round";
      g.beginPath(); g.moveTo(k.a.x, k.a.y + dy); g.quadraticCurveTo(k.c.x, k.c.y + dy, k.b.x, k.b.y + dy); g.stroke();
    };
    g.save();
    g.globalAlpha = apagado ? 0.25 : 1;
    tracar(destaque ? "rgba(150,60,0,.7)" : "rgba(0,50,120,.55)", larg + 2);
    tracar(destaque ? "rgba(255,196,90,.95)" : "rgba(170,225,255,.9)", larg);
    tracar("rgba(255,255,255,.7)", Math.max(1, larg / 3), -1);
    // seta perto de quem recebe
    const p1 = k.ponto(0.82), p2 = k.ponto(0.9);
    g.fillStyle = destaque ? "#a34a00" : "#0a3fb0";
    g.translate(p2.x, p2.y); g.rotate(Math.atan2(p2.y - p1.y, p2.x - p1.x));
    g.beginPath(); g.moveTo(5, 0); g.lineTo(-5, -4.5); g.lineTo(-5, 4.5); g.closePath(); g.fill();
    g.restore();
  }

  function etiqueta(g, texto, x, y, L, { cor = "#12315f", borda = "rgba(10,63,176,.45)", fonte = "700 11px Tahoma, sans-serif" } = {}) {
    g.save();
    g.font = fonte; g.textAlign = "center"; g.textBaseline = "middle";
    const w = g.measureText(texto).width + 10;
    const cx = Math.min(L - 3 - w / 2, Math.max(3 + w / 2, x));      // nunca sai do mapa
    g.fillStyle = "rgba(255,255,255,.92)"; g.strokeStyle = borda; g.lineWidth = 1;
    g.beginPath(); g.roundRect(cx - w / 2, y - 8.5, w, 17, 8); g.fill(); g.stroke();
    g.fillStyle = cor; g.fillText(texto, cx, y + 0.5);
    g.restore();
  }

  /** Ajusta o canvas ao tamanho na tela (nítido em telas de alta densidade). */
  function preparar(canvas) {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const L = canvas.clientWidth, A = canvas.clientHeight;
    if (canvas.width !== Math.round(L * dpr) || canvas.height !== Math.round(A * dpr)) {
      canvas.width = Math.round(L * dpr); canvas.height = Math.round(A * dpr);
    }
    const g = canvas.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { g, L, A, dpr };
  }

  return { COR, corDoRisco, posicoes, fundo, esfera, curva, cano, etiqueta, preparar };
})();

window.Desenho = Desenho;
