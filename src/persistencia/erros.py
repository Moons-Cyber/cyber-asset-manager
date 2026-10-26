"""Erros da camada de persistência."""


class ErroDados(ValueError):
    """Os dados gravados em disco estão ilegíveis ou inconsistentes.

    É um ValueError (o menu e o resto do código que já capturam ValueError
    continuam funcionando), mas permite à API distinguir "arquivo de dados
    corrompido", que é falha do SERVIDOR (503), de "entrada inválida do
    cliente", que é falha de quem pediu (400).
    """
