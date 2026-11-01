"""Testes do simulador de contágio.

O teste mais importante é o primeiro grupo: a média das epidemias sorteadas
(Monte Carlo) tem que chegar no mesmo x do np.linalg.solve.
"""

import json
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from src.api.aplicacao import criar_app
from src.servicos.analise_risco import calcular_risco_efetivo
from src.servicos.contagio import (
    analisar_surto,
    multiplicadores,
    raio_espectral,
    ranking_correcoes,
    resolver_exato,
    respeita_regra_do_projeto,
    simular_surto,
)
from src.servicos.diario_surto import Diario, anotar

# Exemplo da aula, feito à mão:
#   ativo 1 recebe 0,5 do ativo 2; ativo 2 recebe 0,2 do ativo 1
#   x1 = 8 + 0,5·x2   e   x2 = 4 + 0,2·x1   ->   x = (11,11 ; 6,22)
A_MAO = np.array([[0.0, 0.5], [0.2, 0.0]])
B_MAO = np.array([8.0, 4.0])


class TesteAlgebra(unittest.TestCase):
    def test_exemplo_feito_a_mao(self):
        x = resolver_exato(A_MAO, B_MAO)
        np.testing.assert_allclose(x, [100 / 9, 56 / 9])

    def test_raio_espectral_e_o_r0(self):
        # autovalores de [[0, .5], [.2, 0]] são ±sqrt(0,1)
        self.assertAlmostEqual(raio_espectral(A_MAO), 0.1 ** 0.5)
        self.assertAlmostEqual(raio_espectral(A_MAO * 4), 4 * 0.1 ** 0.5)

    def test_sem_solucao_quando_o_surto_explode(self):
        self.assertIsNone(resolver_exato(A_MAO * 4, B_MAO))       # rho = 1,26

    def test_regra_do_projeto_e_mais_exigente_que_o_r0(self):
        # Com escala 1,8 o ativo 1 recebe 0,9 + ... : a regra ainda aceita.
        # Com escala 2,1 recebe 1,05 (> 1): a regra recusa, mas rho = 0,66 < 1.
        self.assertFalse(respeita_regra_do_projeto(A_MAO * 2.1))
        self.assertLess(raio_espectral(A_MAO * 2.1), 1)
        self.assertIsNotNone(resolver_exato(A_MAO * 2.1, B_MAO))

    def test_multiplicador_e_a_soma_da_coluna_da_inversa(self):
        inversa = np.linalg.inv(np.eye(2) - A_MAO)
        np.testing.assert_allclose(multiplicadores(A_MAO), inversa.sum(axis=0))


class TesteMonteCarlo(unittest.TestCase):
    def test_media_das_epidemias_chega_na_solucao(self):
        r = simular_surto(A_MAO, B_MAO, rodadas=20000, semente=1)
        np.testing.assert_allclose(r["estimativa"], resolver_exato(A_MAO, B_MAO), rtol=0.03)
        self.assertFalse(r["explodiu"])
        self.assertEqual(r["rodadas"], 20000)

    def test_mesma_semente_mesmo_resultado(self):
        a = simular_surto(A_MAO, B_MAO, rodadas=500, semente=42)
        b = simular_surto(A_MAO, B_MAO, rodadas=500, semente=42)
        self.assertEqual(a, b)

    def test_sem_dependencias_o_resultado_e_exato(self):
        r = simular_surto(np.zeros((2, 2)), B_MAO, rodadas=100, semente=1)
        self.assertEqual(r["estimativa"], [8.0, 4.0])

    def test_curva_termina_no_total_de_rodadas(self):
        r = simular_surto(A_MAO, B_MAO, rodadas=1000, semente=1, pontos_curva=10)
        self.assertEqual(len(r["curva"]), 10)
        self.assertEqual(r["curva"][-1][0], 1000)
        self.assertAlmostEqual(r["curva"][-1][1], r["global"], places=3)

    def test_surto_com_r0_acima_de_1_explode(self):
        r = simular_surto(A_MAO * 4, B_MAO, rodadas=2000, semente=1, limite=50_000)
        self.assertTrue(r["explodiu"])

    def test_peso_acima_de_1_mantem_a_media(self):
        # Só a escala produz peso > 1. A média por salto tem que ser o peso.
        a = np.array([[0.0, 0.0], [1.5, 0.0]])
        r = simular_surto(a, np.array([2.0, 0.0]), rodadas=4000, semente=3)
        self.assertAlmostEqual(r["estimativa"][1], 1.5 * 2.0, delta=0.15)

    def test_rede_vazia(self):
        r = simular_surto(np.zeros((0, 0)), np.zeros(0), rodadas=10)
        self.assertEqual(r["estimativa"], [])


