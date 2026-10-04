from functools import reduce


def obter_nomes(ativos):
    return list(map(lambda ativo: ativo.nome, ativos))


def filtrar_por_tipo(ativos, tipo):
    return list(filter(lambda ativo: isinstance(ativo, tipo), ativos))


def ordenar_por_nome(ativos):
    return sorted (ativos, key=lambda ativo: ativo.nome)


def contar_vulnerabilidades(ativos):
    return reduce(lambda total, ativo: total + len(ativo.vulnerabilidades), ativos, 0)


def buscar_por_nome_recursivo(ativos, nome, indice=0):
    if indice >= len(ativos):
        return None
    if ativos[indice].nome == nome:
        return ativos[indice]
    return buscar_por_nome_recursivo(ativos, nome, indice + 1)