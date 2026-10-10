
"""Ponto de entrada do sistema de inventário de ativos."""

from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.servicos.gerenciador_ativos import GerenciadorAtivos


def ler_inteiro(mensagem, minimo=None):
    """Solicita um número inteiro válido."""
    while True:
        try:
            valor = int(input(mensagem))

            if minimo is not None and valor < minimo:
                print(f"Informe um número maior ou igual a {minimo}.")
                continue

            return valor
        except ValueError:
            print("Entrada inválida. Digite um número inteiro.")


def ler_texto(mensagem):
    """Solicita um texto não vazio."""
    while True:
        valor = input(mensagem).strip()

        if valor:
            return valor

        print("Este campo não pode ficar vazio.")


def ler_severidade():
    """Solicita uma severidade entre 0 e 10."""
    while True:
        try:
            severidade = float(input("Severidade (0 a 10): "))

            if 0 <= severidade <= 10:
                return severidade

            print("A severidade deve estar entre 0 e 10.")
        except ValueError:
            print("Digite um número válido.")


def cadastrar_vulnerabilidades():
    """Recebe as vulnerabilidades de um ativo."""
    quantidade = ler_inteiro(
        "Quantas vulnerabilidades deseja cadastrar? ",
        minimo=0,
    )

    vulnerabilidades = []

    for indice in range(quantidade):
        print(f"\n--- Vulnerabilidade {indice + 1} ---")

        descricao = ler_texto("Descrição: ")
        categoria = ler_texto("Categoria: ")
        severidade = ler_severidade()
        status = ler_texto("Status: ")

        vulnerabilidades.append(
            Vulnerabilidade(
                descricao,
                categoria,
                severidade,
                status,
            )
        )

    return vulnerabilidades


def cadastrar_ativo(gerenciador):
    """Cadastra um notebook, servidor ou roteador."""
    print("\n=== CADASTRAR ATIVO ===")
    print("1. Notebook")
    print("2. Servidor")
    print("3. Roteador")

    tipo = input("Tipo de ativo: ").strip()

    classes = {
        "1": ("Notebook", Notebook),
        "2": ("Servidor", Servidor),
        "3": ("Roteador", Roteador),
    }

    if tipo not in classes:
        print("Tipo de ativo inválido.")
        return

    nome_tipo, classe = classes[tipo]

    identificador = ler_inteiro("ID: ", minimo=1)
    nome = ler_texto("Nome: ")
    responsavel = ler_texto("Responsável: ")
    setor = ler_texto("Setor: ")
    vulnerabilidades = cadastrar_vulnerabilidades()

    if nome_tipo == "Notebook":
        detalhe = ler_texto("Memória RAM (ex.: 16GB): ")
    elif nome_tipo == "Servidor":
        detalhe = ler_texto("Processador: ")
    else:
        detalhe = ler_texto("Modelo do roteador: ")

    ativo = classe(
        identificador,
        nome,
        responsavel,
        setor,
        vulnerabilidades,
        detalhe,
    )

    try:
        gerenciador.cadastrar_ativo(ativo)
        print(f"\nAtivo '{nome}' cadastrado com sucesso.")
    except ValueError as erro:
        print(f"\nNão foi possível cadastrar: {erro}")


def consultar_ativos(gerenciador):
    """Exibe todos os ativos cadastrados."""
    ativos = gerenciador.listar_ativos()

    print("\n=== INVENTÁRIO DE ATIVOS ===")

    if not ativos:
        print("Nenhum ativo cadastrado.")
        return

    for ativo in ativos:
        print()
        ativo.exibir_detalhes()
        print(f"Tipo: {ativo.obter_tipo()}")


def consultar_por_id(gerenciador):
    """Exibe um ativo específico."""
    identificador = ler_inteiro("ID do ativo: ", minimo=1)
    ativo = gerenciador.buscar_ativo_por_id(identificador)

    if ativo is None:
        print("Ativo não encontrado.")
        return

    ativo.exibir_detalhes()
    print(f"Tipo: {ativo.obter_tipo()}")


