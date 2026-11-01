/* A epidemia, sorteada no navegador (a mesma regra do contagio.py).
 *
 * Uma RODADA: cada ativo i com risco próprio b_i > 0 começa com uma infecção
 * de valor b_i. Uma infecção no ativo j atravessa a seta j -> i com
 * probabilidade A[i][j] (o peso). Cada ativo soma o valor de toda infecção
 * que passa por ele. A média de muitas rodadas tende a x = (I - A)^-1 b.
 */
class Epidemia {
  constructor(A, b, { limitePorRodada = 20000 } = {}) {
    this.A = A;
    this.b = b;
    this.n = b.length;
    this.limite = limitePorRodada;
    // Lista de setas de cada ativo: saidas[j] = [[i, peso], ...]
    this.saidas = Array.from({ length: this.n }, () => []);
    for (let i = 0; i < this.n; i++) {
      for (let j = 0; j < this.n; j++) {
        if (A[i][j] > 0) this.saidas[j].push([i, A[i][j]]);
      }
    }
    this.zerar();
  }

  zerar() {
    this.rodadas = 0;
    this.soma = new Array(this.n).fill(0);     // valor acumulado em cada ativo
    this.curva = [];                           // [rodadas, global estimado]
    this.explodiu = false;
    this.infeccoes = 0;
  }

  /** Quantas cópias passam pela seta: parte inteira certa + sorteio do resto. */
  static copias(peso) {
    const inteiro = Math.floor(peso);
    return inteiro + (Math.random() < peso - inteiro ? 1 : 0);
  }

  /**
   * Roda UMA epidemia. Devolve os saltos [{de, para, geracao, origem}]
   * para a tela animar (só uma amostra é desenhada).
   */
  rodada() {
    if (this.explodiu) return [];
    const saltos = [];
    let total = 0;
    // fila de infecções: [ativo atual, origem, geração]
    let atuais = [];
    for (let j = 0; j < this.n; j++) if (this.b[j] > 0) atuais.push([j, j, 0]);

    while (atuais.length) {
      const novas = [];
      for (const [k, origem, g] of atuais) {
        this.soma[k] += this.b[origem];
        total++;
        for (const [i, peso] of this.saidas[k]) {
          const quantas = Epidemia.copias(peso);
          for (let q = 0; q < quantas; q++) {
            novas.push([i, origem, g + 1]);
            if (saltos.length < 400) saltos.push({ de: k, para: i, geracao: g, origem });
          }
        }
      }
      // Segurança: com R0 >= 1 a epidemia não para; com R0 quase 1 fica enorme.
      if (total + novas.length > this.limite) {
        this.explodiu = true;
        break;
      }
      atuais = novas;
    }

    this.infeccoes += total;
    this.rodadas++;
    if (this.rodadas <= 50 || this.rodadas % Math.ceil(this.rodadas / 200) === 0) {
      this.curva.push([this.rodadas, this.global()]);
    }
    return saltos;
  }

  estimativa() {
    return this.soma.map((v) => (this.rodadas ? v / this.rodadas : 0));
  }

  global() {
    return this.rodadas ? this.soma.reduce((s, v) => s + v, 0) / this.rodadas : 0;
  }
}
