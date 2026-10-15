import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import main
from src.modelos.dependencia import Dependencia
from src.modelos.notebook import Notebook
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.servicos.analise_risco import (
    _diagnosticar, calcular_risco_efetivo, diagnosticar_sistema,
)
from src.servicos.gerenciador_ativos import GerenciadorAtivos
from src.servicos.gerenciador_dependencias import GerenciadorDependencias


def ativo(id_, nota=None):
    vulns = [Vulnerabilidade("d", "c", nota, "Aberta", id=f"V{id_}")] if nota else []
    return Notebook(id_, f"A{id_}", "x", "TI", vulns, "8GB")


class TesteCenarioResolvidoAMao(unittest.TestCase):
    """
    Três ativos em ciclo. Risco próprio b = [10, 5, 0].
    Dependências (origem -> destino, peso):  1->2 (0,5)   2->3 (0,4)   3->1 (0,2)

    Sistema x = b + A x, ou seja:
        x1 = 10 + 0,2 x3
        x2 =  5 + 0,5 x1
        x3 =  0 + 0,4 x2

    Substituindo:  x3 = 0,4(5 + 0,5 x1) = 2 + 0,2 x1
                   x1 = 10 + 0,2(2 + 0,2 x1) = 10,4 + 0,04 x1  ->  x1 = 10,4/0,96 = 130/12
                   x2 = 5 + 0,5 * 130/12 = 125/12
                   x3 = 0,4 * 125/12     =  50/12
    """

    def setUp(self):
        self.ativos = [ativo(1, 10.0), ativo(2, 5.0), ativo(3)]
        self.deps = [Dependencia(1, 2, 0.5), Dependencia(2, 3, 0.4), Dependencia(3, 1, 0.2)]

    def test_risco_proprio(self):
        r = calcular_risco_efetivo(self.ativos, self.deps)
        self.assertEqual([x["risco_proprio"] for x in r], [10.0, 5.0, 0.0])

    def test_risco_efetivo_bate_com_a_conta_a_mao(self):
        r = calcular_risco_efetivo(self.ativos, self.deps)
        esperado = [130 / 12, 125 / 12, 50 / 12]
        for obtido, esp in zip((x["risco_efetivo"] for x in r), esperado):
            self.assertAlmostEqual(obtido, esp, places=9)

    def test_solucao_satisfaz_a_equacao_original(self):
        r = calcular_risco_efetivo(self.ativos, self.deps)
        x = {i + 1: r[i]["risco_efetivo"] for i in range(3)}
        self.assertAlmostEqual(x[1], 10 + 0.2 * x[3])
        self.assertAlmostEqual(x[2], 5 + 0.5 * x[1])
        self.assertAlmostEqual(x[3], 0 + 0.4 * x[2])

    def test_sem_dependencias_risco_efetivo_igual_ao_proprio(self):
        r = calcular_risco_efetivo(self.ativos, [])
        for x in r:
            self.assertEqual(x["risco_efetivo"], x["risco_proprio"])


class TesteDiagnostico(unittest.TestCase):
    def test_sistema_normal_e_invertivel_e_bem_condicionado(self):
        d = diagnosticar_sistema([ativo(1, 10.0), ativo(2, 5.0)], [Dependencia(1, 2, 0.5)])
        self.assertTrue(d["invertivel"])
        self.assertFalse(d["frágil"])
        self.assertEqual(d["posto"], 2)
        self.assertAlmostEqual(d["determinante"], 1.0)  # triangular com diagonal 1

    def test_matriz_singular_e_detectada(self):
        # (I - A) com A = [[0,1],[1,0]]: linhas dependentes, det = 0
        d = _diagnosticar(np.array([[1.0, -1.0], [-1.0, 1.0]]))
        self.assertFalse(d["invertivel"])
        self.assertEqual(d["posto"], 1)
        self.assertAlmostEqual(d["determinante"], 0.0, places=12)

    def test_quase_singular_tem_condicao_enorme(self):
        d = _diagnosticar(np.array([[1.0, -1.0], [-1.0, 1.0 + 1e-14]]))
        self.assertTrue(d["frágil"])

    def test_sem_ativos(self):
        self.assertIsNone(diagnosticar_sistema([], []))

    def test_peso_quase_um_continua_resolvivel_mas_condicao_cresce(self):
        a = [ativo(1, 10.0), ativo(2)]
        d_fraca = diagnosticar_sistema(a, [Dependencia(1, 2, 0.1)])
        d_forte = diagnosticar_sistema(a, [Dependencia(1, 2, 0.999)])
        self.assertTrue(d_forte["invertivel"])
        self.assertGreaterEqual(d_forte["condicao"], d_fraca["condicao"])


