from src.algoritimos.busca_ordenacao import (
    busca_linear,
    busca_binaria,
    bubble_sort,
    selection_sort,
    insertion_sort,
)

numeros = [8, 3, 5, 1, 9, 2]

for nome, algoritmo in [
    ("Bubble Sort", bubble_sort),
    ("Selection Sort", selection_sort),
    ("Insertion Sort", insertion_sort),
]:
    ordenados, comparacoes = algoritmo(numeros)
    print(f"{nome}: {ordenados} | Comparações: {comparacoes}")

print("Busca linear:", busca_linear(numeros, 9))

ordenados = sorted(numeros)
print("Busca binária:", busca_binaria(ordenados, 9))