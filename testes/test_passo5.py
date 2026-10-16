import contextlib
import inspect
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
from src.modelos.ativo import Ativo
from src.modelos.banco_dados import BancoDeDados
from src.modelos.enums import TipoAtivo
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.persistencia import Persistencia
from src.servicos.analise_risco import calcular_risco_efetivo
from src.servicos.consultas import filtrar_por_tipo
from src.servicos.gerenciador_ativos import GerenciadorAtivos

CLASSES = (Notebook, Servidor, Roteador, BancoDeDados)


def banco(id_=10, nome="DB Clientes", sgbd="PostgreSQL", nota=None):
    vulns = [Vulnerabilidade("SQLi", "Injeção", nota, "Aberta", id="CVE-2020-0001")] if nota else []
    return BancoDeDados(id_, nome, "Ana", "TI", vulns, sgbd)


class TesteClasse(unittest.TestCase):
    def test_serializa_com_tipo_e_campo(self):
        d = banco().para_dict()
        self.assertEqual(d["tipo"], "BancoDeDados")
        self.assertEqual(d["sgbd"], "PostgreSQL")

    def test_ida_e_volta_no_json(self):
        with tempfile.TemporaryDirectory() as t:
            arq = Path(t) / "a.json"
            Persistencia().salvar_dados([banco(nota=7.5)], arq)
            lido = Persistencia().carregar_dados(arq)[0]
        self.assertIsInstance(lido, BancoDeDados)
        self.assertEqual((lido.sgbd, lido.vulnerabilidades[0].severidade), ("PostgreSQL", 7.5))

    def test_exibir_detalhes_mostra_o_sgbd(self):
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            banco().exibir_detalhes()
        self.assertIn("SGBD: PostgreSQL", saida.getvalue())

    def test_convive_com_os_outros_tipos_e_filtro_por_tipo_funciona(self):
        ativos = [Notebook(1, "N", "x", "TI", [], "8GB"), banco(2), banco(3)]
        self.assertEqual(len(filtrar_por_tipo(ativos, BancoDeDados)), 2)
        self.assertEqual(len(filtrar_por_tipo(ativos, Notebook)), 1)

    def test_entra_no_calculo_de_risco(self):
        r = calcular_risco_efetivo([banco(nota=9.0)], [])
        self.assertEqual(r[0]["risco_proprio"], 9.0)


class TesteContratoDosTipos(unittest.TestCase):
    """Protegem o futuro: acrescentar um tipo e esquecer algo falha AQUI."""

    def test_campo_declarado_existe_no_construtor_e_no_objeto(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(cls.campo_especifico and cls.rotulo_campo)
                self.assertIn(cls.campo_especifico, inspect.signature(cls.__init__).parameters)
                obj = cls(1, "n", "r", "s", [], "valor")
                self.assertEqual(getattr(obj, cls.campo_especifico), "valor")

    def test_nome_do_tipo_gravado_e_reconhecido_na_leitura(self):
        for cls in CLASSES:
            with self.subTest(cls=cls.__name__):
                obj = cls(1, "n", "r", "s", [], "valor")
                self.assertIs(Persistencia.TIPOS[obj.obter_tipo()], cls)

    def test_todo_tipo_do_enum_tem_classe_e_rotulo(self):
        self.assertEqual(set(main.TIPOS_DISPONIVEIS), set(TipoAtivo))
        for tipo in TipoAtivo:
            self.assertTrue(tipo.rotulo)
            self.assertTrue(issubclass(main.TIPOS_DISPONIVEIS[tipo][0], Ativo))

    def test_codigos_inteiros_sao_unicos(self):
        codigos = [t.value for t in TipoAtivo]
        self.assertEqual(len(codigos), len(set(codigos)))
        self.assertGreaterEqual(len(codigos), 4)   # requisito 2 do T1

    def test_rotulo_de_exibicao(self):
        self.assertEqual(TipoAtivo.BANCO_DADOS.rotulo, "Banco de dados")


class TesteGerenciadorComBanco(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.arq = Path(self.tmp.name) / "a.json"
        self.g = GerenciadorAtivos(self.arq)
        self.g.cadastrar_ativo(banco())

    def test_atualiza_o_campo_proprio(self):
        self.g.atualizar_ativo(10, sgbd="MySQL")
        self.assertEqual(GerenciadorAtivos(self.arq).buscar_ativo_por_id(10).sgbd, "MySQL")

    def test_recusa_campo_de_outro_tipo(self):
        for campo in ("memoria_ram", "processador", "modelo"):
            with self.assertRaises(ValueError):
                self.g.atualizar_ativo(10, **{campo: "x"})

    def test_notebook_nao_aceita_sgbd(self):
        self.g.cadastrar_ativo(Notebook(1, "N", "x", "TI", [], "8GB"))
        with self.assertRaises(ValueError):
            self.g.atualizar_ativo(1, sgbd="x")
        self.g.atualizar_ativo(1, memoria_ram="16GB")   # o próprio continua valendo


class TesteMenu(unittest.TestCase):
    def _executar(self, funcao, respostas, *args):
        with mock.patch("builtins.input", side_effect=respostas), \
             contextlib.redirect_stdout(io.StringIO()) as saida:
            funcao(*args)
        return saida.getvalue()

    def test_cadastro_pelo_menu_com_codigo_4(self):
        with tempfile.TemporaryDirectory() as t:
            g = GerenciadorAtivos(Path(t) / "a.json")
            saida = self._executar(main.cadastrar_ativo,
                                   ["4", "10", "DB Clientes", "Ana", "TI", "PostgreSQL", "0"], g, None)
            self.assertIn("4. Banco de dados", saida)
            self.assertIn("cadastrado com sucesso", saida)
            ativo = g.buscar_ativo_por_id(10)
            self.assertIsInstance(ativo, BancoDeDados)
            self.assertEqual(ativo.sgbd, "PostgreSQL")

    def test_atualizacao_pelo_menu_usa_o_rotulo_do_proprio_tipo(self):
        with tempfile.TemporaryDirectory() as t:
            g = GerenciadorAtivos(Path(t) / "a.json")
            g.cadastrar_ativo(banco())
            saida = self._executar(main.atualizar_ativo, ["10", "4", "MariaDB"], g, None)
            self.assertIn("4. SGBD", saida)
            self.assertEqual(g.buscar_ativo_por_id(10).sgbd, "MariaDB")

    def test_atualizacao_dos_tipos_antigos_continua_igual(self):
        esperado = {Notebook: "4. Memória RAM", Servidor: "4. Processador", Roteador: "4. Modelo"}
        for cls, rotulo in esperado.items():
            with self.subTest(cls=cls.__name__), tempfile.TemporaryDirectory() as t:
                g = GerenciadorAtivos(Path(t) / "a.json")
                g.cadastrar_ativo(cls(1, "X", "r", "s", [], "v"))
                saida = self._executar(main.atualizar_ativo, ["1", "0"], g, None)
                self.assertIn(rotulo, saida)

    def test_codigo_inexistente_continua_sendo_recusado(self):
        with tempfile.TemporaryDirectory() as t:
            g = GerenciadorAtivos(Path(t) / "a.json")
            saida = self._executar(main.cadastrar_ativo, ["9"], g, None)
            self.assertIn("inexistente", saida)


if __name__ == "__main__":
    unittest.main()
