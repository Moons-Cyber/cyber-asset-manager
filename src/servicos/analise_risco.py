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
