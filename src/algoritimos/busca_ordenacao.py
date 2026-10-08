def identidade(item):
    """Retorna o próprio item quando nenhuma chave é informada."""
    return item


def busca_linear(itens, alvo, chave=identidade):
    """Busca um elemento percorrendo a lista do início ao fim."""
    comparacoes = 0

    for indice, item in enumerate(itens):
        comparacoes += 1

        if chave(item) == alvo:
            return indice, comparacoes

    return None, comparacoes


def busca_binaria(itens, alvo, chave=identidade):
    """
    Busca um elemento em uma lista já ordenada.
    Retorna (índice, comparações).
    """
    inicio = 0
    fim = len(itens) - 1
    comparacoes = 0

    while inicio <= fim:
        meio = (inicio + fim) // 2
        valor = chave(itens[meio])

        comparacoes += 1
        if valor == alvo:
            return meio, comparacoes

        comparacoes += 1
        if valor < alvo:
            inicio = meio + 1
        else:
            fim = meio - 1

    return None, comparacoes


def bubble_sort(itens, chave=identidade):
    """Ordena por trocas entre elementos adjacentes."""
    resultado = list(itens)
    comparacoes = 0

    for fim in range(len(resultado) - 1, 0, -1):
        houve_troca = False

        for i in range(fim):
            comparacoes += 1

            if chave(resultado[i]) > chave(resultado[i + 1]):
                resultado[i], resultado[i + 1] = (
                    resultado[i + 1],
                    resultado[i],
                )
                houve_troca = True

        if not houve_troca:
            break

    return resultado, comparacoes


def selection_sort(itens, chave=identidade):
    """Ordena selecionando o menor elemento restante."""
    resultado = list(itens)
    comparacoes = 0

    for i in range(len(resultado) - 1):
        menor = i

        for j in range(i + 1, len(resultado)):
            comparacoes += 1

            if chave(resultado[j]) < chave(resultado[menor]):
                menor = j

        if menor != i:
            resultado[i], resultado[menor] = (
                resultado[menor],
                resultado[i],
            )

    return resultado, comparacoes


def insertion_sort(itens, chave=identidade):
    """Ordena inserindo cada elemento na posição correta."""
    resultado = list(itens)
    comparacoes = 0

    for i in range(1, len(resultado)):
        atual = resultado[i]
        chave_atual = chave(atual)
        j = i - 1

        while j >= 0:
            comparacoes += 1

            if chave(resultado[j]) > chave_atual:
                resultado[j + 1] = resultado[j]
                j -= 1
            else:
                break

        resultado[j + 1] = atual

    return resultado, comparacoes