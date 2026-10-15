
"""Ponto de entrada do Cyber Asset Manager."""

from src.modelos.dependencia import Dependencia
from src.modelos.enums import StatusVulnerabilidade, TipoAtivo
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import (
    Vulnerabilidade,
    normalizar_cve,
    resumir,
)
from src.servicos.analise_risco import (
    calcular_risco_efetivo,
    diagnosticar_sistema,
)
from src.servicos.cliente_nvd import ClienteNVD, ErroNVD
from src.servicos.gerenciador_ativos import GerenciadorAtivos
from src.servicos.gerenciador_dependencias import GerenciadorDependencias


# Tipos que possuem uma classe implementada.
TIPOS_DISPONIVEIS = {
    TipoAtivo.NOTEBOOK: (Notebook, "Memória RAM (ex.: 16GB): "),
    TipoAtivo.SERVIDOR: (Servidor, "Processador: "),
    TipoAtivo.ROTEADOR: (Roteador, "Modelo do roteador: "),
}


# ============================================================
# ENTRADAS E VALIDAÇÕES
# ============================================================

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


def ler_nota():
    """Solicita uma nota CVSS entre 0 e 10."""
    while True:
        try:
            nota = float(input("Nota CVSS (0 a 10): ").replace(",", "."))

            if 0 <= nota <= 10:
                return nota

            print("A nota deve estar entre 0 e 10.")
        except ValueError:
            print("Digite um número válido.")


def ler_peso():
    """Solicita o peso de uma dependência entre 0 e 1."""
    while True:
        try:
            peso = float(
                input("Peso da dependência (0 a 0,99): ").replace(",", ".")
            )

            if 0 <= peso < 1:
                return peso

            print("O peso deve ser maior ou igual a 0 e menor que 1.")
        except ValueError:
            print("Digite um número válido.")


def ler_status():
    """Apresenta os status disponíveis e devolve o escolhido."""
    opcoes = list(StatusVulnerabilidade)

    print("\nStatus:")
    for numero, status in enumerate(opcoes, start=1):
        print(f"  {numero}. {status.value}")

    while True:
        escolha = ler_inteiro("Escolha o status: ", minimo=1)

        if escolha <= len(opcoes):
            return opcoes[escolha - 1]

        print(f"Escolha um número de 1 a {len(opcoes)}.")


def ler_vulnerabilidade(cliente_nvd):
    """Cadastra uma vulnerabilidade manualmente ou por meio de um CVE."""
    cve = None

    while True:
        entrada = input(
            "CVE (ex.: CVE-2021-44228) ou Enter para cadastro manual: "
        ).strip()

        if not entrada:
            break

        cve = normalizar_cve(entrada)

        if cve:
            break

        print(
            "Formato inválido. Use CVE-AAAA-NNNN "
            "(ex.: CVE-2021-44228)."
        )

    # Cadastro manual.
    if cve is None:
        descricao = ler_texto("Descrição: ")
        categoria = ler_texto("Categoria: ")
        nota = ler_nota()
        status = ler_status()

        return Vulnerabilidade(descricao, categoria, nota, status)

    # Consulta ao NVD.
    descricao_nvd = None
    fonte = "manual"

    print(f"Consultando {cve} no NVD...")

    try:
        dados = cliente_nvd.consultar(cve)
        nota = dados.nota_cvss
        descricao_nvd = dados.descricao
        fonte = "NVD"

        print(f"Nota CVSS encontrada: {nota} ({dados.versao_cvss})")
    except ErroNVD as erro:
        print(f"Não foi possível obter a nota automaticamente: {erro}")
        print("Informe a nota manualmente.")
        nota = ler_nota()

    if descricao_nvd:
        sugestao = resumir(descricao_nvd, 100)
        print(f"Resumo do NVD (em inglês): {sugestao}")

        digitada = input(
            "Descrição curta em português "
            "(Enter para usar o resumo acima): "
        ).strip()

        descricao = digitada or sugestao
    else:
        descricao = ler_texto("Descrição: ")

    categoria = ler_texto("Categoria: ")
    status = ler_status()

    return Vulnerabilidade(
        descricao,
        categoria,
        nota,
        status,
        id=cve,
        fonte=fonte,
        descricao_original=descricao_nvd,
    )


