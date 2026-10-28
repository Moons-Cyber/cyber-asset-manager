import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import main
from src.api.aplicacao import _limpar, criar_app
from src.modelos.enums import TipoAtivo
from src.modelos.registro_tipos import CLASSE_POR_TIPO
from src.persistencia.persistencia import Persistencia
from src.servicos.cliente_nvd import CVENaoEncontrado, DadosCVE, NVDIndisponivel

LOG4J = "Apache Log4j2 JNDI features do not protect against attacker controlled LDAP endpoints. More text here."


class NVDFalso:
    def __init__(self, modo="ok"):
        self.modo = modo
        self.chamadas = 0

    def consultar(self, cve_id):
        self.chamadas += 1
        if self.modo == "fora":
            raise NVDIndisponivel("sem rede")
        if self.modo == "inexistente":
            raise CVENaoEncontrado(f"{cve_id} não foi encontrado no NVD.")
        return DadosCVE(cve_id, LOG4J, 10.0, "cvssMetricV31")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.nvd = NVDFalso()
        self.app = criar_app(self.tmp.name, cliente_nvd=self.nvd)
        self.c = self.app.test_client()

    def ativo(self, id_=1, tipo=1, **extra):
        corpo = {"id": id_, "tipo": tipo, "nome": f"Ativo {id_}", "responsavel": "Ana",
                 "setor": "TI", "memoria_ram": "8GB"}
        corpo.update(extra)
        return self.c.post("/api/ativos", json=corpo)

    def vuln(self, id_=1, **corpo):
        base = {"categoria": "RCE", "status": "Aberta"}
        base.update(corpo)
        return self.c.post(f"/api/ativos/{id_}/vulnerabilidades", json=base)


class TesteGeral(Base):
    def test_saude(self):
        r = self.c.get("/api/saude")
        self.assertEqual((r.status_code, r.json), (200, {"status": "ok", "ativos": 0}))

    def test_saude_devolve_503_se_dados_corrompidos(self):
        (Path(self.tmp.name) / "ativos.json").write_text("{ quebrado", encoding="utf-8")
        with self.assertLogs(self.app.logger, level="ERROR"):
            r = self.c.get("/api/saude")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json["status"], "erro")
        self.assertNotIn(self.tmp.name, r.get_data(as_text=True))   # sem caminho do servidor

    def test_tipos_listam_os_quatro(self):
        r = self.c.get("/api/tipos").json
        self.assertEqual([t["codigo"] for t in r], [1, 2, 3, 4])
        self.assertEqual(r[3]["nome"], "Banco de dados")
        self.assertEqual(r[3]["campo"], "sgbd")

    def test_status_validos(self):
        self.assertIn("Corrigida", self.c.get("/api/status").json)

    def test_rota_inexistente_e_metodo_errado_respondem_json(self):
        r = self.c.get("/api/nada")
        self.assertEqual((r.status_code, "erro" in r.json), (404, True))
        r = self.c.put("/api/ativos")
        self.assertEqual((r.status_code, "erro" in r.json), (405, True))

    def test_resposta_da_api_nao_vai_para_cache(self):
        self.assertEqual(self.c.get("/api/saude").headers["Cache-Control"], "no-store")

    def test_erro_inesperado_nao_vaza_detalhes(self):
        with mock.patch("src.api.aplicacao.GerenciadorAtivos.listar_ativos",
                        side_effect=RuntimeError("segredo interno")), \
             self.assertLogs(self.app.logger, level="ERROR") as registro:
            r = self.c.get("/api/ativos")
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("segredo", r.get_data(as_text=True))
        self.assertIn("segredo interno", "\n".join(registro.output))   # o detalhe vai para o log

    def test_limpar_troca_infinito_por_none(self):
        self.assertEqual(_limpar({"a": float("inf"), "b": [float("nan"), 1.5]}),
                         {"a": None, "b": [None, 1.5]})

    def test_registro_de_tipos_bate_com_o_menu_e_a_persistencia(self):
        self.assertEqual(set(CLASSE_POR_TIPO), set(TipoAtivo))
        for tipo, classe in CLASSE_POR_TIPO.items():
            self.assertIs(main.TIPOS_DISPONIVEIS[tipo][0], classe)
            self.assertIs(Persistencia.TIPOS[classe.__name__], classe)


