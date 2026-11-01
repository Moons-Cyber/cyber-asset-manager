/* Pixel art feito à mão: paleta, fonte bitmap 3x5 e sprites.
 *
 * Nada é baixado da internet (o servidor da faculdade pode estar offline):
 * a fonte e os desenhos estão aqui como texto. Cada letra da string de um
 * sprite é a cor de um pixel.
 */
const Pixel = (() => {
  // Paleta "Sweetie 16" (GrafxKid): 16 cores, nenhuma a mais.
  const COR = {
    noite: "#1a1c2c", uva: "#5d275d", sangue: "#b13e53", laranja: "#ef7d57",
    areia: "#ffcd75", lima: "#a7f070", verde: "#38b764", petroleo: "#257179",
    marinho: "#29366f", azul: "#3b5dc9", celeste: "#41a6f6", gelo: "#73eff7",
    branco: "#f4f4f4", nevoa: "#94b0c2", pedra: "#566c86", grafite: "#333c57",
  };

  // letra do sprite -> cor. "A" é a cor de saúde do ativo (muda com o risco).
  const CHAVE = {
    k: COR.noite, g: COR.grafite, s: COR.pedra, l: COR.nevoa, w: COR.branco,
    b: COR.azul, c: COR.celeste, t: COR.gelo, n: COR.marinho, q: COR.petroleo,
    G: COR.verde, L: COR.lima, y: COR.areia, o: COR.laranja, r: COR.sangue, p: COR.uva,
  };

  // ------------------------------------------------------------- fonte 3x5
  const GLIFOS = {
    A: "010101111101101", B: "110101110101110", C: "011100100100011", D: "110101101101110",
    E: "111100110100111", F: "111100110100100", G: "011100101101011", H: "101101111101101",
    I: "111010010010111", J: "001001001101010", K: "101101110101101", L: "100100100100111",
    M: "101111111101101", N: "110101101101101", O: "010101101101010", P: "110101110100100",
    Q: "010101101110011", R: "110101110101101", S: "011100010001110", T: "111010010010010",
    U: "101101101101111", V: "101101101101010", W: "101101111111101", X: "101101010101101",
    Y: "101101010010010", Z: "111001010100111",
    0: "111101101101111", 1: "010110010010111", 2: "110001010100111", 3: "110001010001110",
    4: "101101111001001", 5: "111100110001110", 6: "011100111101111", 7: "111001010010010",
    8: "111101111101111", 9: "111101111001110",
    ".": "000000000000010", ",": "000000000010100", ":": "000010000010000", "-": "000000111000000",
    "+": "000010111010000", "/": "001001010100100", "(": "010100100100010", ")": "010001001001010",
    "%": "101001010100101", "!": "010010010000010", "?": "110001010000010", ">": "100010001010100",
    "<": "001010100010001", "=": "000111000111000", "_": "000000000000111", "#": "101111101111101",
    "*": "000101010101000", "'": "010010000000000", "|": "010010010010010", "^": "010101000000000",
    " ": "000000000000000",
  };

  function normalizar(texto) {
    return String(texto).normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
  }

  function larguraTexto(texto, escala = 1) {
    const n = normalizar(texto).length;
    return n ? (n * 4 - 1) * escala : 0;
  }

  /** Escreve texto pixelado. Opções: cor, escala, alinhar (left|center|right), sombra. */
  function texto(ctx, conteudo, x, y, { cor = COR.branco, escala = 1, alinhar = "left", sombra = COR.noite } = {}) {
    const s = normalizar(conteudo);
    let px = Math.round(x);
    const largura = larguraTexto(s, escala);
    if (alinhar === "center") px = Math.round(x - largura / 2);
    else if (alinhar === "right") px = Math.round(x - largura);
    const py = Math.round(y);

    const pintar = (dx, dy, c) => {
      ctx.fillStyle = c;
      for (let k = 0; k < s.length; k++) {
        const g = GLIFOS[s[k]] || GLIFOS["?"];
        for (let i = 0; i < 15; i++) {
          if (g[i] === "1") {
            ctx.fillRect(px + dx + (k * 4 + (i % 3)) * escala, py + dy + Math.floor(i / 3) * escala, escala, escala);
          }
        }
      }
    };
    if (sombra) pintar(escala, escala, sombra);
    pintar(0, 0, cor);
    return largura;
  }

  // ---------------------------------------------------------------- sprites
  const SPRITES = {
    // 1 Notebook
    notebook: [
      "................",
      "................",
      "...kkkkkkkkkk...",
      "...kggggggggk...",
      "...kgbbbbbbgk...",
      "...kgbcAAcbgk...",
      "...kgbAccAbgk...",
      "...kgbbbbbbgk...",
      "...kggggggggk...",
      "...kkkkkkkkkk...",
      "..kllllllllllk..",
      ".klswswswswswlk.",
      ".kllllllllllllk.",
      "..kkkkkkkkkkkk..",
      "................",
      "................",
    ],
    // 2 Servidor
    servidor: [
      "...kkkkkkkkkk...",
      "...kssssssssk...",
      "...ksggggggsk...",
      "...ksgAgAgwsk...",
      "...ksggggggsk...",
      "...kssssssssk...",
      "...ksggggggsk...",
      "...ksgAgwgAsk...",
      "...ksggggggsk...",
      "...kssssssssk...",
      "...ksggggggsk...",
      "...ksgwgAgwsk...",
      "...ksggggggsk...",
      "...kssssssssk...",
      "...kkkkkkkkkk...",
      "....kk....kk....",
    ],
    // 3 Roteador
    roteador: [
      "................",
      "...A........A...",
      "...k........k...",
      "...k........k...",
      "...k........k...",
      "...k........k...",
      ".kkkkkkkkkkkkkk.",
      ".kbbbbbbbbbbbbk.",
      ".kbccccccccccbk.",
      ".kbcAcAcAcwcbbk.",
      ".kbccccccccccbk.",
      ".kbbbbbbbbbbbbk.",
      ".kkkkkkkkkkkkkk.",
      "..kk........kk..",
      "................",
      "................",
    ],
    // 4 Banco de dados
    banco: [
      "................",
      ".....kkkkkk.....",
      "...kkllllllkk...",
      "..klwwlllllllk..",
      "..kkllllllllkk..",
      "..ksskkkkkkssk..",
      "..kssssssssssk..",
      "..ksAssssssssk..",
      "..kssssssssssk..",
      "..ksskkkkkkssk..",
      "..kssssssssssk..",
      "..ksAssssssssk..",
      "..kssssssssssk..",
      "...kksssssskk...",
      ".....kkkkkk.....",
      "................",
    ],
    germe0: ["r.p.r", ".rrr.", "rwrwr", ".rrr.", "p.r.p"],
    germe1: [".r.r.", "prrrp", "rwrwr", "prrrp", ".r.r."],
    caveira: [".wwwww.", "wwwwwww", "wkkwkkw", "wkkwkkw", "wwwkwww", ".wwwww.", ".w.w.w."],
    escudo: ["GGGGG", "GLLLG", "GLLLG", ".GLG.", "..G.."],
  };

  const POR_TIPO = { 1: "notebook", 2: "servidor", 3: "roteador", 4: "banco" };

  const cache = new Map();
  /** Devolve um canvas com o sprite já pintado (cacheado por nome + cor de saúde). */
  function sprite(nome, saude = COR.verde) {
    const chave = nome + "|" + saude;
    if (cache.has(chave)) return cache.get(chave);
    const linhas = SPRITES[nome] || SPRITES.servidor;
    const c = document.createElement("canvas");
    c.width = linhas[0].length;
    c.height = linhas.length;
    const ctx = c.getContext("2d");
    linhas.forEach((linha, y) => {
      for (let x = 0; x < linha.length; x++) {
        const ch = linha[x];
        if (ch === ".") continue;
        ctx.fillStyle = ch === "A" ? saude : CHAVE[ch];
        ctx.fillRect(x, y, 1, 1);
      }
    });
    cache.set(chave, c);
    return c;
  }

  /** Cor de saúde a partir do risco efetivo (mesmas faixas em toda a tela). */
  function corDoRisco(x) {
    if (x === null || x === undefined || !Number.isFinite(x)) return COR.sangue;
    if (x < 4) return COR.verde;
    if (x < 8) return COR.areia;
    if (x < 15) return COR.laranja;
    return COR.sangue;
  }

  return { COR, texto, larguraTexto, sprite, POR_TIPO, corDoRisco };
})();
