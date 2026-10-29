import unittest

from src.modelos.dependencia import Dependencia
from src.modelos.notebook import Notebook
from src.modelos.vulnerabilidades import Vulnerabilidade, resumir
from src.servicos.analise_risco import (
    calcular_risco_efetivo, construir_matriz_incidencia,
)

LOG4J = (
    "Apache Log4j2 2.0-beta9 through 2.15.0 (excluding security releases "
    "2.12.2, 2.12.3, and 2.3.1) JNDI features used in configuration, log "
    "messages, and parameters do not protect against attacker controlled "
    "LDAP and other JNDI related endpoints. An attacker who can control log "
    "messages or log message parameters can execute arbitrary code."
)


def v(id_, nota, status="Aberta"):
    return Vulnerabilidade("d", "c", nota, status, id=id_)


class TesteResumo(unittest.TestCase):
    def test_texto_curto_fica_intacto(self):
        self.assertEqual(resumir("Senha fraca"), "Senha fraca")

    def test_descricao_longa_do_nvd_e_encurtada_sem_partir_palavra(self):
        r = resumir(LOG4J, 100)
        self.assertLessEqual(len(r), 103)          # 100 + "..."
        self.assertTrue(r.endswith("..."))
        self.assertTrue(r.startswith("Apache Log4j2 2.0-beta9"))
        self.assertNotIn("  ", r)
        corpo = r[:-3]
        self.assertTrue(LOG4J.startswith(corpo))
        self.assertEqual(LOG4J[len(corpo)], " ")    # parou numa fronteira de palavra

    def test_pega_so_a_primeira_frase(self):
        self.assertEqual(resumir("Falha grave. Detalhes longos aqui."), "Falha grave...")

    def test_quebras_de_linha_viram_espaco(self):
        self.assertEqual(resumir("a\nb   c"), "a b c")

    def test_str_da_vulnerabilidade_usa_o_resumo(self):
        texto = str(Vulnerabilidade(LOG4J, "RCE", 10.0, "Aberta", id="CVE-2021-44228"))
        self.assertLess(len(texto), 200)

    def test_original_e_guardado_e_sobrevive_ao_json(self):
        vul = Vulnerabilidade("curta", "RCE", 10.0, "Aberta",
                              id="CVE-2021-44228", descricao_original=LOG4J)
        de_novo = Vulnerabilidade.de_dict(vul.para_dict())
        self.assertEqual(de_novo.descricao_original, LOG4J)

    def test_registro_antigo_sem_original_continua_carregando(self):
        antigo = {"descricao": "x", "categoria": "y", "severidade": 5.0, "status": "Aberta"}
        self.assertIsNone(Vulnerabilidade.de_dict(antigo).descricao_original)