class BaseApi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = criar_app(self.tmp.name)
        self.c = self.app.test_client()

    def ativo(self, id_, nome, *notas):
        r = self.c.post("/api/ativos", json={
            "id": id_, "tipo": 1, "nome": nome, "responsavel": "Ana",
            "setor": "TI", "memoria_ram": "8GB",
            "vulnerabilidades": [
                {"categoria": "RCE", "descricao": f"Falha {k}", "severidade": n}
                for k, n in enumerate(notas)
            ],
        })
        self.assertEqual(r.status_code, 201, r.json)

    def rede(self):
        self.ativo(1, "Servidor", 8.0)
        self.ativo(2, "Estação", 4.0, 3.0)
        self.ativo(3, "Impressora")
        for origem, destino, peso in [(2, 1, 0.5), (1, 2, 0.2), (1, 3, 0.4)]:
            self.c.post("/api/dependencias", json={"origem": origem, "destino": destino, "peso": peso})


class TesteRanking(BaseApi):
    def test_queda_prevista_e_a_queda_real(self):
        """A conta do ranking (linear) bate com recalcular tudo de verdade."""
        self.rede()
        gerente = self.app.test_client().get("/api/risco").json
        antes = sum(r["risco_efetivo"] for r in gerente["resultados"])
        ranking = self.c.get("/api/surto?rodadas=100").json["ranking"]
        self.assertEqual(len(ranking), 3)
        self.assertEqual(ranking, sorted(ranking, key=lambda i: -i["queda_global"]))

        for item in ranking:
            alvo = f"/api/ativos/{item['ativo_id']}/vulnerabilidades/{item['vulnerabilidade_id']}"
            self.c.patch(alvo, json={"status": "Corrigida"})
            depois = sum(r["risco_efetivo"] for r in self.c.get("/api/risco").json["resultados"])
            self.assertAlmostEqual(antes - depois, item["queda_global"], places=9)
            self.c.patch(alvo, json={"status": "Aberta"})

    def test_ranking_vazio_sem_falhas(self):
        self.ativo(1, "Servidor")
        self.assertEqual(self.c.get("/api/surto?rodadas=100").json["ranking"], [])

    def test_funcao_ignora_corrigidas(self):
        self.rede()
        alvo = "/api/ativos/1/vulnerabilidades"
        vid = self.c.get(alvo).json[0]["id"]
        self.c.patch(f"{alvo}/{vid}", json={"status": "Corrigida"})
        pares = [(i["ativo_id"], i["vulnerabilidade_id"])
                 for i in self.c.get("/api/surto?rodadas=100").json["ranking"]]
        self.assertNotIn((1, vid), pares)
        self.assertEqual(len(pares), 2)


class TesteRotaSurto(BaseApi):
    def test_formato_e_concordancia(self):
        self.rede()
        r = self.c.get("/api/surto?rodadas=20000&semente=5")
        self.assertEqual(r.status_code, 200)
        d = r.json
        oficial = {x["id"]: x["risco_efetivo"] for x in self.c.get("/api/risco").json["resultados"]}
        self.assertEqual([a["id"] for a in d["ativos"]], [1, 2, 3])
        np.testing.assert_allclose(d["x"], [oficial[1], oficial[2], oficial[3]])
        self.assertLess(d["erro_relativo"], 0.03)
        self.assertTrue(d["convergente"])
        self.assertTrue(d["regra_do_projeto"])
        self.assertIn("fragil", d["diagnostico"])
        self.assertEqual(len(d["A"]), 3)
        self.assertEqual(d["A"][0][1], 0.5)                  # A[destino][origem]

    def test_escala_explode_sem_mexer_nos_dados(self):
        self.rede()
        d = self.c.get("/api/surto?escala=6&rodadas=500&semente=1").json
        self.assertFalse(d["convergente"])
        self.assertIsNone(d["x"])
        self.assertTrue(d["monte_carlo"]["explodiu"])
        pesos = [x["peso"] for x in self.c.get("/api/dependencias").json]
        self.assertEqual(sorted(pesos), [0.2, 0.4, 0.5])     # dados intactos

    def test_parametros_invalidos(self):
        for url in ["/api/surto?escala=0", "/api/surto?escala=7", "/api/surto?escala=abc",
                    "/api/surto?escala=nan", "/api/surto?rodadas=5", "/api/surto?rodadas=1.5",
                    "/api/surto?semente=-1"]:
            with self.subTest(url=url):
                self.assertEqual(self.c.get(url).status_code, 400)

    def test_sem_ativos(self):
        d = self.c.get("/api/surto").json
        self.assertEqual((d["n"], d["ativos"], d["x"], d["ranking"]), (0, [], [], []))

    def test_pagina_e_arquivos(self):
        for url in ["/surto", "/surto/app.js", "/surto/pixel.js", "/surto/surto.css"]:
            with self.subTest(url=url):
                r = self.c.get(url)
                self.addCleanup(r.close)
                self.assertEqual(r.status_code, 200)
        for url in ["/surto/../servidor.py", "/surto/ativos.json", "/surto/nada.js"]:
            with self.subTest(url=url):
                self.assertEqual(self.c.get(url).status_code, 404)

    def test_raiz_aponta_para_a_interface(self):
        self.assertEqual(self.c.get("/").json["interface"], "/surto")


