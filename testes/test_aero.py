"""Testes do tema Aero: páginas servidas só pela lista de arquivos permitidos."""

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
        em_disco = {p.name for p in PASTA_AERO.iterdir() if p.is_file()}
        self.assertEqual(em_disco - {"index.html"}, set(ARQUIVOS_AERO))

    def test_index_so_carrega_scripts_servidos(self):
        html = (PASTA_AERO / "index.html").read_text(encoding="utf-8")
        for caminho in re.findall(r'(?:src|href)="(/(?:aero|surto)/[^"]+)"', html):
            with self.subTest(caminho=caminho):
                self.assertEqual(self.pegar(caminho).status_code, 200)

    def test_nomes_fora_da_lista_dao_404(self):
        for url in ["/aero/../servidor.py", "/aero/index.html", "/aero/nada.js", "/aero/..%2Fservidor.py"]:
            with self.subTest(url=url):
                self.assertEqual(self.pegar(url).status_code, 404)

    def test_nao_fica_em_cache_e_raiz_aponta_para_ele(self):
        self.assertEqual(self.pegar("/aero").headers["Cache-Control"], "no-store")
        self.assertEqual(self.c.get("/").json["interface_aero"], "/aero")

    def test_tema_pixel_tem_link_para_o_aero(self):
        self.assertIn('href="/aero"', self.pegar("/surto").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
