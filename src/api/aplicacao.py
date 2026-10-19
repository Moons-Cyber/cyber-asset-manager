"""API REST (JSON) do inventário de ativos e vulnerabilidades.

Esta camada só traduz HTTP <-> serviços. Toda a regra de negócio continua nos
gerenciadores e no modelo de risco; nada foi duplicado aqui.
"""

import functools
import math
import threading
from pathlib import Path

from flask import Flask, jsonify, request, url_for
from werkzeug.exceptions import HTTPException

from src.modelos.dependencia import Dependencia
from src.modelos.enums import StatusVulnerabilidade, TipoAtivo
from src.modelos.registro_tipos import CLASSE_POR_TIPO, TIPO_POR_CLASSE
from src.modelos.vulnerabilidades import (
    Vulnerabilidade,
    normalizar_cve,
    resumir,
)
from src.servicos.analise_risco import (
    calcular_risco_efetivo,
    diagnosticar_sistema,
)
from src.servicos.cliente_nvd import (
    ClienteNVD,
    CVENaoEncontrado,
    NVDIndisponivel,
)
from src.servicos.gerenciador_ativos import GerenciadorAtivos
from src.servicos.gerenciador_dependencias import GerenciadorDependencias


# ---------------------------------------------------------------------------
# Erros e validação de entrada
# ---------------------------------------------------------------------------
class ErroApi(Exception):
    """Erro com status HTTP próprio, devolvido ao cliente como JSON."""

    def __init__(self, mensagem, status=400, **extras):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
        self.extras = extras


def _corpo_json():
    corpo = request.get_json(silent=True)

    if not isinstance(corpo, dict):
        raise ErroApi("O corpo da requisição deve ser um objeto JSON.")

    return corpo


def _texto(corpo, campo, obrigatorio=True):
    valor = corpo.get(campo)

    if valor is None:
        if obrigatorio:
            raise ErroApi(f"O campo '{campo}' é obrigatório.")
        return None

    if not isinstance(valor, str) or not valor.strip():
        raise ErroApi(f"O campo '{campo}' deve ser um texto não vazio.")

    return valor.strip()


def _inteiro(corpo, campo, minimo=1):
    valor = corpo.get(campo)

    if valor is None:
        raise ErroApi(f"O campo '{campo}' é obrigatório.")

    # bool é subclasse de int em Python: True passaria como 1 sem esta checagem.
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
        raise ErroApi(
            f"O campo '{campo}' deve ser um inteiro maior ou igual a {minimo}."
        )

    return valor


def _numero(corpo, campo):
    valor = corpo.get(campo)

    if valor is None:
        raise ErroApi(f"O campo '{campo}' é obrigatório.")

    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(valor)
    ):
        raise ErroApi(f"O campo '{campo}' deve ser um número.")

    return float(valor)


def _status(valor):
    try:
        return StatusVulnerabilidade(valor)
    except ValueError:
        validos = ", ".join(s.value for s in StatusVulnerabilidade)
        raise ErroApi(f"Status inválido. Use um destes: {validos}.") from None


