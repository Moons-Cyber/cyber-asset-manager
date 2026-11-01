/* Tela "Ativos": o CRUD do sistema.
 *
 * É a parte de trabalho do sistema, feita para ler. Tudo é
 * montado com createElement + textContent (nunca innerHTML com dados do
 * servidor), então um nome com <tags> aparece como texto e não executa nada.
 *
 * Fala com a mesma API do resto do projeto:
 *   GET/POST /api/ativos          PATCH/DELETE /api/ativos/<id>
 *   POST /api/ativos/<id>/vulnerabilidades   PATCH .../<vid> {status}
 *   GET/POST /api/dependencias    DELETE /api/dependencias/<origem>/<destino>
 */
const Ativos = (() => {
  const $ = (id) => document.getElementById(id);
  const raiz = () => $("tela-ativos");

  const s = {
    aba: "ativos",            // "ativos" | "dependencias"
    tipos: [], status: [],
    busca: "", filtroTipo: "",
    aberto: null,             // id do ativo com a lista de falhas aberta
    form: null,               // {modo:"novo"|"editar", ativo}
    confirma: null,           // {texto, acao}
    mensagem: null,           // {texto, bom}
    ocupado: false,
    base: { ativos: [], deps: [], risco: new Map() },
  };

  // ---------------------------------------------------------------- utilidades
  function el(tag, atributos = {}, ...filhos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(atributos)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "on") for (const [ev, fn] of Object.entries(v)) e.addEventListener(ev, fn);
      else if (k in e && k !== "list") e[k] = v;
      else e.setAttribute(k, v);
    }
    if (tag === "button") e.classList.add("botao");
    for (const f of filhos.flat()) {
      if (f === null || f === undefined || f === false) continue;
      e.append(typeof f === "string" || typeof f === "number" ? document.createTextNode(String(f)) : f);
    }
    return e;
  }

  const n2 = (v) => (v === null || v === undefined || !Number.isFinite(v) ? "--" : v.toFixed(2).replace(".", ","));
  const dados = () => s.base;
  const api = (url, opcoes) => window.App.api(url, opcoes);

  function aviso(texto, bom = true) {
    s.mensagem = { texto, bom };
    window.App.aviso(texto, bom);
  }

  /** Lê ativos, dependências e risco da API. */
  async function recarregar() {
    const [ativos, deps, risco] = await Promise.all([
      api("/api/ativos"),
      api("/api/dependencias"),
      api("/api/risco").catch(() => null),
    ]);
    s.base = {
      ativos,
      deps: deps.map((d) => ({ o: d.ativo_origem_id, d: d.ativo_destino_id, peso: d.peso })),
      risco: new Map(((risco && risco.resultados) || []).map((r) => [r.id, { efetivo: r.risco_efetivo }])),
    };
  }

  async function executar(acao, okTexto) {
    if (s.ocupado) return false;
    s.ocupado = true;
    try {
      await acao();
      await recarregar();
      if (okTexto) aviso(okTexto, true);
      return true;
    } catch (erro) {
      aviso(erro.message, false);
      return false;
    } finally {
      s.ocupado = false;
      desenhar();
    }
  }

  const json = (metodo, corpo) => ({
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });

  async function carregarListas() {
    try {
      if (!s.tipos.length) s.tipos = await api("/api/tipos");
      if (!s.status.length) s.status = await api("/api/status");
    } catch (erro) {
      aviso("Não foi possível carregar os tipos: " + erro.message, false);
    }
  }

  // ----------------------------------------------------------------- formulário
  function campo(rotulo, entrada, ajuda) {
    return el("label", { class: "campo" }, el("span", {}, rotulo), entrada, ajuda ? el("small", {}, ajuda) : null);
  }

  function formularioAtivo() {
    const editando = s.form.modo === "editar";
    const a = s.form.ativo || {};
    const proximoId = Math.max(0, ...dados().ativos.map((x) => x.id)) + 1;

    const tipo = el("select", { name: "tipo", disabled: editando },
      s.tipos.map((t) => el("option", { value: t.codigo, selected: editando ? t.codigo === a.tipo_codigo : false }, t.nome)));
    const id = el("input", { name: "id", type: "number", min: 1, step: 1, required: true, value: editando ? a.id : proximoId, disabled: editando });
    const nome = el("input", { name: "nome", required: true, minLength: 3, value: a.nome || "", autocomplete: "off" });
    const responsavel = el("input", { name: "responsavel", required: true, value: a.responsavel || "", autocomplete: "off" });
    const setor = el("input", { name: "setor", required: true, value: a.setor || "", autocomplete: "off" });
    const especifico = el("input", { name: "especifico", required: true, value: editando ? a.valor_campo : "", autocomplete: "off" });
    const rotuloEspecifico = el("span", {}, "");

    const ajustarRotulo = () => {
      const t = s.tipos.find((x) => x.codigo === Number(tipo.value)) || s.tipos[0];
      rotuloEspecifico.textContent = t ? t.rotulo_campo : "Campo do tipo";
    };
    tipo.addEventListener("change", ajustarRotulo);
    ajustarRotulo();
    if (editando) rotuloEspecifico.textContent = a.rotulo_campo;

    const enviar = async (ev) => {
      ev.preventDefault();
      const t = s.tipos.find((x) => x.codigo === Number(tipo.value));
      if (editando) {
        const corpo = { nome: nome.value, responsavel: responsavel.value, setor: setor.value, [a.campo_especifico]: especifico.value };
        if (await executar(() => api(`/api/ativos/${a.id}`, json("PATCH", corpo)), `${nome.value.trim()} atualizado.`)) s.form = null;
      } else {
        const corpo = {
          tipo: Number(tipo.value), id: Number(id.value), nome: nome.value, responsavel: responsavel.value,
          setor: setor.value, [t.campo]: especifico.value,
        };
        if (await executar(() => api("/api/ativos", json("POST", corpo)), `${nome.value.trim()} cadastrado.`)) s.form = null;
      }
      desenhar();
    };

    return el("form", { class: "cartao", on: { submit: enviar } },
      el("h3", {}, editando ? `Editar ${a.nome}` : "Novo ativo"),
      el("div", { class: "grade" },
        campo("Tipo", tipo), campo("ID", id, editando ? null : `Sugestão: ${proximoId}`),
        campo("Nome", nome, "Mínimo de 3 caracteres"),
        campo("Responsável", responsavel), campo("Setor", setor),
        el("label", { class: "campo" }, rotuloEspecifico, especifico)),
      el("div", { class: "acoes" },
        el("button", { type: "submit", class: "primario", disabled: s.ocupado }, editando ? "Salvar alterações" : "Cadastrar ativo"),
        el("button", { type: "button", on: { click: () => { s.form = null; desenhar(); } } }, "Cancelar")));
  }

  // ----------------------------------------------------------------- falhas
  function painelFalhas(ativo) {
    const lista = ativo.vulnerabilidades;
    const cve = el("input", { name: "cve", placeholder: "CVE-2024-1234 (opcional)", autocomplete: "off" });
    const categoria = el("input", { name: "categoria", required: true, placeholder: "Ex.: Execução remota" });
    const severidade = el("input", { name: "severidade", type: "number", min: 0, max: 10, step: 0.1, placeholder: "0 a 10" });
    const descricao = el("input", { name: "descricao", placeholder: "O que é esta falha" });

    const adicionar = async (ev) => {
      ev.preventDefault();
      const corpo = { categoria: categoria.value };
      if (cve.value.trim()) corpo.cve = cve.value.trim();
      if (severidade.value !== "") corpo.severidade = Number(severidade.value);
      if (descricao.value.trim()) corpo.descricao = descricao.value.trim();
      await executar(() => api(`/api/ativos/${ativo.id}/vulnerabilidades`, json("POST", corpo)),
        "Falha adicionada.");
    };

    return el("div", { class: "falhas" },
      lista.length
        ? el("table", { class: "tabela interna" },
            el("thead", {}, el("tr", {}, ["Falha", "Nota", "Gravidade", "Status", "Descrição"].map((t) => el("th", {}, t)))),
            el("tbody", {}, lista.map((v) => el("tr", {},
              el("td", {}, v.id), el("td", {}, n2(v.severidade)), el("td", {}, v.classificacao),
              el("td", {}, el("select", {
                "aria-label": `Status de ${v.id}`,
                on: { change: (e) => executar(() => api(
                  `/api/ativos/${ativo.id}/vulnerabilidades/${encodeURIComponent(v.id)}`, json("PATCH", { status: e.target.value })),
                  `${v.id}: ${e.target.value}.`) },
              }, s.status.map((st) => el("option", { value: st, selected: st === v.status }, st)))),
              el("td", {}, v.descricao_curta)))))
        : el("p", { class: "vazio" }, "Este ativo não tem falhas registradas."),
      el("form", { class: "linha-form", on: { submit: adicionar } },
        campo("CVE", cve, "Sem nota? Com CVE, ela vem do NVD (precisa de internet)."),
        campo("Categoria", categoria), campo("Nota", severidade), campo("Descrição", descricao),
        el("button", { type: "submit", class: "primario", disabled: s.ocupado }, "Adicionar falha")));
  }

  // ------------------------------------------------------------------ ativos
  function abaAtivos() {
    const termo = s.busca.trim().toLowerCase();
    const lista = dados().ativos.filter((a) =>
      (!s.filtroTipo || String(a.tipo_codigo) === s.filtroTipo) &&
      (!termo || [a.nome, a.responsavel, a.setor, String(a.id)].some((x) => String(x).toLowerCase().includes(termo))));

    const busca = el("input", { type: "search", placeholder: "Buscar por nome, responsável, setor ou ID", value: s.busca, "aria-label": "Buscar ativos",
      on: { input: (e) => { s.busca = e.target.value; clearTimeout(busca._t); busca._t = setTimeout(() => { desenhar(); const n = raiz().querySelector('input[type="search"]'); if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }, 180); } } });
    const filtro = el("select", { "aria-label": "Filtrar por tipo", on: { change: (e) => { s.filtroTipo = e.target.value; desenhar(); } } },
      el("option", { value: "" }, "Todos os tipos"),
      s.tipos.map((t) => el("option", { value: t.codigo, selected: String(t.codigo) === s.filtroTipo }, t.nome)));

    const linhas = [];
    for (const a of lista) {
      const r = dados().risco.get(a.id);
      const abertas = a.vulnerabilidades.filter((v) => v.afeta_risco).length;
      linhas.push(el("tr", {},
        el("td", {}, a.id), el("th", { scope: "row" }, a.nome), el("td", {}, a.tipo_nome),
        el("td", {}, `${a.rotulo_campo}: ${a.valor_campo}`), el("td", {}, a.responsavel), el("td", {}, a.setor),
        el("td", { class: "num" }, n2(r ? r.efetivo : null)),
        el("td", {}, el("div", { class: "botoes" },
          el("button", { type: "button", "aria-expanded": String(s.aberto === a.id), on: { click: () => { s.aberto = s.aberto === a.id ? null : a.id; desenhar(); } } },
            `Falhas (${abertas}/${a.vulnerabilidades.length})`),
          el("button", { type: "button", on: { click: () => { s.form = { modo: "editar", ativo: a }; s.confirma = null; desenhar(); } } }, "Editar"),
          el("button", { type: "button", class: "perigo", on: { click: () => pedirExclusao(a) } }, "Excluir")))));
      if (s.aberto === a.id) linhas.push(el("tr", { class: "detalhe" }, el("td", { colSpan: 8 }, painelFalhas(a))));
    }

    return [
      el("div", { class: "barra-ferramentas" }, busca, filtro,
        el("button", { type: "button", class: "primario", on: { click: () => { s.form = { modo: "novo" }; s.confirma = null; desenhar(); } } }, "+ Novo ativo")),
      s.form ? formularioAtivo() : null,
      lista.length
        ? el("div", { class: "rolagem" }, el("table", { class: "tabela" },
            el("thead", {}, el("tr", {}, ["ID", "Nome", "Tipo", "Detalhe", "Responsável", "Setor", "Risco", "Ações"].map((t) => el("th", { scope: "col" }, t)))),
            el("tbody", {}, linhas)))
        : el("p", { class: "vazio" }, dados().ativos.length
            ? "Nenhum ativo encontrado com esse filtro."
            : "Ainda não há ativos. Use “+ Novo ativo” para cadastrar o primeiro."),
    ];
  }

  function pedirExclusao(a) {
    const ligadas = dados().deps.filter((d) => d.o === a.id || d.d === a.id).length;
    s.form = null;
    s.confirma = {
      texto: `Excluir ${a.nome}?` + (ligadas ? ` Isso também remove ${ligadas} dependência(s) ligada(s) a ele.` : ""),
      acao: async () => {
        await executar(() => api(`/api/ativos/${a.id}`, { method: "DELETE" }), `${a.nome} excluído.`);
        s.confirma = null; if (s.aberto === a.id) s.aberto = null; desenhar();
      },
    };
    desenhar();
  }

  // ------------------------------------------------------------ dependências
  function abaDependencias() {
    const ativos = dados().ativos;
    const nome = (id) => (ativos.find((a) => a.id === id) || {}).nome || `#${id}`;
    const opcoes = (selecionado) => ativos.map((a) => el("option", { value: a.id, selected: a.id === selecionado }, `${a.id} - ${a.nome}`));
    const origem = el("select", { name: "origem", "aria-label": "Quem passa o risco" }, opcoes());
    const destino = el("select", { name: "destino", "aria-label": "Quem recebe o risco" }, opcoes(ativos[1] && ativos[1].id));
    const peso = el("input", { name: "peso", type: "number", min: 0, max: 0.99, step: 0.01, value: 0.2, required: true });

    const criar = async (ev) => {
      ev.preventDefault();
      await executar(() => api("/api/dependencias",
        json("POST", { origem: Number(origem.value), destino: Number(destino.value), peso: Number(peso.value) })),
        "Dependência criada.");
    };

    return [
      el("p", { class: "dica" }, "Uma dependência diz quanto do risco de um ativo (origem) passa para outro (destino). O peso vai de 0 até menos de 1; a soma dos pesos que chegam em um mesmo ativo também precisa ficar abaixo de 1."),
      ativos.length >= 2
        ? el("form", { class: "linha-form", on: { submit: criar } },
            campo("Origem (passa o risco)", origem), campo("Destino (recebe)", destino), campo("Peso", peso),
            el("button", { type: "submit", class: "primario", disabled: s.ocupado }, "Criar dependência"))
        : el("p", { class: "vazio" }, "Cadastre pelo menos dois ativos para ligá-los."),
      dados().deps.length
        ? el("div", { class: "rolagem" }, el("table", { class: "tabela" },
            el("thead", {}, el("tr", {}, ["Origem", "", "Destino", "Peso", "Ações"].map((t) => el("th", { scope: "col" }, t)))),
            el("tbody", {}, dados().deps.map((d) => el("tr", {},
              el("td", {}, nome(d.o)), el("td", { "aria-hidden": "true" }, "→"), el("td", {}, nome(d.d)),
              el("td", { class: "num" }, n2(d.peso)),
              el("td", {}, el("button", { type: "button", class: "perigo", on: { click: () => executar(
                () => api(`/api/dependencias/${d.o}/${d.d}`, { method: "DELETE" }), "Dependência removida.") } }, "Remover")))))))
        : el("p", { class: "vazio" }, "Nenhuma dependência cadastrada."),
    ];
  }

  // ----------------------------------------------------------------- tela
  function desenhar() {
    const r = raiz();
    if (!r) return;
    const mantemRolagem = r.scrollTop;
    const abas = el("div", { class: "sub-abas", role: "tablist", "aria-label": "Cadastro" },
      ["ativos", "dependencias"].map((nome) => el("button", {
        type: "button", role: "tab", "aria-selected": String(s.aba === nome),
        on: { click: () => { s.aba = nome; s.form = null; s.confirma = null; s.mensagem = null; desenhar(); } },
      }, nome === "ativos" ? `Ativos (${dados().ativos.length})` : `Dependências (${dados().deps.length})`)));

    const partes = [
      abas,
      s.mensagem ? el("p", { class: "mensagem " + (s.mensagem.bom ? "ok" : "erro"), role: "alert" }, s.mensagem.texto) : null,
      s.confirma ? el("div", { class: "cartao confirmacao", role: "alertdialog" },
        el("p", {}, s.confirma.texto),
        el("div", { class: "acoes" },
          el("button", { type: "button", class: "perigo", disabled: s.ocupado, on: { click: s.confirma.acao } }, "Sim, excluir"),
          el("button", { type: "button", on: { click: () => { s.confirma = null; desenhar(); } } }, "Cancelar"))) : null,
      ...(s.aba === "ativos" ? abaAtivos() : abaDependencias()),
    ];
    r.replaceChildren(...partes.filter(Boolean));          // null no meio viraria o texto "null"
    r.scrollTop = mantemRolagem;
  }

  function digitando() {
    const r = raiz();
    const f = document.activeElement;
    return !!(r && f && r.contains(f) && f.matches("input, textarea, select") && f.type !== "search");
  }

  return {
    async montar() {
      await carregarListas();
      try { await recarregar(); } catch (erro) { aviso("Não foi possível ler os ativos: " + erro.message, false); }
      desenhar();
    },
    // Chamado a cada atualização automática: só redesenha se ninguém estiver digitando.
    aoAtualizar() { if (!s.form && !digitando() && !s.ocupado) desenhar(); },
  };
})();

window.Ativos = Ativos;   // "const" de topo não vira propriedade de window
