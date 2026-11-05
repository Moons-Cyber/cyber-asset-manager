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


if __name__ == "__main__":
    unittest.main()
