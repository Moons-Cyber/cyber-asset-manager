from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.persistencia import Persistencia

from src.servicos.consultas import (
    obter_nomes,
    filtrar_por_tipo,
    ordenar_por_nome,
    contar_vulnerabilidades
)


def main():

    # =========================
    # VULNERABILIDADES
    # =========================

    vuln1 = Vulnerabilidade(
        "Windows desatualizado",
        "Atualização",
        8.5,
        "Aberta"
    )

    vuln2 = Vulnerabilidade(
        "Senha fraca",
        "Segurança",
        7.0,
        "Em tratamento"
    )

    vuln3 = Vulnerabilidade(
        "Firmware desatualizado",
        "Atualização",
        6.0,
        "Aberta"
    )

    vuln4 = Vulnerabilidade(
        "Porta aberta",
        "Segurança",
        9.0,
        "Aberta"
    )


    vuln5 = Vulnerabilidade(
        "Sistema operacional desatualizado",
        "Atualização", 
        8.0,
        "Em tratamento"
    )     
    
    # =========================
    # ATIVOS
    # =========================

    notebook1 = Notebook(
        1,
        "Notebook A",
        "João",
        "TI",
        [vuln1, vuln2],
        "16GB"
    )

    roteador1 = Roteador(
        2,
        "Roteador B",
        "Maria",
        "Redes",
        [vuln3],
        "Modelo X"
    )

    servidor1 = Servidor(
        3,
        "Servidor C",
        "Carlos",
        "Infraestrutura",
        [vuln4, vuln5],
        "Intel Xeon"
    )


    ativos = [notebook1, roteador1, servidor1]

    # =========================
    # PERSISTÊNCIA
    # =========================

    persistencia = Persistencia()

    persistencia.salvar_dados(
        ativos,
        "ativos.json"
    )

    ativos = persistencia.carregar_dados(
        "ativos.json"
    )

    print(type(ativos[0].vulnerabilidades[0]))
    print(ativos[0].vulnerabilidades[0].descricao)
    print(ativos[0].vulnerabilidades[0].severidade)
    
    # =========================
    # CONSULTAR TODOS OS ATIVOS
    # =========================

    print("=== TODOS OS ATIVOS ===")

    for ativo in ativos:
        ativo.exibir_detalhes()
        print(f"Tipo: {ativo.obter_tipo()}")
        print()

    # =========================
    # MAP - NOMES DOS ATIVOS
    # =========================

    print("=== NOMES DOS ATIVOS ===")

    print(obter_nomes(ativos))

    # =========================
    # FILTER - SERVIDORES
    # =========================

    servidores = filtrar_por_tipo(
        ativos,
        Servidor
    )

    print("\n=== SERVIDORES ===")

    for servidor in servidores:
        servidor.exibir_detalhes()
        print(f"Tipo: {servidor.obter_tipo()}")
        print()

    # =========================
    # LAMBDA - ORDENAÇÃO
    # =========================

    print("=== ATIVOS ORDENADOS POR NOME ===")

    for ativo in ordenar_por_nome(ativos):
        print(ativo.nome)

    # =========================
    # REDUCE - TOTAL DE VULNERABILIDADES
    # =========================

    print("\n=== TOTAL DE VULNERABILIDADES ===")

    print(contar_vulnerabilidades(ativos))

    # =========================
    # TESTE DE VULNERABILIDADES
    # =========================

    print("\n=== VULNERABILIDADES ===")

    print(vuln1.descricao)
    print(vuln1.categoria)
    print(vuln1.severidade)
    print(vuln1.status)

    print()

    print(vuln2.descricao)
    print(vuln2.categoria)
    print(vuln2.severidade)
    print(vuln2.status)
    


if __name__ == "__main__":
    main()

    