class TesteAtivos(Base):
    def test_cria_cada_tipo_e_devolve_201_com_location(self):
        campos = {
            1: ("memoria_ram", "16GB"),
            2: ("processador", "Intel Xeon"),
            3: ("modelo", "TP-Link Archer C6"),
            4: ("sgbd", "PostgreSQL 16"),
        }
        for codigo, (campo, valor) in campos.items():
            r = self.c.post("/api/ativos", json={
                "id": codigo, "tipo": codigo, "nome": f"N{codigo}",
                "responsavel": "Ana", "setor": "TI", campo: valor})
            self.assertEqual(r.status_code, 201, r.json)
            self.assertEqual(r.json["valor_campo"], valor)
            self.assertEqual(r.json["campo_especifico"], campo)
            self.assertTrue(r.headers["Location"].endswith(f"/api/ativos/{codigo}"))
        self.assertEqual(len(self.c.get("/api/ativos").json), 4)

    def test_entradas_invalidas_dao_400(self):
        casos = [
            {"id": "1"}, {"id": True}, {"id": 0}, {"id": -3}, {"id": 1.5},
            {"tipo": 9}, {"tipo": "1"}, {"nome": ""}, {"nome": "   "},
            {"nome": 123}, {"responsavel": None}, {"memoria_ram": ""},
        ]
        for troca in casos:
            with self.subTest(troca=troca):
                self.assertEqual(self.ativo(**troca).status_code, 400)

    def test_campo_obrigatorio_ausente(self):
        r = self.c.post("/api/ativos", json={"id": 1, "tipo": 1, "nome": "x"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("responsavel", r.json["erro"])

    def test_corpo_que_nao_e_objeto_json(self):
        for dado in ("texto solto", "[1,2]", "null"):
            r = self.c.post("/api/ativos", data=dado, content_type="application/json")
            self.assertEqual(r.status_code, 400)
        self.assertEqual(self.c.post("/api/ativos", data="{ruim").status_code, 400)

    def test_id_duplicado_da_409(self):
        self.ativo(1)
        self.assertEqual(self.ativo(1).status_code, 409)

    def test_obter_e_404(self):
        self.ativo(1)
        self.assertEqual(self.c.get("/api/ativos/1").json["nome"], "Ativo 1")
        self.assertEqual(self.c.get("/api/ativos/99").status_code, 404)

    def test_busca_por_nome_e_tipo(self):
        self.ativo(1, nome="Notebook Financeiro")
        self.ativo(2, nome="notebook rh")
        self.c.post("/api/ativos", json={"id": 3, "tipo": 4, "nome": "DB",
                                         "responsavel": "x", "setor": "y", "sgbd": "PG"})
        self.assertEqual(len(self.c.get("/api/ativos?q=NOTEBOOK").json), 2)
        self.assertEqual([a["id"] for a in self.c.get("/api/ativos?tipo=4").json], [3])
        self.assertEqual(self.c.get("/api/ativos?tipo=abc").status_code, 400)
        self.assertEqual(self.c.get("/api/ativos?tipo=99").status_code, 400)

    def test_patch_altera_campos_permitidos_e_persiste(self):
        self.ativo(1)
        r = self.c.patch("/api/ativos/1", json={"nome": "Novo", "memoria_ram": "32GB"})
        self.assertEqual((r.status_code, r.json["nome"], r.json["valor_campo"]), (200, "Novo", "32GB"))
        reaberto = criar_app(self.tmp.name).test_client()
        self.assertEqual(reaberto.get("/api/ativos/1").json["nome"], "Novo")

    def test_patch_recusa_id_campo_de_outro_tipo_vazio_e_inexistente(self):
        self.ativo(1)
        for corpo in ({"id": 5}, {"sgbd": "x"}, {"tipo": 2}, {"vulnerabilidades": []}, {}):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.c.patch("/api/ativos/1", json=corpo).status_code, 400)
        self.assertEqual(self.c.patch("/api/ativos/1", json={"nome": ""}).status_code, 400)
        self.assertEqual(self.c.patch("/api/ativos/99", json={"nome": "x"}).status_code, 404)

    def test_delete_remove_o_ativo_e_as_dependencias(self):
        for i in (1, 2, 3):
            self.ativo(i)
        self.c.post("/api/dependencias", json={"origem": 1, "destino": 2, "peso": 0.3})
        self.c.post("/api/dependencias", json={"origem": 2, "destino": 3, "peso": 0.3})
        r = self.c.delete("/api/ativos/2")
        self.assertEqual((r.status_code, r.json["dependencias_removidas"]), (200, 2))
        self.assertEqual(self.c.get("/api/dependencias").json, [])
        self.assertEqual(self.c.get("/api/risco").status_code, 200)
        self.assertEqual(self.c.delete("/api/ativos/2").status_code, 404)

    def test_criar_com_vulnerabilidades_manuais(self):
        r = self.ativo(1, vulnerabilidades=[
            {"descricao": "Senha fraca", "categoria": "Acesso", "severidade": 7.5}])
        self.assertEqual(r.status_code, 201)
        v = r.json["vulnerabilidades"][0]
        self.assertEqual((v["classificacao"], v["status"], v["afeta_risco"]), ("Alta", "Aberta", True))
        self.assertTrue(v["id"].startswith("LOCAL-"))

    def test_criar_com_cve_sem_severidade_nao_consulta_o_nvd(self):
        r = self.ativo(1, vulnerabilidades=[{"cve": "CVE-2021-44228", "categoria": "RCE"}])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.nvd.chamadas, 0)

    def test_criar_com_vulnerabilidades_repetidas_ou_malformadas(self):
        v = {"descricao": "x", "categoria": "y", "severidade": 5}
        self.assertEqual(self.ativo(1, vulnerabilidades=[v, v]).status_code, 400)
        self.assertEqual(self.ativo(2, vulnerabilidades="nao-lista").status_code, 400)
        self.assertEqual(self.ativo(3, vulnerabilidades=["texto"]).status_code, 400)
        self.assertEqual(self.c.get("/api/ativos").json, [])   # nada foi gravado pela metade


