"""Simulador de contágio: a mesma conta do risco, vista como uma epidemia.

A ideia em uma frase
--------------------
O risco efetivo x resolve  x = b + A·x,  ou seja  (I - A)x = b.
Esse mesmo x é o resultado MÉDIO de uma epidemia em que:

  * cada ativo i "espalha" uma infecção de valor b_i (o seu risco próprio);
  * cada infecção que está no ativo j atravessa a seta j -> i com
    probabilidade A[i][j] (o peso da dependência);
  * cada ativo soma o valor de todas as infecções que passaram por ele.

Por que dá o mesmo número?
  Depois de 0 saltos, a infecção de j está em j          -> conta b
  Depois de 1 salto, a chance de estar em i é A[i][j]     -> conta A·b
  Depois de 2 saltos, A²[i][j] ...                        -> conta A²·b
  Somando:  b + A·b + A²·b + ...  =  (I - A)^-1 · b  =  x
(a série só termina se o raio espectral de A for menor que 1).

Então sortear milhares de epidemias e tirar a média (método de Monte Carlo)
tem que chegar no mesmo x que o np.linalg.solve. O simulador é uma PROVA
experimental de que a conta do projeto está certa.

Epidemiologia de graça
  O raio espectral rho(A) é o "R0" da epidemia: quantas novas infecções, em
  média, cada infecção gera a longo prazo.
    rho < 1  -> o surto morre sozinho e (I - A) tem solução com significado;
    rho >= 1 -> o surto explode; a série não termina.
  A regra do projeto (soma dos pesos recebidos < 1 em cada ativo) garante
  rho < 1. Ela é suficiente, mas mais exigente do que o necessário.
"""

import numpy as np

from src.modelos.dependencia import soma_de_pesos_valida
from src.servicos.analise_risco import _diagnosticar, _montar_sistema

RODADAS_PADRAO = 2000
LIMITE_INFECCOES = 2_000_000      # acima disso o surto é declarado "fora de controle"
MAX_GERACOES = 400


# ---------------------------------------------------------------------------
# Peças da álgebra
# ---------------------------------------------------------------------------
def montar_contagio(ativos, dependencias):
    """Devolve (A, b) como arrays do NumPy, na ordem dos ativos.

    Reaproveita a montagem oficial do projeto: b = F·(M·v) e I - A.
    """
    sistema, riscos_proprios = _montar_sistema(ativos, dependencias)
    matriz_a = np.eye(len(ativos)) - sistema
    return matriz_a, np.asarray(riscos_proprios, dtype=float)


def raio_espectral(matriz_a):
    """rho(A): o maior |autovalor|. É o R0 do surto."""
    if matriz_a.size == 0:
        return 0.0
    return float(max(abs(np.linalg.eigvals(matriz_a))))


def respeita_regra_do_projeto(matriz_a):
    """A regra usada no cadastro: cada LINHA de A (pesos recebidos) soma < 1."""
    return all(soma_de_pesos_valida(float(s)) for s in matriz_a.sum(axis=1))


def resolver_exato(matriz_a, b):
    """x = (I - A)^-1 b pelo np.linalg.solve, com a conferência do resíduo.

    Devolve None quando o surto não converge (rho >= 1) ou (I - A) não é
    invertível: nesses casos não existe um risco finito com significado.
    """
    n = len(b)
    if n == 0:
        return np.zeros(0)
    if raio_espectral(matriz_a) >= 1:
        return None

    sistema = np.eye(n) - matriz_a
    if not _diagnosticar(sistema)["invertivel"]:
        return None

    x = np.linalg.solve(sistema, b)
    if not np.allclose(sistema @ x, b, rtol=1e-9, atol=1e-9):
        return None
    return x


