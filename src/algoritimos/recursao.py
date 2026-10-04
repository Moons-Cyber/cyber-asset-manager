def fatorial_iterativo(n):
    resultado = 1
    for numero in range (1, n + 1):
        resultado *= numero
    return resultado

def fatorial_recursivo(n):
    if n == 0 or n == 1:
        return 1
    return n * fatorial_recursivo(n - 1)
 
def fibonacci_recursivo(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci_recursivo(n - 1) + fibonacci_recursivo(n - 2)


def fibonacci_memoizado(n, memoria=None):
    if memoria is None:
        memoria = {}

    if n in memoria:
        return memoria[n]

    if n <= 0:
        return 0

    if n == 1:
        return 1

    resultado = (
        fibonacci_memoizado(n - 1, memoria)
        + fibonacci_memoizado(n - 2, memoria)
    )

    memoria[n] = resultado

    return resultado