# ---------------------------------------------------------------------------
# Serialização (objeto -> JSON)
# ---------------------------------------------------------------------------
def _limpar(valor):
    """Troca infinito/NaN por None: eles não existem em JSON válido."""
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {chave: _limpar(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_limpar(item) for item in valor]
    return valor


def _vulnerabilidade_para_json(vulnerabilidade):
    dados = vulnerabilidade.para_dict()
    dados.pop("descricao_original", None)  # texto longo do NVD, não vai na lista
    dados["descricao_curta"] = resumir(vulnerabilidade.descricao)
    dados["classificacao"] = vulnerabilidade.classificacao.value
    dados["afeta_risco"] = vulnerabilidade.afeta_risco
    return dados


def _ativo_para_json(ativo):
    tipo = TIPO_POR_CLASSE[type(ativo)]
    dados = ativo.para_dict()

    dados["tipo_codigo"] = tipo.value
    dados["tipo_nome"] = tipo.rotulo
    dados["campo_especifico"] = ativo.campo_especifico
    dados["rotulo_campo"] = ativo.rotulo_campo
    dados["valor_campo"] = getattr(ativo, ativo.campo_especifico)
    dados["vulnerabilidades"] = [
        _vulnerabilidade_para_json(v) for v in ativo.vulnerabilidades
    ]
    return dados


# ---------------------------------------------------------------------------
# Fábrica da aplicação
# ---------------------------------------------------------------------------
def criar_app(pasta_dados=".", cliente_nvd=None):
    """Cria a aplicação Flask.

    pasta_dados: onde ficam ativos.json, dependencias.json e cache_cve.json.
                 No Docker, aponte para o volume.
    cliente_nvd: permite injetar um cliente falso nos testes.
    """
    pasta = Path(pasta_dados)
    pasta.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.json.ensure_ascii = False        # acentos legíveis no JSON
    app.json.sort_keys = False           # mantém a ordem dos campos

    gerenciador = GerenciadorAtivos(pasta / "ativos.json")
    gerenciador_dependencias = GerenciadorDependencias(pasta / "dependencias.json")
    nvd = cliente_nvd or ClienteNVD(pasta / "cache_cve.json")

    # Cadeado dos dados: o dict em memória não é seguro para escritas
    # simultâneas. RLock porque um handler pode chamar outra função travada.
    trava = threading.RLock()
    # Cadeado próprio do NVD: a consulta pode levar segundos (limite de
    # requisições) e não pode segurar o cadeado dos dados nesse tempo.
    trava_nvd = threading.Lock()

    def com_trava(funcao):
        @functools.wraps(funcao)
        def interna(*args, **kwargs):
            with trava:
                return funcao(*args, **kwargs)
        return interna

    def ativo_ou_404(identificador):
        ativo = gerenciador.buscar_ativo_por_id(identificador)

        if ativo is None:
            raise ErroApi(f"Ativo {identificador} não encontrado.", 404)

        return ativo

    def consultar_cve(cve):
        try:
            with trava_nvd:
                return nvd.consultar(cve)
        except CVENaoEncontrado as erro:
            raise ErroApi(str(erro), 404) from erro
        except NVDIndisponivel as erro:
            raise ErroApi(
                str(erro),
                503,
                dica="Envie 'severidade' manualmente para cadastrar "
                     "sem consultar o NVD.",
            ) from erro

    def montar_vulnerabilidade(corpo, consulta_permitida):
        """Monta uma Vulnerabilidade a partir do JSON (consulta o NVD se preciso)."""
        cve = None

        if corpo.get("cve") is not None:
            candidato = corpo["cve"]
            cve = normalizar_cve(candidato) if isinstance(candidato, str) else None

            if cve is None:
                raise ErroApi("Formato de CVE inválido. Use CVE-AAAA-NNNN.")

        categoria = _texto(corpo, "categoria")
        status = _status(corpo.get("status", StatusVulnerabilidade.ABERTA.value))
        descricao = _texto(corpo, "descricao", obrigatorio=False)
        original = None
        fonte = "manual"

        if corpo.get("severidade") is not None:
            nota = _numero(corpo, "severidade")
        elif cve and consulta_permitida:
            dados = consultar_cve(cve)
            nota, original, fonte = dados.nota_cvss, dados.descricao, "NVD"
            if descricao is None:
                descricao = resumir(dados.descricao, 100)
        elif cve:
            raise ErroApi(
                "Informe 'severidade' ou adicione a vulnerabilidade depois, "
                "pelo endpoint de vulnerabilidades (que consulta o NVD)."
            )
        else:
            raise ErroApi("O campo 'severidade' é obrigatório sem CVE.")

        if descricao is None:
            raise ErroApi("O campo 'descricao' é obrigatório.")

        return Vulnerabilidade(
            descricao, categoria, nota, status,
            id=cve, fonte=fonte, descricao_original=original,
        )

    # ------------------------------------------------------------ erros HTTP
    @app.errorhandler(ErroApi)
    def tratar_erro_api(erro):
        return jsonify({"erro": erro.mensagem, **erro.extras}), erro.status

    @app.errorhandler(ValueError)
    def tratar_valor_invalido(erro):
        # Regras de domínio (ex.: nota fora de 0-10, peso inválido).
        return jsonify({"erro": str(erro)}), 400

    @app.errorhandler(HTTPException)
    def tratar_http(erro):
        return jsonify({"erro": erro.description}), erro.code

    @app.errorhandler(OSError)
    def tratar_armazenamento(erro):
        app.logger.exception("Falha de armazenamento")
        return jsonify({"erro": "Erro ao acessar o armazenamento de dados."}), 500

    @app.errorhandler(Exception)
    def tratar_inesperado(erro):
        # Nunca devolve o traceback ao cliente; ele vai para o log.
        app.logger.exception("Erro inesperado")
        return jsonify({"erro": "Erro interno do servidor."}), 500

    # ---------------------------------------------------------------- geral
    @app.get("/")
    def raiz():
        return jsonify({"servico": "Inventário de ativos", "saude": "/api/saude"})

    @app.get("/api/saude")
    def saude():
        """Usado pelo Docker (HEALTHCHECK) para saber se o serviço responde.

        Só devolve 200 se os dados estão legíveis; se o arquivo estiver
        corrompido, devolve 503 para o monitor marcar o serviço como doente.
        """
        try:
            with trava:
                total = len(gerenciador.listar_ativos())
                gerenciador_dependencias.listar_dependencias()
        except (ValueError, OSError) as erro:
            return jsonify({"status": "erro", "detalhe": str(erro)}), 503

        return jsonify({"status": "ok", "ativos": total})

    @app.get("/api/tipos")
    def listar_tipos():
        return jsonify([
            {
                "codigo": tipo.value,
                "nome": tipo.rotulo,
                "campo": classe.campo_especifico,
                "rotulo_campo": classe.rotulo_campo,
            }
            for tipo, classe in CLASSE_POR_TIPO.items()
        ])

    @app.get("/api/status")
    def listar_status():
        return jsonify([s.value for s in StatusVulnerabilidade])

    # ---------------------------------------------------------------- ativos
    @app.get("/api/ativos")
    @com_trava
    def listar_ativos():
        ativos = gerenciador.listar_ativos()
        texto = request.args.get("q", "").strip()
        codigo = request.args.get("tipo", "").strip()

        if texto:
            ativos = gerenciador.buscar_ativos_por_nome(texto)

        if codigo:
            try:
                classe = CLASSE_POR_TIPO[TipoAtivo(int(codigo))]
            except (ValueError, KeyError):
                raise ErroApi("Parâmetro 'tipo' inválido.") from None
            ativos = [a for a in ativos if isinstance(a, classe)]

        return jsonify([_ativo_para_json(a) for a in ativos])

    @app.post("/api/ativos")
    @com_trava
    def criar_ativo():
        corpo = _corpo_json()

        try:
            tipo = TipoAtivo(_inteiro(corpo, "tipo"))
        except ValueError:
            codigos = ", ".join(str(t.value) for t in TipoAtivo)
            raise ErroApi(f"Tipo inexistente. Códigos válidos: {codigos}.") from None

        classe = CLASSE_POR_TIPO[tipo]
        identificador = _inteiro(corpo, "id")
        nome = _texto(corpo, "nome")
        responsavel = _texto(corpo, "responsavel")
        setor = _texto(corpo, "setor")
        valor = _texto(corpo, classe.campo_especifico)

        if gerenciador.buscar_ativo_por_id(identificador) is not None:
            raise ErroApi(f"Já existe um ativo com ID {identificador}.", 409)

        itens = corpo.get("vulnerabilidades", [])

        if not isinstance(itens, list):
            raise ErroApi("O campo 'vulnerabilidades' deve ser uma lista.")

        # Sem consulta ao NVD aqui: várias consultas seguidas estourariam o
        # tempo da requisição. Para usar CVE, adicione depois.
        vulnerabilidades = []
        for item in itens:
            if not isinstance(item, dict):
                raise ErroApi("Cada vulnerabilidade deve ser um objeto JSON.")
            nova = montar_vulnerabilidade(item, consulta_permitida=False)
            if any(v.id == nova.id for v in vulnerabilidades):
                raise ErroApi(f"Vulnerabilidade repetida: {nova.id}.")
            vulnerabilidades.append(nova)

        ativo = classe(identificador, nome, responsavel, setor, vulnerabilidades, valor)
        gerenciador.cadastrar_ativo(ativo)

        resposta = jsonify(_ativo_para_json(ativo))
        resposta.status_code = 201
        resposta.headers["Location"] = url_for(
            "obter_ativo", identificador=identificador
        )
        return resposta

    @app.get("/api/ativos/<int:identificador>")
    @com_trava
    def obter_ativo(identificador):
        return jsonify(_ativo_para_json(ativo_ou_404(identificador)))

    @app.patch("/api/ativos/<int:identificador>")
    @com_trava
    def atualizar_ativo(identificador):
        ativo = ativo_ou_404(identificador)
        corpo = _corpo_json()

        permitidos = {"nome", "responsavel", "setor", ativo.campo_especifico}
        invalidos = set(corpo) - permitidos

        if invalidos:
            raise ErroApi(
                "Campos não permitidos: " + ", ".join(sorted(invalidos))
                + ". Permitidos: " + ", ".join(sorted(permitidos)) + "."
            )

        if not corpo:
            raise ErroApi("Informe pelo menos um campo para atualizar.")

        alteracoes = {campo: _texto(corpo, campo) for campo in corpo}
        gerenciador.atualizar_ativo(identificador, **alteracoes)

        return jsonify(_ativo_para_json(ativo))

    @app.delete("/api/ativos/<int:identificador>")
    @com_trava
    def remover_ativo(identificador):
        ativo_ou_404(identificador)
        gerenciador.remover_ativo(identificador)
        removidas = gerenciador_dependencias.remover_dependencias_do_ativo(
            identificador
        )
        return jsonify({"removido": identificador, "dependencias_removidas": removidas})

    # -------------------------------------------------------- vulnerabilidades
    @app.get("/api/ativos/<int:identificador>/vulnerabilidades")
    @com_trava
    def listar_vulnerabilidades(identificador):
        ativo = ativo_ou_404(identificador)
        return jsonify([_vulnerabilidade_para_json(v) for v in ativo.vulnerabilidades])

    @app.post("/api/ativos/<int:identificador>/vulnerabilidades")
    def adicionar_vulnerabilidade(identificador):
        corpo = _corpo_json()

        with trava:                       # falha cedo se o ativo não existe
            ativo_ou_404(identificador)

        # A consulta ao NVD acontece FORA do cadeado dos dados.
        nova = montar_vulnerabilidade(corpo, consulta_permitida=True)

        with trava:
            ativo = ativo_ou_404(identificador)   # pode ter sido removido no meio

            if any(v.id == nova.id for v in ativo.vulnerabilidades):
                raise ErroApi(
                    f"O ativo '{ativo.nome}' já possui {nova.id}.", 409
                )

            gerenciador.adicionar_vulnerabilidade(identificador, nova)

        resposta = jsonify(_vulnerabilidade_para_json(nova))
        resposta.status_code = 201
        return resposta

    @app.patch("/api/ativos/<int:identificador>/vulnerabilidades/<id_vulnerabilidade>")
    @com_trava
    def atualizar_vulnerabilidade(identificador, id_vulnerabilidade):
        ativo = ativo_ou_404(identificador)
        corpo = _corpo_json()

        if set(corpo) - {"status"} or "status" not in corpo:
            raise ErroApi("Só é possível alterar o campo 'status'.")

        novo_status = _status(corpo["status"])
        alvo = next(
            (v for v in ativo.vulnerabilidades if v.id == id_vulnerabilidade), None
        )

        if alvo is None:
            raise ErroApi(
                f"O ativo não possui a vulnerabilidade {id_vulnerabilidade}.", 404
            )

        gerenciador.atualizar_status_vulnerabilidade(
            identificador, id_vulnerabilidade, novo_status
        )
        return jsonify(_vulnerabilidade_para_json(alvo))

    @app.get("/api/cve/<cve_id>")
    def pesquisar_cve(cve_id):
        """Prévia da nota de um CVE, para a interface mostrar antes de salvar."""
        cve = normalizar_cve(cve_id)

        if cve is None:
            raise ErroApi("Formato de CVE inválido. Use CVE-AAAA-NNNN.")

        dados = consultar_cve(cve)
        return jsonify({
            "id": dados.cve_id,
            "severidade": dados.nota_cvss,
            "versao_cvss": dados.versao_cvss,
            "descricao_curta": resumir(dados.descricao, 100),
            "descricao_original": dados.descricao,
        })

    # ----------------------------------------------------------- dependências
    @app.get("/api/dependencias")
    @com_trava
    def listar_dependencias():
        nomes = {a.id: a.nome for a in gerenciador.listar_ativos()}
        return jsonify([
            {
                **d.para_dict(),
                "origem_nome": nomes.get(d.ativo_origem_id),
                "destino_nome": nomes.get(d.ativo_destino_id),
            }
            for d in gerenciador_dependencias.listar_dependencias()
        ])

    @app.post("/api/dependencias")
    @com_trava
    def criar_dependencia():
        corpo = _corpo_json()
        dependencia = Dependencia(
            _inteiro(corpo, "origem"),
            _inteiro(corpo, "destino"),
            _numero(corpo, "peso"),
        )
        gerenciador_dependencias.cadastrar_dependencia(
            dependencia, gerenciador.listar_ativos()
        )

        resposta = jsonify(dependencia.para_dict())
        resposta.status_code = 201
        return resposta

    @app.delete("/api/dependencias/<int:origem>/<int:destino>")
    @com_trava
    def remover_dependencia(origem, destino):
        if not gerenciador_dependencias.remover_dependencia(origem, destino):
            raise ErroApi("Dependência não encontrada.", 404)

        return jsonify({"removida": {"origem": origem, "destino": destino}})

    # ------------------------------------------------------------------ risco
    @app.get("/api/risco")
    @com_trava
    def analisar_risco():
        ativos = gerenciador.listar_ativos()
        dependencias = gerenciador_dependencias.listar_dependencias()

        try:
            diagnostico = diagnosticar_sistema(ativos, dependencias)
            resultados = calcular_risco_efetivo(ativos, dependencias)
        except ValueError as erro:
            raise ErroApi(str(erro), 422) from erro

        if diagnostico is not None:
            # A chave interna tem acento; na API usamos um nome sem acento.
            diagnostico = dict(diagnostico)
            diagnostico["fragil"] = diagnostico.pop("frágil")

        return jsonify(_limpar({"resultados": resultados, "diagnostico": diagnostico}))

    # Respostas da API são sempre dinâmicas: o navegador não deve reaproveitá-las.
    @app.after_request
    def nao_guardar_em_cache(resposta):
        if request.path.startswith("/api/"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    return app