def multiplicadores(matriz_a):
    """Quanto 1 ponto de risco próprio no ativo i vira de risco na REDE TODA.

    É a soma da coluna i de (I - A)^-1. Em vez de inverter a matriz,
    resolvemos (I - A)^T · m = [1, 1, ..., 1]  (mesmo resultado, mais preciso).
    Um ativo com multiplicador 1 não contamina ninguém.
    """
    n = matriz_a.shape[0]
    if n == 0 or raio_espectral(matriz_a) >= 1:
        return None
    return np.linalg.solve((np.eye(n) - matriz_a).T, np.ones(n))


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------
def simular_surto(matriz_a, b, rodadas=RODADAS_PADRAO, semente=None,
                  pontos_curva=40, limite=LIMITE_INFECCOES):
    """Sorteia `rodadas` epidemias e devolve a média (estimativa de x).

    Em cada rodada, cada ativo com b > 0 começa com UMA infecção. A cada
    geração, cada infecção no ativo j tenta atravessar cada seta j -> i e
    consegue com probabilidade A[i][j]. Tudo é feito "em lote" com o
    NumPy: em vez de sortear infecção por infecção, sorteamos de uma vez
    quantas das C infecções passam (distribuição binomial). É a mesma
    coisa, só que rápida.

    Retorna:
      estimativa   x̂ por ativo (média das rodadas)
      global       soma de x̂
      curva        [[rodadas_feitas, global_estimado], ...] para o gráfico
      explodiu     True se o número de infecções passou do limite de segurança.
                   Com R0 >= 1 isso sempre acontece (a epidemia não para);
                   com R0 muito perto de 1 também pode acontecer, porque
                   cada epidemia fica enorme, mesmo a série convergindo.
      geracoes     a maior "distância" (em saltos) que uma infecção andou
    """
    n = len(b)
    rng = np.random.default_rng(semente)
    origens = [j for j in range(n) if b[j] > 0]
    valor = np.asarray([b[j] for j in origens], dtype=float)
    arestas = [
        (j, i, float(matriz_a[i, j]))
        for i in range(n) for j in range(n)
        if matriz_a[i, j] > 0
    ]

    visitas = np.zeros((n, len(origens)), dtype=np.int64)   # visitas[k, o]
    curva = []
    feitas = 0
    explodiu = False
    geracao_maxima = 0

    rodadas = max(1, int(rodadas))
    lotes = max(1, min(pontos_curva, rodadas))
    tamanhos = [rodadas // lotes + (1 if k < rodadas % lotes else 0) for k in range(lotes)]

    for tamanho in tamanhos:
        if not origens:
            feitas += tamanho
            curva.append([feitas, 0.0])
            continue

        # Geração 0: `tamanho` infecções em cada origem, uma coluna por origem.
        atuais = np.zeros((n, len(origens)), dtype=np.int64)
        for coluna, j in enumerate(origens):
            atuais[j, coluna] = tamanho

        geracao = 0
        while atuais.any():
            visitas += atuais
            if visitas.sum() > limite or geracao >= MAX_GERACOES:
                explodiu = True
                break
            novas = np.zeros_like(atuais)
            for j, i, peso in arestas:
                if atuais[j].any():
                    # Peso 0,3: cada infecção passa com 30% de chance.
                    # Peso 2,4 (só com a escala): passam 2 cópias certas e
                    # uma 3ª com 40% de chance. A média continua sendo o peso.
                    inteiro = int(peso)
                    novas[i] += atuais[j] * inteiro + rng.binomial(atuais[j], peso - inteiro)
            atuais = novas
            geracao += 1

        geracao_maxima = max(geracao_maxima, geracao)
        feitas += tamanho
        estimativa = visitas @ valor / feitas
        curva.append([feitas, round(float(estimativa.sum()), 4)])
        if explodiu:
            break

    estimativa = (visitas @ valor / max(feitas, 1)) if origens else np.zeros(n)
    return {
        "rodadas": feitas,
        "estimativa": [float(v) for v in estimativa],
        "global": float(np.sum(estimativa)),
        "curva": curva,
        "explodiu": explodiu,
        "geracoes": geracao_maxima,
    }


# ---------------------------------------------------------------------------
# Defesa: qual correção derruba mais o risco?
# ---------------------------------------------------------------------------
def ranking_correcoes(ativos, matriz_a):
    """Para cada falha em aberto: quanto o risco GLOBAL cai se ela for corrigida.

    Conta (linear, sem simular nada):
      corrigir uma falha de nota s no ativo i tira F_i·s do risco próprio b_i;
      o risco global cai  F_i · s · multiplicador_i.
    """
    mult = multiplicadores(matriz_a)
    if mult is None:
        return []

    itens = []
    for i, ativo in enumerate(ativos):
        fator = float(ativo.obter_fator_exposicao())
        for vulnerabilidade in ativo.vulnerabilidades:
            if not vulnerabilidade.afeta_risco:
                continue
            nota = float(vulnerabilidade.severidade)
            itens.append({
                "ativo_id": ativo.id,
                "ativo_nome": ativo.nome,
                "vulnerabilidade_id": vulnerabilidade.id,
                "descricao": vulnerabilidade.descricao,
                "nota": nota,
                "fator": fator,
                "multiplicador": float(mult[i]),
                "queda_global": fator * nota * float(mult[i]),
            })

    itens.sort(key=lambda item: item["queda_global"], reverse=True)
    return itens


# ---------------------------------------------------------------------------
# Tudo junto, para a API
# ---------------------------------------------------------------------------
def analisar_surto(ativos, dependencias, escala=1.0, rodadas=RODADAS_PADRAO,
                   semente=None):
    """Monta, resolve, simula e compara. `escala` multiplica TODOS os pesos
    (só na simulação, nunca nos dados) para mostrar o surto explodindo."""
    matriz_real, b = montar_contagio(ativos, dependencias)
    matriz_a = matriz_real * float(escala)
    n = len(ativos)

    rho = raio_espectral(matriz_a)
    sistema = np.eye(n) - matriz_a
    diagnostico = _diagnosticar(sistema) if n else None
    x = resolver_exato(matriz_a, b)
    mc = simular_surto(matriz_a, b, rodadas=rodadas, semente=semente)
    mult = multiplicadores(matriz_a)

    erro_relativo = None
    if x is not None and float(np.sum(x)) > 0 and not mc["explodiu"]:
        erro_relativo = abs(mc["global"] - float(np.sum(x))) / float(np.sum(x))

    return {
        "n": n,
        "escala": float(escala),
        "A": matriz_a.tolist(),
        "b": b.tolist(),
        "x": None if x is None else x.tolist(),
        "risco_global": None if x is None else float(np.sum(x)),
        "multiplicadores": None if mult is None else mult.tolist(),
        "rho": rho,
        "convergente": rho < 1,
        "regra_do_projeto": respeita_regra_do_projeto(matriz_a),
        "diagnostico": diagnostico,
        "monte_carlo": mc,
        "erro_relativo": erro_relativo,
        # O ranking usa sempre os pesos REAIS: as correções mexem nos dados.
        "ranking": ranking_correcoes(ativos, matriz_real),
    }
