import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.modelos.notebook import Notebook
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.persistencia import Persistencia
from src.servicos.gerenciador_ativos import GerenciadorAtivos


def nb(id_, nome=None):
    return Notebook(id_, nome or f"NB{id_}", "x", "TI", [], "8GB")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.arq = Path(self.tmp.name) / "ativos.json"
        self.g = GerenciadorAtivos(self.arq)


class TesteDictEmMemoria(Base):
    def test_arquivo_e_lido_uma_unica_vez(self):
        for i in (1, 2, 3):
            self.g.cadastrar_ativo(nb(i))
        novo = GerenciadorAtivos(self.arq)   # simula reabrir o programa
        with mock.patch.object(Persistencia, "carregar_dados",
                               wraps=novo.persistencia.carregar_dados) as espiao:
            for _ in range(50):
                novo.buscar_ativo_por_id(2)
                novo.buscar_ativos_por_nome("nb")
                novo.listar_ativos()
            self.assertEqual(espiao.call_count, 1)

    def test_busca_por_id_devolve_o_mesmo_objeto(self):
        self.g.cadastrar_ativo(nb(7))
        self.assertIs(self.g.buscar_ativo_por_id(7), self.g.buscar_ativo_por_id(7))
        self.assertIsNone(self.g.buscar_ativo_por_id(99))

    def test_ordem_de_cadastro_e_preservada_apos_reabrir(self):
        for i in (5, 1, 9):
            self.g.cadastrar_ativo(nb(i))
        ids = [a.id for a in GerenciadorAtivos(self.arq).listar_ativos()]
        self.assertEqual(ids, [5, 1, 9])

    def test_alteracoes_chegam_ao_arquivo(self):
        self.g.cadastrar_ativo(nb(1))
        self.g.atualizar_ativo(1, nome="Renomeado")
        self.g.adicionar_vulnerabilidade(1, Vulnerabilidade("d", "c", 5, "Aberta", id="CVE-2020-0001"))
        self.g.cadastrar_ativo(nb(2))
        self.g.remover_ativo(2)
        de_novo = GerenciadorAtivos(self.arq)
        self.assertEqual([a.nome for a in de_novo.listar_ativos()], ["Renomeado"])
        self.assertEqual(de_novo.buscar_ativo_por_id(1).vulnerabilidades[0].id, "CVE-2020-0001")

    def test_id_duplicado_no_cadastro(self):
        self.g.cadastrar_ativo(nb(1))
        with self.assertRaises(ValueError):
            self.g.cadastrar_ativo(nb(1, "Outro"))
        self.assertEqual(len(self.g.listar_ativos()), 1)

    def test_remover_inexistente(self):
        self.assertFalse(self.g.remover_ativo(42))

    def test_arquivo_inexistente_vira_lista_vazia(self):
        self.assertEqual(self.g.listar_ativos(), [])

    def test_recarregar_enxerga_edicao_manual_do_json(self):
        self.g.cadastrar_ativo(nb(1))
        dados = json.loads(self.arq.read_text(encoding="utf-8"))
        dados[0]["nome"] = "Editado na mao"
        self.arq.write_text(json.dumps(dados), encoding="utf-8")
        self.assertEqual(self.g.buscar_ativo_por_id(1).nome, "NB1")   # memória antiga
        self.g.recarregar()
        self.assertEqual(self.g.buscar_ativo_por_id(1).nome, "Editado na mao")


class TesteArquivoRuim(Base):
    def test_id_repetido_no_arquivo_e_detectado(self):
        a = nb(1).para_dict()
        self.arq.write_text(json.dumps([a, a]), encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            self.g.listar_ativos()
        self.assertIn("repetido", str(ctx.exception))

    def test_erro_aparece_no_uso_e_nao_no_construtor(self):
        self.arq.write_text("{ quebrado", encoding="utf-8")
        g = GerenciadorAtivos(self.arq)      # não pode levantar aqui
        with self.assertRaises(ValueError):
            g.listar_ativos()

    def test_corrigir_o_arquivo_e_tentar_de_novo_funciona(self):
        self.arq.write_text("{ quebrado", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.g.listar_ativos()
        self.arq.write_text("[]", encoding="utf-8")
        self.assertEqual(self.g.listar_ativos(), [])

    def test_registro_sem_campo_obrigatorio_vira_valueerror(self):
        ruim = nb(1).para_dict()
        del ruim["responsavel"]
        self.arq.write_text(json.dumps([ruim]), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.g.listar_ativos()


class TesteFalhaNaGravacao(Base):
    def test_cadastro_que_falha_ao_gravar_nao_deixa_fantasma_na_memoria(self):
        self.g.cadastrar_ativo(nb(1))
        with mock.patch.object(Persistencia, "salvar_dados", side_effect=OSError("disco cheio")):
            with self.assertRaises(OSError):
                self.g.cadastrar_ativo(nb(2))
        self.assertEqual([a.id for a in self.g.listar_ativos()], [1])

    def test_remocao_que_falha_ao_gravar_nao_perde_o_ativo(self):
        self.g.cadastrar_ativo(nb(1))
        with mock.patch.object(Persistencia, "salvar_dados", side_effect=OSError("x")):
            with self.assertRaises(OSError):
                self.g.remover_ativo(1)
        self.assertIsNotNone(self.g.buscar_ativo_por_id(1))

    def test_atualizacao_que_falha_ao_gravar_volta_ao_valor_do_disco(self):
        self.g.cadastrar_ativo(nb(1, "Original"))
        with mock.patch.object(Persistencia, "salvar_dados", side_effect=OSError("x")):
            with self.assertRaises(OSError):
                self.g.atualizar_ativo(1, nome="Nao gravado")
        self.assertEqual(self.g.buscar_ativo_por_id(1).nome, "Original")


class TesteGravacaoAtomica(Base):
    def test_nao_sobra_arquivo_temporario(self):
        self.g.cadastrar_ativo(nb(1))
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["ativos.json"])

    def test_queda_no_meio_da_escrita_preserva_o_arquivo_antigo(self):
        self.g.cadastrar_ativo(nb(1, "Seguro"))
        antes = self.arq.read_text(encoding="utf-8")
        with mock.patch("src.persistencia.persistencia.json.dump",
                        side_effect=RuntimeError("queda de energia")):
            with self.assertRaises(RuntimeError):
                Persistencia().salvar_dados([nb(2)], self.arq)
        self.assertEqual(self.arq.read_text(encoding="utf-8"), antes)
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["ativos.json"])

    def test_acentos_sao_gravados_legiveis(self):
        self.g.cadastrar_ativo(Notebook(1, "Notebook João", "Conceição", "TI", [], "8GB"))
        self.assertIn("Conceição", self.arq.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