class TesteVulnerabilidades(Base):
    def setUp(self):
        super().setUp()
        self.ativo(1)

    def test_manual(self):
        r = self.vuln(descricao="Senha fraca", severidade=7)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json["fonte"], "manual")
        self.assertEqual(len(self.c.get("/api/ativos/1/vulnerabilidades").json), 1)

    def test_por_cve_busca_a_nota_e_resume_a_descricao(self):
        r = self.vuln(cve="cve-2021-44228")
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual((r.json["id"], r.json["severidade"], r.json["fonte"]),
                         ("CVE-2021-44228", 10.0, "NVD"))
        self.assertLess(len(r.json["descricao"]), 110)
        self.assertEqual(r.json["classificacao"], "Crítica")
        self.assertNotIn("descricao_original", r.json)

    def test_original_do_nvd_fica_guardado_no_arquivo(self):
        self.vuln(cve="CVE-2021-44228")
        gravado = json.loads((Path(self.tmp.name) / "ativos.json").read_text(encoding="utf-8"))
        self.assertEqual(gravado[0]["vulnerabilidades"][0]["descricao_original"], LOG4J)

    def test_descricao_do_usuario_tem_prioridade(self):
        r = self.vuln(cve="CVE-2021-44228", descricao="Log4Shell no servidor")
        self.assertEqual(r.json["descricao"], "Log4Shell no servidor")

    def test_nvd_fora_do_ar_da_503_com_dica_e_manual_funciona(self):
        self.nvd.modo = "fora"
        r = self.vuln(cve="CVE-2021-44228")
        self.assertEqual(r.status_code, 503)
        self.assertIn("severidade", r.json["dica"])
        r = self.vuln(cve="CVE-2021-44228", severidade=9.8, descricao="Log4Shell")
        self.assertEqual((r.status_code, r.json["id"], r.json["fonte"]), (201, "CVE-2021-44228", "manual"))

    def test_cve_inexistente_da_404(self):
        self.nvd.modo = "inexistente"
        self.assertEqual(self.vuln(cve="CVE-2099-0001").status_code, 404)

    def test_entradas_invalidas(self):
        casos = [
            {"cve": "abc", "severidade": 5, "descricao": "x"},
            {"cve": 123, "severidade": 5, "descricao": "x"},
            {"descricao": "x"},                                # sem severidade nem CVE
            {"descricao": "x", "severidade": 11},
            {"descricao": "x", "severidade": -1},
            {"descricao": "x", "severidade": "alta"},
            {"descricao": "x", "severidade": True},
            {"descricao": "x", "severidade": 5, "status": "Inventado"},
            {"severidade": 5},                                 # sem descrição
        ]
        for corpo in casos:
            with self.subTest(corpo=corpo):
                self.assertEqual(self.vuln(**corpo).status_code, 400)

    def test_categoria_obrigatoria(self):
        r = self.c.post("/api/ativos/1/vulnerabilidades",
                        json={"descricao": "x", "severidade": 5})
        self.assertEqual(r.status_code, 400)

    def test_duplicada_da_409_e_ativo_inexistente_da_404_sem_consultar_nvd(self):
        self.vuln(cve="CVE-2021-44228")
        self.assertEqual(self.vuln(cve="CVE-2021-44228").status_code, 409)
        antes = self.nvd.chamadas
        self.assertEqual(self.vuln(id_=99, cve="CVE-2021-44228").status_code, 404)
        self.assertEqual(self.nvd.chamadas, antes)

    def test_atualizar_status_e_erros(self):
        self.vuln(cve="CVE-2021-44228")
        r = self.c.patch("/api/ativos/1/vulnerabilidades/CVE-2021-44228", json={"status": "Corrigida"})
        self.assertEqual((r.status_code, r.json["status"], r.json["afeta_risco"]), (200, "Corrigida", False))
        patch = lambda url, corpo: self.c.patch(url, json=corpo).status_code
        self.assertEqual(patch("/api/ativos/1/vulnerabilidades/CVE-2021-44228", {"status": "xx"}), 400)
        self.assertEqual(patch("/api/ativos/1/vulnerabilidades/CVE-2021-44228", {"severidade": 1}), 400)
        self.assertEqual(patch("/api/ativos/1/vulnerabilidades/CVE-2021-44228", {}), 400)
        self.assertEqual(patch("/api/ativos/1/vulnerabilidades/CVE-1999-0001", {"status": "Aberta"}), 404)
        self.assertEqual(patch("/api/ativos/99/vulnerabilidades/CVE-2021-44228", {"status": "Aberta"}), 404)

    def test_previa_de_cve(self):
        r = self.c.get("/api/cve/cve-2021-44228")
        self.assertEqual((r.status_code, r.json["severidade"]), (200, 10.0))
        self.assertEqual(r.json["descricao_original"], LOG4J)
        self.assertEqual(self.c.get("/api/cve/abc").status_code, 400)
        self.nvd.modo = "fora"
        self.assertEqual(self.c.get("/api/cve/CVE-2021-44228").status_code, 503)