def consultar_vulnerabilidades_do_ativo(gerenciador):
    """Lista as vulnerabilidades associadas a um ativo."""
    identificador = ler_inteiro(
        "ID do ativo: ",
        minimo=1,
    )

    ativo = gerenciador.buscar_ativo_por_id(identificador)

    if ativo is None:
        print("Ativo não encontrado.")
        return

    print(f"\n=== VULNERABILIDADES: {ativo.nome} ===")

    if not ativo.vulnerabilidades:
        print("Este ativo não possui vulnerabilidades cadastradas.")
        return

    for indice, vulnerabilidade in enumerate(
        ativo.vulnerabilidades,
        start=1,
    ):
        print(f"\n{indice}. {vulnerabilidade}")


def atualizar_ativo(gerenciador):
    """Atualiza um campo de um ativo existente."""
    identificador = ler_inteiro("ID do ativo a atualizar: ", minimo=1)
    ativo = gerenciador.buscar_ativo_por_id(identificador)

    if ativo is None:
        print("Ativo não encontrado.")
        return

    campos = {
        "1": ("nome", "Nome"),
        "2": ("responsavel", "Responsável"),
        "3": ("setor", "Setor"),
    }

    campo_especifico = {
        "Notebook": ("memoria_ram", "Memória RAM"),
        "Servidor": ("processador", "Processador"),
        "Roteador": ("modelo", "Modelo"),
    }

    chave, rotulo = campo_especifico[ativo.obter_tipo()]
    campos["4"] = (chave, rotulo)

    print("\n=== ATUALIZAR ATIVO ===")
    print("1. Nome")
    print("2. Responsável")
    print("3. Setor")
    print(f"4. {rotulo}")
    print("5. Substituir lista de vulnerabilidades")
    print("0. Cancelar")

    opcao = input("Escolha o campo: ").strip()

    if opcao == "0":
        print("Operação cancelada.")
        return

    if opcao == "5":
        alteracoes = {
            "vulnerabilidades": cadastrar_vulnerabilidades()
        }
    elif opcao in campos:
        campo, nome_campo = campos[opcao]
        alteracoes = {campo: ler_texto(f"Novo valor para {nome_campo}: ")}
    else:
        print("Opção inválida.")
        return

    try:
        gerenciador.atualizar_ativo(identificador, **alteracoes)
        print("Ativo atualizado com sucesso.")
    except (ValueError, TypeError) as erro:
        print(f"Não foi possível atualizar: {erro}")


def remover_ativo(gerenciador):
    """Solicita confirmação antes de remover um ativo."""
    identificador = ler_inteiro("ID do ativo a remover: ", minimo=1)
    ativo = gerenciador.buscar_ativo_por_id(identificador)

    if ativo is None:
        print("Ativo não encontrado.")
        return

    print(f"Ativo selecionado: {ativo.nome}")
    confirmacao = input("Confirma a remoção? (s/n): ").strip().lower()

    if confirmacao != "s":
        print("Remoção cancelada.")
        return

    if gerenciador.remover_ativo(identificador):
        print("Ativo removido com sucesso.")
    else:
        print("Não foi possível remover o ativo.")


def main():
    """Executa o menu principal do inventário."""
    gerenciador = GerenciadorAtivos("ativos.json")

    while True:
        print("\n========== INVENTÁRIO DE ATIVOS ==========")
        print("1. Cadastrar ativo")
        print("2. Consultar todos os ativos")
        print("3. Consultar ativo por ID")
        print("4. Atualizar ativo")
        print("5. Remover ativo")
        print("6. Consultar vulnerabilidades de um ativo")
        print("7. Sair")
        print("==========================================")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            cadastrar_ativo(gerenciador)
        elif opcao == "2":
            consultar_ativos(gerenciador)
        elif opcao == "3":
            consultar_por_id(gerenciador)
        elif opcao == "4":
            atualizar_ativo(gerenciador)
        elif opcao == "5":
            remover_ativo(gerenciador)
        elif opcao == "6":
            consultar_vulnerabilidades_do_ativo(gerenciador)
        elif opcao == "7":
            print("Encerrando o inventário. Até mais!")
            break
        else:
            print("Opção inválida. Escolha uma opção de 1 a 6.")


if __name__ == "__main__":
    main()
