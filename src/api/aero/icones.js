/* Ícones do tema Aero, desenhados do zero em SVG (vidro, brilho e gradiente).
 * Os textos abaixo são fixos do próprio código; nenhum dado do servidor entra aqui.
 */
const Icones = (() => {
  "use strict";

  const BRILHO = (cx, cy, rx, ry, op = 0.45) =>
    `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="#fff" opacity="${op}"/>`;

  const bolaVidro = (id, claro, meio, escuro) =>
    `<radialGradient id="${id}" cx=".35" cy=".28" r=".85"><stop offset="0" stop-color="${claro}"/><stop offset=".45" stop-color="${meio}"/><stop offset="1" stop-color="${escuro}"/></radialGradient>`;

  const SVGS = {
    ativos: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>
        <linearGradient id="ic-a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b7e3ff"/><stop offset=".48" stop-color="#3b97f2"/><stop offset=".52" stop-color="#1a6fe0"/><stop offset="1" stop-color="#0a49b8"/></linearGradient></defs>
      <g stroke="#06358f" stroke-width=".8"><rect x="3.5" y="3" width="25" height="7.6" rx="2.4" fill="url(#ic-a)"/><rect x="3.5" y="12.2" width="25" height="7.6" rx="2.4" fill="url(#ic-a)"/><rect x="3.5" y="21.4" width="25" height="7.6" rx="2.4" fill="url(#ic-a)"/></g>
      <g fill="#8dff72" stroke="#1c7a10" stroke-width=".5"><circle cx="8" cy="6.8" r="1.3"/><circle cx="8" cy="16" r="1.3"/><circle cx="8" cy="25.2" r="1.3"/></g>
      <g stroke="#e8f6ff" stroke-width="1.2" stroke-linecap="round" opacity=".85"><path d="M13 6.8h11M13 16h11M13 25.2h11"/></g>
      <path d="M5 4.6h22" stroke="#fff" stroke-opacity=".55" stroke-width="1.2" stroke-linecap="round"/></svg>`,

    surto: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-s", "#e9f7ff", "#4aa6f6", "#0a49b8")}</defs>
      <circle cx="16" cy="16" r="13.5" fill="url(#ic-s)" stroke="#06358f" stroke-width=".9"/>
      <g stroke="#fff" stroke-width="1.4" stroke-linecap="round" opacity=".9"><path d="M10 20.5L16 10M16 10L22.5 20M10 20.5H22.5"/></g>
      <g fill="#fff" stroke="#06358f" stroke-width=".6"><circle cx="10" cy="20.5" r="2.4"/><circle cx="16" cy="10" r="2.4"/></g>
      <circle cx="22.5" cy="20" r="2.9" fill="#ff5a3c" stroke="#7a1305" stroke-width=".6"/>${BRILHO(12, 7.2, 7, 3.6)}</svg>`,

    monitor: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>
        <linearGradient id="ic-m" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a8fff"/><stop offset="1" stop-color="#0a3a9e"/></linearGradient></defs>
      <rect x="3" y="4" width="26" height="18" rx="2.6" fill="#dfe8f5" stroke="#06358f" stroke-width=".9"/>
      <rect x="5" y="6" width="22" height="14" rx="1.4" fill="url(#ic-m)"/>
      <polyline points="6.5,14 11,14 13,9.5 16,18 18.5,12 20,14 25.5,14" fill="none" stroke="#8dff72" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
      <rect x="10" y="24.5" width="12" height="3.2" rx="1.2" fill="#9fb4d4" stroke="#06358f" stroke-width=".7"/><path d="M16 22v2.6" stroke="#06358f" stroke-width="1.4"/>
      <path d="M5 6h22v6C20 11 12 11 5 12z" fill="#fff" opacity=".22"/></svg>`,

    ajuda: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-h", "#e9f7ff", "#4aa6f6", "#0a49b8")}</defs>
      <circle cx="16" cy="16" r="13.5" fill="url(#ic-h)" stroke="#06358f" stroke-width=".9"/>
      <text x="16" y="23.5" text-anchor="middle" font-family="Trebuchet MS, Tahoma, sans-serif" font-weight="700" font-size="21" fill="#fff" stroke="#06358f" stroke-width=".6">?</text>${BRILHO(12, 7, 7.5, 3.6)}</svg>`,

    orbe: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-o", "#eaffdc", "#5fd048", "#1c7a1a")}</defs>
      <circle cx="16" cy="16" r="14" fill="url(#ic-o)" stroke="#145a10" stroke-width=".9"/>
      <g fill="#fff" opacity=".92"><circle cx="12" cy="13.5" r="4"/><circle cx="20.5" cy="12" r="3"/><circle cx="19" cy="20.5" r="4.6"/><circle cx="10.5" cy="21.5" r="2.2"/></g>${BRILHO(13, 7.5, 8, 4)}</svg>`,

    escudo: (cor = "ok") => {
      const [a, b, c] = { ok: ["#d8ffc9", "#4fd13b", "#17790f"], falha: ["#ffd9d2", "#ee5a44", "#8f1a0c"], neutro: ["#eef2f7", "#9aa8bb", "#55637a"] }[cor] || [];
      return `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-e-" + cor, a, b, c)}</defs>
        <path d="M16 2.5 27.5 7v8.5c0 7-5 11.6-11.5 14C9.5 27.100 4.500 22.500 4.500 15.500V7z" fill="url(#ic-e-${cor})" stroke="#0b2a66" stroke-width=".9" stroke-linejoin="round"/>
        ${cor === "falha"
          ? '<path d="M11.500 11.500l9 9m0-9l-9 9" stroke="#fff" stroke-width="2.600" stroke-linecap="round"/>'
          : cor === "ok"
            ? '<path d="M10.500 16.500l4 4 7.500-9" fill="none" stroke="#fff" stroke-width="2.800" stroke-linecap="round" stroke-linejoin="round"/>'
            : '<path d="M16 10v7M16 20.500v1.500" stroke="#fff" stroke-width="2.800" stroke-linecap="round"/>'}
        ${BRILHO(12.500, 8, 6.500, 3.200, 0.4)}</svg>`;
    },

    erro: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-x", "#ffd9d2", "#ee5a44", "#8f1a0c")}</defs>
      <circle cx="16" cy="16" r="13.5" fill="url(#ic-x)" stroke="#6e1308" stroke-width=".9"/>
      <path d="M10.500 10.500l11 11m0-11l-11 11" stroke="#fff" stroke-width="3.200" stroke-linecap="round"/>${BRILHO(12, 7, 7.500, 3.600, 0.4)}</svg>`,

    pergunta: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-q", "#e9f7ff", "#4aa6f6", "#0a49b8")}</defs>
      <circle cx="16" cy="16" r="13.5" fill="url(#ic-q)" stroke="#06358f" stroke-width=".9"/>
      <text x="16" y="23.500" text-anchor="middle" font-family="Trebuchet MS, Tahoma, sans-serif" font-weight="700" font-size="21" fill="#fff" stroke="#06358f" stroke-width=".6">?</text>${BRILHO(12, 7, 7.500, 3.600)}</svg>`,

    info: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-i", "#e9f7ff", "#4aa6f6", "#0a49b8")}</defs>
      <circle cx="16" cy="16" r="13.5" fill="url(#ic-i)" stroke="#06358f" stroke-width=".9"/>
      <circle cx="16" cy="9.500" r="2" fill="#fff"/><path d="M16 14v9" stroke="#fff" stroke-width="3.200" stroke-linecap="round"/>${BRILHO(12, 7, 7.500, 3.600)}</svg>`,

    aviso: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>
        <linearGradient id="ic-w" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff3a0"/><stop offset=".55" stop-color="#f6c515"/><stop offset="1" stop-color="#c98a00"/></linearGradient></defs>
      <path d="M16 3.500 29.500 27.500H2.500z" fill="url(#ic-w)" stroke="#7a5200" stroke-width=".9" stroke-linejoin="round"/>
      <path d="M16 11v8" stroke="#3a2a00" stroke-width="3" stroke-linecap="round"/><circle cx="16" cy="23" r="1.700" fill="#3a2a00"/></svg>`,

    ok: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>${bolaVidro("ic-k", "#eaffdc", "#5fd048", "#1c7a1a")}</defs>
      <circle cx="16" cy="16" r="13.5" fill="url(#ic-k)" stroke="#145a10" stroke-width=".9"/>
      <path d="M9.500 16.500l4.500 4.500 8.500-10" fill="none" stroke="#fff" stroke-width="3.200" stroke-linecap="round" stroke-linejoin="round"/>${BRILHO(12, 7, 7.500, 3.600, 0.4)}</svg>`,

    pixel: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="28" height="28" rx="3" fill="#1a1c2c" stroke="#06358f"/>
      <g shape-rendering="crispEdges"><rect x="6" y="6" width="6" height="6" fill="#a7f070"/><rect x="14" y="6" width="6" height="6" fill="#38b764"/><rect x="22" y="14" width="6" height="6" fill="#ef7d57"/>
        <rect x="6" y="14" width="6" height="6" fill="#41a6f6"/><rect x="14" y="22" width="6" height="6" fill="#ffcd75"/><rect x="6" y="22" width="6" height="6" fill="#b13e53"/></g></svg>`,

    janelas: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><defs>
        <linearGradient id="ic-j" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8ec2ff"/><stop offset="1" stop-color="#1a58d8"/></linearGradient></defs>
      <rect x="3" y="5" width="18" height="14" rx="2" fill="url(#ic-j)" stroke="#06358f"/><rect x="11" y="12" width="18" height="14" rx="2" fill="url(#ic-j)" stroke="#06358f"/>
      <path d="M13 14.500h14" stroke="#fff" stroke-width="2" opacity=".8"/></svg>`,
  };

  let contador = 0;

  /** Cria um elemento SVG novo. `variante` serve ao escudo (ok | falha | neutro). */
  function criar(nome, variante) {
    let fonte = SVGS[nome] || SVGS.info;
    if (typeof fonte === "function") fonte = fonte(variante);
    // Cada instância ganha ids próprios: gradientes repetidos em um SVG escondido (menu fechado) param de funcionar.
    const sufixo = `-${++contador}`;
    fonte = fonte.replace(/id="(ic-[^"]+)"/g, `id="$1${sufixo}"`).replace(/url\(#(ic-[^)]+)\)/g, `url(#$1${sufixo})`);
    const molde = document.createElement("template");
    molde.innerHTML = fonte.trim();                      // texto fixo deste arquivo
    const svg = molde.content.firstElementChild;
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    return svg;
  }

  return { criar };
})();

window.Icones = Icones;
