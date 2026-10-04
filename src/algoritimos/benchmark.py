from time import perf_counter
from src.algoritimos.recursao import fatorial_recursivo, fatorial_iterativo, fibonacci_recursivo, fibonacci_memoizado

def medir_tempo(funcao, n, repeticoes=1000):
    inicio = perf_counter()

    for _ in range(repeticoes):
        funcao(n)   
    fim = perf_counter()
    return fim - inicio 

print("=== BENCHMARK DE FATORIAL ===")
tempo_iterativo = medir_tempo(fatorial_iterativo, 500)
tempo_recursivo = medir_tempo(fatorial_recursivo, 500)

print(f"Iterativo: {tempo_iterativo:.6f}s")
print(f"Recursivo: {tempo_recursivo:.6f}s")


print("\n=== BENCHMARK DE FIBONACCI ===")

tempo_recursivo = medir_tempo(fibonacci_recursivo, 30, 10)
tempo_memoizado = medir_tempo(fibonacci_memoizado, 30, 10)

print(f"Recursivo: {tempo_recursivo:.6f}s")
print(f"Memoizado: {tempo_memoizado:.6f}s")