def cadastrar_vulnerabilidades(cliente_nvd):
    """Recebe as vulnerabilidades iniciais de um ativo."""
    quantidade = ler_inteiro(
        "Quantas vulnerabilidades deseja cadastrar? ",
        minimo=0,
    )

    vulnerabilidades = []

    for indice in range(quantidade):
        print(f"\n--- Vulnerabilidade {indice + 1} ---")
        vulnerabilidade = ler_vulnerabilidade(cliente_nvd)

        if any(v.id == vulnerabilidade.id for v in vulnerabilidades):
            print(
                f"{vulnerabilidade.id} já foi informada para este ativo."
            )
            continue

        vulnerabilidades.append(vulnerabilidade)

    return vulnerabilidades


# ============================================================
# OPERAÇÕES DE ATIVOS
# ============================================================

def cadastrar_ativo(gerenciador, cliente_nvd):
    """Cadastra um ativo do tipo disponível."""
    print("\n=== CADASTRAR ATIVO ===")
    print("Tipos de ativo:")

    for tipo in TIPOS_DISPONIVEIS:
        nome_tipo = tipo.name.replace("_", " ").title()
        print(f"  {tipo.value}. {nome_tipo}")

    codigo = ler_inteiro("Código do tipo: ", minimo=1)

    try:
        tipo = TipoAtivo(codigo)
    except ValueError:
        print("Código de tipo inexistente.")
        return

    if tipo not in TIPOS_DISPONIVEIS:
        print("Esse tipo ainda não está disponível para cadastro.")
        return

    classe, texto_detalhe = TIPOS_DISPONIVEIS[tipo]

    identificador = ler_inteiro("ID: ", minimo=1)
    nome = ler_texto("Nome: ")
    responsavel = ler_texto("Responsável: ")
    setor = ler_texto("Setor: ")
    detalhe = ler_texto(texto_detalhe)
    vulnerabilidades = cadastrar_vulnerabilidades(cliente_nvd)

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


def buscar_ativo(gerenciador):
    """Busca ativos por ID ou por nome."""
    print("\n=== BUSCAR ATIVO ===")
    print("1. Por ID")
    print("2. Por nome")

    opcao = input("Escolha: ").strip()

    if opcao == "1":
        identificador = ler_inteiro("ID do ativo: ", minimo=1)
        ativo = gerenciador.buscar_ativo_por_id(identificador)
        encontrados = [ativo] if ativo else []
    elif opcao == "2":
        nome = ler_texto("Nome ou parte do nome: ")
        encontrados = gerenciador.buscar_ativos_por_nome(nome)
    else:
        print("Opção inválida.")
        return

    if not encontrados:
        print("Nenhum ativo encontrado.")
        return

    print(f"\n{len(encontrados)} ativo(s) encontrado(s):")

    for ativo in encontrados:
        print()
        ativo.exibir_detalhes()
        print(f"Tipo: {ativo.obter_tipo()}")


def atualizar_ativo(gerenciador, cliente_nvd):
    """Atualiza um campo de um ativo existente."""
    identificador = ler_inteiro(
        "ID do ativo a atualizar: ",
        minimo=1,
    )
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
    print("5. Substituir toda a lista de vulnerabilidades")
    print("0. Cancelar")

    opcao = input("Escolha o campo: ").strip()

    if opcao == "0":
        print("Operação cancelada.")
        return

    if opcao == "5":
        alteracoes = {
            "vulnerabilidades": cadastrar_vulnerabilidades(cliente_nvd)
        }
    elif opcao in campos:
        campo, nome_campo = campos[opcao]
        alteracoes = {
            campo: ler_texto(f"Novo valor para {nome_campo}: ")
        }
    else:
        print("Opção inválida.")
        return

    try:
        gerenciador.atualizar_ativo(identificador, **alteracoes)
        print("Ativo atualizado com sucesso.")
    except (ValueError, TypeError) as erro:
        print(f"Não foi possível atualizar: {erro}")


def remover_ativo(gerenciador, gerenciador_dependencias):
    """Remove um ativo e as dependências associadas."""
    identificador = ler_inteiro(
        "ID do ativo a remover: ",
        minimo=1,
    )
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
        removidas = (
            gerenciador_dependencias.remover_dependencias_do_ativo(
                identificador
            )
        )

        print("Ativo removido com sucesso.")

        if removidas:
            print(
                f"{removidas} dependência(s) ligada(s) a ele "
                "também removida(s)."
            )
    else:
        print("Não foi possível remover o ativo.")


# ============================================================
# OPERAÇÕES DE VULNERABILIDADES
# ============================================================

