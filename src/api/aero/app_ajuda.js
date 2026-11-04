/* Central de Ajuda: a matemática do projeto em linguagem simples. */
const AppAjuda = (() => {
  "use strict";
  const { el, rico } = Nucleo;

  const TOPICOS = [
    { id: "risco", titulo: "1. O risco se espalha", blocos: [
      ["p", "Cada ativo tem um **risco próprio** b (as notas das falhas abertas × o fator de exposição). Se o ativo j alimenta o ativo i com peso A[i][j], uma parte do risco de j chega em i."],
      ["pre", "x = b + A·x        →        (I − A)·x = b"],
      ["p", "O projeto resolve essa equação com `np.linalg.solve`, depois de verificar que I − A é invertível."],
    ] },
    { id: "epidemia", titulo: "2. A mesma conta, como epidemia", blocos: [
      ["p", "Imagine que cada falha é uma infecção. Ela começa no ativo dela e, a cada passo, atravessa cada cano com probabilidade igual ao peso. Cada ativo soma o valor de todas as infecções que passaram por ele."],
      ["pre", "0 saltos:  b\n1 salto:   A·b\n2 saltos:  A²·b\n...\ntotal:     b + A·b + A²·b + ...  =  (I − A)⁻¹·b  =  x"],
      ["p", "Por isso a **média** de muitas epidemias sorteadas (método de Monte Carlo) tem que chegar no mesmo número da álgebra. Na Varredura de Contágio você vê as duas coisas lado a lado."],
    ] },
    { id: "r0", titulo: "3. R0: quando explode", blocos: [
      ["p", "R0 é o **raio espectral** ρ(A): o maior valor absoluto entre os autovalores de A."],
      ["ul", ["**ρ(A) < 1**: a série termina, o surto morre sozinho e x existe.", "**ρ(A) ≥ 1**: a série não termina, o surto explode e o risco não tem valor finito."]],
      ["p", "A regra do cadastro (a soma dos pesos que **chegam** em cada ativo precisa ser menor que 1) garante ρ(A) < 1. Ela é segura, mas exigente: use o controle **Pesos** na Varredura e veja a regra recusar antes de o R0 chegar a 1."],
    ] },
    { id: "defesa", titulo: "4. Defesa: o que corrigir", blocos: [
      ["p", "O **multiplicador** de um ativo é a soma da coluna dele em (I − A)⁻¹: quanto 1 ponto de risco ali vira de risco na rede toda. Corrigir uma falha de nota s no ativo i derruba o risco global em"],
      ["pre", "queda = fator_i × s × multiplicador_i"],
      ["p", "Os testes do projeto conferem essa previsão contra o recálculo completo, falha por falha."],
    ] },
    { id: "horas", titulo: "5. As 24 horas", blocos: [
      ["p", "Com o container no ar, o servidor roda um surto a cada hora e anota o resultado no diário (`diario_surto.json`, dentro do volume do Docker). O Monitor do Serviço mostra uma marca por hora: é a prova de que o serviço ficou no ar e de que o sorteio concordou com a álgebra."],
    ] },
    { id: "dicas", titulo: "Dicas da interface", blocos: [
      ["ul", [
        "Arraste as janelas pela barra azul; clique duas vezes nela para maximizar.",
        "Na Varredura, **Espaço** inicia e pausa o surto.",
        "No Gerenciador de Ativos, **Enter** edita, **Delete** exclui e as setas trocam a seleção.",
        "O escudo na bandeja mostra se o serviço está no ar; clique nele para abrir o Monitor.",
        "O menu iniciar tem o link para voltar ao tema Pixel Art.",
      ]],
    ] },
  ];

  function bloco([tipo, conteudo]) {
    if (tipo === "pre") return el("pre", {}, conteudo);
    if (tipo === "ul") return el("ul", {}, conteudo.map((t) => el("li", {}, rico(t))));
    return el("p", {}, rico(conteudo));
  }

  function abrir() {
    if (Janelas.aberta("ajuda")) { Janelas.focar("ajuda"); return; }
    const artigo = el("article", { tabindex: "0" });
    const botoes = TOPICOS.map((t) => el("button", { type: "button", on: { click: () => mostrar(t.id) } }, t.titulo));
    function mostrar(id) {
      const t = TOPICOS.find((x) => x.id === id);
      botoes.forEach((b, i) => b.setAttribute("aria-current", String(TOPICOS[i].id === id)));
      artigo.replaceChildren(el("h3", {}, t.titulo), ...t.blocos.map(bloco));
      artigo.scrollTop = 0;
    }
    const raiz = el("div", { class: "ajuda" }, el("nav", { "aria-label": "Tópicos" }, botoes), artigo);
    Janelas.abrir({ id: "ajuda", titulo: "Central de Ajuda", icone: "ajuda", largura: 720, altura: 480, conteudo: raiz });
    mostrar(TOPICOS[0].id);
  }

  return { abrir };
})();

window.AppAjuda = AppAjuda;
