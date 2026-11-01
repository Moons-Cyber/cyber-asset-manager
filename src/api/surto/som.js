/* Som de videogame de 8 bits, sintetizado no navegador (sem arquivos).
 * O navegador só libera áudio depois de um clique: por isso começa desligado. */
const Som = (() => {
  let ctx = null, mestre = null, ligado = false, ultimoBlip = 0;

  function preparar() {
    if (!ctx) {
      const Contexto = window.AudioContext || window.webkitAudioContext;
      if (!Contexto) return false;
      ctx = new Contexto();
      mestre = ctx.createGain();
      mestre.gain.value = 0.18;
      mestre.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return true;
  }

  /** Toca uma sequência de notas [frequência, duração] com onda quadrada. */
  function notas(lista, tipo = "square", volume = 0.6) {
    if (!ligado || !preparar()) return;
    let t = ctx.currentTime;
    for (const [freq, dur] of lista) {
      const osc = ctx.createOscillator();
      const ganho = ctx.createGain();
      osc.type = tipo;
      osc.frequency.setValueAtTime(freq, t);
      ganho.gain.setValueAtTime(volume, t);
      ganho.gain.exponentialRampToValueAtTime(0.001, t + dur);
      osc.connect(ganho).connect(mestre);
      osc.start(t);
      osc.stop(t + dur);
      t += dur * 0.9;
    }
  }

  return {
    alternar() {
      ligado = !ligado;
      if (ligado) notas([[523, 0.07], [784, 0.1]]);
      return ligado;
    },
    /** Infecção chegando num ativo (no máximo ~10 por segundo). */
    blip() {
      if (!ligado) return;
      const agora = performance.now();
      if (agora - ultimoBlip < 90) return;
      ultimoBlip = agora;
      notas([[300 + Math.random() * 500, 0.04]], "square", 0.25);
    },
    inicio() { notas([[392, 0.06], [523, 0.06], [659, 0.1]]); },
    cura() { notas([[523, 0.06], [659, 0.06], [784, 0.06], [1047, 0.16]], "triangle", 0.8); },
    explosao() { notas([[392, 0.12], [311, 0.12], [262, 0.12], [196, 0.3], [98, 0.4]], "sawtooth", 0.5); },
  };
})();