class TesteDependencias(Base):
    def setUp(self):
        super().setUp()
        for i in (1, 2, 3):
            self.ativo(i)

    def dep(self, o, d, p):
        return self.c.post("/api/dependencias", json={"origem": o, "destino": d, "peso": p})

    def test_cria_lista_com_nomes_e_remove(self):
        self.assertEqual(self.dep(1, 2, 0.5).status_code, 201)
        lista = self.c.get("/api/dependencias").json
        self.assertEqual((lista[0]["origem_nome"], lista[0]["destino_nome"]), ("Ativo 1", "Ativo 2"))
        self.assertEqual(self.c.delete("/api/dependencias/1/2").status_code, 200)
        self.assertEqual(self.c.delete("/api/dependencias/1/2").status_code, 404)

    def test_regras_de_validacao(self):
        casos = [(1, 1, 0.5), (1, 99, 0.5), (1, 2, 1.0), (1, 2, -0.1), (1, 2, "meio"), (1, 2, True)]
        for o, d, p in casos:
            with self.subTest(o=o, d=d, p=p):
                self.assertEqual(self.dep(o, d, p).status_code, 400)

    def test_duplicada_e_soma_maior_ou_igual_a_um(self):
        self.dep(1, 3, 0.6)
        self.assertEqual(self.dep(1, 3, 0.1).status_code, 400)
        self.assertEqual(self.dep(2, 3, 0.4).status_code, 400)
        self.assertEqual(self.dep(2, 3, 0.3).status_code, 201)