class TesteCorrigidaReduzRisco(unittest.TestCase):
    def ativos(self, status_log4j):
        a = Notebook(1, "Alienware", "Jio", "TI", [v("CVE-1", 10.0, status_log4j), v("L-2", 4.0)], "8GB")
        b = Notebook(2, "Acer", "Gab", "TI", [v("CVE-1", 10.0, status_log4j)], "8GB")
        return [a, b]

    def test_corrigida_sai_da_matriz(self):
        M, vetor, _ = construir_matriz_incidencia(self.ativos("Corrigida"))
        self.assertEqual(vetor, [4.0])              # só sobrou L-2
        self.assertEqual(M, [[1], [0]])

    def test_risco_cai_ao_corrigir(self):
        antes = calcular_risco_efetivo(self.ativos("Aberta"), [])
        depois = calcular_risco_efetivo(self.ativos("Corrigida"), [])
        self.assertEqual([r["risco_proprio"] for r in antes], [14.0, 10.0])
        self.assertEqual([r["risco_proprio"] for r in depois], [4.0, 0.0])

    def test_risco_aceito_e_em_tratamento_continuam_contando(self):
        for status in ("Risco aceito", "Em tratamento"):
            r = calcular_risco_efetivo(self.ativos(status), [])
            self.assertEqual(r[1]["risco_proprio"], 10.0)

    def test_tudo_corrigido_nao_quebra_e_da_zero(self):
        a = Notebook(1, "Alienware", "Jio", "TI", [v("CVE-1", 9.0, "Corrigida")], "8GB")
        b = Notebook(2, "Acer", "Gab", "TI", [], "8GB")
        r = calcular_risco_efetivo([a, b], [])
        self.assertEqual([x["risco_efetivo"] for x in r], [0.0, 0.0])

    def test_corrigir_tambem_reduz_o_risco_herdado(self):
        # B depende de A com peso 0.5: x_B = b_B + 0.5 * x_A
        ativos = self.ativos("Aberta")
        dep = [Dependencia(1, 2, 0.5)]   # origem 1 -> destino 2
        antes = calcular_risco_efetivo(ativos, dep)
        depois = calcular_risco_efetivo(self.ativos("Corrigida"), dep)
        self.assertAlmostEqual(antes[1]["risco_efetivo"], 10.0 + 0.5 * 14.0)
        self.assertAlmostEqual(depois[1]["risco_efetivo"], 0.0 + 0.5 * 4.0)



class TesteMesmoIdNotasDiferentes(unittest.TestCase):
    """Regressão: a nota do segundo ativo era descartada em silêncio."""

    def test_mesma_descricao_manual_com_notas_diferentes(self):
        a = Notebook(1, "Alienware", "Jio", "TI", [Vulnerabilidade("Senha fraca", "Acesso", 10.0, "Aberta")], "8GB")
        b = Notebook(2, "Acer", "Gab", "TI", [Vulnerabilidade("Senha fraca", "Acesso", 5.0, "Aberta")], "8GB")
        self.assertEqual(a.vulnerabilidades[0].id, b.vulnerabilidades[0].id)   # mesmo ID local
        r = calcular_risco_efetivo([a, b], [])
        self.assertEqual([x["risco_proprio"] for x in r], [10.0, 5.0])

    def test_mesmo_cve_com_nota_do_nvd_e_nota_digitada(self):
        a = Notebook(1, "Alienware", "Jio", "TI", [Vulnerabilidade("d", "c", 10.0, "Aberta", id="CVE-2021-44228")], "8GB")
        b = Notebook(2, "Acer", "Gab", "TI", [Vulnerabilidade("d", "c", 9.8, "Aberta", id="CVE-2021-44228")], "8GB")
        r = calcular_risco_efetivo([a, b], [])
        self.assertEqual([x["risco_proprio"] for x in r], [10.0, 9.8])

    def test_mesmo_id_e_mesma_nota_continua_numa_coluna_so(self):
        a = Notebook(1, "Alienware", "Jio", "TI", [v("CVE-1", 7.0)], "8GB")
        b = Notebook(2, "Acer", "Gab", "TI", [v("CVE-1", 7.0, "Em tratamento")], "8GB")
        M, vetor, _ = construir_matriz_incidencia([a, b])
        self.assertEqual((M, vetor), ([[1], [1]], [7.0]))

    def test_risco_proprio_e_sempre_a_soma_das_notas_das_vulnerabilidades_ativas(self):
        # Propriedade geral: independe de como os ativos compartilham IDs.
        import itertools
        notas = [3.0, 5.5, 9.0]
        for combinacao in itertools.product(notas, repeat=3):
            ativos = [Notebook(i + 1, f"Alienware{i}", "Jio", "TI",
                      [Vulnerabilidade("igual", "igual", n, "Aberta"), v(f"U{i}", 1.0)], "8GB")
                      for i, n in enumerate(combinacao)]
            r = calcular_risco_efetivo(ativos, [])
            self.assertEqual([x["risco_proprio"] for x in r], [n + 1.0 for n in combinacao])


if __name__ == "__main__":
    unittest.main()
