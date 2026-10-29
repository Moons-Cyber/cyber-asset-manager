"""Conformidade com o material do professor (aulas S3_09 a S3_12).

Cada teste reproduz um exemplo dos slides com o código do projeto.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from src.api.aplicacao import criar_app
from src.modelos.ativo import Ativo
from src.modelos.banco_dados import BancoDeDados
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.dependencia import (
    MARGEM_SOMA_PESOS, Dependencia, soma_de_pesos_valida,
)
from src.modelos.notebook import Notebook
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.servicos.analise_risco import (
    LIMITE_CONDICAO_ALERTA, LIMITE_CONDICAO_SINGULAR, _diagnosticar,
    calcular_risco_efetivo, construir_matriz_dependencias, construir_matriz_exposicao,
    diagnosticar_sistema, multiplicar_matriz_vetor,
)
from src.servicos.gerenciador_dependencias import GerenciadorDependencias


def vuln(i, nota):
    return Vulnerabilidade(f"V{i}", "c", nota, "Aberta", id=f"V{i}")


def ativos_da_aula():
    """Slide 'O cenário que vamos usar': V1=9,8 (Web); V2=5,3 (Web e BD); V3=7,5 (App)."""
    return [Notebook(1, "Web", "Joe", "TI", [vuln(1, 9.8), vuln(2, 5.3)], "16GB"),
            Notebook(2, "App", "Gab", "TI", [vuln(3, 7.5)], "16GB"),
            Notebook(3, "Banco BD", "Lina", "TI", [vuln(2, 5.3)], "16GB")]


def detalhe_valido(classe):
    """Devolve um campo específico válido para cada tipo de ativo."""
    return {
        Notebook: "16GB",
        Servidor: "Intel Xeon",
        Roteador: "TP-Link Archer C6",
        BancoDeDados: "PostgreSQL 16",
    }[classe]


def dependencias_da_aula():
    # A[Web][App]=0,2   A[App][Web]=0,5   A[BD][App]=0,6   (origem -> destino)
    return [Dependencia(2, 1, 0.2), Dependencia(1, 2, 0.5), Dependencia(2, 3, 0.6)]


class TesteCenarioDaAula(unittest.TestCase):
    def test_risco_proprio_b_igual_a_Mv(self):
        r = calcular_risco_efetivo(ativos_da_aula(), dependencias_da_aula())
        for obtido, esperado in zip((x["risco_proprio"] for x in r), (15.1, 7.5, 5.3)):
            self.assertAlmostEqual(obtido, esperado, places=9)

    def test_risco_efetivo_bate_com_o_slide(self):
        r = calcular_risco_efetivo(ativos_da_aula(), dependencias_da_aula())
        self.assertEqual([round(x["risco_efetivo"], 2) for x in r], [18.44, 16.72, 15.33])

    def test_determinante_e_numero_de_condicao_do_slide(self):
        d = diagnosticar_sistema(ativos_da_aula(), dependencias_da_aula())
        self.assertAlmostEqual(d["determinante"], 0.9, places=9)
        self.assertAlmostEqual(d["condicao"], 2.59, places=2)
        self.assertTrue(d["invertivel"])
        self.assertFalse(d["frágil"])

    def test_conta_a_mao_do_escalonamento(self):
        # x_A = 15,05 / 0,9 ; x_W = 15,1 + 0,2 x_A ; x_D = 5,3 + 0,6 x_A
        r = calcular_risco_efetivo(ativos_da_aula(), dependencias_da_aula())
        xa = 15.05 / 0.9
        for obtido, esperado in zip((x["risco_efetivo"] for x in r),
                                    (15.1 + 0.2 * xa, xa, 5.3 + 0.6 * xa)):
            self.assertAlmostEqual(obtido, esperado, places=9)

    def test_banco_tinha_o_menor_risco_proprio_mas_o_efetivo_quase_triplica(self):
        r = calcular_risco_efetivo(ativos_da_aula(), dependencias_da_aula())
        bd = r[2]
        self.assertEqual(min(x["risco_proprio"] for x in r), bd["risco_proprio"])
        self.assertGreater(bd["risco_efetivo"] / bd["risco_proprio"], 2.8)

    def test_soma_dos_saltos_converge_para_a_solucao(self):
        # x = b + Ab + A^2 b + ...  (slide 'Intuição: o risco que viaja')
        ativos, deps = ativos_da_aula(), dependencias_da_aula()
        A = np.array(construir_matriz_dependencias(ativos, deps))
        b = np.array([x["risco_proprio"] for x in calcular_risco_efetivo(ativos, deps)])
        soma, termo = b.copy(), b.copy()
        for _ in range(10):
            termo = A @ termo
            soma += termo
        self.assertEqual([round(v, 2) for v in soma], [18.44, 16.72, 15.33])   # tabela: 10 saltos


class TesteQuandoOModeloQuebra(unittest.TestCase):
    def test_tres_ativos_herdando_50_e_50_sao_singulares(self):
        quebra = np.eye(3) - 0.5 * (np.ones((3, 3)) - np.eye(3))
        d = _diagnosticar(quebra)
        self.assertFalse(d["invertivel"])
        self.assertEqual(d["posto"], 2)
        self.assertGreater(d["condicao"], 1e30)               # slide: ~4,7e32

    def test_cadastro_recusa_a_dependencia_que_leva_a_soma_a_1(self):
        with tempfile.TemporaryDirectory() as t:
            g = GerenciadorDependencias(Path(t) / "d.json")
            ativos = [Notebook(i, f"Ativo{i}", "x", "TI", [], "16GB") for i in (1, 2, 3)]
            g.cadastrar_dependencia(Dependencia(2, 1, 0.5), ativos)
            with self.assertRaises(ValueError):
                g.cadastrar_dependencia(Dependencia(3, 1, 0.5), ativos)

    def test_perigo_real_A2_linhas_somando_1(self):
        A2 = np.array([[0, .1, .9], [.1, 0, .9], [.1, .9, 0]])
        d = _diagnosticar(np.eye(3) - A2)
        self.assertFalse(d["invertivel"])                      # kappa ~ 2e16 > 1/eps
        self.assertGreater(d["condicao"], LIMITE_CONDICAO_SINGULAR)
        self.assertLess(abs(d["determinante"]), 1e-15)          # slide: -2,2e-16, e NÃO é == 0
        self.assertNotEqual(d["determinante"], 0.0)


class TesteToleranciaNaSomaDosPesos(unittest.TestCase):
    """Regressão: o cadastro usava '< 1' exato e a montagem de A usava sum();
    em ponto flutuante os dois discordavam (0,7+0,2+0,1 = 0,9999999999999999)."""

    def test_a_regra_usa_margem(self):
        self.assertTrue(soma_de_pesos_valida(0.999999))
        self.assertFalse(soma_de_pesos_valida(1.0))
        self.assertFalse(soma_de_pesos_valida(0.9999999999999999))
        self.assertFalse(soma_de_pesos_valida(1 - MARGEM_SOMA_PESOS / 2))

    def test_cadastro_recusa_pesos_que_somam_1_em_qualquer_ordem(self):
        for ordem in ((0.7, 0.2, 0.1), (0.1, 0.2, 0.7), (0.2, 0.7, 0.1), (0.1, 0.7, 0.2)):
            with self.subTest(ordem=ordem), tempfile.TemporaryDirectory() as t:
                g = GerenciadorDependencias(Path(t) / "d.json")
                ativos = [Notebook(i, f"Ativo{i}", "x", "TI", [], "16GB") for i in (1, 2, 3, 4)]
                for origem, peso in zip((2, 3), ordem[:2]):
                    g.cadastrar_dependencia(Dependencia(origem, 1, peso), ativos)
                with self.assertRaises(ValueError):
                    g.cadastrar_dependencia(Dependencia(4, 1, ordem[2]), ativos)

    def test_montagem_de_A_tambem_recusa_arquivo_editado_a_mao(self):
        ativos = [Notebook(i, f"Ativo{i}", "x", "TI", [], "16GB") for i in (1, 2, 3, 4)]
        deps = [Dependencia(2, 1, 0.7), Dependencia(3, 1, 0.2), Dependencia(4, 1, 0.1)]
        with self.assertRaises(ValueError):
            construir_matriz_dependencias(ativos, deps)

    def test_cadastro_e_montagem_concordam(self):
        with tempfile.TemporaryDirectory() as t:
            g = GerenciadorDependencias(Path(t) / "d.json")
            ativos = [Notebook(i, f"Ativo{i}", "x", "TI", [vuln(i, 5.0)], "16GB") for i in (1, 2, 3, 4)]
            for destino in (1, 2, 3, 4):
                outros = [i for i in (1, 2, 3, 4) if i != destino]
                for origem, peso in zip(outros, (0.7, 0.2, 0.1)):
                    try:
                        g.cadastrar_dependencia(Dependencia(origem, destino, peso), ativos)
                    except ValueError:
                        pass
            # o que o cadastro aceitou, o cálculo consegue resolver (sem erro de soma)
            r = calcular_risco_efetivo(ativos, g.listar_dependencias())
            self.assertEqual(len(r), 4)

    def test_pesos_altos_mas_validos_continuam_aceitos(self):
        with tempfile.TemporaryDirectory() as t:
            g = GerenciadorDependencias(Path(t) / "d.json")
            ativos = [Notebook(i, f"Ativo{i}", "x", "TI", [], "16GB") for i in (1, 2)]
            g.cadastrar_dependencia(Dependencia(2, 1, 0.999), ativos)
            self.assertEqual(len(g.listar_dependencias()), 1)


class TesteBoasPraticasDaAula(unittest.TestCase):
    def test_produto_matricial_com_arroba_igual_ao_slide(self):
        M = [[1, 1, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]]          # V4: coluna nula
        v = [9.8, 5.3, 7.5, 4.3]
        b = multiplicar_matriz_vetor(M, v)
        for obtido, esperado in zip(b, (15.1, 7.5, 5.3)):
            self.assertAlmostEqual(obtido, esperado, places=9)
        np.testing.assert_allclose(b, np.array(M) @ np.array(v))

    def test_composicao_com_fator_de_exposicao_do_slide(self):
        M = np.array([[1, 1, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]])
        v = np.array([9.8, 5.3, 7.5, 4.3])
        F = np.diag([1.5, 1, 1])
        np.testing.assert_allclose(F @ M @ v, [22.65, 7.5, 5.3])

    def test_formas_incompativeis_dao_erro_em_vez_de_resultado_errado(self):
        with self.assertRaises(ValueError):
            multiplicar_matriz_vetor([[1, 1], [0, 1]], [1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            multiplicar_matriz_vetor([[1, 1], [0]], [1.0, 2.0])
        self.assertEqual(multiplicar_matriz_vetor([], []), [])
        self.assertEqual(multiplicar_matriz_vetor([[], []], []), [0.0, 0.0])

    def test_limites_do_numero_de_condicao_sao_os_da_aula(self):
        self.assertEqual(LIMITE_CONDICAO_SINGULAR, 1 / np.finfo(float).eps)
        self.assertEqual(LIMITE_CONDICAO_ALERTA, 1e8)
        self.assertIs(type(LIMITE_CONDICAO_SINGULAR), float)

    def test_diagnostico_so_tem_tipos_serializaveis_em_json(self):
        d = diagnosticar_sistema(ativos_da_aula(), dependencias_da_aula())
        self.assertIs(type(d["invertivel"]), bool)
        self.assertIs(type(d["frágil"]), bool)
        json.dumps(d)

    def test_solucao_e_conferida_substituindo_de_volta(self):
        ativos, deps = ativos_da_aula(), dependencias_da_aula()
        with mock.patch("src.servicos.analise_risco.np.linalg.solve",
                        return_value=np.array([1.0, 2.0, 3.0])):
            with self.assertRaises(ValueError) as erro:
                calcular_risco_efetivo(ativos, deps)
        self.assertIn("não é confiável", str(erro.exception))

    def test_sistema_quase_singular_avisa_como_fragil(self):
        d = _diagnosticar(np.array([[1.0, 1.0], [1.0, 1.0001]]))   # slide 'Condicionamento'
        self.assertAlmostEqual(d["condicao"], 40002, delta=1)
        self.assertFalse(d["frágil"])                                # 4e4 < 1e8: ainda confiável
        self.assertTrue(d["invertivel"])



class TesteFatorDeExposicao(unittest.TestCase):
    """b = F (M v), com F diagonal: cada tipo de ativo informa o seu fator."""

    def test_cada_tipo_informa_o_seu_fator(self):
        esperado = {Notebook: 1.0, Servidor: 1.5, Roteador: 1.2, BancoDeDados: 1.0}
        for classe, fator in esperado.items():
            with self.subTest(tipo=classe.__name__):
                self.assertEqual(
                    classe(1, "nome", "r", "s", [], detalhe_valido(classe)).obter_fator_exposicao(),
                    fator,
                )

    def test_tipo_sem_fator_nao_pode_ser_criado(self):
        class SemFator(Ativo):
            def exibir_detalhes(self): pass
            def obter_tipo(self): return "SemFator"
        with self.assertRaises(TypeError):
            SemFator(1, "n", "r", "s", [])

    def test_matriz_F_e_diagonal_na_ordem_dos_ativos(self):
        ativos = [Servidor(1, "Ativo a", "r", "s", [], "Intel Xeon"),
                  Notebook(2, "Ativo b", "r", "s", [], "16GB"),
                  Roteador(3, "Ativo c", "r", "s", [], "TP-Link Archer C6")]
        np.testing.assert_array_equal(construir_matriz_exposicao(ativos), np.diag([1.5, 1.0, 1.2]))

    def test_exemplo_do_slide_F_igual_a_diag_1_5_1_1(self):
        # Web = Servidor (1,5); App e BD com fator 1,0. Slide: F @ M @ v = [22,65  7,5  5,3]
        ativos = ativos_da_aula()
        ativos[0] = Servidor(1, "Web", "x", "TI", [vuln(1, 9.8), vuln(2, 5.3)], "Intel Xeon")
        r = calcular_risco_efetivo(ativos, dependencias_da_aula())
        for obtido, esperado in zip((x["risco_proprio"] for x in r), (22.65, 7.5, 5.3)):
            self.assertAlmostEqual(obtido, esperado, places=9)
        self.assertEqual([x["fator_exposicao"] for x in r], [1.5, 1.0, 1.0])

    def test_risco_efetivo_com_F_conta_a_mao(self):
        # x_W = 22,65 + 0,2 x_A ; x_A = 7,5 + 0,5 x_W  =>  0,9 x_A = 18,825
        ativos = ativos_da_aula()
        ativos[0] = Servidor(1, "Web", "x", "TI", [vuln(1, 9.8), vuln(2, 5.3)], "Intel Xeon")
        r = calcular_risco_efetivo(ativos, dependencias_da_aula())
        xa = 18.825 / 0.9
        for obtido, esperado in zip((x["risco_efetivo"] for x in r),
                                    (22.65 + 0.2 * xa, xa, 5.3 + 0.6 * xa)):
            self.assertAlmostEqual(obtido, esperado, places=9)

    def test_F_multiplica_so_o_risco_proprio_e_nao_muda_a_invertibilidade(self):
        # F entra em b, não em A: determinante e número de condição de I - A não mudam.
        com_servidor = ativos_da_aula()
        com_servidor[0] = Servidor(1, "Web", "x", "TI", [vuln(1, 9.8), vuln(2, 5.3)], "Intel Xeon")
        d1 = diagnosticar_sistema(ativos_da_aula(), dependencias_da_aula())
        d2 = diagnosticar_sistema(com_servidor, dependencias_da_aula())
        self.assertEqual((d1["determinante"], d1["condicao"]), (d2["determinante"], d2["condicao"]))

    def test_risco_proprio_e_a_soma_das_notas_vezes_o_fator_em_todos_os_tipos(self):
        for classe in (Notebook, Servidor, Roteador, BancoDeDados):
            with self.subTest(tipo=classe.__name__):
                ativo = classe(1, "nome", "r", "s", [vuln(1, 4.0), vuln(2, 4.0)], detalhe_valido(classe))
                r = calcular_risco_efetivo([ativo], [])[0]
                self.assertAlmostEqual(r["risco_proprio"], 8.0 * ativo.obter_fator_exposicao())

    def test_menu_mostra_o_fator_ao_lado_do_risco_proprio(self):
        import main
        from src.servicos.gerenciador_ativos import GerenciadorAtivos
        with tempfile.TemporaryDirectory() as t:
            ga = GerenciadorAtivos(Path(t) / "a.json")
            gd = GerenciadorDependencias(Path(t) / "d.json")
            ga.cadastrar_ativo(Servidor(1, "Web", "x", "TI", [vuln(1, 8.0)], "Intel Xeon"))
            with contextlib.redirect_stdout(io.StringIO()) as saida:
                main.analisar_risco(ga, gd)
        self.assertIn("Risco próprio: 12.00 (fator de exposição 1.5)", saida.getvalue())

    def test_api_devolve_o_fator_e_o_risco_ponderado(self):
        with tempfile.TemporaryDirectory() as t:
            c = criar_app(t).test_client()
            c.post("/api/ativos", json={"id": 1, "tipo": 2, "nome": "Web", "responsavel": "x",
                   "setor": "TI", "processador": "Xeon",
                   "vulnerabilidades": [{"descricao": "d", "categoria": "c", "severidade": 8.0}]})
            r = c.get("/api/risco").json["resultados"][0]
        self.assertEqual((r["risco_proprio"], r["fator_exposicao"], r["risco_efetivo"]), (12.0, 1.5, 12.0))


if __name__ == "__main__":
    unittest.main()