class TesteDiario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)

    def test_desligado_por_padrao(self):
        c = criar_app(self.tmp.name).test_client()
        self.assertEqual(c.get("/api/surto/diario").status_code, 404)
        self.assertFalse((self.pasta / "diario_surto.json").exists())

    def test_anota_ao_ligar_e_sobrevive_ao_reinicio(self):
        app = criar_app(self.tmp.name, diario_intervalo=0)
        self.assertIsNone(app.extensions["gravador_diario"])      # 0 = sem thread
        d = app.test_client().get("/api/surto/diario").json
        self.assertEqual([e["motivo"] for e in d["entradas"]], ["inicialização"])
        criar_app(self.tmp.name, diario_intervalo=0)
        d = criar_app(self.tmp.name, diario_intervalo=0).test_client().get("/api/surto/diario").json
        self.assertEqual(len(d["entradas"]), 3)

    def test_thread_periodica(self):
        app = criar_app(self.tmp.name, diario_intervalo=0.05)
        gravador = app.extensions["gravador_diario"]
        self.addCleanup(gravador.parar)
        fim = time.time() + 3
        while time.time() < fim and len(app.extensions["diario"].listar()) < 3:
            time.sleep(0.02)
        motivos = [e["motivo"] for e in app.extensions["diario"].listar()]
        self.assertEqual(motivos[0], "inicialização")
        self.assertIn("periódica", motivos)

    def test_arquivo_corrompido_recomeca_vazio(self):
        (self.pasta / "diario_surto.json").write_text("{ quebrado", encoding="utf-8")
        with self.assertLogs("src.servicos.diario_surto", level="WARNING"):
            self.assertEqual(Diario(self.pasta / "diario_surto.json").listar(), [])

    def test_tamanho_maximo(self):
        diario = Diario(self.pasta / "d.json", max_entradas=10)
        for t in range(25):
            diario.adicionar({"t": t})
        self.assertEqual([e["t"] for e in diario.listar()], list(range(15, 25)))
        dados = json.loads((self.pasta / "d.json").read_text(encoding="utf-8"))
        self.assertEqual(len(dados["entradas"]), 10)

    def test_falha_no_diario_nao_derruba_a_api(self):
        app = criar_app(self.tmp.name, diario_intervalo=0)
        app.extensions["diario"].adicionar = lambda e: (_ for _ in ()).throw(OSError("disco cheio"))
        with self.assertLogs(app.logger, level="ERROR"):
            app.extensions["anotar_surto"]("teste")      # o mesmo caminho da thread
        self.assertEqual(app.test_client().get("/api/saude").status_code, 200)

    def test_anotar_registra_erro_em_vez_de_quebrar(self):
        class Quebrado:
            id = 1
            nome = "x"
            vulnerabilidades = []

            def obter_fator_exposicao(self):
                raise ValueError("dados ruins")

        try:
            entrada = anotar([Quebrado()], [], "teste", rodadas=10, agora=5)
        except ValueError:
            self.fail("anotar() deveria capturar o ValueError")
        self.assertEqual((entrada["t"], entrada["erro"]), (5, "dados ruins"))
