import random

from src.algoritimos.busca_ordenacao import (
    busca_linear,
    busca_binaria,
    bubble_sort,
    selection_sort,
    insertion_sort,
)


def testar_ordenacao():
    tamanhos = [10, 50, 100, 200]
    algoritmos = [
        ("Bubble Sort", bubble_sort),
        ("Selection Sort", selection_sort),
        ("Insertion Sort", insertion_sort),
    ]

    print("\n=== COMPARAÇÃO DOS ALGORITMOS DE ORDENAÇÃO ===")
    print(
        f"{'Tamanho':>8} | {'Cenário':<10} | "
        f"{'Bubble':>8} | {'Selection':>10} | {'Insertion':>10}"
    )
    print("-" * 65)

    for tamanho in tamanhos:
        gerador = random.Random(42)
        aleatorios = gerador.sample(
            range(tamanho * 10),
            tamanho,
        )

        cenarios = {
            "Ordenado": list(range(tamanho)),
            "Invertido": list(range(tamanho - 1, -1, -1)),
            "Aleatorio": aleatorios,
        }

        for nome_cenario, dados in cenarios.items():
            resultados = []

            for _, algoritmo in algoritmos:
                _, comparacoes = algoritmo(dados)
                resultados.append(comparacoes)

            print(
                f"{tamanho:>8} | {nome_cenario:<10} | "
                f"{resultados[0]:>8} | "
                f"{resultados[1]:>10} | "
                f"{resultados[2]:>10}"
            )


def testar_buscas():
    tamanhos = [10, 50, 100, 200]

    print("\n=== COMPARAÇÃO DOS ALGORITMOS DE BUSCA ===")
    print(
        f"{'Tamanho':>8} | {'Linear':>8} | "
        f"{'Binaria':>8} | {'Encontrado':>10}"
    )
    print("-" * 45)

    for tamanho in tamanhos:
        dados = list(range(tamanho))
        alvo = tamanho - 1

        indice_linear, comp_linear = busca_linear(dados, alvo)
        indice_binaria, comp_binaria = busca_binaria(dados, alvo)

        assert indice_linear == indice_binaria

        print(
            f"{tamanho:>8} | {comp_linear:>8} | "
            f"{comp_binaria:>8} | {str(indice_binaria):>10}"
        )


if __name__ == "__main__":
    testar_ordenacao()
    testar_buscas()