class TesteRisco(Base):
    def test_sem_ativos(self):
        r = self.c.get("/api/risco")
        self.assertEqual((r.status_code, r.json), (200, {"resultados": [], "diagnostico": None}))

    def test_cenario_de_tres_ativos_em_ciclo_resolvido_a_mao(self):
        for i, nota in ((1, 10), (2, 5), (3, None)):
            extra = {"vulnerabilidades": [{"descricao": "d", "categoria": "c", "severidade": nota}]} if nota else {}
            self.ativo(i, **extra)
        for o, d, p in ((1, 2, 0.5), (2, 3, 0.4), (3, 1, 0.2)):
            self.assertEqual(self.c.post("/api/dependencias", json={"origem": o, "destino": d, "peso": p}).status_code, 201)
        r = self.c.get("/api/risco").json
        efetivos = [x["risco_efetivo"] for x in r["resultados"]]
        for obtido, esperado in zip(efetivos, (130 / 12, 125 / 12, 50 / 12)):
            self.assertAlmostEqual(obtido, esperado, places=9)
        d = r["diagnostico"]
        self.assertTrue(d["invertivel"])
        self.assertFalse(d["fragil"])
        self.assertNotIn("frágil", d)

    def test_corrigir_pela_api_reduz_o_risco(self):
        self.ativo(1)
        self.vuln(cve="CVE-2021-44228")
        antes = self.c.get("/api/risco").json["resultados"][0]["risco_efetivo"]
        self.c.patch("/api/ativos/1/vulnerabilidades/CVE-2021-44228", json={"status": "Corrigida"})
        depois = self.c.get("/api/risco").json["resultados"][0]["risco_efetivo"]
        self.assertEqual((antes, depois), (10.0, 0.0))

    def test_dados_inconsistentes_viram_422(self):
        self.ativo(1)
        self.ativo(2)
        (Path(self.tmp.name) / "dependencias.json").write_text(
            json.dumps([{"ativo_origem_id": 1, "ativo_destino_id": 99, "peso": 0.5}]), encoding="utf-8")
        self.assertEqual(self.c.get("/api/risco").status_code, 422)


class TesteConcorrenciaEPersistencia(Base):
    def test_cadastros_simultaneos_nao_perdem_nem_corrompem_nada(self):
        resultados = []

        def cadastrar(i):
            cliente = self.app.test_client()
            r = cliente.post("/api/ativos", json={"id": i, "tipo": 1, "nome": f"A{i}",
                             "responsavel": "x", "setor": "y", "memoria_ram": "8GB"})
            resultados.append(r.status_code)

        fios = [threading.Thread(target=cadastrar, args=(i,)) for i in range(1, 41)]
        [f.start() for f in fios]
        [f.join() for f in fios]

        self.assertEqual(resultados.count(201), 40)
        self.assertEqual(len(self.c.get("/api/ativos").json), 40)
        em_disco = Persistencia().carregar_dados(Path(self.tmp.name) / "ativos.json")
        self.assertEqual(sorted(a.id for a in em_disco), list(range(1, 41)))

    def test_ids_iguais_simultaneos_so_um_vence(self):
        resultados = []

        def cadastrar():
            r = self.app.test_client().post("/api/ativos", json={"id": 7, "tipo": 1, "nome": "A",
                                            "responsavel": "x", "setor": "y", "memoria_ram": "8GB"})
            resultados.append(r.status_code)

        fios = [threading.Thread(target=cadastrar) for _ in range(15)]
        [f.start() for f in fios]
        [f.join() for f in fios]
        self.assertEqual((resultados.count(201), resultados.count(409)), (1, 14))

    def test_dados_sobrevivem_a_reiniciar_o_servico(self):
        self.ativo(1)
        self.vuln(descricao="Senha fraca", severidade=7)
        reiniciado = criar_app(self.tmp.name, cliente_nvd=self.nvd).test_client()
        self.assertEqual(len(reiniciado.get("/api/ativos/1/vulnerabilidades").json), 1)

    def test_pasta_de_dados_inexistente_e_criada(self):
        nova = Path(self.tmp.name) / "volume" / "dados"
        criar_app(nova)
        self.assertTrue(nova.is_dir())



