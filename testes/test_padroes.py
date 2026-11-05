"""Testes dos padrões de projeto: Factory, Repository e Strategy."""

import json
import tempfile
import unittest
from pathlib import Path

from src.api.aplicacao import criar_app
from src.modelos.banco_dados import BancoDeDados
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.persistencia.erros import ErroDados
from src.persistencia.fabrica_ativos import FabricaAtivos
from src.persistencia.repositorio import (
    RepositorioAtivos, RepositorioAtivosJson, RepositorioAtivosMemoria,
)
from src.servicos.gerenciador_ativos import GerenciadorAtivos
from src.servicos.ordenacao import ESTRATEGIAS, ordenar


def nb(id_, nome, setor="TI", responsavel="Ana"):
    return Notebook(id_, nome, responsavel, setor, [], "16 GB")


class TesteFabrica(unittest.TestCase):
    def test_cada_tipo_volta_como_sua_subclasse(self):
        originais = [
            nb(1, "Notebook Ana"),
            Servidor(2, "Servidor Arquivos", "Bia", "TI", [], "Xeon"),
            Roteador(3, "Roteador Central", "Caio", "TI", [], "RB4011"),
            BancoDeDados(4, "Banco Clientes", "Dani", "Vendas", [], "PostgreSQL"),
        ]
        for original in originais:
            with self.subTest(tipo=original.obter_tipo()):
                refeito = FabricaAtivos.reconstruir(original.para_dict())
                self.assertIs(type(refeito), type(original))
                self.assertEqual(refeito.para_dict(), original.para_dict())

    def test_tipo_desconhecido_ou_registro_ruim_vira_erro_de_dados(self):
        for dado in [{"tipo": "Impressora", "id": 1}, {"id": 1}, "texto", None,
                     {"tipo": "Notebook", "id": 1}]:
            with self.subTest(dado=dado):
                with self.assertRaises(ErroDados):
                    FabricaAtivos.reconstruir(dado)


class TesteRepositorio(unittest.TestCase):
    def test_json_guarda_e_devolve_e_arquivo_ausente_e_lista_vazia(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = RepositorioAtivosJson(Path(tmp) / "a.json")
            self.assertEqual(repo.listar(), [])
            repo.salvar([nb(1, "Notebook Ana"), nb(2, "Notebook Bia")])
            self.assertEqual([a.nome for a in repo.listar()], ["Notebook Ana", "Notebook Bia"])
            self.assertEqual(len(json.loads((Path(tmp) / "a.json").read_text("utf-8"))), 2)

    def test_gerenciador_funciona_com_repositorio_em_memoria(self):
        repo = RepositorioAtivosMemoria([nb(1, "Notebook Ana")])
        ger = GerenciadorAtivos("nao_usado.json", repositorio=repo)
        self.assertEqual([a.id for a in ger.listar_ativos()], [1])
        ger.cadastrar_ativo(nb(2, "Notebook Bia"))
        self.assertEqual([a.id for a in repo.listar()], [1, 2])
        self.assertFalse(Path("nao_usado.json").exists())

    def test_repositorio_abstrato_nao_instancia(self):
        with self.assertRaises(TypeError):
            RepositorioAtivos()


class TesteEstrategia(unittest.TestCase):
    def setUp(self):
        self.ativos = [nb(3, "casa", "RH", "Zé"), nb(1, "Banco", "TI", "ana"), nb(2, "abacaxi", "RH", "Bia")]

    def test_cada_criterio(self):
        ids = lambda c, **k: [a.id for a in ordenar(self.ativos, c, **k)]
        self.assertEqual(ids("id"), [1, 2, 3])
        self.assertEqual(ids("nome"), [2, 1, 3])                    # ignora maiúsculas
        self.assertEqual(ids("nome", decrescente=True), [3, 1, 2])
        self.assertEqual(ids("setor"), [2, 3, 1])                   # empate no setor: desempata pelo nome
        self.assertEqual(ids("responsavel"), [1, 2, 3])

    def test_criterio_invalido_e_nao_altera_a_lista(self):
        copia = list(self.ativos)
        with self.assertRaises(ValueError):
            ordenar(self.ativos, "cor")
        self.assertEqual(self.ativos, copia)

    def test_estrategias_sao_funcoes_comuns(self):
        self.assertTrue(all(callable(f) for f in ESTRATEGIAS.values()))


class TesteApiOrdem(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = criar_app(self.tmp.name).test_client()
        for i, nome in [(1, "Zeta"), (2, "Alfa"), (3, "Meio")]:
            r = self.c.post("/api/ativos", json={"tipo": 1, "id": i, "nome": nome + " nb", "responsavel": "Ana",
                                                  "setor": "TI", "memoria_ram": "8 GB"})
            self.assertEqual(r.status_code, 201, r.get_json())

    def nomes(self, query):
        r = self.c.get("/api/ativos" + query)
        return r.status_code, [a["nome"] for a in r.get_json()] if r.status_code == 200 else r.get_json()

    def test_ordem_e_sentido(self):
        self.assertEqual(self.nomes("?ordem=nome")[1], ["Alfa nb", "Meio nb", "Zeta nb"])
        self.assertEqual(self.nomes("?ordem=nome&sentido=desc")[1], ["Zeta nb", "Meio nb", "Alfa nb"])
        self.assertEqual(self.nomes("")[1], ["Zeta nb", "Alfa nb", "Meio nb"])   # sem ordem: cadastro

    def test_parametros_invalidos_dao_400_no_formato_padrao(self):
        for q in ["?ordem=cor", "?ordem=nome&sentido=lado"]:
            status, corpo = self.nomes(q)
            self.assertEqual(status, 400)
            self.assertIn("erro", corpo)


if __name__ == "__main__":
    unittest.main()
