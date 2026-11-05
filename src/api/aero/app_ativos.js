/* Gerenciador de Ativos: o CRUD do sistema.
 *
 * Lista de ativos com botões Novo / Editar / Excluir sempre visíveis, painel
 * de falhas do ativo selecionado e uma aba de dependências. Fala com a mesma
 * API REST do resto do projeto:
 *   GET/POST /api/ativos          PATCH/DELETE /api/ativos/<id>
 *   POST /api/ativos/<id>/vulnerabilidades   PATCH .../<vid> {status}
 *   GET/POST /api/dependencias    DELETE /api/dependencias/<origem>/<destino>
 */
const AppAtivos = (() => {
  "use strict";
  const { el, num, pilula, dados, api, json, alterar } = Nucleo;

  const s = { aba: "ativos", busca: "", tipo: "", sel: null, desinscrever: null };
  let ui = null;                       // elementos da janela aberta (null = fechada)
  let tempoMensagem = null;

  // ----------------------------------------------------------- mensagens
  function mensagem(texto, bom = true) {
    if (!ui) return;
    ui.msg.textContent = texto;
    ui.msg.className = bom ? "ok" : "erro";
    clearTimeout(tempoMensagem);
    tempoMensagem = setTimeout(() => { if (ui) { ui.msg.textContent = "Pronto."; ui.msg.className = ""; } }, 7000);
  }

  /** Roda uma alteração, relê os dados e redesenha; erros viram mensagem na barra. */
  async function executar(acao, ok) {
    try {
      await alterar(acao);
      if (ok) mensagem(ok, true);
      return true;
    } catch (erro) {
      mensagem(erro.message + (erro.dica ? ` ${erro.dica}` : ""), false);
      return false;
    } finally {
      desenhar();
    }
  }

  const campo = (rotulo, entrada, ajuda) =>
    el("label", { class: "campo" }, el("span", {}, rotulo), entrada, ajuda ? el("small", {}, ajuda) : null);

  // ---------------------------------------------------------- formulário
  function formulario(modo, ativo) {
    const editando = modo === "editar";
    const a = ativo || {};
    const proximoId = Math.max(0, ...dados.ativos.map((x) => x.id)) + 1;

    const tipo = el("select", { name: "tipo", disabled: editando },
      dados.tipos.map((t) => el("option", { value: t.codigo, selected: editando ? t.codigo === a.tipo_codigo : false }, t.nome)));
    const id = el("input", { name: "id", type: "number", min: 1, step: 1, required: true, value: editando ? a.id : proximoId, disabled: editando });
    const nome = el("input", { name: "nome", required: true, minLength: 3, value: a.nome || "", autocomplete: "off" });
    const responsavel = el("input", { name: "responsavel", required: true, value: a.responsavel || "", autocomplete: "off" });
    const setor = el("input", { name: "setor", required: true, value: a.setor || "", autocomplete: "off" });
    const especifico = el("input", { name: "especifico", required: true, value: editando ? a.valor_campo : "", autocomplete: "off" });
    const rotuloEspecifico = el("span", {}, "");
    const ajustar = () => {
      const t = dados.tipos.find((x) => x.codigo === Number(tipo.value)) || dados.tipos[0];
      rotuloEspecifico.textContent = editando ? a.rotulo_campo : (t ? t.rotulo_campo : "Campo do tipo");
    };
    tipo.addEventListener("change", ajustar);
    ajustar();

    const form = el("form", { novalidate: false, class: "grade-campos" },
      campo("Tipo", tipo), campo("ID", id, editando ? null : `Sugestão: ${proximoId}`),
      el("div", { class: "largo" }, campo("Nome", nome, "Mínimo de 3 caracteres")),
      campo("Responsável", responsavel), campo("Setor", setor),
      el("div", { class: "largo" }, el("label", { class: "campo" }, rotuloEspecifico, especifico)));
    form.addEventListener("submit", (ev) => {              // Enter confirma
      ev.preventDefault();
      const principal = form.closest(".janela").querySelector(".botao.gel");
      if (principal) principal.click();
    });

    Janelas.dialogo({
      titulo: editando ? `Editar ${a.nome}` : "Novo ativo", icone: editando ? "ativos" : "ativos", corpo: form,
      botoes: [
        {
          rotulo: editando ? "Salvar" : "Cadastrar", primario: true,
          aoClicar: async () => {
            if (!form.reportValidity()) return false;
            if (editando) {
              const corpo = { nome: nome.value, responsavel: responsavel.value, setor: setor.value, [a.campo_especifico]: especifico.value };
              await alterar(() => api(`/api/ativos/${a.id}`, json("PATCH", corpo)));
              mensagem(`${nome.value.trim()} atualizado.`);
            } else {
              const t = dados.tipos.find((x) => x.codigo === Number(tipo.value));
              const corpo = { tipo: Number(tipo.value), id: Number(id.value), nome: nome.value, responsavel: responsavel.value, setor: setor.value, [t.campo]: especifico.value };
              await alterar(() => api("/api/ativos", json("POST", corpo)));
              s.sel = corpo.id;
              mensagem(`${nome.value.trim()} cadastrado.`);
            }
            desenhar();
            return true;
          },
        },
        { rotulo: "Cancelar" },
      ],
    });
  }

  function excluir(a) {
    const ligadas = dados.deps.filter((d) => d.o === a.id || d.d === a.id).length;
    Janelas.dialogo({
      titulo: "Excluir ativo", icone: "pergunta",
      texto: `Excluir "${a.nome}"?` + (ligadas ? ` Isso também remove ${ligadas} dependência(s) ligada(s) a ele.` : " Esta ação não pode ser desfeita."),
      botoes: [
        {
          rotulo: "Excluir", perigo: true,
          aoClicar: async () => {
            await alterar(() => api(`/api/ativos/${a.id}`, { method: "DELETE" }));
            if (s.sel === a.id) s.sel = null;
            mensagem(`${a.nome} excluído.`);
            desenhar();
          },
        },
        { rotulo: "Cancelar", foco: true },
      ],
    });
  }

  // -------------------------------------------------------------- lista
  function filtrados() {
    const termo = s.busca.trim().toLowerCase();
    return dados.ativos.filter((a) =>
      (!s.tipo || String(a.tipo_codigo) === s.tipo) &&
      (!termo || [a.nome, a.responsavel, a.setor, String(a.id)].some((x) => String(x).toLowerCase().includes(termo))));
  }

  function tabelaAtivos(lista) {
    if (!lista.length) {
      return el("p", { class: "vazio" }, dados.ativos.length
        ? "Nenhum ativo encontrado com esse filtro."
        : "Ainda não há ativos. Clique em “+ Novo ativo” para cadastrar o primeiro.");
    }
    const mover = (ev, i) => {
      const ir = (j) => { ev.preventDefault(); const alvo = lista[Math.max(0, Math.min(lista.length - 1, j))]; s.sel = alvo.id; desenhar(); focarLinha(alvo.id); };
      if (ev.key === "ArrowDown") ir(i + 1);
      else if (ev.key === "ArrowUp") ir(i - 1);
      else if (ev.key === "Enter") { ev.preventDefault(); formulario("editar", lista[i]); }
      else if (ev.key === "Delete") { ev.preventDefault(); excluir(lista[i]); }
    };
    return el("table", { class: "lista" },
      el("thead", {}, el("tr", {}, ["ID", "Nome", "Tipo", "Detalhe", "Responsável", "Setor", "Falhas", "Risco efetivo"].map((t, k) =>
        el("th", { scope: "col", class: k === 7 ? "num" : null }, t)))),
      el("tbody", {}, lista.map((a, i) => {
        const r = dados.risco.get(a.id);
        const abertas = a.vulnerabilidades.filter((v) => v.afeta_risco).length;
        return el("tr", {
          tabindex: "0", "aria-selected": String(s.sel === a.id), "data-id": a.id,
          on: {
            click: () => { s.sel = a.id; desenhar(); focarLinha(a.id); },
            dblclick: () => formulario("editar", a),
            keydown: (ev) => mover(ev, i),
          },
        },
          el("td", {}, a.id), el("th", { scope: "row" }, a.nome), el("td", {}, a.tipo_nome),
          el("td", {}, `${a.rotulo_campo}: ${a.valor_campo}`), el("td", {}, a.responsavel), el("td", {}, a.setor),
          el("td", {}, `${abertas} aberta(s) de ${a.vulnerabilidades.length}`),
          el("td", { class: "num" }, r ? pilula(r.risco_efetivo) : "--"));
      })));
  }

  function focarLinha(id) {
    const linha = ui && ui.painel.querySelector(`tr[data-id="${id}"]`);
    if (linha) linha.focus({ preventScroll: false });
  }

  // ----------------------------------------------------------- falhas
  function painelDetalhes() {
    const a = dados.ativos.find((x) => x.id === s.sel);
    if (!a) {
      s.sel = null;
      return el("p", { class: "vazio" }, "Selecione um ativo na lista para ver e cadastrar as falhas (vulnerabilidades) dele.");
    }
    const r = dados.risco.get(a.id);

    const cve = el("input", { name: "cve", placeholder: "CVE-2024-1234 (opcional)", autocomplete: "off" });
    const categoria = el("input", { name: "categoria", required: true, placeholder: "Ex.: Execução remota" });
    const severidade = el("input", { name: "severidade", type: "number", min: 0, max: 10, step: 0.1, placeholder: "0 a 10" });
    const descricao = el("input", { name: "descricao", required: true, placeholder: "O que é esta falha" });

    const adicionar = async (ev) => {
      ev.preventDefault();
      const corpo = { categoria: categoria.value };
      if (cve.value.trim()) corpo.cve = cve.value.trim();
      if (severidade.value !== "") corpo.severidade = Number(severidade.value);
      if (descricao.value.trim()) corpo.descricao = descricao.value.trim();
      await executar(() => api(`/api/ativos/${a.id}/vulnerabilidades`, json("POST", corpo)), "Falha adicionada.");
    };

    const tabela = a.vulnerabilidades.length
      ? el("div", { class: "caixa-lista" }, el("table", { class: "lista" },
          el("thead", {}, el("tr", {}, ["Falha", "Nota", "Gravidade", "Status", "Descrição", ""].map((t, k) => el("th", { scope: "col", class: k === 1 ? "num" : null }, t)))),
          el("tbody", {}, a.vulnerabilidades.map((v) => el("tr", {},
            el("td", {}, v.id), el("td", { class: "num" }, num(v.severidade, 1)), el("td", {}, v.classificacao),
            el("td", {}, el("select", {
              "aria-label": `Status de ${v.id}`,
              on: {
                change: (e) => executar(() => api(
                  `/api/ativos/${a.id}/vulnerabilidades/${encodeURIComponent(v.id)}`, json("PATCH", { status: e.target.value })),
                `${v.id}: ${e.target.value}.`),
              },
            }, dados.status.map((st) => el("option", { value: st, selected: st === v.status }, st)))),
            el("td", {}, v.descricao_curta),
            el("td", {}, el("button", {
              type: "button", class: "botao pequeno", title: "O que é esta falha e como prevenir",
              on: { click: () => AppAssistente.explicarFalha(a.id, v.id) },
            }, "Explicar")))))))
      : el("p", { class: "vazio" }, "Este ativo não tem falhas registradas.");

    return el("div", {},
      el("div", { class: "detalhes-topo" },
        el("h3", {}, a.nome),
        el("span", {}, `${a.tipo_nome} · ID ${a.id}`),
        r ? el("span", {}, "Risco próprio ", pilula(r.risco_proprio), " efetivo ", pilula(r.risco_efetivo)) : null),
      tabela,
      el("p", { class: "dica", style: "margin:8px 0 0" }, "Nova falha: informe a descrição e a nota (0 a 10). Com um CVE, a nota pode vir do NVD (precisa de internet)."),
      el("form", { class: "linha-form", style: "margin-top:4px", on: { submit: adicionar } },
        campo("CVE", cve),
        campo("Categoria", categoria), campo("Nota", severidade), campo("Descrição", descricao),
        el("button", { type: "submit", class: "botao gel" }, "Adicionar falha")));
  }

  // ------------------------------------------------------- dependências
  function painelDeps() {
    const ativos = dados.ativos;
    const nome = (id) => (ativos.find((a) => a.id === id) || {}).nome || `#${id}`;
    const opcoes = (padrao) => ativos.map((a) => el("option", { value: a.id, selected: a.id === padrao }, `${a.id} - ${a.nome}`));
    const origem = el("select", { name: "origem", "aria-label": "Quem passa o risco" }, opcoes());
    const destino = el("select", { name: "destino", "aria-label": "Quem recebe o risco" }, opcoes(ativos[1] && ativos[1].id));
    const peso = el("input", { name: "peso", type: "number", min: 0, max: 0.99, step: 0.01, value: 0.2, required: true });
    const soma = new Map();
    for (const d of dados.deps) soma.set(d.d, (soma.get(d.d) || 0) + d.peso);

    const criar = async (ev) => {
      ev.preventDefault();
      await executar(() => api("/api/dependencias",
        json("POST", { origem: Number(origem.value), destino: Number(destino.value), peso: Number(peso.value) })), "Dependência criada.");
    };

    return el("div", {},
      el("p", { class: "dica" }, "Uma dependência diz quanto do risco de um ativo (origem) passa para outro (destino). O peso vai de 0 até menos de 1, e a soma dos pesos que chegam em um mesmo ativo também precisa ficar abaixo de 1: é isso que garante que (I − A) seja invertível."),
      ativos.length >= 2
        ? el("form", { class: "linha-form", style: "border-top:0;margin-top:0;padding-top:0", on: { submit: criar } },
            campo("Origem (passa o risco)", origem), campo("Destino (recebe)", destino), campo("Peso", peso),
            el("button", { type: "submit", class: "botao gel" }, "Criar dependência"))
        : el("p", { class: "vazio" }, "Cadastre pelo menos dois ativos para ligá-los."),
      dados.deps.length
        ? el("div", { class: "caixa-lista", style: "margin-top:10px" }, el("table", { class: "lista" },
            el("thead", {}, el("tr", {}, ["Origem", "", "Destino", "Peso", "Soma no destino", "Ações"].map((t, k) => el("th", { scope: "col", class: k === 3 || k === 4 ? "num" : null }, t)))),
            el("tbody", {}, dados.deps.map((d) => el("tr", {},
              el("td", {}, nome(d.o)), el("td", { "aria-hidden": "true" }, "→"), el("td", {}, nome(d.d)),
              el("td", { class: "num" }, num(d.peso)), el("td", { class: "num" }, `${num(soma.get(d.d))} de 1,00`),
              el("td", {}, el("button", {
                type: "button", class: "botao pequeno perigo",
                on: { click: () => executar(() => api(`/api/dependencias/${d.o}/${d.d}`, { method: "DELETE" }), "Dependência removida.") },
              }, "Remover")))))))
        : el("p", { class: "vazio" }, "Nenhuma dependência cadastrada."));
  }

  // -------------------------------------------------------------- tela
  function desenhar() {
    if (!ui) return;
    const sel = dados.ativos.find((a) => a.id === s.sel);
    ui.btnEditar.disabled = !sel;
    ui.btnExcluir.disabled = !sel;
    ui.ferramentas.querySelectorAll(".so-ativos").forEach((n) => { n.hidden = s.aba !== "ativos"; });
    ui.abaAtivos.setAttribute("aria-selected", String(s.aba === "ativos"));
    ui.abaDeps.setAttribute("aria-selected", String(s.aba === "deps"));
    ui.abaAtivos.firstChild.textContent = `Ativos (${dados.ativos.length})`;
    ui.abaDeps.firstChild.textContent = `Dependências (${dados.deps.length})`;
    ui.contagem1.textContent = `${dados.ativos.length} ativo(s)`;
    ui.contagem2.textContent = `${dados.deps.length} dependência(s)`;

    const rolagem = ui.painel.querySelector(".ativos-lista");
    const antes = rolagem ? rolagem.scrollTop : 0;
    const filhos = s.aba === "ativos"
      ? el("div", { class: "ativos-corpo", style: "height:100%" },
          el("div", { class: "caixa-lista ativos-lista" }, tabelaAtivos(filtrados())),
          el("div", { class: "ativos-detalhes" }, painelDetalhes()))
      : painelDeps();
    ui.painel.replaceChildren(filhos);
    const novaLista = ui.painel.querySelector(".ativos-lista");
    if (novaLista) novaLista.scrollTop = antes;
  }

  function construir() {
    const busca = el("input", {
      type: "search", class: "so-ativos", placeholder: "Buscar por nome, responsável, setor ou ID", "aria-label": "Buscar ativos", style: "min-width:230px",
      on: { input: (e) => { s.busca = e.target.value; clearTimeout(busca._t); busca._t = setTimeout(desenhar, 150); } },
    });
    const filtro = el("select", {
      class: "so-ativos", "aria-label": "Filtrar por tipo",
      on: { change: (e) => { s.tipo = e.target.value; desenhar(); } },
    }, el("option", { value: "" }, "Todos os tipos"), dados.tipos.map((t) => el("option", { value: t.codigo }, t.nome)));
    const btnNovo = el("button", { type: "button", class: "botao gel so-ativos", on: { click: () => formulario("novo") } }, "+ Novo ativo");
    const btnEditar = el("button", { type: "button", class: "botao so-ativos", on: { click: () => { const a = dados.ativos.find((x) => x.id === s.sel); if (a) formulario("editar", a); } } }, "Editar");
    const btnExcluir = el("button", { type: "button", class: "botao perigo so-ativos", on: { click: () => { const a = dados.ativos.find((x) => x.id === s.sel); if (a) excluir(a); } } }, "Excluir");
    const ferramentas = el("div", { class: "ferramentas" }, btnNovo, btnEditar, btnExcluir,
      el("span", { class: "separador so-ativos" }), busca, filtro);

    const aba = (nome) => el("button", {
      type: "button", class: "aba", role: "tab",
      on: { click: () => { s.aba = nome; desenhar(); } },
    }, "");
    const abaAtivos = aba("ativos"), abaDeps = aba("deps");
    const painel = el("div", { class: "painel-aba", role: "tabpanel" });
    const msg = el("span", {}, "Pronto.");
    const contagem1 = el("span", {}, ""), contagem2 = el("span", {}, "");
    const raiz = el("div", { class: "app" }, ferramentas,
      el("div", { class: "abas", role: "tablist", "aria-label": "Cadastro" }, abaAtivos, abaDeps),
      painel, el("div", { class: "barra-status" }, msg, contagem1, contagem2));
    ui = { raiz, ferramentas, painel, btnEditar, btnExcluir, abaAtivos, abaDeps, msg, contagem1, contagem2 };
    return raiz;
  }

  /** Abre o Gerenciador; com `id`, já deixa esse ativo selecionado (vindo do Mapa). */
  function abrir(id) {
    if (typeof id === "number") { s.aba = "ativos"; s.sel = id; }
    if (ui) { Janelas.focar("ativos"); desenhar(); return; }
    const conteudo = construir();
    s.desinscrever = Nucleo.assinar(() => {
      // Atualização vinda de outra janela: não atrapalha quem está digitando.
      const f = document.activeElement;
      const digitando = ui && f && ui.painel.contains(f) && f.matches("input, textarea");
      if (!digitando) desenhar();
    });
    Janelas.abrir({
      id: "ativos", titulo: "Gerenciador de Ativos", icone: "ativos", largura: 960, altura: 640, conteudo,
      aoFechar: () => { if (s.desinscrever) s.desinscrever(); ui = null; },
    });
    desenhar();
    Nucleo.recarregar().catch((e) => mensagem(`Não foi possível ler os dados: ${e.message}`, false));
  }

  return { abrir };
})();

window.AppAtivos = AppAtivos;
