"""Padrão Strategy: o critério de ordenação é uma peça que se troca.

`ordenar` faz sempre a mesma coisa (sorted); o que muda de um pedido para
outro é a estratégia: uma função que recebe um ativo e devolve a chave de
comparação. Em Python, funções são objetos comuns, então cada estratégia é
só uma função num dicionário, sem uma classe por critério.
"""


def _por_nome(ativo):
    return ativo.nome.casefold()


def _por_id(ativo):
    return ativo.id


def _por_setor(ativo):
    return (ativo.setor.casefold(), ativo.nome.casefold())


def _por_responsavel(ativo):
    return (ativo.responsavel.casefold(), ativo.nome.casefold())


def _por_falhas(ativo):
    return len(ativo.vulnerabilidades)


ESTRATEGIAS = {
    "nome": _por_nome,
    "id": _por_id,
    "setor": _por_setor,
    "responsavel": _por_responsavel,
    "falhas": _por_falhas,
}


def ordenar(ativos, criterio="id", decrescente=False):
    """Ordena `ativos` pelo critério escolhido. Critério inválido: ValueError."""
    try:
        chave = ESTRATEGIAS[criterio]
    except KeyError:
        validos = ", ".join(ESTRATEGIAS)
        raise ValueError(f"Critério de ordenação inválido: {criterio!r}. Use: {validos}.") from None
    return sorted(ativos, key=chave, reverse=decrescente)