class TesteDadosCorrompidos(Base):
    """Arquivo ruim é falha do SERVIDOR (503), nunca do cliente (400)."""

    def escrever(self, nome, conteudo):
        (Path(self.tmp.name) / nome).write_text(conteudo, encoding="utf-8")

    def requisitar(self, metodo, url, **kw):
        with self.assertLogs(self.app.logger, level="ERROR"):
            return getattr(self.c, metodo)(url, **kw)

    def test_ativos_corrompidos_dao_503_em_leitura_escrita_e_risco(self):
        self.escrever("ativos.json", "{ quebrado")
        corpo = {"id": 1, "tipo": 1, "nome": "x", "responsavel": "y", "setor": "z", "memoria_ram": "8GB"}
        for metodo, url, kw in (("get", "/api/ativos", {}), ("get", "/api/ativos/1", {}),
                                ("get", "/api/risco", {}), ("post", "/api/ativos", {"json": corpo})):
            with self.subTest(metodo=metodo, url=url):
                r = self.requisitar(metodo, url, **kw)
                self.assertEqual(r.status_code, 503)
                self.assertNotIn(self.tmp.name, r.get_data(as_text=True))   # não vaza caminho

    def test_cada_tipo_de_corrupcao_vira_503(self):
        ruim = {"id": 1, "tipo": "Notebook", "nome": "n", "responsavel": "r", "setor": "s",
                "vulnerabilidades": [], "memoria_ram": "8GB"}
        casos = {
            "id repetido": json.dumps([ruim, ruim]),
            "tipo desconhecido": json.dumps([{**ruim, "tipo": "Impressora"}]),
            "campo ausente": json.dumps([{k: v for k, v in ruim.items() if k != "responsavel"}]),
            "não é lista": json.dumps({"a": 1}),
        }
        for nome, conteudo in casos.items():
            with self.subTest(caso=nome):
                self.escrever("ativos.json", conteudo)
                criar = criar_app(self.tmp.name, cliente_nvd=self.nvd).test_client()
                with self.assertLogs("src.api.aplicacao", level="ERROR"):
                    r = criar.get("/api/ativos")
                self.assertEqual(r.status_code, 503)

    def test_dependencias_corrompidas_dao_503(self):
        for conteudo in ("{ quebrado", json.dumps([{"ativo_origem_id": 1, "ativo_destino_id": 2, "peso": 1.5}]),
                         json.dumps([{"formato": "errado"}])):
            with self.subTest(conteudo=conteudo[:30]):
                self.escrever("dependencias.json", conteudo)
                app = criar_app(self.tmp.name, cliente_nvd=self.nvd)
                with self.assertLogs(app.logger, level="ERROR"):
                    r = app.test_client().get("/api/dependencias")
                self.assertEqual(r.status_code, 503)

    def test_servico_se_recupera_quando_o_arquivo_e_corrigido(self):
        self.escrever("ativos.json", "{ quebrado")
        self.assertEqual(self.requisitar("get", "/api/ativos").status_code, 503)
        self.escrever("ativos.json", "[]")
        self.assertEqual(self.c.get("/api/ativos").status_code, 200)
        self.assertEqual(self.c.get("/api/saude").status_code, 200)

    def test_entrada_invalida_do_cliente_continua_400(self):
        r = self.ativo(1, id="texto")
        self.assertEqual(r.status_code, 400)

    def test_erro_de_dados_continua_sendo_valueerror_para_o_menu(self):
        from src.persistencia.erros import ErroDados
        self.assertTrue(issubclass(ErroDados, ValueError))


if __name__ == "__main__":
    unittest.main()