def consultar_vulnerabilidades_do_ativo(gerenciador):
    """Lista as vulnerabilidades associadas a um ativo."""
    identificador = ler_inteiro("ID do ativo: ", minimo=1)
    ativo = gerenciador.buscar_ativo_por_id(identificador)

    if ativo is None:
        print("Ativo não encontrado.")
        return

    print(f"\n=== VULNERABILIDADES: {ativo.nome} ===")

    if not ativo.vulnerabilidades:
        print("Este ativo está sem vulnerabilidades registradas.")
        return

    for indice, vulnerabilidade in enumerate(
        ativo.vulnerabilidades,
        start=1,
    ):
        print(f"\n{indice}. {vulnerabilidade}")


def adicionar_vulnerabilidade_ao_ativo(gerenciador, cliente_nvd):
    """Acrescenta uma vulnerabilidade a um ativo existente."""
    identificador = ler_inteiro("ID do ativo: ", minimo=1)
    ativo = gerenciador.buscar_ativo_por_id(identificador)

    if ativo is None:
        print("Ativo não encontrado.")
        return

    print(f"Ativo selecionado: {ativo.nome}")
    vulnerabilidade = ler_vulnerabilidade(cliente_nvd)

    try:
        gerenciador.adicionar_vulnerabilidade(
            identificador,
            vulnerabilidade,
        )
        print(f"{vulnerabilidade.id} adicionada a '{ativo.nome}'.")
    except ValueError as erro:
        print(f"Não foi possível adicionar: {erro}")


def atualizar_status_da_vulnerabilidade(gerenciador):
    """Altera o status de uma vulnerabilidade de um ativo."""
    identificador = ler_inteiro("ID do ativo: ", minimo=1)
    ativo = gerenciador.buscar_ativo_por_id(identificador)

    if ativo is None:
        print("Ativo não encontrado.")
        return

    if not ativo.vulnerabilidades:
        print("Este ativo está sem vulnerabilidades registradas.")
        return

    for indice, vulnerabilidade in enumerate(
        ativo.vulnerabilidades,
        start=1,
    ):
        print(f"{indice}. {vulnerabilidade}")

    while True:
        escolha = ler_inteiro(
            "Número da vulnerabilidade: ",
            minimo=1,
        )

        if escolha <= len(ativo.vulnerabilidades):
            break

        print(
            f"Escolha um número de 1 a "
            f"{len(ativo.vulnerabilidades)}."
        )

    alvo = ativo.vulnerabilidades[escolha - 1]
    novo_status = ler_status()

    try:
        gerenciador.atualizar_status_vulnerabilidade(
            identificador,
            alvo.id,
            novo_status,
        )
        print(
            f"Status de {alvo.id} alterado para "
            f"'{novo_status.value}'."
        )
    except ValueError as erro:
        print(f"Não foi possível atualizar: {erro}")


# ============================================================
# OPERAÇÕES DE DEPENDÊNCIAS
# ============================================================

def cadastrar_dependencia(gerenciador, gerenciador_dependencias):
    """Cadastra uma dependência entre dois ativos."""
    ativos = gerenciador.listar_ativos()

    if len(ativos) < 2:
        print("São necessários pelo menos 2 ativos cadastrados.")
        return

    print("\n=== CADASTRAR DEPENDÊNCIA ===")

    for ativo in ativos:
        print(f"  {ativo.id}. {ativo.nome}")

    print(
        "\nO risco do ativo de ORIGEM é transmitido "
        "ao ativo de DESTINO."
    )
    print(
        "Ex.: um servidor depende de um banco de dados: "
        "origem = banco, destino = servidor."
    )

    origem = ler_inteiro(
        "ID do ativo de origem (transmite o risco): ",
        minimo=1,
    )
    destino = ler_inteiro(
        "ID do ativo de destino (recebe o risco): ",
        minimo=1,
    )
    peso = ler_peso()

    try:
        dependencia = Dependencia(origem, destino, peso)
        gerenciador_dependencias.cadastrar_dependencia(
            dependencia,
            ativos,
        )
        print(f"Dependência cadastrada: {dependencia}")
    except ValueError as erro:
        print(f"Não foi possível cadastrar: {erro}")


