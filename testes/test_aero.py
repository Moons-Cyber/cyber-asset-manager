"""Testes da interface (tema Aero): arquivos servidos só pela lista permitida,
e as explicações do Assistente batendo com o código de verdade."""

import json
import re
import tempfile
import unittest

from src.api.aplicacao import ARQUIVOS_AERO, PASTA_AERO, criar_app


class TesteTemaAero(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = criar_app(self.tmp.name).test_client()

    def pegar(self, url):
        r = self.c.get(url)
        self.addCleanup(r.close)
        return r

    def test_pagina_e_todos_os_arquivos_da_lista(self):
        self.assertEqual(self.pegar("/aero").status_code, 200)
        for nome in sorted(ARQUIVOS_AERO):
            with self.subTest(arquivo=nome):
                self.assertEqual(self.pegar(f"/aero/{nome}").status_code, 200)

    def test_arquivos_da_lista_existem_e_nada_sobra_na_pasta(self):
        em_disco = {p.name for p in PASTA_AERO.iterdir() if p.is_file() and p.suffix != ".bak"}
        self.assertEqual(em_disco - {"index.html"}, set(ARQUIVOS_AERO))

    def test_index_so_carrega_scripts_servidos(self):
        html = (PASTA_AERO / "index.html").read_text(encoding="utf-8")
        for caminho in re.findall(r'(?:src|href)="(/aero/[^"]+)"', html):
            with self.subTest(caminho=caminho):
                self.assertEqual(self.pegar(caminho).status_code, 200)

    def test_nomes_fora_da_lista_dao_404(self):
        for url in ["/aero/../servidor.py", "/aero/index.html", "/aero/nada.js", "/aero/..%2Fservidor.py"]:
            with self.subTest(url=url):
                self.assertEqual(self.pegar(url).status_code, 404)

    def test_nao_fica_em_cache_e_raiz_aponta_para_ele(self):
        self.assertEqual(self.pegar("/aero").headers["Cache-Control"], "no-store")
        self.assertEqual(self.c.get("/").json["interface"], "/aero")

    def test_tema_pixel_e_surto_foram_removidos(self):
        for url in ["/surto", "/surto/app.js", "/api/surto", "/api/surto/diario"]:
            with self.subTest(url=url):
                self.assertEqual(self.pegar(url).status_code, 404)


class TesteExplicacoesDoAssistente(unittest.TestCase):
    """Cada caixa "No código" cita um trecho real: se o código mudar, isto avisa."""

    RAIZ = PASTA_AERO.parents[2]
    PADRAO = re.compile(r'arquivo: "([^"]+)", funcao: "([^"]+)", trecho: "((?:[^"\\]|\\.)*)"')

    def citacoes(self):
        texto = (PASTA_AERO / "explicacoes.js").read_text(encoding="utf-8")
        return [(a, f, json.loads(f'"{t}"')) for a, f, t in self.PADRAO.findall(texto)]

    def test_ha_citacoes(self):
        self.assertGreaterEqual(len(self.citacoes()), 10)

    def test_cada_trecho_existe_no_arquivo_e_na_funcao_citada(self):
        for arquivo, funcao, trecho in self.citacoes():
            with self.subTest(arquivo=arquivo, trecho=trecho):
                fonte = (self.RAIZ / arquivo).read_text(encoding="utf-8")
                inicio = fonte.find(f"def {funcao}(")
                self.assertNotEqual(inicio, -1, f"função {funcao} não existe em {arquivo}")
                proxima = re.search(r"\n(?:    )?def |\n    @app\.", fonte[inicio + 4:])
                corpo = fonte[inicio: inicio + 4 + proxima.start()] if proxima else fonte[inicio:]
                self.assertIn(trecho, corpo, f"o trecho não está dentro de {funcao}()")

    def test_arquivos_do_guia_existem(self):
        texto = (PASTA_AERO / "explicacoes.js").read_text(encoding="utf-8")
        for caminho in re.findall(r'\["((?:src/|servidor|Dockerfile|docker-compose)[^" ]*)', texto):
            with self.subTest(caminho=caminho):
                self.assertTrue((self.RAIZ / caminho).exists(), caminho)


class TesteMatrizesEGrafico(unittest.TestCase):
    """A janela Matrizes só desenha /api/risco/passos: estes testes garantem que
    ela está ligada à tela e que os dados que ela lê têm o formato esperado."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = criar_app(self.tmp.name).test_client()

    def test_janela_esta_no_index_no_desktop_e_no_assistente(self):
        self.assertIn("app_matrizes.js", (PASTA_AERO / "index.html").read_text(encoding="utf-8"))
        self.assertIn("AppMatrizes.abrir", (PASTA_AERO / "desktop.js").read_text(encoding="utf-8"))
        self.assertIn("AppMatrizes.abrir", (PASTA_AERO / "app_assistente.js").read_text(encoding="utf-8"))
        self.assertIn("matriz:", (PASTA_AERO / "icones.js").read_text(encoding="utf-8"))

    def test_dados_lidos_pela_janela_tem_o_formato_esperado(self):
        ids = [1, 2, 3]
        campos = {3: {"modelo": "RB"}, 2: {"processador": "Xeon"}, 4: {"sgbd": "PostgreSQL"}}
        for id_, nome, tipo in [(1, "Roteador", 3), (2, "Servidor", 2), (3, "Banco", 4)]:
            r = self.c.post("/api/ativos", json={"tipo": tipo, "id": id_, "nome": nome, "setor": "TI",
                                                 "responsavel": "Ana", **campos[tipo]})
            self.assertEqual(r.status_code, 201, r.json)
        for o, d, peso in [(1, 2, 0.3), (2, 3, 0.2)]:
            r = self.c.post("/api/dependencias", json={"origem": o, "destino": d, "peso": peso})
            self.assertEqual(r.status_code, 201, r.json)
        d = self.c.get("/api/risco/passos").json
        n = len(ids)
        for campo in ("A", "I_menos_A"):
            self.assertEqual(len(d[campo]), n)
            self.assertTrue(all(len(linha) == n for linha in d[campo]))
        self.assertEqual(len(d["b"]), n)
        self.assertEqual(len(d["x"]), n)
        self.assertEqual(len(d["somas_recebidas"]), n)
        self.assertTrue(d["diagnostico"]["invertivel"])
        # A[destino][origem]: o Servidor (linha 1) recebe 0,3 do Roteador (coluna 0)
        self.assertAlmostEqual(d["A"][1][0], 0.3)
        self.assertAlmostEqual(d["I_menos_A"][1][0], -0.3)
        self.assertAlmostEqual(d["I_menos_A"][1][1], 1.0)

    def test_sem_ativos_a_janela_recebe_listas_vazias(self):
        d = self.c.get("/api/risco/passos").json
        self.assertEqual(d["ativos"], [])
        self.assertEqual(d["A"], [])


if __name__ == "__main__":
    unittest.main()
