/* Surto: a tela principal.
 *
 *  - busca /api/surto (A, b, a solução do solve, o R0, o ranking de defesa);
 *  - sorteia epidemias no navegador (simulacao.js) e anima uma amostra delas
 *    na cidade em pixel art;
 *  - mostra, ao lado, a média do sorteio chegando na resposta da álgebra.
 */
(() => {
  "use strict";

  const P = Pixel, C = Pixel.COR;
  const W = 384, H = 216;
  const AREA = { x0: 40, x1: 344, y0: 34, y1: 166 };
  const $ = (id) => document.getElementById(id);
  const calmo = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const mapa = $("mapa");
  const ctx = mapa.getContext("2d");
  ctx.imageSmoothingEnabled = false;

  const est = {
    aba: "surto",
    dados: null,
    erro: null,
    escala: 1,
    epi: null,
    rodando: false,
    vel: 3,                 // epidemias por segundo
    acumulado: 0,
    ultimoVisual: 0,
    particulas: [],
    flashes: new Map(),
    fumaca: [],
    pos: {},
    explodiuEm: null,
    ultimaCorrecao: null,
  };

  // ------------------------------------------------------------ utilidades
  async function api(url, opcoes) {
    const resposta = await fetch(url, opcoes);
    let corpo = null;
    try { corpo = await resposta.json(); } catch { /* sem JSON */ }
    if (!resposta.ok) {
      const erro = new Error((corpo && corpo.erro) || `Erro HTTP ${resposta.status}`);
      erro.status = resposta.status;
      throw erro;
    }
    return corpo;
  }

  function num(v, casas = 2) {
    if (v === null || v === undefined || !Number.isFinite(v)) return "--";
    if (Math.abs(v) >= 1e5) return v.toExponential(1).replace(".", ",");
    return v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  }
  const numPixel = (v, casas = 2) => num(v, casas).replace(/\./g, "");

  let tempoAviso = null;
  function aviso(texto, bom = true) {
    const el = $("aviso");
    el.textContent = texto;
    el.classList.toggle("ruim", !bom);
    el.classList.add("visivel");
    clearTimeout(tempoAviso);
    tempoAviso = setTimeout(() => el.classList.remove("visivel"), 4200);
  }

  function el(tag, atributos = {}, ...filhos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(atributos)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "on") for (const [ev, fn] of Object.entries(v)) e.addEventListener(ev, fn);
      else if (k === "style") e.style.cssText = v;
      else if (k in e) e[k] = v;
      else e.setAttribute(k, v);
    }
    for (const f of filhos.flat()) {
      if (f === null || f === undefined || f === false) continue;
      e.append(typeof f === "object" ? f : document.createTextNode(String(f)));
    }
    return e;
  }

  // ------------------------------------------------------------- dados
  async function carregar() {
    try {
      const d = await api(`/api/surto?escala=${est.escala}&rodadas=2000`);
      est.dados = d;
      est.erro = null;
      est.epi = new Epidemia(d.A, d.b);
      est.rodando = false;
      est.particulas = [];
      est.explodiuEm = null;
      est.pos = layout(d.ativos.map((a) => a.id), d.dependencias);
      atualizarBotaoIniciar();
      montarPainel();
      montarRanking();
    } catch (erro) {
      est.erro = erro.message;
      $("veredito-texto").textContent = erro.message;
    }
  }

  // --------------------------------------------------------------- layout
  // Posições por uma simulação simples de molas (determinística): setas
  // aproximam os ativos ligados e todos se repelem.
  const layouts = new Map();
  function layout(ids, deps) {
    const chave = ids.join(",") + "|" + deps.map((d) => `${d.ativo_origem_id}>${d.ativo_destino_id}`).sort().join(",");
    if (layouts.has(chave)) return layouts.get(chave);
    const n = ids.length, pos = {};
    if (!n) return pos;
    if (n === 1) { pos[ids[0]] = { x: (AREA.x0 + AREA.x1) / 2, y: (AREA.y0 + AREA.y1) / 2 }; return pos; }

    const P2 = ids.map((id, i) => {
      const a = (2 * Math.PI * i) / n + Math.sin(id * 12.9898) * 0.3;
      return { id, x: Math.cos(a), y: Math.sin(a) * 0.6, dx: 0, dy: 0 };
    });
    const indice = new Map(P2.map((p, i) => [p.id, i]));
    const arestas = deps.map((d) => [indice.get(d.ativo_origem_id), indice.get(d.ativo_destino_id)]).filter(([a, b]) => a !== undefined && b !== undefined);
    const k = 0.9;
    for (let it = 0; it < 360; it++) {
      const temp = 0.12 * (1 - it / 360) + 0.003;
      for (const p of P2) { p.dx = 0; p.dy = 0; }
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
        let dx = P2[i].x - P2[j].x, dy = (P2[i].y - P2[j].y) * 1.6;
        const d = Math.max(0.02, Math.hypot(dx, dy)), f = (k * k) / d;
        dx /= d; dy /= d;
        P2[i].dx += dx * f; P2[i].dy += dy * f; P2[j].dx -= dx * f; P2[j].dy -= dy * f;
      }
      for (const [a, b] of arestas) {
        let dx = P2[a].x - P2[b].x, dy = P2[a].y - P2[b].y;
        const d = Math.max(0.02, Math.hypot(dx, dy)), f = (d * d) / k;
        dx /= d; dy /= d;
        P2[a].dx -= dx * f; P2[a].dy -= dy * f; P2[b].dx += dx * f; P2[b].dy += dy * f;
      }
      for (const p of P2) {
        p.dx -= p.x * 0.3; p.dy -= p.y * 0.3;
        const m = Math.max(1e-4, Math.hypot(p.dx, p.dy));
        p.x += (p.dx / m) * Math.min(m, temp);
        p.y += (p.dy / m) * Math.min(m, temp);
      }
    }
    const xs = P2.map((p) => p.x), ys = P2.map((p) => p.y);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const pontos = P2.map((p) => ({
      id: p.id,
      x: AREA.x0 + ((p.x - x0) / Math.max(1e-3, x1 - x0)) * (AREA.x1 - AREA.x0),
      y: AREA.y0 + ((p.y - y0) / Math.max(1e-3, y1 - y0)) * (AREA.y1 - AREA.y0),
    }));

    // Afasta prédios que ficaram em cima um do outro: cada um precisa de uma
    // "caixa" livre de 56 x 40 pixels (prédio + nome + barrinha).
    const LX = 56, LY = 40;
    for (let volta = 0; volta < 200; volta++) {
      let mexeu = false;
      for (let i = 0; i < pontos.length; i++) for (let j = i + 1; j < pontos.length; j++) {
        const a = pontos[i], b = pontos[j];
        const dx = b.x - a.x, dy = b.y - a.y;
        const sobraX = LX - Math.abs(dx), sobraY = LY - Math.abs(dy);
        if (sobraX <= 0 || sobraY <= 0) continue;
        mexeu = true;
        if (sobraX / LX < sobraY / LY) {                  // empurra pelo eixo mais barato
          const m = (sobraX / 2 + 0.5) * (dx >= 0 ? 1 : -1);
          a.x -= m; b.x += m;
        } else {
          const m = (sobraY / 2 + 0.5) * (dy >= 0 ? 1 : -1);
          a.y -= m; b.y += m;
        }
      }
      for (const p of pontos) {
        p.x = Math.min(AREA.x1, Math.max(AREA.x0, p.x));
        p.y = Math.min(AREA.y1, Math.max(AREA.y0, p.y));
      }
      if (!mexeu) break;
    }
    for (const p of pontos) pos[p.id] = { x: Math.round(p.x), y: Math.round(p.y) };
    layouts.set(chave, pos);
    return pos;
  }

  // ------------------------------------------------------------- desenho
  const fundo = document.createElement("canvas");
  fundo.width = W; fundo.height = H;
  (() => {
    const f = fundo.getContext("2d");
    f.fillStyle = C.noite; f.fillRect(0, 0, W, H);
    let semente = 7;
    const sorteio = () => ((semente = (semente * 16807) % 2147483647) / 2147483647);
    for (let y = 0; y < H; y += 8) for (let x = 0; x < W; x += 8) {
      if ((x / 8 + y / 8) % 2 === 0 && sorteio() < 0.5) { f.fillStyle = "#1f2236"; f.fillRect(x, y, 8, 8); }
    }
    f.fillStyle = C.marinho;
    for (let y = 8; y < H; y += 16) for (let x = 8; x < W; x += 16) f.fillRect(x, y, 1, 1);
    for (let i = 0; i < 140; i++) {                      // pedrinhas
      f.fillStyle = sorteio() < 0.5 ? C.grafite : "#24283f";
      f.fillRect(Math.floor(sorteio() * W), Math.floor(sorteio() * H), 1, 1);
    }
  })();


  /** Linha pixel a pixel (Bresenham). `traco` > 0 desenha tracejado. */
  function linhaPixel(x0, y0, x1, y1, cor, traco = 0, deslocamento = 0) {
    x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let erro = dx + dy, passo = 0;
    ctx.fillStyle = cor;
    for (;;) {
      if (!traco || Math.floor((passo + deslocamento) / traco) % 2 === 0) ctx.fillRect(x0, y0, 1, 1);
      if (x0 === x1 && y0 === y1) break;
      const e2 = 2 * erro;
      if (e2 >= dy) { erro += dy; x0 += sx; }
      if (e2 <= dx) { erro += dx; y0 += sy; }
      passo++;
    }
  }

  function arestas() {
    const d = est.dados;
    if (!d) return [];
    const indice = new Map(d.ativos.map((a, i) => [a.id, i]));
    return d.dependencias.map((dep) => {
      const o = dep.ativo_origem_id, de = dep.ativo_destino_id;
      return { o, d: de, peso: d.A[indice.get(de)][indice.get(o)] };
    });
  }

  function desenharEstradas(t) {
    const fluxo = est.rodando ? Math.floor(t * 14) : 0;
    for (const e of arestas()) {
      const a = est.pos[e.o], b = est.pos[e.d];
      if (!a || !b) continue;
      const largura = e.peso >= 0.3 ? 3 : 2;
      for (let k = 0; k < largura; k++) {
        const off = k - Math.floor(largura / 2);
        const vertical = Math.abs(b.y - a.y) > Math.abs(b.x - a.x);
        linhaPixel(a.x + (vertical ? off : 0), a.y + (vertical ? 0 : off),
                   b.x + (vertical ? off : 0), b.y + (vertical ? 0 : off), C.grafite);
      }
      linhaPixel(a.x, a.y, b.x, b.y, C.pedra, 3, -fluxo);          // faixa andando: o sentido do risco

      // seta perto do destino
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.max(1, Math.hypot(dx, dy));
      const ux = dx / d, uy = dy / d;
      const px = b.x - ux * 13, py = b.y - uy * 13;
      ctx.fillStyle = C.nevoa;
      for (let s = 0; s < 4; s++) {
        ctx.fillRect(Math.round(px - ux * s - uy * s), Math.round(py - uy * s + ux * s), 1, 1);
        ctx.fillRect(Math.round(px - ux * s + uy * s), Math.round(py - uy * s - ux * s), 1, 1);
      }
      const rot = numPixel(e.peso);
      P.texto(ctx, rot, (a.x + b.x) / 2, (a.y + b.y) / 2 - 7, { cor: C.nevoa, alinhar: "center" });
    }
  }

  function desenharPredios(t) {
    const d = est.dados;
    if (!d) return;
    const estimativa = est.epi ? est.epi.estimativa() : [];
    const explodiu = est.explodiuEm !== null;
    const maximo = Math.max(1, ...(d.x || d.b));

    d.ativos.forEach((a, i) => {
      const p = est.pos[a.id];
      if (!p) return;
      const x = d.x ? d.x[i] : null;
      const cor = explodiu ? C.sangue : P.corDoRisco(x ?? d.b[i]);
      const nome = P.POR_TIPO[a.tipo_codigo] || "servidor";
      const tremor = explodiu && !calmo ? Math.round(Math.sin(t * 40 + i) * 1) : 0;

      // sombra
      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.fillRect(p.x - 7, p.y + 7, 14, 2);
      ctx.drawImage(P.sprite(nome, cor), p.x - 8 + tremor, p.y - 8);

      // piscada branca quando uma infecção chega
      const flash = est.flashes.get(a.id);
      if (flash !== undefined && t - flash < 0.14) {
        ctx.strokeStyle = C.branco;
        ctx.lineWidth = 1;
        ctx.strokeRect(p.x - 9.5, p.y - 9.5, 19, 19);
      }

      // caveira nos ativos críticos (piscando)
      if ((explodiu || (x !== null && x >= 15)) && Math.floor(t * 2.5 + i) % 2 === 0) {
        ctx.drawImage(P.sprite("caveira"), p.x - 3, p.y - 22);
      } else if (x !== null && x < 4) {
        ctx.drawImage(P.sprite("escudo"), p.x + 6, p.y - 12);
      }

      // valor (álgebra) em cima, nome embaixo
      P.texto(ctx, explodiu ? "???" : numPixel(x ?? NaN, 1), p.x, p.y - 15, { cor, alinhar: "center" });
      const rotulo = a.nome.length > 11 ? a.nome.slice(0, 10) + "." : a.nome;
      P.texto(ctx, rotulo, p.x, p.y + 11, { cor: C.nevoa, alinhar: "center" });

      // barrinha da prova: laranja = média do sorteio, marca azul = álgebra
      if (x !== null && est.epi && est.epi.rodadas > 0) {
        const largura = 24, alvo = 16;
        const cheio = Math.min(largura, Math.round((estimativa[i] / Math.max(x, 1e-9)) * alvo));
        const bx = p.x - 12, by = p.y + 18;
        ctx.fillStyle = C.grafite; ctx.fillRect(bx, by, largura, 2);
        ctx.fillStyle = C.laranja; ctx.fillRect(bx, by, cheio, 2);
        ctx.fillStyle = C.celeste; ctx.fillRect(bx + alvo, by - 1, 1, 4);
      }

      // fumaça saindo dos prédios em risco
      if (!calmo && (explodiu || (x !== null && x >= 8)) && Math.random() < (explodiu ? 0.25 : 0.06)) {
        est.fumaca.push({ x: p.x - 3 + Math.random() * 6, y: p.y - 9, t0: t, vida: 1 + Math.random() });
      }
      void maximo;
    });
  }

  function desenharFumaca(t) {
    est.fumaca = est.fumaca.filter((f) => t - f.t0 < f.vida);
    for (const f of est.fumaca) {
      const idade = (t - f.t0) / f.vida;
      ctx.fillStyle = idade < 0.5 ? C.nevoa : C.pedra;
      ctx.fillRect(Math.round(f.x + Math.sin(idade * 6) * 2), Math.round(f.y - idade * 14), idade < 0.6 ? 2 : 1, idade < 0.6 ? 2 : 1);
    }
  }

  function desenharParticulas(t) {
    const vivas = [];
    for (const q of est.particulas) {
      if (t < q.t0) { vivas.push(q); continue; }
      const k = (t - q.t0) / q.dur;
      if (k >= 1) {
        est.flashes.set(q.para, t);
        Som.blip();
        continue;
      }
      const a = est.pos[q.de], b = est.pos[q.para];
      if (!a || !b) continue;
      const suave = k * k * (3 - 2 * k);
      const x = a.x + (b.x - a.x) * suave, y = a.y + (b.y - a.y) * suave - Math.sin(k * Math.PI) * 6;
      ctx.drawImage(P.sprite(Math.floor(t * 7 + q.fase) % 2 ? "germe1" : "germe0"), Math.round(x) - 2, Math.round(y) - 2);
      vivas.push(q);
    }
    est.particulas = vivas;
  }

  function desenharHud(t) {
    const d = est.dados;
    ctx.fillStyle = "rgba(26,28,44,0.85)";
    ctx.fillRect(0, 0, W, 11);
    ctx.fillRect(0, H - 13, W, 13);
    const rodadas = est.epi ? est.epi.rodadas : 0;
    P.texto(ctx, `EPIDEMIAS ${rodadas}`, 4, 3, { cor: C.branco });
    if (d) {
      const explodiu = !d.convergente;
      P.texto(ctx, `R0 ${numPixel(d.rho, 3)}`, W - 4, 3, { cor: explodiu ? C.laranja : C.lima, alinhar: "right" });
      if (est.escala !== 1) P.texto(ctx, `PESOS X${numPixel(est.escala, 1)}`, W / 2, 3, { cor: C.areia, alinhar: "center" });
    }

    let rodape;
    if (est.erro) rodape = "SEM DADOS: " + est.erro;
    else if (!d) rodape = "CARREGANDO...";
    else if (!d.ativos.length) rodape = "CADASTRE ATIVOS NA ABA ATIVOS";
    else if (est.explodiuEm !== null) rodape = d.convergente ? "R0 PERTO DE 1: CADA EPIDEMIA DEMORA MUITO PARA ACABAR" : "R0 >= 1: A EPIDEMIA NAO PARA DE CRESCER";
    else if (est.rodando) rodape = `INFECCOES SORTEADAS: ${est.epi.infeccoes}`;
    else if (rodadas) rodape = "PAUSADO. ESPACO CONTINUA";
    else rodape = "APERTE INICIAR SURTO (OU ESPACO)";
    P.texto(ctx, rodape.slice(0, 92), W / 2, H - 9, { cor: C.nevoa, alinhar: "center" });

    // legenda das cores
    const faixas = [[C.verde, "<4"], [C.areia, "<8"], [C.laranja, "<15"], [C.sangue, "15+"]];
    let lx = 4;
    P.texto(ctx, "RISCO", lx, H - 22, { cor: C.pedra }); lx += 22;
    for (const [cor, txt] of faixas) {
      ctx.fillStyle = cor; ctx.fillRect(lx, H - 22, 4, 5);
      lx += 6 + P.texto(ctx, txt, lx + 6, H - 22, { cor: C.pedra }) + 4;
    }

    if (est.explodiuEm !== null && Math.floor((t - est.explodiuEm) * 2) % 2 === 0) {
      ctx.fillStyle = "rgba(93,39,93,0.85)";
      ctx.fillRect(0, H / 2 - 16, W, 30);
      const quase = est.dados && est.dados.convergente;
      P.texto(ctx, quase ? "EPIDEMIA GIGANTE" : "SURTO FORA DE CONTROLE", W / 2, H / 2 - 11, { cor: C.branco, escala: 2, alinhar: "center", sombra: C.sangue });
      P.texto(ctx, quase ? "R0 QUASE 1: O SORTEIO PAROU POR SEGURANCA" : "BAIXE OS PESOS ATE O R0 FICAR ABAIXO DE 1", W / 2, H / 2 + 5, { cor: C.areia, alinhar: "center" });
    }
  }

  // ----------------------------------------------------------- simulação
  function passoDaSimulacao(t, dt) {
    if (!est.rodando || !est.epi) return;
    est.acumulado += dt * est.vel;
    let feitas = 0;
    const duracao = est.vel <= 3 ? 0.55 : est.vel <= 30 ? 0.4 : 0.3;
    const intervaloVisual = est.vel <= 3 ? 0 : est.vel <= 30 ? 0.12 : 0.22;

    while (est.acumulado >= 1 && feitas < 400) {
      est.acumulado -= 1;
      feitas++;
      const saltos = est.epi.rodada();
      if (est.epi.explodiu) { explodir(t); break; }

      const mostrar = t - est.ultimoVisual >= intervaloVisual && est.particulas.length < 140;
      if (mostrar && saltos.length) {
        est.ultimoVisual = t;
        for (const s of saltos.slice(0, 60)) {
          est.particulas.push({ de: s.de, para: s.para, t0: t + s.geracao * duracao, dur: duracao, fase: Math.random() * 2 });
        }
      }
      // chegada também acende quem só tem risco próprio
      if (mostrar) est.epi.b.forEach((v, i) => { if (v > 0 && est.dados.ativos[i]) est.flashes.set(est.dados.ativos[i].id, t); });
    }
  }

  function explodir(t) {
    est.rodando = false;
    est.explodiuEm = t;
    Som.explosao();
    atualizarBotaoIniciar();
    aviso(est.dados.convergente
      ? "R0 muito perto de 1: as epidemias ficaram enormes e o sorteio parou por segurança. A álgebra ainda tem solução."
      : "O surto explodiu: com esses pesos o R0 é maior ou igual a 1.", false);
  }

  function chuvaDeGermes(t) {
    // depois de explodir, o contágio continua tomando tudo (só visual)
    if (est.explodiuEm === null || calmo) return;
    const lista = arestas();
    if (!lista.length) return;
    while (est.particulas.length < 90) {
      const e = lista[Math.floor(Math.random() * lista.length)];
      est.particulas.push({ de: e.o, para: e.d, t0: t + Math.random() * 0.6, dur: 0.35, fase: Math.random() * 2 });
    }
  }

  // ------------------------------------------------------------- quadros
  let anterior = performance.now();
  let ultimoPainel = 0;
  function quadro(agora) {
    const t = agora / 1000;
    const dt = Math.min(0.1, (agora - anterior) / 1000);
    anterior = agora;

    if (est.aba === "surto") {
      passoDaSimulacao(t, dt);
      chuvaDeGermes(t);
      const tremor = est.explodiuEm !== null && !calmo && t - est.explodiuEm < 0.7
        ? [Math.round((Math.random() - 0.5) * 4), Math.round((Math.random() - 0.5) * 4)] : [0, 0];
      ctx.setTransform(1, 0, 0, 1, tremor[0], tremor[1]);
      ctx.drawImage(fundo, 0, 0);
      desenharEstradas(t);
      desenharPredios(t);
      desenharParticulas(t);
      desenharFumaca(t);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      desenharHud(t);
      if (agora - ultimoPainel > 250) { atualizarPlacar(); ultimoPainel = agora; }
    }
    requestAnimationFrame(quadro);
  }

  // ------------------------------------------------------------- painel
  function montarPainel() {
    const d = est.dados;
    const card = $("veredito");
    card.classList.toggle("explodiu", !d.convergente);
    $("r0").textContent = num(d.rho, 3);
    let texto;
    if (!d.n) texto = "Sem ativos, sem surto. Cadastre ativos na aba Ativos.";
    else if (!d.convergente) texto = "Maior ou igual a 1: o surto explode. A série b + A·b + A²·b + ... não termina e não existe risco finito.";
    else if (!d.regra_do_projeto) texto = "Menor que 1: ainda converge. Mas algum ativo recebe pesos que somam 1 ou mais, e o cadastro recusaria. A regra é mais exigente que o R0.";
    else texto = "Menor que 1: cada infecção gera menos de uma nova, o surto morre sozinho e I − A tem solução.";
    $("veredito-texto").textContent = texto;

    // tabela ativo por ativo
    const tabela = $("tabela-ativos");
    tabela.replaceChildren(
      el("thead", {}, el("tr", {},
        el("th", { scope: "col" }, "Ativo"), el("th", { scope: "col", class: "num", title: "Risco próprio" }, "b"),
        el("th", { scope: "col", class: "num", title: "Álgebra: (I − A)x = b" }, "x solve"),
        el("th", { scope: "col", class: "num", title: "Média das epidemias sorteadas" }, "x sorteio"),
        el("th", { scope: "col", class: "num", title: "Quanto 1 ponto de risco aqui vira na rede" }, "mult."))),
      el("tbody", {}, d.ativos.map((a, i) => el("tr", {},
        el("th", { scope: "row" },
          el("span", { class: "bolinha", style: `background:${P.corDoRisco(d.x ? d.x[i] : null)}` }), a.nome),
        el("td", { class: "num" }, num(d.b[i])),
        el("td", { class: "num" }, d.x ? num(d.x[i]) : "--"),
        el("td", { class: "num mc", "data-i": i }, "--"),
        el("td", { class: "num" }, d.multiplicadores ? num(d.multiplicadores[i]) : "--")))));

    // matriz A
    const ids = d.ativos.map((a) => a.id);
    $("matriz").replaceChildren(d.n ? el("table", { class: "matriz" },
      el("caption", { class: "dica", style: "text-align:left;caption-side:top;margin-bottom:6px" },
        "A[linha][coluna] = quanto do risco da coluna chega na linha"),
      el("thead", {}, el("tr", {}, el("th", {}, ""), ids.map((id) => el("th", { scope: "col" }, id)))),
      el("tbody", {}, d.A.map((linha, i) => el("tr", {},
        el("th", { scope: "row" }, ids[i]),
        linha.map((v) => el("td", {
          style: v > 0 ? `background: rgba(239,125,87,${Math.min(0.85, 0.2 + v)}); color:#1a1c2c; font-weight:bold` : "color:#566c86",
        }, v > 0 ? num(v) : "0")))))) : el("p", { class: "vazio" }, "Sem ativos."));

    const g = d.diagnostico;
    $("diagnostico").replaceChildren(...(g ? [
      ["Posto de I − A", `${g.posto} de ${g.ordem}`],
      ["Determinante", num(g.determinante, 4)],
      ["Número de condição κ", g.condicao === null ? "infinito" : num(g.condicao, 2)],
      ["Invertível", g.invertivel ? "sim" : "não"],
      ["Regra do cadastro (somas < 1)", d.regra_do_projeto ? "respeitada" : "violada"],
      ["Sorteio no servidor (NumPy)", d.erro_relativo === null ? (d.convergente ? "parou (R0 perto de 1)" : "explodiu")
        : `${d.monte_carlo.rodadas} epidemias, diferença ${num(d.erro_relativo * 100)}%`],
    ].flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]) : []));

    atualizarPlacar();
  }

  function atualizarPlacar() {
    const d = est.dados;
    if (!d || !est.epi) return;
    const exato = d.risco_global;
    const mc = est.epi.global();
    $("v-exato").textContent = num(exato);
    $("v-mc").textContent = est.epi.rodadas ? (est.epi.explodiu ? (d.convergente ? "parou" : "explodiu") : num(mc)) : "--";
    $("v-erro").textContent = est.epi.rodadas && exato ? `${num(Math.abs(mc - exato) / exato * 100)}%` : "--";
    $("v-rodadas").textContent = est.epi.rodadas.toLocaleString("pt-BR");
    const estimativa = est.epi.estimativa();
    document.querySelectorAll("#tabela-ativos .mc").forEach((td) => {
      td.textContent = est.epi.rodadas ? num(estimativa[Number(td.dataset.i)]) : "--";
    });
    desenharGrafico();
  }

  const grafico = $("grafico");
  const g2 = grafico.getContext("2d");
  function desenharGrafico() {
    const d = est.dados, epi = est.epi;
    const GW = grafico.width, GH = grafico.height;
    g2.fillStyle = C.noite; g2.fillRect(0, 0, GW, GH);
    const x0 = 4, x1 = GW - 4, y0 = 12, y1 = GH - 12;
    g2.fillStyle = C.grafite;
    g2.fillRect(x0, y1, x1 - x0, 1);
    if (!d || !epi) return;

    const exato = d.risco_global;
    const curva = epi.curva;
    // Janela de 50% a 150% da resposta da álgebra: dá para ver o sorteio "mirando" nela.
    const base = exato ? exato * 0.5 : 0;
    const topo = exato ? exato * 1.5 : Math.max(1, ...curva.map((p) => p[1]));
    const maxR = Math.max(50, epi.rodadas);
    const px = (r) => x0 + (r / maxR) * (x1 - x0);
    const py = (v) => y1 - Math.max(0, Math.min(1, (v - base) / (topo - base))) * (y1 - y0);

    if (exato) {
      g2.fillStyle = C.celeste;
      for (let x = x0; x < x1; x += 4) g2.fillRect(x, Math.round(py(exato)), 2, 1);
      P.texto(g2, `SOLVE ${numPixel(exato)}`, x1, Math.round(py(exato)) - 7, { cor: C.celeste, alinhar: "right" });
    } else {
      P.texto(g2, "SEM SOLUCAO FINITA", GW / 2, y0, { cor: C.laranja, alinhar: "center" });
    }

    let antes = null;
    for (const [r, v] of curva) {
      const ponto = [Math.round(px(r)), Math.round(py(v))];
      if (antes) {
        const [ax, ay] = antes, [bx, by] = ponto;
        const passos = Math.max(Math.abs(bx - ax), Math.abs(by - ay), 1);
        g2.fillStyle = C.laranja;
        for (let s = 0; s <= passos; s++) g2.fillRect(Math.round(ax + ((bx - ax) * s) / passos), Math.round(ay + ((by - ay) * s) / passos), 1, 1);
      }
      antes = ponto;
    }
    if (exato) {
      P.texto(g2, `+50%`, x0, y0 - 9, { cor: C.pedra });
      P.texto(g2, `-50%`, x0, y1 - 7, { cor: C.pedra });
    }
    P.texto(g2, "0", x0, y1 + 3, { cor: C.pedra });
    P.texto(g2, `${maxR} EPIDEMIAS`, x1, y1 + 3, { cor: C.pedra, alinhar: "right" });
    if (epi.rodadas && antes) P.texto(g2, "SORTEIO", Math.min(antes[0] + 3, x1 - 28), Math.max(y0, Math.min(y1 - 14, antes[1] + 4)), { cor: C.laranja });
  }

  // ------------------------------------------------------------- defesa
  function montarRanking() {
    const d = est.dados;
    const lista = $("ranking");
    if (!d.ranking.length) {
      lista.replaceChildren(el("li", { class: "vazio" }, d.n ? "Nenhuma falha aberta. Rede limpa." : "Sem ativos cadastrados."));
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
      el("button", { type: "button", class: "botao primario", on: { click: () => corrigir(r) } }, "Corrigir")));

    const desfazer = est.ultimaCorrecao
      ? el("li", {}, el("span", {}), el("span", { class: "dica" },
          `Última correção: ${est.ultimaCorrecao.vulnerabilidade_id} em ${est.ultimaCorrecao.ativo_nome}.`),
          el("span", {}), el("button", { type: "button", class: "botao", on: { click: desfazerCorrecao } }, "Desfazer"))
      : null;
    lista.replaceChildren(...itens, ...(desfazer ? [desfazer] : []));
  }

  async function mudarStatus(item, status) {
    await api(`/api/ativos/${item.ativo_id}/vulnerabilidades/${encodeURIComponent(item.vulnerabilidade_id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  }

  async function corrigir(item) {
    const antes = est.dados.risco_global;
    try {
      await mudarStatus(item, "Corrigida");
      est.ultimaCorrecao = item;
      Som.cura();
      await carregar();
      aviso(`${item.vulnerabilidade_id} corrigida. Risco global ${num(antes)} → ${num(est.dados.risco_global)}.`);
    } catch (erro) {
      aviso(`Não foi possível corrigir: ${erro.message}`, false);
    }
  }

  async function desfazerCorrecao() {
    const item = est.ultimaCorrecao;
    if (!item) return;
    try {
      await mudarStatus(item, "Aberta");
      est.ultimaCorrecao = null;
      await carregar();
      aviso(`${item.vulnerabilidade_id} reaberta em ${item.ativo_nome}.`);
    } catch (erro) {
      aviso(`Não foi possível desfazer: ${erro.message}`, false);
    }
  }

  // ------------------------------------------------------------- diário
  const graficoDiario = $("grafico-diario");
  async function carregarDiario() {
    let dados;
    try {
      dados = await api("/api/surto/diario");
    } catch (erro) {
      $("diario-resumo").textContent = erro.status === 404
        ? "O diário está desligado neste servidor. Ele liga com o servidor.py (variável SURTO_INTERVALO_S, padrão: 1 hora)."
        : `Não foi possível ler o diário: ${erro.message}`;
      desenharDiario([], 0, 3600);
      $("tabela-diario").replaceChildren();
      return;
    }
    const e = dados.entradas;
    const intervalo = dados.intervalo_s > 0 ? dados.intervalo_s : 3600;
    const agora = dados.agora;
    const inicioJanela = agora - 24 * 3600;
    const horas = new Set(e.filter((x) => x.t >= inicioJanela).map((x) => Math.floor((x.t - inicioJanela) / 3600)));
    const piorErro = Math.max(0, ...e.map((x) => x.erro_relativo ?? 0));
    const desde = e.length ? new Date(e[0].t * 1000).toLocaleString("pt-BR") : null;
    $("diario-resumo").textContent = e.length
      ? `${e.length} anotações desde ${desde}. Nas últimas 24 horas, ${horas.size} de 24 horas têm registro. `
        + `Maior diferença entre sorteio e álgebra: ${num(piorErro * 100)}%.`
      : "Nenhuma anotação ainda. A primeira é feita quando o servidor liga.";
    desenharDiario(e, agora, intervalo);

    $("tabela-diario").replaceChildren(
      el("thead", {}, el("tr", {}, ["Quando", "Motivo", "Ativos", "Álgebra", "Sorteio", "Diferença", "R0"]
        .map((t, k) => el("th", { scope: "col", class: k >= 2 ? "num" : null }, t)))),
      el("tbody", {}, e.slice(-48).reverse().map((x) => el("tr", {},
        el("td", {}, new Date(x.t * 1000).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })),
        el("td", {}, x.erro ? `${x.motivo} (erro: ${x.erro})` : x.motivo),
        el("td", { class: "num" }, x.ativos),
        el("td", { class: "num" }, num(x.risco_global)),
        el("td", { class: "num" }, num(x.monte_carlo)),
        el("td", { class: "num" }, x.erro_relativo === null ? "--" : `${num(x.erro_relativo * 100)}%`),
        el("td", { class: "num" }, num(x.rho, 3))))));
  }

  function desenharDiario(entradas, agora, intervalo) {
    const g = graficoDiario.getContext("2d");
    const GW = graficoDiario.width, GH = graficoDiario.height;
    g.fillStyle = C.noite; g.fillRect(0, 0, GW, GH);
    const x0 = 6, x1 = GW - 6, y0 = 10, y1 = GH - 14;
    const inicio = (agora || Date.now() / 1000) - 24 * 3600;
    const fim = inicio + 24 * 3600;
    const px = (t) => x0 + ((t - inicio) / (fim - inicio)) * (x1 - x0);
    const janela = entradas.filter((e) => e.t >= inicio);
    const topo = Math.max(1, ...janela.map((e) => Math.max(e.risco_global || 0, e.monte_carlo || 0))) * 1.15;
    const py = (v) => y1 - (v / topo) * (y1 - y0);

    // horas sem registro (depois da primeira anotação) = servidor fora do ar
    const primeira = janela.length ? janela[0].t : null;
    for (let h = 0; h < 24; h++) {
      const a = inicio + h * 3600, b = a + 3600;
      const tem = janela.some((e) => e.t >= a && e.t < b);
      if (!tem && primeira !== null && b > primeira && a < (agora - intervalo)) {
        g.fillStyle = C.grafite;
        g.fillRect(Math.round(px(a)), y0, Math.max(1, Math.round(px(b) - px(a)) - 1), y1 - y0);
      }
    }
    g.fillStyle = C.pedra; g.fillRect(x0, y1, x1 - x0, 1);
    for (let h = 0; h <= 24; h += 6) {
      const t = inicio + h * 3600;
      g.fillRect(Math.round(px(t)), y1, 1, 3);
      const rotulo = new Date(t * 1000).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
      P.texto(g, rotulo, px(t), y1 + 5, { cor: C.pedra, alinhar: h === 0 ? "left" : h === 24 ? "right" : "center" });
    }
    for (const e of janela) {
      const x = Math.round(px(e.t));
      if (e.risco_global !== null) {
        g.fillStyle = C.celeste;
        g.fillRect(x - 1, Math.round(py(e.risco_global)), 3, y1 - Math.round(py(e.risco_global)));
      }
      if (e.monte_carlo !== null) {
        g.fillStyle = C.laranja;
        g.fillRect(x - 1, Math.round(py(e.monte_carlo)) - 1, 3, 3);
      }
    }
    if (!janela.length) P.texto(g, "SEM ANOTACOES NAS ULTIMAS 24 HORAS", GW / 2, GH / 2 - 4, { cor: C.pedra, alinhar: "center" });
  }

  // ------------------------------------------------------------- controles
  function atualizarBotaoIniciar() {
    const b = $("btn-iniciar");
    if (est.explodiuEm !== null) { b.textContent = "Explodiu"; b.disabled = true; return; }
    b.disabled = !est.dados || !est.dados.n;
    b.textContent = est.rodando ? "Pausar" : (est.epi && est.epi.rodadas ? "Continuar" : "Iniciar surto");
  }

  function alternar() {
    if (!est.dados || !est.dados.n || est.explodiuEm !== null) return;
    est.rodando = !est.rodando;
    if (est.rodando) Som.inicio();
    atualizarBotaoIniciar();
  }

  function zerar() {
    if (!est.dados) return;
    est.epi = new Epidemia(est.dados.A, est.dados.b);
    est.rodando = false;
    est.particulas = [];
    est.fumaca = [];
    est.explodiuEm = null;
    atualizarBotaoIniciar();
    atualizarPlacar();
  }

  function trocarAba(nome) {
    est.aba = nome;
    for (const aba of ["surto", "ativos", "diario", "como"]) {
      $(`aba-${aba}`).setAttribute("aria-selected", String(aba === nome));
      $(`aba-${aba}`).tabIndex = aba === nome ? 0 : -1;
      $(`tela-${aba}`).hidden = aba !== nome;
    }
    if (nome === "ativos" && window.Ativos) window.Ativos.montar();
    if (nome === "diario") carregarDiario();
    if (nome === "surto") carregar();
  }

  $("btn-iniciar").addEventListener("click", alternar);
  $("btn-zerar").addEventListener("click", zerar);
  document.querySelectorAll(".vel").forEach((b) => b.addEventListener("click", () => {
    est.vel = Number(b.dataset.vel);
    document.querySelectorAll(".vel").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
  }));

  let esperaEscala = null;
  $("escala").addEventListener("input", (e) => {
    est.escala = Number(e.target.value);
    $("escala-valor").textContent = `×${num(est.escala, 1)}`;
    clearTimeout(esperaEscala);
    esperaEscala = setTimeout(carregar, 200);
  });

  const abas = ["surto", "ativos", "diario", "como"];
  abas.forEach((nome) => $(`aba-${nome}`).addEventListener("click", () => trocarAba(nome)));
  document.querySelector(".abas").addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const i = abas.indexOf(est.aba);
    const proxima = abas[(i + (e.key === "ArrowRight" ? 1 : abas.length - 1)) % abas.length];
    trocarAba(proxima);
    $(`aba-${proxima}`).focus();
  });

  $("btn-som").addEventListener("click", () => {
    const ligado = Som.alternar();
    $("btn-som").setAttribute("aria-pressed", String(ligado));
    $("btn-som").textContent = ligado ? "Som: ligado" : "Som: desligado";
  });

  document.addEventListener("keydown", (e) => {
    if (est.aba !== "surto" || e.target.matches("input, select, textarea, button")) return;
    if (e.key === " ") { e.preventDefault(); alternar(); }
    else if (e.key === "r" || e.key === "R") zerar();
  });

  // Escala inteira do canvas: cada pixel do jogo vira 2x2, 3x3... na tela.
  function ajustarTamanho() {
    const disponivel = mapa.parentElement.clientWidth;
    const fator = Math.floor(disponivel / W);
    const largura = fator >= 1 ? W * fator : disponivel;
    mapa.style.width = `${largura}px`;
    mapa.style.height = `${(largura * H) / W}px`;
  }
  window.addEventListener("resize", ajustarTamanho);
  ajustarTamanho();

  // logo
  (() => {
    const lg = $("logo").getContext("2d");
    lg.drawImage(P.sprite("germe0"), 0, 4);
    lg.drawImage(P.sprite("germe1"), 57, 4);
    P.texto(lg, "SURTO", 32, 2, { cor: C.lima, escala: 2, alinhar: "center", sombra: C.verde });
  })();

  // Interface para a tela de cadastro (ativos.js).
  window.App = { api, aviso, recarregar: carregar, dados: () => est.dados };

  carregar();
  requestAnimationFrame(quadro);
})();