def listar_dependencias(gerenciador, gerenciador_dependencias):
    """Lista dependências com os nomes dos ativos."""
    dependencias = gerenciador_dependencias.listar_dependencias()

    print("\n=== DEPENDÊNCIAS ===")

    if not dependencias:
        print("Nenhuma dependência cadastrada.")
        return

    nomes = {
        ativo.id: ativo.nome
        for ativo in gerenciador.listar_ativos()
    }

    for numero, dependencia in enumerate(dependencias, start=1):
        origem = nomes.get(dependencia.ativo_origem_id, "?")
        destino = nomes.get(dependencia.ativo_destino_id, "?")

        print(
            f"{numero}. {origem} (ID {dependencia.ativo_origem_id}) -> "
            f"{destino} (ID {dependencia.ativo_destino_id}) | "
            f"peso {dependencia.peso:.2f}"
        )


def remover_dependencia(gerenciador, gerenciador_dependencias):
    """Remove uma dependência escolhida pelo usuário."""
    dependencias = gerenciador_dependencias.listar_dependencias()

    if not dependencias:
        print("Nenhuma dependência cadastrada.")
        return

    listar_dependencias(gerenciador, gerenciador_dependencias)

    while True:
        escolha = ler_inteiro(
            "Número da dependência a remover: ",
            minimo=1,
        )

        if escolha <= len(dependencias):
            break

        print(f"Escolha um número de 1 a {len(dependencias)}.")

    alvo = dependencias[escolha - 1]

    removida = gerenciador_dependencias.remover_dependencia(
        alvo.ativo_origem_id,
        alvo.ativo_destino_id,
    )

    print(
        "Dependência removida."
        if removida
        else "Dependência não encontrada."
    )


# ============================================================
# ANÁLISE DE RISCO
# ============================================================

def analisar_risco(gerenciador_ativos, gerenciador_dependencias):
    """Calcula e exibe o risco próprio e efetivo dos ativos."""
    ativos = gerenciador_ativos.listar_ativos()

    if not ativos:
        print("Nenhum ativo cadastrado para análise.")
        return

    dependencias = gerenciador_dependencias.listar_dependencias()

    print("\n=== ANÁLISE DE RISCO ===")

    diagnostico = diagnosticar_sistema(ativos, dependencias)

    if diagnostico["frágil"]:
        print(
            "ATENÇÃO: número de condição alto "
            f"({diagnostico['condicao']:.4g}); "
            "a solução pode ser pouco confiável."
        )

    resultados = calcular_risco_efetivo(ativos, dependencias)

    for resultado in resultados:
        print(
            f"\nID: {resultado['id']} | Ativo: {resultado['nome']}\n"
            f"  Risco próprio: {resultado['risco_proprio']:.2f}\n"
            f"  Risco efetivo: {resultado['risco_efetivo']:.2f}"
        )


def diagnostico_tecnico(gerenciador_ativos, gerenciador_dependencias):
    """Exibe os indicadores numéricos do sistema de risco."""
    ativos = gerenciador_ativos.listar_ativos()

    if not ativos:
        print("Nenhum ativo cadastrado para análise.")
        return

    dependencias = gerenciador_dependencias.listar_dependencias()

    print("\n=== DIAGNÓSTICO TÉCNICO ===")

    try:
        diagnostico = diagnosticar_sistema(ativos, dependencias)
    except ValueError as erro:
        print(f"Erro ao montar o sistema: {erro}")
        return

    print(
        f"Ordem do sistema (I - A): "
        f"{diagnostico['ordem']}x{diagnostico['ordem']}"
    )
    print(
        f"Posto: {diagnostico['posto']} "
        f"(precisa ser {diagnostico['ordem']})"
    )
    print(f"Determinante: {diagnostico['determinante']:.4g}")
    print(f"Número de condição: {diagnostico['condicao']:.4g}")
    print(
        "Invertível: "
        + ("sim" if diagnostico["invertivel"] else "NÃO")
    )
    print(
        "Confiabilidade numérica: "
        + ("frágil" if diagnostico["frágil"] else "boa")
    )


# ============================================================
# TRATAMENTO DE ERROS
# ============================================================

def executar_com_tratamento(funcao, *args):
    """Executa uma operação e apresenta erros esperados."""
    try:
        funcao(*args)
    except (ValueError, OSError) as erro:
        print(f"Erro: {erro}")


# ============================================================
# SUBMENU: ATIVOS
# ============================================================

