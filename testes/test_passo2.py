import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
from src.modelos.enums import StatusVulnerabilidade
from src.modelos.notebook import Notebook
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.servicos.cliente_nvd import DadosCVE, NVDIndisponivel
from src.servicos.gerenciador_ativos import GerenciadorAtivos


def vuln(id_="CVE-2021-44228", status="Aberta"):
    return Vulnerabilidade("Log4Shell", "RCE", 10.0, status, id=id_, fonte="NVD")


class TesteGerenciador(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.g = GerenciadorAtivos(Path(self.tmp.name) / "ativos.json")
        self.g.cadastrar_ativo(Notebook(1, "Notebook Financeiro", "Ana", "Fin", [], "8GB"))
        self.g.cadastrar_ativo(Servidor(2, "Servidor Web", "Beto", "TI", [], "Xeon"))
        self.g.cadastrar_ativo(Notebook(3, "notebook rh", "Cris", "RH", [], "16GB"))

    def test_busca_por_nome_ignora_maiusculas_e_acha_varios(self):
        nomes = [a.nome for a in self.g.buscar_ativos_por_nome("NOTEBOOK")]
        self.assertEqual(nomes, ["Notebook Financeiro", "notebook rh"])

    def test_busca_por_nome_vazia_ou_inexistente(self):
        self.assertEqual(self.g.buscar_ativos_por_nome("   "), [])
        self.assertEqual(self.g.buscar_ativos_por_nome("impressora"), [])

    def test_adicionar_preserva_as_existentes_e_persiste(self):
        self.g.adicionar_vulnerabilidade(1, vuln("CVE-2021-44228"))
        self.g.adicionar_vulnerabilidade(1, vuln("CVE-2022-0001"))
        ids = [v.id for v in self.g.buscar_ativo_por_id(1).vulnerabilidades]
        self.assertEqual(ids, ["CVE-2021-44228", "CVE-2022-0001"])

    def test_adicionar_duplicada_e_recusado(self):
        self.g.adicionar_vulnerabilidade(1, vuln())
        with self.assertRaises(ValueError):
            self.g.adicionar_vulnerabilidade(1, vuln())

    def test_mesmo_cve_pode_estar_em_ativos_diferentes(self):
        self.g.adicionar_vulnerabilidade(1, vuln())
        self.g.adicionar_vulnerabilidade(2, vuln())
        self.assertEqual(len(self.g.buscar_ativo_por_id(2).vulnerabilidades), 1)

    def test_adicionar_em_ativo_inexistente(self):
        self.assertIsNone(self.g.adicionar_vulnerabilidade(99, vuln()))

    def test_atualizar_status_mantem_o_id(self):
        self.g.adicionar_vulnerabilidade(1, vuln())
        self.g.atualizar_status_vulnerabilidade(
            1, "CVE-2021-44228", StatusVulnerabilidade.CORRIGIDA)
        v = self.g.buscar_ativo_por_id(1).vulnerabilidades[0]
        self.assertEqual(v.status, StatusVulnerabilidade.CORRIGIDA)
        self.assertEqual(v.id, "CVE-2021-44228")

    def test_atualizar_status_de_vuln_inexistente(self):
        with self.assertRaises(ValueError):
            self.g.atualizar_status_vulnerabilidade(
                1, "CVE-0000-0000", StatusVulnerabilidade.CORRIGIDA)


class NVDFalso:
    def __init__(self, falha=False):
        self.falha = falha

    def consultar(self, cve_id):
        if self.falha:
            raise NVDIndisponivel("sem rede")
        return DadosCVE(cve_id, "Log4j remote code execution", 10.0, "cvssMetricV31")


def digitar(respostas, nvd):
    """Executa ler_vulnerabilidade com respostas pré-programadas."""
    with mock.patch("builtins.input", side_effect=respostas), \
         contextlib.redirect_stdout(io.StringIO()):
        return main.ler_vulnerabilidade(nvd)


class TesteMenuVulnerabilidade(unittest.TestCase):
    def test_manual(self):
        v = digitar(["", "Senha fraca", "Acesso", "7,5", "1"], NVDFalso())
        self.assertTrue(v.id.startswith("LOCAL-"))
        self.assertEqual((v.severidade, v.fonte), (7.5, "manual"))
        self.assertEqual(v.status, StatusVulnerabilidade.ABERTA)

    def test_cve_com_nota_do_nvd_e_enter_aceita_descricao(self):
        v = digitar(["cve-2021-44228", "", "RCE", "2"], NVDFalso())
        self.assertEqual(v.id, "CVE-2021-44228")
        self.assertEqual((v.severidade, v.fonte), (10.0, "NVD"))
        self.assertEqual(v.descricao, "Log4j remote code execution")
        self.assertEqual(v.status, StatusVulnerabilidade.EM_TRATAMENTO)

    def test_cve_com_nvd_fora_do_ar_pede_nota_manual_e_mantem_id(self):
        v = digitar(["CVE-2021-44228", "9,8", "Minha descrição", "RCE", "1"],
                    NVDFalso(falha=True))
        self.assertEqual(v.id, "CVE-2021-44228")
        self.assertEqual((v.severidade, v.fonte), (9.8, "manual"))

    def test_formato_de_cve_invalido_pergunta_de_novo(self):
        v = digitar(["abc", "", "Desc", "Cat", "3", "1"], NVDFalso())
        self.assertTrue(v.id.startswith("LOCAL-"))
        self.assertEqual(v.severidade, 3.0)

    def test_nota_fora_da_faixa_e_texto_sao_rejeitados(self):
        v = digitar(["", "D", "C", "11", "abc", "4", "1"], NVDFalso())
        self.assertEqual(v.severidade, 4.0)

    def test_status_fora_da_lista_e_rejeitado(self):
        v = digitar(["", "D", "C", "5", "9", "0", "4"], NVDFalso())
        self.assertEqual(v.status, StatusVulnerabilidade.RISCO_ACEITO)


if __name__ == "__main__":
    unittest.main()
