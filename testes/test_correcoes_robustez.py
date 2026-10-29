"""Regressões: validação na atualização, gravação atômica, cache do NVD,
remoção consistente de ativo e ID de CVE sem diferenciar maiúsculas."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.api.aplicacao import criar_app
from src.modelos.dependencia import Dependencia
from src.modelos.notebook import Notebook
from src.persistencia.persistencia import Persistencia
from src.servicos.cliente_nvd import ClienteNVD, DadosCVE
from src.servicos.gerenciador_ativos import GerenciadorAtivos
from src.servicos.gerenciador_dependencias import GerenciadorDependencias

from testes.test_passo6_api import NVDFalso


def nb(id_):
    return Notebook(id_, f"NB {id_}", "Ana", "TI", [], "8GB")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)


class TesteValidacaoNaAtualizacao(Base):
    def test_gerenciador_rejeita_campo_invalido_sem_alterar_o_ativo(self):
        g = GerenciadorAtivos(self.pasta / "a.json")
        g.cadastrar_ativo(nb(1))
        with self.assertRaises(ValueError):
            g.atualizar_ativo(1, nome="Novo", memoria_ram="abc")
        ativo = g.buscar_ativo_por_id(1)
        self.assertEqual((ativo.nome, ativo.memoria_ram), ("NB 1", "8GB"))

    def test_gerenciador_grava_o_valor_normalizado(self):
        g = GerenciadorAtivos(self.pasta / "a.json")
        g.cadastrar_ativo(nb(1))
        g.atualizar_ativo(1, memoria_ram="16 gb")
        self.assertEqual(GerenciadorAtivos(self.pasta / "a.json")
                         .buscar_ativo_por_id(1).memoria_ram, "16GB")

    def test_api_responde_400_e_o_arquivo_continua_carregando(self):
        c = criar_app(self.pasta, cliente_nvd=NVDFalso()).test_client()
        c.post("/api/ativos", json={"id": 1, "tipo": 1, "nome": "Note N", "responsavel": "R",
                                    "setor": "S", "memoria_ram": "8GB"})
        r = c.patch("/api/ativos/1", json={"memoria_ram": "abc"})
        self.assertEqual(r.status_code, 400)

        reiniciado = criar_app(self.pasta, cliente_nvd=NVDFalso()).test_client()
        self.assertEqual(reiniciado.get("/api/saude").status_code, 200)
        self.assertEqual(reiniciado.get("/api/ativos/1").json["memoria_ram"], "8GB")


class TesteGravacaoAtomica(Base):
    def test_falha_ao_gravar_dependencias_preserva_o_arquivo_antigo(self):
        ativos = [nb(1), nb(2), nb(3)]
        gd = GerenciadorDependencias(self.pasta / "d.json")
        gd.cadastrar_dependencia(Dependencia(1, 2, 0.5), ativos)

        with mock.patch("src.persistencia.persistencia.os.replace",
                        side_effect=OSError("disco cheio")):
            with self.assertRaises(OSError):
                gd.cadastrar_dependencia(Dependencia(1, 3, 0.5), ativos)

        self.assertEqual(len(gd.listar_dependencias()), 1)
        self.assertEqual(list(self.pasta.glob("*.tmp")), [])


class TesteCacheNVD(Base):
    def test_entrada_malformada_e_descartada_e_consulta_o_nvd(self):
        cache = self.pasta / "cache.json"
        cache.write_text(json.dumps({"CVE-2021-44228": {"lixo": 1}}), encoding="utf-8")
        resposta = {"vulnerabilities": [{"cve": {
            "descriptions": [{"lang": "en", "value": "Log4Shell"}],
            "metrics": {"cvssMetricV31": [{"type": "Primary",
                                           "cvssData": {"baseScore": 10.0}}]},
        }}]}
        requisicao = mock.Mock(return_value=resposta)
        cliente = ClienteNVD(cache, chave_api="x", requisicao=requisicao)

        with mock.patch("src.servicos.cliente_nvd.time.sleep"):
            dados = cliente.consultar("CVE-2021-44228")

        self.assertEqual(dados, DadosCVE("CVE-2021-44228", "Log4Shell", 10.0, "cvssMetricV31"))
        requisicao.assert_called_once()
        self.assertEqual(json.loads(cache.read_text(encoding="utf-8"))
                         ["CVE-2021-44228"]["nota_cvss"], 10.0)

    def test_cache_que_nao_e_objeto_e_ignorado(self):
        cache = self.pasta / "cache.json"
        cache.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(ClienteNVD(cache)._cache, {})


class TesteRemocaoConsistente(Base):
    def setUp(self):
        super().setUp()
        self.ga = GerenciadorAtivos(self.pasta / "a.json")
        self.gd = GerenciadorDependencias(self.pasta / "d.json")
        for i in (1, 2, 3):
            self.ga.cadastrar_ativo(nb(i))
        todos = self.ga.listar_ativos()
        self.gd.cadastrar_dependencia(Dependencia(1, 2, 0.5), todos)
        self.gd.cadastrar_dependencia(Dependencia(2, 3, 0.5), todos)

    def test_remove_ativo_e_dependencias(self):
        self.assertEqual(self.gd.remover_ativo_com_dependencias(self.ga, 2), 2)
        self.assertIsNone(self.ga.buscar_ativo_por_id(2))
        self.assertEqual(self.gd.listar_dependencias(), [])

    def test_ativo_inexistente_devolve_none_sem_mexer_em_nada(self):
        self.assertIsNone(self.gd.remover_ativo_com_dependencias(self.ga, 42))
        self.assertEqual(len(self.gd.listar_dependencias()), 2)

    def test_falha_ao_remover_ativo_restaura_as_dependencias(self):
        with mock.patch.object(Persistencia, "salvar_dados", side_effect=OSError("x")):
            with self.assertRaises(OSError):
                self.gd.remover_ativo_com_dependencias(self.ga, 2)

        self.assertIsNotNone(self.ga.buscar_ativo_por_id(2))
        self.assertEqual(len(self.gd.listar_dependencias()), 2)


class TesteIdDeCveNaUrl(Base):
    def test_patch_aceita_cve_em_minusculas(self):
        c = criar_app(self.pasta, cliente_nvd=NVDFalso()).test_client()
        c.post("/api/ativos", json={"id": 1, "tipo": 1, "nome": "Note N", "responsavel": "R",
                                    "setor": "S", "memoria_ram": "8GB"})
        c.post("/api/ativos/1/vulnerabilidades",
               json={"cve": "CVE-2021-44228", "categoria": "RCE"})

        r = c.patch("/api/ativos/1/vulnerabilidades/cve-2021-44228",
                    json={"status": "Corrigida"})

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["status"], "Corrigida")


if __name__ == "__main__":
    unittest.main()
