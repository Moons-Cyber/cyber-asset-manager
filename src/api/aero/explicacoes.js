/* O que o Assistente diz: as explicações do cálculo, com os números reais
 * vindos de /api/risco/passos, e o guia do código.
 *
 * Cada passo tem uma caixa "No código" com { arquivo, funcao, trecho }.
 * O teste testes/test_aero.py confere que cada trecho existe mesmo naquele
 * arquivo, dentro do projeto: se o código mudar, o teste avisa que a
 * explicação ficou desatualizada.
 */
const Explicacoes = (() => {
  "use strict";
  const { el, num, rico, pilula } = Nucleo;

  const MAX = 8;                                  // tabelas maiores que isso são cortadas
  const curto = (t, n = 14) => (t.length > n ? t.slice(0, n - 1) + "…" : t);
  const p = (texto) => el("p", {}, rico(texto));

  // ---------------------------------------------------------- tabelas
  function matriz(valores, linhas, colunas, { casas = 2, destacar = (v) => v !== 0, legenda } = {}) {
    const nl = Math.min(linhas.length, MAX), nc = Math.min(colunas.length, MAX);
    const tabela = el("table", { class: "matriz" },
      legenda ? el("caption", {}, legenda) : null,
      el("thead", {}, el("tr", {}, el("th", {}, ""), colunas.slice(0, nc).map((c) => el("th", { scope: "col", title: c }, curto(c, 10))))),
      el("tbody", {}, valores.slice(0, nl).map((linha, i) => el("tr", {},
        el("th", { scope: "row", title: linhas[i] }, curto(linhas[i])),
        linha.slice(0, nc).map((v) => el("td", { class: destacar(v) ? "forte" : "fraco" }, Number.isInteger(v) && casas === 0 ? String(v) : num(v, casas)))))));
    const cortou = linhas.length > MAX || colunas.length > MAX;
    return el("div", { class: "rolagem-matriz" }, tabela,
      cortou ? el("p", { class: "dica" }, `Mostrando só as ${MAX} primeiras linhas e colunas.`) : null);
  }

  /** Lista "nome: conta = resultado", uma linha por ativo. */
  function contas(itens) {
    return el("ul", { class: "contas" }, itens.slice(0, 12).map(([nome, conta, resultado]) =>
      el("li", {}, el("span", { class: "quem" }, nome), el("span", { class: "conta" }, conta), el("b", {}, resultado))));
  }

  const nomes = (d) => d.ativos.map((a) => a.nome);
  const abertas = (d) => d.vulnerabilidades.length;
  const deps = (d) => d.A.reduce((s, linha) => s + linha.filter((v) => v > 0).length, 0);

  // ===================================================== passo a passo
  function calculo(d) {
    if (!d.ativos.length) {
      return [{
        titulo: "Ainda não há o que calcular",
        corpo: [p("Não há ativos cadastrados. Abra o **Gerenciador de Ativos**, cadastre alguns, registre as falhas deles e volte aqui: eu refaço a conta com os seus dados.")],
        codigo: [],
      }];
    }
    const n = d.ativos.length;
    const passos = [];

    passos.push({
      titulo: "Assistente do Cálculo de Risco",
      corpo: [
        p(`Vamos refazer, passo a passo, a conta que o sistema faz para descobrir o risco de cada ativo, com os dados cadastrados **agora**: ${n} ativo(s), ${abertas(d)} falha(s) aberta(s) e ${deps(d)} dependência(s).`),
        el("ol", { class: "roteiro" },
          el("li", {}, "As falhas de cada ativo viram números."),
          el("li", {}, "Cada tipo de ativo tem um peso (fator de exposição)."),
          el("li", {}, "O risco passa de um ativo para outro pelas dependências."),
          el("li", {}, "Uma equação, (I − A)x = b, calcula tudo de uma vez."),
          el("li", {}, "Antes de resolver, o sistema confere se a equação tem resposta.")),
        p("Embaixo de cada passo, a caixa **No código** mostra onde aquilo acontece no projeto."),
      ],
      codigo: [],
    });

    // 1. M e v
    const colunas = d.vulnerabilidades.map((v) => v.id);
    passos.push({
      titulo: "1. Quais falhas cada ativo tem (M e v)",
      corpo: d.vulnerabilidades.length ? [
        p("Montamos uma tabela **M**: uma linha por ativo e uma coluna por falha aberta. Vale **1** quando o ativo tem a falha e **0** quando não tem."),
        matriz(d.M, nomes(d), colunas, { casas: 0, legenda: "M (ativos × falhas)" }),
        p("O vetor **v** guarda a nota de cada falha, de 0 a 10, na mesma ordem das colunas:"),
        matriz([d.v], ["v (nota)"], colunas, { casas: 1, destacar: () => true }),
        p("Falhas com status **Corrigida** ficam fora da tabela: elas não contam mais no risco."),
      ] : [
        p("Nenhum ativo tem falha aberta agora, então a tabela **M** fica vazia e todos os riscos dão zero. Registre uma falha no Gerenciador de Ativos para ver a conta ganhar vida."),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "construir_matriz_incidencia", trecho: "if not vulnerabilidade.afeta_risco:", texto: "Pula as falhas corrigidas." },
        { arquivo: "src/servicos/analise_risco.py", funcao: "construir_matriz_incidencia", trecho: "matriz[indice_ativo][indice_coluna] = 1", texto: "Marca com 1 a falha que o ativo tem." },
      ],
    });

    // 2. M v
    passos.push({
      titulo: "2. Somando as notas (M · v)",
      corpo: [
        p("Multiplicar **M** por **v** soma, em cada linha, as notas das falhas que aquele ativo tem:"),
        contas(d.ativos.map((a, i) => {
          const notas = d.M[i].map((m, j) => (m ? d.v[j] : null)).filter((x) => x !== null);
          return [a.nome, notas.length ? notas.map((x) => num(x, 1)).join(" + ") + " =" : "nenhuma falha =", num(d.Mv[i])];
        })),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "multiplicar_matriz_vetor", trecho: "return (m @ v).tolist()", texto: "Em NumPy, @ é o produto de matrizes. O * multiplicaria elemento a elemento, que é outra conta." },
      ],
    });

    // 3. b = F M v
    passos.push({
      titulo: "3. O peso do tipo de ativo (b = F · Mv)",
      corpo: [
        p("Cada tipo de ativo fica mais ou menos exposto na rede. O fator de exposição é **1,5** para Servidor, **1,2** para Roteador e **1,0** para Notebook e Banco de dados."),
        p("Multiplicando a soma das notas pelo fator, chegamos ao **risco próprio b**: o risco do ativo sozinho, sem contar a rede."),
        contas(d.ativos.map((a, i) => [a.nome, `${num(a.fator, 1)} × ${num(d.Mv[i])} =`, num(d.b[i])])),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "construir_matriz_exposicao", trecho: "return np.diag([ativo.obter_fator_exposicao() for ativo in ativos])", texto: "F é uma matriz diagonal com os fatores. Cada objeto informa o próprio fator: isso é polimorfismo." },
        { arquivo: "src/modelos/servidor.py", funcao: "obter_fator_exposicao", trecho: "return 1.5", texto: "A classe Servidor define o fator dela; Notebook, Roteador e BancoDeDados fazem o mesmo." },
      ],
    });

    // 4. A
    const recebe = d.somas_recebidas;
    passos.push({
      titulo: "4. Quem passa risco para quem (A)",
      corpo: deps(d) ? [
        p("Uma dependência diz que parte do risco de um ativo chega em outro. A matriz **A** guarda isso: **A[linha][coluna]** é quanto do risco da coluna chega na linha. A linha é quem **recebe**; a coluna é quem **passa**."),
        matriz(d.A, nomes(d), nomes(d), { legenda: "A (linha recebe de coluna)" }),
        p("Somando cada linha, vemos quanto cada ativo recebe no total:"),
        contas(d.ativos.map((a, i) => [a.nome, "recebe", `${num(recebe[i])} ${recebe[i] < 1 ? "✓ menor que 1" : "✗"}`])),
        p("Essa soma precisa ficar **abaixo de 1** em todos os ativos. O cadastro recusa uma dependência que quebre a regra, e é ela que garante, no passo 6, que a conta tenha resposta."),
      ] : [
        p("Ainda não há dependências: a matriz **A** é toda de zeros. Então ninguém recebe risco de ninguém e o risco efetivo de cada ativo vai ser igual ao próprio."),
        p("Crie uma dependência na aba **Dependências** do Gerenciador de Ativos para ver o risco passar de um ativo para outro."),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "construir_matriz_dependencias", trecho: "matriz[indice_destino][indice_origem] = float(peso)", texto: "Linha = destino (quem recebe); coluna = origem (quem passa)." },
        { arquivo: "src/modelos/dependencia.py", funcao: "soma_de_pesos_valida", trecho: "return soma < LIMITE_SOMA_PESOS", texto: "A regra do projeto: o que um ativo recebe soma menos que 1." },
      ],
    });

    // 5. (I - A) x = b
    const iEx = d.ativos.findIndex((_, i) => d.A[i].some((v) => v > 0));
    const exemplo = iEx >= 0
      ? `x(${d.ativos[iEx].nome}) = ${num(d.b[iEx])} + ` + d.A[iEx].map((v, j) => (v > 0 ? `${num(v)} × x(${d.ativos[j].nome})` : null)).filter(Boolean).join(" + ")
      : null;
    passos.push({
      titulo: "5. A equação (I − A) x = b",
      corpo: [
        p("O **risco efetivo x** de um ativo é o risco próprio dele **mais** o que chega pelas dependências:"),
        el("pre", { class: "formula" }, "x = b + A · x"),
        exemplo ? p("Por exemplo, com os seus dados:") : null,
        exemplo ? el("pre", { class: "formula" }, exemplo) : null,
        p("O **x** aparece dos dois lados porque o risco que chega do vizinho já inclui o que o vizinho recebeu dos vizinhos dele. Passando **A · x** para o outro lado:"),
        el("pre", { class: "formula" }, "x − A · x = b     →     (I − A) · x = b"),
        p("**I** é a matriz identidade (1 na diagonal e 0 no resto). Esta é a matriz **I − A** da sua rede:"),
        matriz(d.I_menos_A, nomes(d), nomes(d), { destacar: (v) => v !== 0, legenda: "I − A" }),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "_montar_sistema", trecho: "sistema = np.eye(len(ativos)) - np.asarray(matriz_dependencias, dtype=float)", texto: "np.eye(n) cria a identidade I de tamanho n." },
      ],
    });

    // 6. invertibilidade
    passos.push(passoInvertibilidade(d));

    // 7. solve
    passos.push({
      titulo: "7. Resolvendo o sistema",
      corpo: d.x ? [
        p("Com **I − A** invertível, o NumPy resolve o sistema com `np.linalg.solve`. Ele não calcula a inversa, porque isso seria mais lento e menos preciso."),
        el("div", { class: "rolagem-matriz" }, el("table", { class: "matriz resultado" },
          el("thead", {}, el("tr", {}, ["Ativo", "Próprio (b)", "Veio da rede", "Efetivo (x)"].map((t) => el("th", { scope: "col" }, t)))),
          el("tbody", {}, d.ativos.slice(0, 12).map((a, i) => el("tr", {},
            el("th", { scope: "row" }, a.nome), el("td", {}, num(d.b[i])), el("td", {}, `+ ${num(d.x[i] - d.b[i])}`), el("td", {}, pilula(d.x[i]))))))),
        p(`**Conferência:** o sistema põe o x de volta na equação e compara (I − A)·x com b. A maior diferença foi **${d.residuo < 1e-12 ? "praticamente zero" : d.residuo.toExponential(1).replace(".", ",")}**, dentro da tolerância de 10⁻⁹. Comparar com == seria um erro, porque números com vírgula no computador quase nunca batem exatamente.`),
      ] : [
        p("Como **I − A** não é invertível, não existe um único x. O sistema para com uma mensagem de erro em vez de mostrar um número errado."),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "calcular_risco_efetivo", trecho: "riscos_efetivos = np.linalg.solve(", texto: "Resolve (I − A)x = b." },
        { arquivo: "src/servicos/analise_risco.py", funcao: "calcular_risco_efetivo", trecho: "if not np.allclose(", texto: "Confere a resposta com tolerância." },
      ],
    });

    // fim
    if (d.x) {
      const iMax = d.x.indexOf(Math.max(...d.x));
      passos.push({
        titulo: "Pronto!",
        corpo: [
          el("div", { class: "global" }, el("span", {}, "Risco global da rede (soma de todos os x)"), el("strong", {}, num(d.risco_global))),
          p(`O ativo com maior risco efetivo é **${d.ativos[iMax].nome}**, com ${num(d.x[iMax])}. Corrigir as falhas dele, ou de quem passa risco para ele, é o que mais derruba esse número.`),
          p("**Dica:** no **Mapa da Rede**, clique numa esfera e use **Por que esse valor?** para ver a conta de um ativo só."),
        ],
        codigo: [
          { arquivo: "src/api/aplicacao.py", funcao: "analisar_risco", trecho: "resultados = calcular_risco_efetivo(ativos, dependencias)", texto: "A rota GET /api/risco chama o cálculo; o Mapa usa essa resposta para colorir as esferas." },
        ],
      });
    }
    return passos;
  }

  function passoInvertibilidade(d) {
    const g = d.diagnostico;
    const k = g.condicao;
    const leitura = k === null || k === undefined ? "infinito: a matriz é singular"
      : k < 10 ? "muito bom (perto de 1)" : k < 1e8 ? "aceitável" : "alto: o resultado perde precisão";
    return {
      titulo: "6. Antes de resolver: I − A é invertível?",
      corpo: [
        p("Uma equação **(I − A)x = b** só tem **uma única** resposta se a matriz **I − A** for **invertível**. O sistema confere isso antes de resolver:"),
        el("dl", { class: "diagnostico" },
          el("dt", {}, "Posto"), el("dd", {}, `${g.posto} de ${g.ordem}`),
          el("dd", { class: "explica" }, "Precisa ser igual ao número de ativos: nenhuma linha pode ser combinação das outras."),
          el("dt", {}, "Número de condição κ"), el("dd", {}, k === null || k === undefined ? "infinito" : num(k)),
          el("dd", { class: "explica" }, `Mede quanto um erro pequeno nos dados aumenta no resultado. O seu é ${leitura}.`),
          el("dt", {}, "Determinante"), el("dd", {}, num(g.determinante, 4)),
          el("dd", { class: "explica" }, "Diferente de zero. É só informativo: sozinho ele não decide, porque o tamanho dele muda com o número de ativos.")),
        el("div", { class: `veredicto ${g.invertivel ? "ok" : "falha"}` },
          Icones.criar(g.invertivel ? "ok" : "erro"),
          el("span", {}, g.invertivel
            ? "I − A é invertível: a equação tem uma única resposta."
            : "I − A não é invertível: o sistema para aqui com um erro, em vez de mostrar um número errado.")),
        p("Por que a regra do passo 4 garante isso? Se cada ativo recebe menos de 1, a diagonal de **I − A** (sempre 1) é maior que a soma do resto da linha. Uma matriz assim é sempre invertível."),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "_diagnosticar", trecho: "posto = int(np.linalg.matrix_rank(sistema))", texto: "Calcula o posto." },
        { arquivo: "src/servicos/analise_risco.py", funcao: "_diagnosticar", trecho: "condicao = float(np.linalg.cond(sistema))", texto: "Calcula o número de condição." },
        { arquivo: "src/servicos/analise_risco.py", funcao: "_diagnosticar", trecho: "\"invertivel\": bool(posto == n and condicao < LIMITE_CONDICAO_SINGULAR),", texto: "A decisão: posto cheio e condição finita." },
      ],
    };
  }

  /** Índice do passo da invertibilidade dentro de calculo(d), para abrir direto nele. */
  const PASSO_INVERTIBILIDADE = 6;

  // ================================================= um ativo só
  function ativo(d, id) {
    const i = d.ativos.findIndex((a) => a.id === id);
    if (i < 0) return [{ titulo: "Ativo não encontrado", corpo: [p("Esse ativo não existe mais. Ele pode ter sido excluído em outra janela.")], codigo: [] }];
    const a = d.ativos[i];
    const notas = d.M[i].map((m, j) => (m ? d.vulnerabilidades[j] : null)).filter(Boolean);
    const entradas = d.A[i].map((peso, j) => [peso, j]).filter(([peso]) => peso > 0);
    const saidas = d.ativos.map((_, k) => [d.A[k][i], k]).filter(([peso]) => peso > 0);

    const passos = [{
      titulo: `Risco próprio de ${a.nome}`,
      corpo: [
        p(`O risco próprio (**b**) vem só das falhas abertas do ativo e do tipo dele (${a.tipo}, fator **${num(a.fator, 1)}**).`),
        notas.length
          ? contas(notas.map((v) => [v.id, v.descricao ? curto(v.descricao, 34) : v.categoria, `nota ${num(v.severidade, 1)}`]))
          : p("Ele não tem falha aberta, então o risco próprio é **zero**."),
        el("pre", { class: "formula" }, `b = ${num(a.fator, 1)} × (${notas.length ? notas.map((v) => num(v.severidade, 1)).join(" + ") : "0"}) = ${num(d.b[i])}`),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "_montar_sistema", trecho: "construir_matriz_exposicao(ativos) @ np.asarray(soma_das_notas, dtype=float)", texto: "b = F · (M v): fator × soma das notas." },
      ],
    }, {
      titulo: "O que chega pelas dependências",
      corpo: entradas.length ? [
        p(`${a.nome} recebe uma parte do risco **efetivo** de ${entradas.length} ativo(s):`),
        contas(entradas.map(([peso, j]) => [d.ativos[j].nome, `${num(peso)} × ${d.x ? num(d.x[j]) : "x"} =`, d.x ? num(peso * d.x[j]) : "--"])),
        d.x ? p(`No total, chegam **${num(d.x[i] - d.b[i])}** pela rede.`) : null,
      ] : [
        p(`Nenhum ativo passa risco para ${a.nome}. Então o risco efetivo dele é igual ao próprio.`),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "construir_matriz_dependencias", trecho: "matriz[indice_destino][indice_origem] = float(peso)", texto: "Cada dependência vira um número na linha de quem recebe." },
      ],
    }, {
      titulo: `Risco efetivo de ${a.nome}`,
      corpo: d.x ? [
        el("pre", { class: "formula" }, `x = ${num(d.b[i])} + ${num(d.x[i] - d.b[i])} = ${num(d.x[i])}`),
        el("p", {}, "Resultado: ", pilula(d.x[i])),
        entradas.length
          ? p("Repare que o x de cada vizinho **já inclui** o que ele recebeu dos vizinhos dele. É por isso que o sistema resolve todos de uma vez com **(I − A)x = b**, em vez de ativo por ativo.")
          : null,
        saidas.length
          ? p(`${a.nome} também passa risco para: ${saidas.map(([peso, k]) => `${d.ativos[k].nome} (${num(peso)})`).join(", ")}. Corrigir falhas aqui ajuda esses ativos também.`)
          : null,
      ] : [
        p("Com os dados atuais, **I − A** não é invertível e o sistema não calcula o risco efetivo. Use **Como o risco é calculado?** para ver o diagnóstico."),
      ],
      codigo: [
        { arquivo: "src/servicos/analise_risco.py", funcao: "calcular_risco_efetivo", trecho: "riscos_efetivos = np.linalg.solve(", texto: "Resolve todos os ativos juntos." },
      ],
    }];
    return passos;
  }

  // ================================================= como usar
  const COMO_USAR = [
    ["Cadastrar um ativo", "Abra o **Gerenciador de Ativos** e clique em **+ Novo ativo**. Escolha o tipo, preencha os campos e clique em **Cadastrar**."],
    ["Registrar uma falha", "No Gerenciador, clique no ativo. No painel de baixo, preencha a categoria, a nota (0 a 10) e a descrição, e clique em **Adicionar falha**."],
    ["Marcar uma falha como corrigida", "Na tabela de falhas do ativo, troque o **Status** para **Corrigida**. Ela sai do cálculo na hora."],
    ["Ligar dois ativos", "Na aba **Dependências**, escolha a origem (quem passa o risco), o destino (quem recebe) e o peso (de 0 até menos de 1)."],
    ["Editar ou excluir", "Selecione o ativo na lista e use **Editar** ou **Excluir**. Atalhos: **Enter** edita, **Delete** exclui, as setas trocam a seleção."],
    ["Entender uma falha", "No Gerenciador, clique em **Explicar** ao lado da falha (ou pergunte à Gota). O Assistente de Segurança diz o que ela é, por que é perigosa, como prevenir e o que fazer agora."],
    ["Ver o risco", "O **Mapa da Rede** mostra cada ativo com a cor do risco efetivo. Clique numa esfera para ver de onde vem o risco."],
    ["Saber se o serviço está no ar", "O escudo na bandeja fica verde quando a API responde. Clique nele para abrir o **Monitor do Serviço** e o diário das 24 horas."],
    ["Mexer nas janelas", "Arraste pela barra azul, redimensione pelo canto, e clique duas vezes no título para maximizar."],
  ];

  // ================================================= mapa do código
  const CODIGO = [
    { grupo: "Modelos (as classes)", itens: [
      ["src/modelos/ativo.py", "Classe abstrata **Ativo**: os campos comuns e os métodos que toda subclasse precisa ter (`@abstractmethod`)."],
      ["src/modelos/servidor.py (e notebook, roteador, banco_dados)", "As subclasses. Cada uma tem o seu campo próprio e o seu **fator de exposição** (herança e polimorfismo)."],
      ["src/modelos/vulnerabilidades.py", "Classe **Vulnerabilidade**: nota, categoria, status. `afeta_risco` diz se ela ainda conta."],
      ["src/modelos/dependencia.py", "Classe **Dependencia** e a regra de que a soma dos pesos recebidos fica abaixo de 1."],
      ["src/modelos/registro_tipos.py", "Tabela única que liga cada tipo de ativo à sua classe."],
    ] },
    { grupo: "Persistência (o JSON)", itens: [
      ["src/persistencia/persistencia.py", "Lê e grava o JSON. A gravação é **atômica**: escreve num arquivo temporário e só depois troca, para nunca deixar o arquivo pela metade."],
      ["src/persistencia/fabrica_ativos.py", "Padrão **Factory**: transforma cada registro do JSON no objeto da subclasse certa, pelo campo `tipo`."],
      ["src/persistencia/repositorio.py", "Padrão **Repository**: o resto do sistema só pede listar e salvar, sem saber que é um arquivo."],
    ] },
    { grupo: "Serviços (as regras)", itens: [
      ["src/servicos/gerenciador_ativos.py", "Cadastrar, buscar, editar e remover ativos; impede ID repetido; grava a cada mudança."],
      ["src/servicos/gerenciador_dependencias.py", "Cadastra dependências e recusa as que quebram a regra dos pesos."],
      ["src/servicos/analise_risco.py", "**A matemática**: monta M, v, F, A e resolve (I − A)x = b com a verificação de invertibilidade."],
      ["src/servicos/ordenacao.py", "Padrão **Strategy**: os critérios de ordenação da lista, como funções."],
      ["src/servicos/orientacao_seguranca.py", "O que é cada tipo de falha e como prevenir. Reconhece o tipo por palavras-chave e calcula quanto o risco cai ao corrigir."],
      ["src/servicos/diario.py", "O diário das 24 horas: calcula o risco a cada hora e anota."],
      ["src/servicos/cliente_nvd.py", "Busca a nota de um CVE no NVD (com cache) quando há internet."],
    ] },
    { grupo: "API e Docker", itens: [
      ["src/api/aplicacao.py", "As rotas REST em Flask (GET, POST, PATCH, DELETE), os erros em JSON e a trava contra gravações simultâneas."],
      ["servidor.py", "Ponto de entrada: lê as variáveis de ambiente e cria a aplicação."],
      ["Dockerfile", "Como a imagem é montada: Python, dependências, gunicorn e o HEALTHCHECK que chama /api/saude."],
      ["docker-compose.yml", "Sobe o container com volume para os dados e `restart: unless-stopped` para voltar sozinho."],
      ["src/api/aero/", "Esta interface (HTML, CSS e JavaScript). Ela só conversa com a API REST."],
    ] },
  ];

  // ================================================= uma falha
  /** Passos do Assistente de Segurança, a partir de /api/ativos/<id>/vulnerabilidades/<vid>/orientacao. */
  function falha(o, { mudarStatus }) {
    const v = o.vulnerabilidade, e = o.efeito_no_risco;
    const lista = (itens) => el("ol", { class: "roteiro" }, itens.map((t) => el("li", {}, rico(t))));
    const ehCve = /^CVE-/.test(v.id);
    const reconhecida = o.tipo !== "generica";

    const status = (rotulo, novo, primario) => el("button", {
      type: "button", class: `botao${primario ? " gel" : ""}`, on: { click: () => mudarStatus(novo) },
    }, rotulo);
    const botoes = [];
    if (v.status !== "Em tratamento" && v.status !== "Corrigida") botoes.push(status("Marcar como Em tratamento", "Em tratamento"));
    if (v.status !== "Corrigida") botoes.push(status("Marcar como Corrigida", "Corrigida", true));
    else botoes.push(status("Reabrir a falha", "Aberta"));

    return [{
      titulo: reconhecida ? o.titulo : "Uma falha que não reconheci",
      corpo: [
        el("div", { class: "ficha-falha" },
          el("div", {}, el("b", {}, v.descricao_curta || v.descricao), el("small", {}, `${v.id} · categoria: ${v.categoria} · ${o.ativo.nome} (${o.ativo.tipo})`)),
          pilula(v.severidade, 1)),
        p(o.o_que_e),
        reconhecida
          ? p(`Reconheci o tipo pela **${o.reconhecido_por}** (o termo “${o.termo}”). Referência: **${o.cwe}**, no catálogo público de tipos de fraqueza de software (CWE, mantido pelo MITRE).`)
          : p("Para eu explicar melhor, edite a falha com uma categoria mais clara (por exemplo, “Injeção SQL”, “Senha padrão”, “Sistema desatualizado”) ou cadastre-a com o CVE."),
        ehCve ? p(`**${v.id}** é o identificador público desta falha. A nota ${num(v.severidade, 1)} veio do NVD, a base oficial de vulnerabilidades dos EUA.`) : null,
      ],
      codigo: [
        { arquivo: "src/servicos/orientacao_seguranca.py", funcao: "reconhecer", trecho: "termo = orientacao.encontrar(texto)", texto: "Procura as palavras-chave de cada tipo, primeiro na categoria, depois na descrição e no texto do NVD." },
        { arquivo: "src/servicos/orientacao_seguranca.py", funcao: "normalizar", trecho: "return \"\".join(c for c in sem_acento if not unicodedata.combining(c)).lower()", texto: "Tira acentos e maiúsculas, para “Injeção” e “injecao” serem a mesma coisa." },
      ],
    }, {
      titulo: "Por que é perigosa",
      corpo: [
        p(o.por_que_perigoso),
        o.neste_ativo ? el("div", { class: "dica-ativo" }, el("b", {}, `Neste ${o.ativo.tipo.toLowerCase()}: `), o.neste_ativo) : null,
        el("dl", { class: "diagnostico" },
          el("dt", {}, "Gravidade"), el("dd", {}, v.classificacao),
          el("dd", { class: "explica" }, o.gravidade),
          el("dt", {}, "Situação"), el("dd", {}, v.status),
          el("dd", { class: "explica" }, o.situacao)),
        e && e.conta_no_risco && e.reducao > 0
          ? p(`**No risco:** corrigir esta falha tira ${num(e.fator, 1)} × ${num(v.severidade, 1)} = **${num(e.reducao)}** do risco próprio de ${o.ativo.nome}, que vai de ${num(e.risco_proprio_atual)} para **${num(e.risco_proprio_sem_ela)}**.`
            + (e.passa_risco_para.length ? ` Isso também diminui o risco que ele passa para: ${e.passa_risco_para.join(", ")}.` : ""))
          : null,
      ],
      codigo: [
        { arquivo: "src/servicos/orientacao_seguranca.py", funcao: "efeito_no_risco", trecho: "reducao = fator * vulnerabilidade.severidade", texto: "A falha sai da soma das notas, então o risco próprio cai fator × nota." },
        { arquivo: "src/modelos/vulnerabilidades.py", funcao: "classificacao", trecho: "return Severidade.a_partir_da_nota(self.severidade)", texto: "A gravidade (Baixa, Média, Alta, Crítica) vem da nota, pelas faixas do CVSS." },
      ],
    }, {
      titulo: "Como prevenir",
      corpo: [
        p("Para que esta falha, ou outra do mesmo tipo, não apareça:"),
        lista(o.como_prevenir),
      ],
      codigo: [],
    }, {
      titulo: "O que fazer agora",
      corpo: [
        lista(o.como_corrigir_agora),
        p(`**Situação no inventário:** ${v.status}. Marque como **Corrigida** só depois de aplicar a correção de verdade: aí ela sai do cálculo do risco.`),
        el("div", { class: "acoes" }, botoes),
        p(ehCve
          ? `Estas orientações são gerais para o tipo de falha. A correção exata de ${v.id} (versão a instalar, configuração a mudar) está no boletim do fornecedor e na página do CVE no NVD.`
          : "Estas orientações são gerais para o tipo de falha. Para a correção exata, procure o boletim do fornecedor do produto afetado."),
      ],
      codigo: [
        { arquivo: "src/modelos/vulnerabilidades.py", funcao: "afeta_risco", trecho: "return self.status != StatusVulnerabilidade.CORRIGIDA", texto: "Só o status Corrigida tira a falha do cálculo; Em tratamento e Risco aceito continuam contando." },
        { arquivo: "src/api/aplicacao.py", funcao: "atualizar_vulnerabilidade", trecho: "gerenciador.atualizar_status_vulnerabilidade(", texto: "Os botões acima chamam PATCH /api/ativos/<id>/vulnerabilidades/<falha>, que grava o novo status." },
      ],
    }];
  }

  return { calculo, ativo, falha, PASSO_INVERTIBILIDADE, COMO_USAR, CODIGO };
})();

window.Explicacoes = Explicacoes;
