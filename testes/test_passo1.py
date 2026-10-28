import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from src.modelos.enums import Severidade, StatusVulnerabilidade
from src.modelos.notebook import Notebook
from src.modelos.vulnerabilidades import Vulnerabilidade, normalizar_cve
from src.persistencia.persistencia import Persistencia
from src.servicos.analise_risco import construir_matriz_incidencia
from src.servicos.cliente_nvd import (
    CVENaoEncontrado, ClienteNVD, NVDIndisponivel,
)


def resposta_nvd(metricas):
    return {"vulnerabilities": [{"cve": {
        "id": "CVE-2021-44228",
        "descriptions": [{"lang": "es", "value": "hola"},
                         {"lang": "en", "value": "Log4j RCE"}],
        "metrics": metricas,
    }}]}


class TesteCliente(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name) / "cache.json"
        patcher = mock.patch("src.servicos.cliente_nvd.time.sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_prefere_v31_primary(self):
        metricas = {
            "cvssMetricV2": [{"cvssData": {"baseScore": 9.3}}],
            "cvssMetricV31": [
                {"type": "Secondary", "cvssData": {"baseScore": 9.0}},
                {"type": "Primary", "cvssData": {"baseScore": 10.0}},
            ],
        }
        c = ClienteNVD(self.cache, requisicao=lambda *a: resposta_nvd(metricas))
        d = c.consultar("CVE-2021-44228")
        self.assertEqual(d.nota_cvss, 10.0)
        self.assertEqual(d.versao_cvss, "cvssMetricV31")
        self.assertEqual(d.descricao, "Log4j RCE")

    def test_cai_para_v2_quando_nao_ha_v3(self):
        metricas = {"cvssMetricV2": [{"cvssData": {"baseScore": 5.0}}]}
        c = ClienteNVD(self.cache, requisicao=lambda *a: resposta_nvd(metricas))
        self.assertEqual(c.consultar("CVE-2010-0001").nota_cvss, 5.0)

    def test_sem_nota_levanta_erro(self):
        c = ClienteNVD(self.cache, requisicao=lambda *a: resposta_nvd({}))
        with self.assertRaises(CVENaoEncontrado):
            c.consultar("CVE-2099-0001")

    def test_cve_inexistente(self):
        c = ClienteNVD(self.cache, requisicao=lambda *a: {"vulnerabilities": []})
        with self.assertRaises(CVENaoEncontrado):
            c.consultar("CVE-2099-9999")

    def test_cache_evita_segunda_chamada(self):
        chamadas = []
        def falsa(*a):
            chamadas.append(1)
            return resposta_nvd({"cvssMetricV31": [{"cvssData": {"baseScore": 7.5}}]})
        c = ClienteNVD(self.cache, requisicao=falsa)
        c.consultar("CVE-2021-44228")
        c.consultar("CVE-2021-44228")
        self.assertEqual(len(chamadas), 1)
        # e sobrevive a reiniciar o programa (novo cliente lendo o arquivo)
        c2 = ClienteNVD(self.cache, requisicao=falsa)
        c2.consultar("CVE-2021-44228")
        self.assertEqual(len(chamadas), 1)

    def test_http_429_vira_nvd_indisponivel(self):
        def falsa(*a):
            raise urllib.error.HTTPError("u", 429, "x", {}, io.BytesIO())
        c = ClienteNVD(self.cache, requisicao=falsa)
        with self.assertRaises(NVDIndisponivel):
            c.consultar("CVE-2021-44228")

    def test_sem_rede_vira_nvd_indisponivel(self):
        def falsa(*a):
            raise urllib.error.URLError("sem rede")
        c = ClienteNVD(self.cache, requisicao=falsa)
        with self.assertRaises(NVDIndisponivel):
            c.consultar("CVE-2021-44228")


class TesteVulnerabilidade(unittest.TestCase):
    def test_normalizar_cve(self):
        self.assertEqual(normalizar_cve(" cve-2021-44228 "), "CVE-2021-44228")
        self.assertIsNone(normalizar_cve("CVE-21-1"))
        self.assertIsNone(normalizar_cve("senha fraca"))

    def test_faixas_de_severidade(self):
        casos = {0.0: Severidade.BAIXA, 3.9: Severidade.BAIXA, 4.0: Severidade.MEDIA,
                 6.9: Severidade.MEDIA, 7.0: Severidade.ALTA, 8.9: Severidade.ALTA,
                 9.0: Severidade.CRITICA, 10.0: Severidade.CRITICA}
        for nota, esperado in casos.items():
            self.assertEqual(Severidade.a_partir_da_nota(nota), esperado)

    def test_nota_invalida(self):
        with self.assertRaises(ValueError):
            Vulnerabilidade("x", "y", 11, "Aberta")

    def test_status_invalido(self):
        with self.assertRaises(ValueError):
            Vulnerabilidade("x", "y", 5, "qualquer coisa")


# Amostra no formato ANTIGO (sem "id" nem "fonte" nas vulnerabilidades).
# Fica embutida aqui para o teste NÃO depender do ativos.json real do projeto,
# que o usuário altera ao cadastrar ativos de verdade.
DADOS_ANTIGOS = [
    {
        "id": 1, "tipo": "Notebook", "nome": "Notebook A",
        "responsavel": "João", "setor": "TI",
        "vulnerabilidades": [
            {"descricao": "Windows desatualizado", "categoria": "Atualização",
             "severidade": 8.5, "status": "Aberta"},
            {"descricao": "Senha fraca", "categoria": "Segurança",
             "severidade": 7.0, "status": "Em tratamento"},
        ],
        "memoria_ram": "16GB",
    },
    {
        "id": 2, "tipo": "Roteador", "nome": "Roteador B",
        "responsavel": "Maria", "setor": "Redes",
        "vulnerabilidades": [
            {"descricao": "Firmware desatualizado", "categoria": "Atualização",
             "severidade": 6.0, "status": "Aberta"},
        ],
        "modelo": "Modelo X",
    },
    {
        "id": 3, "tipo": "Servidor", "nome": "Servidor C",
        "responsavel": "Carlos", "setor": "Infraestrutura",
        "vulnerabilidades": [],
        "processador": "Intel Xeon",
    },
]


class TesteDadosAntigos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.arquivo = Path(self.tmp.name) / "antigo.json"
        self.arquivo.write_text(
            json.dumps(DADOS_ANTIGOS, ensure_ascii=False), encoding="utf-8"
        )

    def test_formato_antigo_carrega(self):
        ativos = Persistencia().carregar_dados(self.arquivo)
        self.assertEqual(len(ativos), 3)
        v = ativos[0].vulnerabilidades[0]
        self.assertTrue(v.id.startswith("LOCAL-"))
        self.assertEqual(v.status, StatusVulnerabilidade.ABERTA)
        self.assertEqual(v.fonte, "manual")

    def test_id_local_e_estavel_entre_leituras(self):
        a = Persistencia().carregar_dados(self.arquivo)[0].vulnerabilidades[0].id
        b = Persistencia().carregar_dados(self.arquivo)[0].vulnerabilidades[0].id
        self.assertEqual(a, b)

    def test_ida_e_volta_no_json(self):
        ativos = Persistencia().carregar_dados(self.arquivo)
        saida = Path(self.tmp.name) / "novo.json"
        Persistencia().salvar_dados(ativos, saida)
        de_novo = Persistencia().carregar_dados(saida)
        self.assertEqual([a.para_dict() for a in ativos],
                         [a.para_dict() for a in de_novo])


class TesteMatrizPorId(unittest.TestCase):
    def test_mudar_status_nao_cria_coluna_nova(self):
        v1 = Vulnerabilidade("Log4Shell", "RCE", 10.0, "Aberta", id="CVE-2021-44228", fonte="NVD")
        v2 = Vulnerabilidade("Log4Shell", "RCE", 10.0, "Em tratamento", id="CVE-2021-44228", fonte="NVD")
        a = Notebook(1, "A", "x", "TI", [v1], "8GB")
        b = Notebook(2, "B", "y", "TI", [v2], "8GB")
        M, v, rotulos = construir_matriz_incidencia([a, b])
        self.assertEqual(M, [[1], [1]])   # uma única coluna, afetando os dois
        self.assertEqual(v, [10.0])


if __name__ == "__main__":
    unittest.main()
