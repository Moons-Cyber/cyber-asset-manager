"""Rota /api/risco/passos: as etapas da conta que o Assistente mostra."""

import tempfile
import unittest

from src.api.aplicacao import criar_app


class TestePassos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = criar_app(self.tmp.name).test_client()

    def ok(self, r, status=201):
        self.assertEqual(r.status_code, status, r.get_json())
        return r.get_json()

    def montar_rede(self):
        # Roteador (fator 1,2) passa 50% do risco para o Servidor (fator 1,5).
        self.ok(self.c.post("/api/ativos", json={"tipo": 3, "id": 1, "nome": "Roteador", "responsavel": "Ana",
                                                 "setor": "TI", "modelo": "RB"}))
        self.ok(self.c.post("/api/ativos", json={"tipo": 2, "id": 2, "nome": "Servidor", "responsavel": "Ana",
                                                 "setor": "TI", "processador": "Xeon"}))
        self.ok(self.c.post("/api/ativos/1/vulnerabilidades", json={"categoria": "Rede", "severidade": 5,
                                                                    "descricao": "Senha padrão"}))
        self.ok(self.c.post("/api/ativos/2/vulnerabilidades", json={"categoria": "Web", "severidade": 4,
                                                                    "descricao": "Versão antiga"}))
        self.ok(self.c.post("/api/dependencias", json={"origem": 1, "destino": 2, "peso": 0.5}))

    def test_etapas_conferem_com_a_conta_feita_a_mao(self):
        self.montar_rede()
        p = self.ok(self.c.get("/api/risco/passos"), 200)
        self.assertEqual(p["M"], [[1, 0], [0, 1]])
        self.assertEqual(p["v"], [5.0, 4.0])
        self.assertEqual(p["Mv"], [5.0, 4.0])
        self.assertEqual([a["fator"] for a in p["ativos"]], [1.2, 1.5])
        self.assertAlmostEqual(p["b"][0], 6.0)            # 1,2 × 5
        self.assertAlmostEqual(p["b"][1], 6.0)            # 1,5 × 4
        self.assertEqual(p["A"], [[0.0, 0.0], [0.5, 0.0]])  # linha = quem recebe
        self.assertEqual(p["I_menos_A"], [[1.0, 0.0], [-0.5, 1.0]])
        self.assertAlmostEqual(p["x"][0], 6.0)
        self.assertAlmostEqual(p["x"][1], 9.0)            # 6 + 0,5 × 6
        self.assertAlmostEqual(p["risco_global"], 15.0)
        self.assertLess(p["residuo"], 1e-9)
        self.assertTrue(p["diagnostico"]["invertivel"])
        self.assertIn("fragil", p["diagnostico"])
        self.assertEqual(p["somas_recebidas"], [0.0, 0.5])

    def test_mesmo_resultado_que_a_rota_de_risco(self):
        self.montar_rede()
        passos = self.ok(self.c.get("/api/risco/passos"), 200)
        risco = self.ok(self.c.get("/api/risco"), 200)
        for x, r in zip(passos["x"], risco["resultados"]):
            self.assertAlmostEqual(x, r["risco_efetivo"])

    def test_vulnerabilidade_traz_o_id(self):
        self.montar_rede()
        p = self.ok(self.c.get("/api/risco/passos"), 200)
        self.assertTrue(all(v["id"] for v in p["vulnerabilidades"]))

    def test_sem_ativos(self):
        p = self.ok(self.c.get("/api/risco/passos"), 200)
        self.assertEqual((p["ativos"], p["x"], p["diagnostico"]), ([], None, None))


if __name__ == "__main__":
    unittest.main()
