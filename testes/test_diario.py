"""Diário do serviço (prova das 24 h): uma anotação do risco por hora."""

import json
import tempfile
import time
import unittest
from pathlib import Path

from src.api.aplicacao import criar_app
from src.servicos.diario import Diario, anotar


class TesteDiario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)

    def test_desligado_por_padrao(self):
        c = criar_app(self.tmp.name).test_client()
        self.assertEqual(c.get("/api/diario").status_code, 404)
        self.assertFalse((self.pasta / "diario.json").exists())

    def test_anota_ao_ligar_e_sobrevive_ao_reinicio(self):
        app = criar_app(self.tmp.name, diario_intervalo=0)
        self.assertIsNone(app.extensions["gravador_diario"])      # 0 = sem thread
        d = app.test_client().get("/api/diario").json
        self.assertEqual([e["motivo"] for e in d["entradas"]], ["inicialização"])
        criar_app(self.tmp.name, diario_intervalo=0)
        d = criar_app(self.tmp.name, diario_intervalo=0).test_client().get("/api/diario").json
        self.assertEqual(len(d["entradas"]), 3)

    def test_entrada_traz_o_risco_global_exato(self):
        app = criar_app(self.tmp.name, diario_intervalo=0)
        c = app.test_client()
        c.post("/api/ativos", json={"tipo": 2, "id": 1, "nome": "Servidor web", "responsavel": "Ana",
                                    "setor": "TI", "processador": "Xeon"})
        c.post("/api/ativos/1/vulnerabilidades", json={"categoria": "Web", "severidade": 8,
                                                       "descricao": "Falha no servidor web"})
        app.extensions["anotar_diario"]("teste")
        ultima = c.get("/api/diario").json["entradas"][-1]
        self.assertEqual(ultima["motivo"], "teste")
        self.assertAlmostEqual(ultima["risco_global"], 8 * 1.5)    # nota × fator do Servidor
        self.assertTrue(ultima["invertivel"])
        self.assertIsNone(ultima["erro"])

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
        (self.pasta / "diario.json").write_text("{ quebrado", encoding="utf-8")
        with self.assertLogs("src.servicos.diario", level="WARNING"):
            self.assertEqual(Diario(self.pasta / "diario.json").listar(), [])

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
            app.extensions["anotar_diario"]("teste")      # o mesmo caminho da thread
        self.assertEqual(app.test_client().get("/api/saude").status_code, 200)

    def test_anotar_registra_erro_em_vez_de_quebrar(self):
        class Quebrado:
            id = 1
            nome = "x"
            vulnerabilidades = []

            def obter_fator_exposicao(self):
                raise ValueError("dados ruins")

        entrada = anotar([Quebrado()], [], "teste", agora=5)
        self.assertEqual((entrada["t"], entrada["erro"]), (5, "dados ruins"))


if __name__ == "__main__":
    unittest.main()
