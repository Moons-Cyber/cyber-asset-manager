"""Orientação de segurança: reconhecer o tipo da falha e explicar a prevenção."""

import re
import tempfile
import unittest

from src.api.aplicacao import criar_app
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.servicos.orientacao_seguranca import (
    DICA_POR_TIPO, GENERICA, ORIENTACOES, normalizar, reconhecer,
)


def falha(categoria, descricao="x", original=None, nota=7.0, status="Aberta"):
    return Vulnerabilidade(descricao, categoria, nota, status, descricao_original=original)


class TesteReconhecer(unittest.TestCase):
    def tipo(self, *args, **kw):
        return reconhecer(falha(*args, **kw))[0].chave

    def test_categorias_em_portugues(self):
        casos = {
            "Injeção SQL": "injecao_sql", "injecao de sql": "injecao_sql",
            "XSS": "xss", "Execução remota": "execucao_remota",
            "Elevação de privilégio": "privilegio", "Senha padrão": "credenciais",
            "Sistema desatualizado": "desatualizado", "Negação de serviço": "negacao_servico",
            "Vazamento de dados": "dados_expostos", "Configuração insegura": "configuracao",
            "Bypass de autenticação": "autenticacao", "Path traversal": "caminho",
            "Estouro de buffer": "memoria", "CSRF": "csrf", "Desserialização": "desserializacao",
            "Injeção de comando": "injecao_comando",
        }
        for categoria, esperado in casos.items():
            with self.subTest(categoria=categoria):
                self.assertEqual(self.tipo(categoria), esperado)

    def test_texto_do_nvd_em_ingles(self):
        original = "Apache Log4j2 JNDI features ... allows remote code execution by an attacker."
        o, onde, termo = reconhecer(falha("Biblioteca", "Falha na biblioteca de log", original))
        self.assertEqual((o.chave, onde, termo), ("execucao_remota", "descrição do NVD", "remote code execution"))

    def test_categoria_tem_prioridade_sobre_a_descricao(self):
        self.assertEqual(self.tipo("Senha fraca", "permite execução remota"), "credenciais")

    def test_palavra_curta_nao_engana(self):
        # "dos" em português não é DoS; "PostgreSQL" não é injeção de SQL.
        self.assertEqual(self.tipo("Problema dos ativos", "Banco PostgreSQL"), GENERICA.chave)

    def test_sem_reconhecer_cai_na_generica(self):
        o, onde, termo = reconhecer(falha("Outro", "algo estranho"))
        self.assertIs(o, GENERICA)
        self.assertIsNone(onde)

    def test_normalizar(self):
        self.assertEqual(normalizar("Elevação de PRIVILÉGIO"), "elevacao de privilegio")


class TesteBase(unittest.TestCase):
    def test_cada_tipo_esta_completo(self):
        for o in ORIENTACOES + (GENERICA,):
            with self.subTest(tipo=o.chave):
                self.assertTrue(o.titulo and o.o_que_e and o.por_que_perigoso)
                self.assertGreaterEqual(len(o.como_prevenir), 3)
                self.assertGreaterEqual(len(o.como_corrigir_agora), 2)
                if o is not GENERICA:
                    self.assertRegex(o.cwe, r"^CWE-\d+$")
                    self.assertTrue(o.padroes)

    def test_padroes_estao_sem_acento_e_em_minusculas(self):
        # O texto é normalizado antes da busca; um padrão com acento nunca acharia nada.
        for o in ORIENTACOES:
            for padrao in o.padroes:
                with self.subTest(padrao=padrao):
                    self.assertEqual(padrao, normalizar(padrao))
                    re.compile(padrao)

    def test_chaves_unicas_e_dica_para_todo_tipo_de_ativo(self):
        chaves = [o.chave for o in ORIENTACOES]
        self.assertEqual(len(chaves), len(set(chaves)))
        self.assertEqual(set(DICA_POR_TIPO), {"Notebook", "Servidor", "Roteador", "BancoDeDados"})


class TesteRota(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = criar_app(self.tmp.name).test_client()
        self.post("/api/ativos", {"tipo": 3, "id": 1, "nome": "Roteador", "responsavel": "Ana",
                                  "setor": "TI", "modelo": "RB"})
        self.post("/api/ativos", {"tipo": 2, "id": 2, "nome": "Servidor web", "responsavel": "Ana",
                                  "setor": "TI", "processador": "Xeon"})
        self.vid = self.post("/api/ativos/2/vulnerabilidades",
                             {"categoria": "Injeção SQL", "severidade": 8, "descricao": "Busca do site"})["id"]
        self.post("/api/ativos/2/vulnerabilidades",
                  {"categoria": "Web", "severidade": 4, "descricao": "Cabeçalho ausente"})
        self.post("/api/dependencias", {"origem": 2, "destino": 1, "peso": 0.5})

    def post(self, url, corpo):
        r = self.c.post(url, json=corpo)
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()

    def orientacao(self, vid=None, ativo=2):
        return self.c.get(f"/api/ativos/{ativo}/vulnerabilidades/{vid or self.vid}/orientacao")

    def test_explica_e_calcula_o_efeito_no_risco(self):
        r = self.orientacao()
        self.assertEqual(r.status_code, 200)
        o = r.get_json()
        self.assertEqual((o["tipo"], o["cwe"], o["reconhecido_por"]), ("injecao_sql", "CWE-89", "categoria"))
        self.assertEqual(o["ativo"]["nome"], "Servidor web")
        self.assertIn("Servidores", o["neste_ativo"])
        self.assertTrue(o["gravidade"].startswith("Alta"))
        e = o["efeito_no_risco"]
        self.assertAlmostEqual(e["risco_proprio_atual"], 1.5 * (8 + 4))
        self.assertAlmostEqual(e["reducao"], 1.5 * 8)
        self.assertAlmostEqual(e["risco_proprio_sem_ela"], 1.5 * 4)
        self.assertEqual(e["passa_risco_para"], ["Roteador"])

    def test_corrigida_nao_reduz_mais(self):
        self.c.patch(f"/api/ativos/2/vulnerabilidades/{self.vid}", json={"status": "Corrigida"})
        o = self.orientacao().get_json()
        self.assertFalse(o["efeito_no_risco"]["conta_no_risco"])
        self.assertEqual(o["efeito_no_risco"]["reducao"], 0)
        self.assertIn("corrigida", o["situacao"])

    def test_nao_encontrada(self):
        self.assertEqual(self.orientacao("LOCAL-00000000").status_code, 404)
        self.assertEqual(self.orientacao(ativo=99).status_code, 404)

    def test_nao_altera_nada(self):
        antes = self.c.get("/api/ativos").get_json()
        self.orientacao()
        self.assertEqual(self.c.get("/api/ativos").get_json(), antes)


class TesteRepetida(unittest.TestCase):
    def test_copia_repetida_no_mesmo_ativo_nao_reduz(self):
        from src.servicos.orientacao_seguranca import efeito_no_risco
        v1, v2 = falha("Senha", "igual", nota=5), falha("Senha", "igual", nota=5)
        s = Servidor(1, "Servidor", "Ana", "TI", [v1, v2], "Xeon")
        self.assertEqual(efeito_no_risco([s], [], s, v1)["reducao"], 0.0)


if __name__ == "__main__":
    unittest.main()
