import numpy as np 


"""Funções para construir o modelo de risco próprio dos ativos."""


def _chave_vulnerabilidade(vulnerabilidade):
    """Identifica a coluna de M pelo par (ID, nota).

    - O STATUS fica de fora: mudar de "Aberta" para "Em tratamento" não pode
      criar uma vulnerabilidade nova.
    - A NOTA entra na chave porque cada coluna de M tem UMA nota em v. Sem
      isso, duas vulnerabilidades com o mesmo ID e notas diferentes (ex.: a
      mesma descrição manual com nota 10 num ativo e 5 em outro, ou um CVE
      com nota do NVD num ativo e digitada em outro) cairiam na mesma coluna
      e a segunda nota seria descartada em silêncio, errando o risco.
    Mesmo ID com a mesma nota continua compartilhando a coluna.
    """
    return (vulnerabilidade.id, float(vulnerabilidade.severidade))


def construir_matriz_incidencia(ativos):
    """
    Constrói a matriz M e o vetor v a partir dos ativos.

    Retorna:
        matriz: linhas representam ativos e colunas representam
            vulnerabilidades distintas.
        severidades: severidade de cada vulnerabilidade, na mesma
            ordem das colunas da matriz.
        rotulos: dados das vulnerabilidades que identificam as colunas.
    """
    indices = {}
    rotulos = []

    # Registra cada vulnerabilidade distinta na ordem de aparição.
    for ativo in ativos:
        for vulnerabilidade in ativo.vulnerabilidades:
            # Corrigida não afeta mais o ativo: fica fora de M.
            if not vulnerabilidade.afeta_risco:
                continue

            chave = _chave_vulnerabilidade(vulnerabilidade)

            if chave not in indices:
                indices[chave] = len(rotulos)
                rotulos.append(
                    {
                        "descricao": vulnerabilidade.descricao,
                        "categoria": vulnerabilidade.categoria,
                        "severidade": float(vulnerabilidade.severidade),
                        "status": vulnerabilidade.status.value,
                    }
                )

    # Inicializa M com zeros: uma linha por ativo.
    matriz = [
        [0] * len(rotulos)
        for _ in ativos
    ]

    # Marca com 1 as vulnerabilidades associadas a cada ativo.
    for indice_ativo, ativo in enumerate(ativos):
        for vulnerabilidade in ativo.vulnerabilidades:
            if not vulnerabilidade.afeta_risco:
                continue

            chave = _chave_vulnerabilidade(vulnerabilidade)
            indice_coluna = indices[chave]
            matriz[indice_ativo][indice_coluna] = 1

    severidades = [
        vulnerabilidade["severidade"]
        for vulnerabilidade in rotulos
    ]

    return matriz, severidades, rotulos


def multiplicar_matriz_vetor(matriz, vetor):
    """Calcula o produto de uma matriz por um vetor."""
    for linha in matriz:
        if len(linha) != len(vetor):
            raise ValueError(
                "As colunas da matriz devem corresponder "
                "ao tamanho do vetor."
            )

    return [
        sum(
            coeficiente * vetor[indice]
            for indice, coeficiente in enumerate(linha)
        )
        for linha in matriz
    ]


def construir_matriz_dependencias(ativos, dependencias):
    """
    Constrói a matriz A na ordem dos ativos recebidos.

    A[i][j] representa a fração do risco do ativo j
    transmitida ao ativo i.
    """
    ids_ativos = [ativo.id for ativo in ativos]

    if len(set(ids_ativos)) != len(ids_ativos):
        raise ValueError("Existem IDs de ativos duplicados.")

    indice_por_id = {
        identificador: indice
        for indice, identificador in enumerate(ids_ativos)
    }

    quantidade = len(ativos)

    matriz = [
        [0.0] * quantidade
        for _ in range(quantidade)
    ]

    pares_cadastrados = set()

    for dependencia in dependencias:
        origem = dependencia.ativo_origem_id
        destino = dependencia.ativo_destino_id
        peso = dependencia.peso

        if origem not in indice_por_id:
            raise ValueError(
                f"O ativo de origem {origem} não existe."
            )

        if destino not in indice_por_id:
            raise ValueError(
                f"O ativo de destino {destino} não existe."
            )

        if origem == destino:
            raise ValueError(
                "Um ativo não pode depender de si mesmo."
            )

        if not 0 <= peso < 1:
            raise ValueError(
                "O peso deve estar entre 0 e 1, excluindo 1."
            )

        par = (origem, destino)

        if par in pares_cadastrados:
            raise ValueError(
                f"Dependência duplicada: {origem} -> {destino}."
            )

        pares_cadastrados.add(par)

        indice_origem = indice_por_id[origem]
        indice_destino = indice_por_id[destino]

        matriz[indice_destino][indice_origem] = float(peso)

    for indice, linha in enumerate(matriz):
        soma_pesos = sum(linha)

        if soma_pesos >= 1:
            identificador = ids_ativos[indice]

            raise ValueError(
                f"A soma dos pesos recebidos pelo ativo "
                f"{identificador} deve ser menor que 1."
            )

    return matriz



