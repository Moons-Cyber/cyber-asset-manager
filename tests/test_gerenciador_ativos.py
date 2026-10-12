import pytest

from src.modelos.notebook import Notebook
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.servicos.gerenciador_ativos import GerenciadorAtivos


@pytest.fixture
def gerenciador(tmp_path):
    """Cria um gerenciador isolado para cada teste."""
    arquivo = tmp_path / "ativos.json"
    return GerenciadorAtivos(arquivo)


def criar_notebook(
    identificador=1001,
    nome="Notebook de teste",
):
    """Cria um notebook de exemplo para os testes."""
    vulnerabilidades = [
        Vulnerabilidade(
            "Sistema desatualizado",
            "Atualização",
            8.5,
            "Aberta",
        )
    ]

    return Notebook(
        identificador,
        nome,
        "Gabriel",
        "TI",
        vulnerabilidades,
        "16GB",
    )


def test_lista_vazia_quando_arquivo_nao_existe(gerenciador):
    assert gerenciador.listar_ativos() == []


def test_cadastrar_e_buscar_ativo(gerenciador):
    notebook = criar_notebook()

    gerenciador.cadastrar_ativo(notebook)
    encontrado = gerenciador.buscar_ativo_por_id(1001)

    assert encontrado is not None
    assert encontrado.nome == "Notebook de teste"
    assert encontrado.memoria_ram == "16GB"


def test_impede_ids_duplicados(gerenciador):
    gerenciador.cadastrar_ativo(criar_notebook())

    duplicado = criar_notebook(nome="Outro notebook")

    with pytest.raises(ValueError, match="ID 1001"):
        gerenciador.cadastrar_ativo(duplicado)

    assert len(gerenciador.listar_ativos()) == 1


def test_busca_id_inexistente(gerenciador):
    assert gerenciador.buscar_ativo_por_id(9999) is None


def test_atualiza_e_persiste_dados(gerenciador):
    gerenciador.cadastrar_ativo(criar_notebook())

    atualizado = gerenciador.atualizar_ativo(
        1001,
        nome="Notebook atualizado",
        memoria_ram="32GB",
    )

    assert atualizado.nome == "Notebook atualizado"
    assert atualizado.memoria_ram == "32GB"

    # Nova leitura do JSON para conferir a persistência.
    recarregado = gerenciador.buscar_ativo_por_id(1001)

    assert recarregado.nome == "Notebook atualizado"
    assert recarregado.memoria_ram == "32GB"


def test_atualizacao_de_id_inexistente(gerenciador):
    resultado = gerenciador.atualizar_ativo(
        9999,
        nome="Não existe",
    )

    assert resultado is None


def test_atualizacao_sem_campos_e_rejeitada(gerenciador):
    gerenciador.cadastrar_ativo(criar_notebook())

    with pytest.raises(ValueError, match="pelo menos um campo"):
        gerenciador.atualizar_ativo(1001)


def test_rejeita_campo_nao_permitido(gerenciador):
    gerenciador.cadastrar_ativo(criar_notebook())

    with pytest.raises(ValueError, match="Campos não permitidos"):
        gerenciador.atualizar_ativo(
            1001,
            campo_inexistente="valor",
        )

    ativo = gerenciador.buscar_ativo_por_id(1001)
    assert ativo.nome == "Notebook de teste"


def test_rejeita_vulnerabilidades_invalidas(gerenciador):
    gerenciador.cadastrar_ativo(criar_notebook())

    with pytest.raises(TypeError, match="deve conter objetos Vulnerabilidade"):
        gerenciador.atualizar_ativo(
            1001,
            vulnerabilidades=["vulnerabilidade inválida"],
        )


def test_remove_ativo(gerenciador):
    gerenciador.cadastrar_ativo(criar_notebook())

    assert gerenciador.remover_ativo(1001) is True
    assert gerenciador.buscar_ativo_por_id(1001) is None
    assert gerenciador.listar_ativos() == []


def test_remocao_de_id_inexistente(gerenciador):
    assert gerenciador.remover_ativo(9999) is False


def test_rejeita_vulnerabilidades_que_nao_sao_lista(
    gerenciador,
):
    gerenciador.cadastrar_ativo(criar_notebook())

    with pytest.raises(
        TypeError,
        match="Vulnerabilidades deve ser uma lista",
    ):
        gerenciador.atualizar_ativo(
            1001,
            vulnerabilidades="valor inválido",
        )