import pytest

from src.modelos.ativo import Ativo
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade

CLASSES = [
    (Notebook, "Notebook", "memoria_ram", "Memória RAM"),
    (Servidor, "Servidor", "processador", "Processador"),
    (Roteador, "Roteador", "modelo", "Modelo"),
]


def test_ativo_e_abstrato():
    with pytest.raises(TypeError):
        Ativo(1, "x", "y", "z", [])


@pytest.mark.parametrize("classe, tipo, campo, rotulo", CLASSES)
def test_polimorfismo_para_dict(classe, tipo, campo, rotulo):
    ativo = classe(1, "n", "r", "s", [], "valor")
    dados = ativo.para_dict()

    assert isinstance(ativo, Ativo)
    assert ativo.obter_tipo() == tipo
    assert dados["tipo"] == tipo
    assert dados[campo] == "valor"


@pytest.mark.parametrize("classe, tipo, campo, rotulo", CLASSES)
def test_exibir_detalhes_mostra_dados_comuns_e_especificos(
    classe, tipo, campo, rotulo, capsys
):
    vuln = Vulnerabilidade("Falha X", "Rede", 7.5, "Aberta")
    classe(1, "Ativo1", "Ana", "TI", [vuln], "valor").exibir_detalhes()
    saida = capsys.readouterr().out

    assert "Nome: Ativo1" in saida
    assert "Falha X" in saida
    assert f"{rotulo}: valor" in saida


def test_vulnerabilidade_str_e_para_dict():
    v = Vulnerabilidade("d", "c", 7.5, "Aberta")

    assert "Severidade: 7.5" in str(v)
    assert v.para_dict() == {
        "descricao": "d",
        "categoria": "c",
        "severidade": 7.5,
        "status": "Aberta",
    }