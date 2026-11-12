"""S4_06/S4_07: persistência em SQLite no lugar do JSON, relatórios e migração."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from src.api.aplicacao import criar_app
from src.modelos.dependencia import Dependencia
from src.modelos.notebook import Notebook
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.erros import ErroDados
from src.persistencia.fabrica_repositorios import criar_repositorios, modo_do_ambiente
from src.persistencia.repositorio_sqlite import RepositorioAtivosSqlite, RepositorioDependenciasSqlite
from src.servicos import relatorios_sql
from src.servicos.gerenciador_ativos import GerenciadorAtivos
from src.servicos.gerenciador_dependencias import GerenciadorDependencias

RAIZ = Path(__file__).resolve().parent.parent


def vuln(id_, nota, status="Aberta", cat="Segurança"):
    return Vulnerabilidade(f"Falha {id_}", cat, nota, status, id=id_, fonte="NVD")


def ativos_exemplo():
    return [
        Notebook(1, "Notebook A", "Ana", "TI", [vuln("CVE-1", 10.0), vuln("CVE-2", 5.0, "Corrigida")], "16GB"),
        Servidor(2, "Servidor B", "Bia", "RH", [vuln("CVE-1", 10.0, "Em tratamento"), vuln("CVE-3", 8.8)], "AMD EPYC"),
        Notebook(3, "Notebook C", "Caio", "TI", [], "8GB"),
    ]


class TesteRepositorioSqlite(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.banco = Path(self.pasta.name) / "inventario.db"
        self.repo = RepositorioAtivosSqlite(self.banco)

    def tearDown(self):
        self.pasta.cleanup()

    def test_banco_vazio_devolve_lista_vazia(self):
        self.assertEqual(self.repo.listar(), [])

    def test_ida_e_volta_preserva_tudo(self):
        self.repo.salvar(ativos_exemplo())
        volta = self.repo.listar()
        self.assertEqual([a.para_dict() for a in volta], [a.para_dict() for a in ativos_exemplo()])

    def test_status_e_do_par_ativo_vulnerabilidade(self):
        """A mesma CVE fica 'Aberta' num ativo e 'Em tratamento' em outro."""
        self.repo.salvar(ativos_exemplo())
        por_id = {a.id: a for a in self.repo.listar()}
        self.assertEqual(por_id[1].vulnerabilidades[0].status.value, "Aberta")
        self.assertEqual(por_id[2].vulnerabilidades[0].status.value, "Em tratamento")
        with closing(sqlite3.connect(self.banco)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM vulnerabilidades WHERE id='CVE-1'").fetchone()[0], 1)

    def test_salvar_substitui_e_remove_vulnerabilidades_sem_uso(self):
        self.repo.salvar(ativos_exemplo())
        self.repo.salvar(ativos_exemplo()[2:])          # só o ativo 3, sem vulnerabilidades
        with closing(sqlite3.connect(self.banco)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM vulnerabilidades").fetchone()[0], 0)
        self.assertEqual([a.id for a in self.repo.listar()], [3])

    def test_falha_no_meio_nao_deixa_o_banco_pela_metade(self):
        self.repo.salvar(ativos_exemplo())
        a, b = ativos_exemplo()[:2]
        b.id = a.id                                      # ID repetido: viola a chave primária
        with self.assertRaises(ErroDados):
            self.repo.salvar([a, b])
        self.assertEqual(len(self.repo.listar()), 3)     # o conteúdo antigo continua inteiro

    def test_arquivo_que_nao_e_banco_vira_erro_de_dados(self):
        self.banco.write_text("isto não é um banco sqlite")
        with self.assertRaises(ErroDados):
            self.repo.listar()

    def test_nome_com_aspas_e_sql_nao_executa(self):
        perigoso = Notebook(1, "x'); DROP TABLE ativos;--", "Ana", "TI", [], "16GB")
        self.repo.salvar([perigoso])
        self.assertEqual(self.repo.listar()[0].nome, "x'); DROP TABLE ativos;--")

    def test_gerenciador_funciona_sobre_o_sqlite(self):
        g = GerenciadorAtivos(self.banco, repositorio=self.repo)
        g.cadastrar_ativo(Notebook(7, "Notebook Z", "Zé", "TI", [], "32GB"))
        g2 = GerenciadorAtivos(self.banco, repositorio=RepositorioAtivosSqlite(self.banco))
        self.assertEqual(g2.buscar_ativo_por_id(7).nome, "Notebook Z")


class TesteDependenciasSqlite(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.banco = Path(self.pasta.name) / "inventario.db"
        RepositorioAtivosSqlite(self.banco).salvar(ativos_exemplo())
        self.repo = RepositorioDependenciasSqlite(self.banco)

    def tearDown(self):
        self.pasta.cleanup()

    def test_ida_e_volta_mantem_a_ordem(self):
        self.repo.salvar([Dependencia(2, 1, 0.4), Dependencia(3, 2, 0.3)])
        self.assertEqual([d.para_dict() for d in self.repo.listar()],
                         [{"ativo_origem_id": 2, "ativo_destino_id": 1, "peso": 0.4},
                          {"ativo_origem_id": 3, "ativo_destino_id": 2, "peso": 0.3}])

    def test_chave_estrangeira_recusa_ativo_inexistente(self):
        with self.assertRaises(ErroDados):
            self.repo.salvar([Dependencia(2, 99, 0.4)])

    def test_gerenciador_remove_ativo_com_dependencias(self):
        ga = GerenciadorAtivos(self.banco, repositorio=RepositorioAtivosSqlite(self.banco))
        gd = GerenciadorDependencias(self.banco, repositorio=self.repo)
        gd.cadastrar_dependencia(Dependencia(2, 1, 0.4), ga.listar_ativos())
        self.assertEqual(gd.remover_ativo_com_dependencias(ga, 1), 1)
        self.assertEqual(gd.listar_dependencias(), [])
        self.assertIsNone(ga.buscar_ativo_por_id(1))


class TesteFabrica(unittest.TestCase):
    def test_modo_padrao_e_json(self):
        os.environ.pop("PERSISTENCIA", None)
        self.assertEqual(modo_do_ambiente(), "json")

    def test_modo_invalido_e_recusado(self):
        os.environ["PERSISTENCIA"] = "mongo"
        try:
            with self.assertRaises(ValueError):
                modo_do_ambiente()
        finally:
            os.environ.pop("PERSISTENCIA")
        with self.assertRaises(ValueError):
            criar_repositorios(".", "mongo")


class TesteRelatorios(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.banco = Path(self.pasta.name) / "inventario.db"
        RepositorioAtivosSqlite(self.banco).salvar(ativos_exemplo())
        RepositorioDependenciasSqlite(self.banco).salvar([Dependencia(2, 1, 0.4)])

    def tearDown(self):
        self.pasta.cleanup()

    def q(self, nome, params=()):
        return relatorios_sql.consultar(self.banco, nome, params)[1]

    def test_inner_join(self):
        self.assertEqual(len(self.q("vulnerabilidades_x_ativos")), 4)

    def test_left_join_sem_correspondencia(self):
        self.assertEqual(self.q("ativos_sem_vulnerabilidade"), [(3, "Notebook C")])

    def test_autojuncao(self):
        self.assertEqual(self.q("dependencias"), [("Servidor B", "Notebook A", 0.4)])

    def test_soma_ignora_corrigida_e_zera_quem_nao_tem(self):
        soma = {i: s for i, _, _, _, s in self.q("soma_cvss_por_ativo")}
        self.assertEqual(soma, {1: 10.0, 2: 18.8, 3: 0})

    def test_soma_sql_bate_com_o_modelo_em_python(self):
        esperado = relatorios_sql.risco_proprio_em_python(self.banco)
        fatores = {a.id: a.obter_fator_exposicao() for a in RepositorioAtivosSqlite(self.banco).listar()}
        for i, _, _, _, soma in self.q("soma_cvss_por_ativo"):
            self.assertAlmostEqual(soma * fatores[i], esperado[i])

    def test_having_e_top_parametrizados(self):
        self.assertEqual([n for n, _ in self.q("acima_do_limite", (10,))], ["Servidor B"])
        self.assertEqual(len(self.q("top_ativos", (2,))), 2)

    def test_parametro_hostil_so_e_texto(self):
        self.assertEqual(self.q("vulnerabilidades_do_ativo", ("1 OR 1=1",)), [])

    def test_faixas_com_case(self):
        faixas = dict(self.q("faixas_cvss"))
        self.assertEqual(faixas, {"Crítica": 1, "Alta": 1, "Média": 1})

    def test_relatorio_completo_confere(self):
        texto = relatorios_sql.gerar_relatorio(self.banco)
        self.assertIn("ok", texto)
        self.assertNotIn("DIFERENTE", texto)


class TesteApiComSqlite(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.app = criar_app(self.pasta.name, persistencia="sqlite")
        self.http = self.app.test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def test_cria_ativo_e_grava_no_banco_sem_gerar_json(self):
        r = self.http.post("/api/ativos", json={"id": 1, "tipo": 1, "nome": "Notebook API", "responsavel": "Ana",
                                                 "setor": "TI", "memoria_ram": "16GB"})
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        self.assertTrue((Path(self.pasta.name) / "inventario.db").exists())
        self.assertFalse((Path(self.pasta.name) / "ativos.json").exists())
        self.assertEqual(len(self.http.get("/api/ativos").get_json()), 1)

    def test_persiste_entre_instancias(self):
        self.http.post("/api/ativos", json={"id": 1, "tipo": 1, "nome": "Notebook API", "responsavel": "Ana",
                                             "setor": "TI", "memoria_ram": "16GB"})
        outra = criar_app(self.pasta.name, persistencia="sqlite").test_client()
        self.assertEqual(outra.get("/api/ativos").get_json()[0]["nome"], "Notebook API")


class TesteMigracao(unittest.TestCase):
    def test_migra_json_para_sqlite_sem_tocar_nos_json(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as p:
            pasta = Path(p)
            (pasta / "ativos.json").write_text(json.dumps([a.para_dict() for a in ativos_exemplo()]), encoding="utf-8")
            (pasta / "dependencias.json").write_text(json.dumps([{"ativo_origem_id": 2, "ativo_destino_id": 1, "peso": 0.4}]))
            antes = (pasta / "ativos.json").read_bytes()
            cmd = [sys.executable, str(RAIZ / "scripts" / "migrar_json_para_sqlite.py"), "--pasta", p]
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((pasta / "ativos.json").read_bytes(), antes)
            ativos, deps = criar_repositorios(pasta, "sqlite")
            self.assertEqual(len(ativos.listar()), 3)
            self.assertEqual(len(deps.listar()), 1)
            r2 = subprocess.run(cmd, capture_output=True, text=True)      # segunda vez: não sobrescreve sem --forcar
            self.assertNotEqual(r2.returncode, 0)


if __name__ == "__main__":
    unittest.main()