def menu_ativos(gerenciador, gerenciador_dependencias, cliente_nvd):
    """Agrupa as operações de gerenciamento de ativos."""
    while True:
        print("\n========== GERENCIAR ATIVOS ==========")
        print("1. Cadastrar ativo")
        print("2. Listar todos os ativos")
        print("3. Buscar ativo por ID ou nome")
        print("4. Atualizar ativo")
        print("5. Remover ativo")
        print("0. Voltar")
        print("======================================")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            executar_com_tratamento(
                cadastrar_ativo,
                gerenciador,
                cliente_nvd,
            )
        elif opcao == "2":
            executar_com_tratamento(consultar_ativos, gerenciador)
        elif opcao == "3":
            executar_com_tratamento(buscar_ativo, gerenciador)
        elif opcao == "4":
            executar_com_tratamento(
                atualizar_ativo,
                gerenciador,
                cliente_nvd,
            )
        elif opcao == "5":
            executar_com_tratamento(
                remover_ativo,
                gerenciador,
                gerenciador_dependencias,
            )
        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ============================================================
# SUBMENU: VULNERABILIDADES
# ============================================================

def menu_vulnerabilidades(gerenciador, cliente_nvd):
    """Agrupa as operações de vulnerabilidades."""
    while True:
        print("\n======= GERENCIAR VULNERABILIDADES =======")
        print("1. Consultar vulnerabilidades de um ativo")
        print("2. Adicionar vulnerabilidade a um ativo")
        print("3. Atualizar status de uma vulnerabilidade")
        print("0. Voltar")
        print("==========================================")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            executar_com_tratamento(
                consultar_vulnerabilidades_do_ativo,
                gerenciador,
            )
        elif opcao == "2":
            executar_com_tratamento(
                adicionar_vulnerabilidade_ao_ativo,
                gerenciador,
                cliente_nvd,
            )
        elif opcao == "3":
            executar_com_tratamento(
                atualizar_status_da_vulnerabilidade,
                gerenciador,
            )
        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ============================================================
# SUBMENU: RISCO E DEPENDÊNCIAS
# ============================================================

def menu_risco(gerenciador, gerenciador_dependencias):
    """Agrupa análise de risco, dependências e diagnóstico."""
    while True:
        print("\n======= ANÁLISE DE RISCO =======")
        print("1. Calcular risco próprio e efetivo")
        print("2. Gerenciar dependências entre ativos")
        print("3. Diagnóstico técnico do cálculo")
        print("0. Voltar")
        print("================================")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            executar_com_tratamento(
                analisar_risco,
                gerenciador,
                gerenciador_dependencias,
            )
        elif opcao == "2":
            menu_dependencias(gerenciador, gerenciador_dependencias)
        elif opcao == "3":
            executar_com_tratamento(
                diagnostico_tecnico,
                gerenciador,
                gerenciador_dependencias,
            )
        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ============================================================
# SUBMENU: DEPENDÊNCIAS
# ============================================================

def menu_dependencias(gerenciador, gerenciador_dependencias):
    """Gerencia as dependências entre ativos."""
    while True:
        print("\n=== DEPENDÊNCIAS ENTRE ATIVOS ===")
        print("1. Cadastrar dependência")
        print("2. Listar dependências")
        print("3. Remover dependência")
        print("0. Voltar")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            executar_com_tratamento(
                cadastrar_dependencia,
                gerenciador,
                gerenciador_dependencias,
            )
        elif opcao == "2":
            executar_com_tratamento(
                listar_dependencias,
                gerenciador,
                gerenciador_dependencias,
            )
        elif opcao == "3":
            executar_com_tratamento(
                remover_dependencia,
                gerenciador,
                gerenciador_dependencias,
            )
        elif opcao == "0":
            return
        else:
            print("Opção inválida.")


# ============================================================
# MENU PRINCIPAL
# ============================================================

def main():
    """Executa o menu principal do Cyber Asset Manager."""
    gerenciador = GerenciadorAtivos("ativos.json")
    gerenciador_dependencias = GerenciadorDependencias(
        "dependencias.json"
    )
    cliente_nvd = ClienteNVD("cache_cve.json")

    while True:
        print("\n========== CYBER ASSET MANAGER ==========")
        print("1. Gerenciar ativos")
        print("2. Gerenciar vulnerabilidades")
        print("3. Análise de risco e dependências")
        print("0. Sair")
        print("=========================================")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            menu_ativos(
                gerenciador,
                gerenciador_dependencias,
                cliente_nvd,
            )
        elif opcao == "2":
            menu_vulnerabilidades(
                gerenciador,
                cliente_nvd,
            )
        elif opcao == "3":
            menu_risco(
                gerenciador,
                gerenciador_dependencias,
            )
        elif opcao == "0":
            print("Encerrando o inventário. Até mais!")
            break
        else:
            print("Opção inválida. Escolha 0, 1, 2 ou 3.")


if __name__ == "__main__":
    main()
