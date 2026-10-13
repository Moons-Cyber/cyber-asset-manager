"""Funções para construir o modelo de risco próprio dos ativos."""


def _chave_vulnerabilidade(vulnerabilidade):
    """Cria uma chave para identificar uma vulnerabilidade."""
    return (
        vulnerabilidade.descricao,
        vulnerabilidade.categoria,
        float(vulnerabilidade.severidade),
        vulnerabilidade.status,
    )


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
            chave = _chave_vulnerabilidade(vulnerabilidade)

            if chave not in indices:
                indices[chave] = len(rotulos)
                rotulos.append(
                    {
                        "descricao": vulnerabilidade.descricao,
                        "categoria": vulnerabilidade.categoria,
                        "severidade": float(vulnerabilidade.severidade),
                        "status": vulnerabilidade.status,
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