class TesteGerenciadorDependencias(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.g = GerenciadorDependencias(Path(self.tmp.name) / "dep.json")
        self.ativos = [ativo(1), ativo(2), ativo(3)]

    def test_cadastrar_e_listar(self):
        self.g.cadastrar_dependencia(Dependencia(1, 2, 0.5), self.ativos)
        self.assertEqual(len(self.g.listar_dependencias()), 1)

    def test_ativo_inexistente_e_recusado(self):
        with self.assertRaises(ValueError):
            self.g.cadastrar_dependencia(Dependencia(1, 99, 0.5), self.ativos)

    def test_duplicada_e_recusada(self):
        self.g.cadastrar_dependencia(Dependencia(1, 2, 0.3), self.ativos)
        with self.assertRaises(ValueError):
            self.g.cadastrar_dependencia(Dependencia(1, 2, 0.3), self.ativos)

    def test_soma_recebida_deve_ser_menor_que_um(self):
        self.g.cadastrar_dependencia(Dependencia(1, 3, 0.6), self.ativos)
        with self.assertRaises(ValueError):
            self.g.cadastrar_dependencia(Dependencia(2, 3, 0.4), self.ativos)  # soma = 1,0

    def test_peso_invalido_nem_cria_o_objeto(self):
        for peso in (1.0, -0.1, float("nan"), True):
            with self.assertRaises(ValueError):
                Dependencia(1, 2, peso)

    def test_remover_uma_dependencia(self):
        self.g.cadastrar_dependencia(Dependencia(1, 2, 0.3), self.ativos)
        self.assertTrue(self.g.remover_dependencia(1, 2))
        self.assertFalse(self.g.remover_dependencia(1, 2))
        self.assertEqual(self.g.listar_dependencias(), [])

    def test_remover_dependencias_do_ativo_pega_origem_e_destino(self):
        self.g.cadastrar_dependencia(Dependencia(1, 2, 0.3), self.ativos)
        self.g.cadastrar_dependencia(Dependencia(2, 3, 0.3), self.ativos)
        self.g.cadastrar_dependencia(Dependencia(1, 3, 0.3), self.ativos)
        self.assertEqual(self.g.remover_dependencias_do_ativo(2), 2)
        restantes = [(d.ativo_origem_id, d.ativo_destino_id) for d in self.g.listar_dependencias()]
        self.assertEqual(restantes, [(1, 3)])

    def test_arquivo_corrompido_vira_valueerror(self):
        (Path(self.tmp.name) / "dep.json").write_text("{ isto nao e json", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.g.listar_dependencias()


class TesteRemoverAtivoLimpaOrfas(unittest.TestCase):
    def test_remover_ativo_apaga_dependencias_e_analise_continua_funcionando(self):
        with tempfile.TemporaryDirectory() as d:
            ga = GerenciadorAtivos(Path(d) / "a.json")
            gd = GerenciadorDependencias(Path(d) / "d.json")
            for a in (ativo(1, 10.0), ativo(2, 5.0), ativo(3, 2.0)):
                ga.cadastrar_ativo(a)
            todos = ga.listar_ativos()
            gd.cadastrar_dependencia(Dependencia(1, 2, 0.5), todos)
            gd.cadastrar_dependencia(Dependencia(2, 3, 0.5), todos)

            with mock.patch("builtins.input", side_effect=["2", "s"]), \
                 contextlib.redirect_stdout(io.StringIO()) as saida:
                main.remover_ativo(ga, gd)

            self.assertIn("2 dependência(s)", saida.getvalue())
            self.assertEqual(gd.listar_dependencias(), [])
            r = calcular_risco_efetivo(ga.listar_ativos(), gd.listar_dependencias())
            self.assertEqual([x["id"] for x in r], [1, 3])

    def test_sem_a_limpeza_a_analise_quebraria(self):
        with tempfile.TemporaryDirectory() as d:
            ga = GerenciadorAtivos(Path(d) / "a.json")
            ga.cadastrar_ativo(ativo(1, 10.0))
            ga.cadastrar_ativo(ativo(2, 5.0))
            orfa = [Dependencia(1, 2, 0.5)]
            ga.remover_ativo(2)
            with self.assertRaises(ValueError):
                calcular_risco_efetivo(ga.listar_ativos(), orfa)


class TesteMenuDependencias(unittest.TestCase):
    def test_cadastro_pelo_menu_e_calculo_de_ponta_a_ponta(self):
        with tempfile.TemporaryDirectory() as d:
            ga = GerenciadorAtivos(Path(d) / "a.json")
            gd = GerenciadorDependencias(Path(d) / "d.json")
            ga.cadastrar_ativo(ativo(1, 10.0))
            ga.cadastrar_ativo(ativo(2, 4.0))

            # origem 1, destino 2, peso "0,5" (com vírgula) -- primeiro um peso inválido
            with mock.patch("builtins.input", side_effect=["1", "2", "1", "0,5"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                main.cadastrar_dependencia(ga, gd)

            r = calcular_risco_efetivo(ga.listar_ativos(), gd.listar_dependencias())
            self.assertAlmostEqual(r[1]["risco_efetivo"], 4.0 + 0.5 * 10.0)

    def test_menu_recusa_ativo_inexistente_sem_quebrar(self):
        with tempfile.TemporaryDirectory() as d:
            ga = GerenciadorAtivos(Path(d) / "a.json")
            gd = GerenciadorDependencias(Path(d) / "d.json")
            ga.cadastrar_ativo(ativo(1))
            ga.cadastrar_ativo(ativo(2))
            with mock.patch("builtins.input", side_effect=["1", "99", "0,5"]), \
                 contextlib.redirect_stdout(io.StringIO()) as saida:
                main.cadastrar_dependencia(ga, gd)
            self.assertIn("Não foi possível cadastrar", saida.getvalue())
            self.assertEqual(gd.listar_dependencias(), [])


if __name__ == "__main__":
    unittest.main()


class TesteSaidaDoDiagnostico(unittest.TestCase):
    def _rodar(self, funcao, deps):
        with tempfile.TemporaryDirectory() as d:
            ga = GerenciadorAtivos(Path(d) / "a.json")
            gd = GerenciadorDependencias(Path(d) / "d.json")
            ga.cadastrar_ativo(ativo(1, 10.0))
            ga.cadastrar_ativo(ativo(2, 5.0))
            if deps:
                gd.cadastrar_dependencia(Dependencia(1, 2, 0.5), ga.listar_ativos())
            with contextlib.redirect_stdout(io.StringIO()) as saida:
                funcao(ga, gd)
            return saida.getvalue()

    def test_analise_normal_nao_mostra_numeros_tecnicos(self):
        texto = self._rodar(main.analisar_risco, deps=True)
        self.assertIn("Risco Efetivo", texto)
        self.assertNotIn("determinante", texto.lower())
        self.assertNotIn("ATENÇÃO", texto)

    def test_opcao_tecnica_mostra_os_numeros(self):
        texto = self._rodar(main.diagnostico_tecnico, deps=True)
        for trecho in ("Posto", "Determinante", "Número de condição", "Invertível: sim"):
            self.assertIn(trecho, texto)