# Limites usados para julgar a confiabilidade numérica do sistema.
LIMITE_CONDICAO_SINGULAR = 1e12   # acima disso, tratamos como não invertível
LIMITE_CONDICAO_ALERTA = 1e6      # acima disso, avisamos que a solução é frágil


def _montar_sistema(ativos, dependencias):
    """Monta (I - A) e o vetor b = M v a partir dos dados persistidos."""
    matriz_incidencia, severidades, _ = construir_matriz_incidencia(ativos)
    riscos_proprios = multiplicar_matriz_vetor(matriz_incidencia, severidades)
    matriz_dependencias = construir_matriz_dependencias(ativos, dependencias)

    sistema = np.eye(len(ativos)) - np.asarray(matriz_dependencias, dtype=float)
    return sistema, riscos_proprios


def _diagnosticar(sistema):
    """Avalia se (I - A) pode ser resolvida com confiança.

    Três medidas:
      * posto: precisa ser n (posto cheio);
      * número de condição: mede quanto um erro pequeno nos dados é
        ampliado na solução. Perto de infinito = quase singular;
      * determinante: informativo. NÃO decide sozinho, porque o seu valor
        depende do tamanho do sistema (com muitos ativos, um determinante
        legítimo pode ser minúsculo) e porque em ponto flutuante um
        determinante "zero" quase nunca é exatamente 0.
    """
    n = sistema.shape[0]
    posto = int(np.linalg.matrix_rank(sistema))
    determinante = float(np.linalg.det(sistema))

    try:
        condicao = float(np.linalg.cond(sistema))
    except np.linalg.LinAlgError:
        condicao = float("inf")

    return {
        "ordem": n,
        "posto": posto,
        "determinante": determinante,
        "condicao": condicao,
        "invertivel": posto == n and condicao < LIMITE_CONDICAO_SINGULAR,
        "frágil": condicao > LIMITE_CONDICAO_ALERTA,
    }


def diagnosticar_sistema(ativos, dependencias):
    """Devolve o diagnóstico de (I - A), ou None se não há ativos."""
    if not ativos:
        return None

    sistema, _ = _montar_sistema(ativos, dependencias)
    return _diagnosticar(sistema)


def calcular_risco_efetivo(ativos, dependencias):
    """
    Calcula o risco próprio e o risco efetivo de cada ativo.

    Resolve (I - A)x = b, verificando a invertibilidade antes de resolver.
    Usa np.linalg.solve (e não a inversa), que é mais preciso e rápido.
    """
    if not ativos:
        return []

    sistema, riscos_proprios = _montar_sistema(ativos, dependencias)
    diagnostico = _diagnosticar(sistema)

    if not diagnostico["invertivel"]:
        raise ValueError(
            "A matriz I - A não é invertível (ou é numericamente "
            "singular); não é possível calcular o risco efetivo."
        )

    try:
        riscos_efetivos = np.linalg.solve(
            sistema,
            np.asarray(riscos_proprios, dtype=float),
        )
    except np.linalg.LinAlgError as erro:
        raise ValueError("Não foi possível resolver o sistema de risco.") from erro

    return [
        {
            "id": ativo.id,
            "nome": ativo.nome,
            "risco_proprio": float(riscos_proprios[indice]),
            "risco_efetivo": float(riscos_efetivos[indice]),
        }
        for indice, ativo in enumerate(ativos)
    ]