import json
import tempfile
import unittest
from pathlib import Path

from src.modelos.notebook import Notebook
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.persistencia import Persistencia


class TestPersistencia(unittest.TestCase):
    def setUp(self):
        """Prepara um arquivo temporário para cada teste."""
        self.pasta_temporaria = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta_temporaria.name) / "ativos.json"
        self.persistencia = Persistencia()

        vulnerabilidade = Vulnerabilidade(
            "Sistema desatualizado",
            "Atualização",
            8.5,
            "Aberta",
        )

        self.notebook = Notebook(
            1001,
            "Notebook de teste",
            "Gabriel",
            "TI",
            [vulnerabilidade],
            "16GB",
        )

    def tearDown(self):
        """Remove o diretório temporário após cada teste."""
        self.pasta_temporaria.cleanup()

    def test_salvar_e_carregar_reconstroi_objetos(self):
        self.persistencia.salvar_dados(
            [self.notebook],
            self.arquivo,
        )

        ativos = self.persistencia.carregar_dados(self.arquivo)

        self.assertEqual(len(ativos), 1)
        self.assertIsInstance(ativos[0], Notebook)
        self.assertEqual(ativos[0].nome, "Notebook de teste")
        self.assertEqual(ativos[0].memoria_ram, "16GB")

        vulnerabilidade = ativos[0].vulnerabilidades[0]

        self.assertIsInstance(vulnerabilidade, Vulnerabilidade)
        self.assertEqual(vulnerabilidade.severidade, 8.5)

    def test_json_contem_uma_lista_de_objetos(self):
        self.persistencia.salvar_dados(
            [self.notebook],
            self.arquivo,
        )

        with self.arquivo.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        self.assertIsInstance(dados, list)
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["tipo"], "Notebook")
        self.assertEqual(dados[0]["id"], 1001)

    def test_salvar_e_carregar_lista_vazia(self):
        self.persistencia.salvar_dados([], self.arquivo)

        ativos = self.persistencia.carregar_dados(self.arquivo)

        self.assertEqual(ativos, [])


if __name__ == "__main__":
    unittest.main()