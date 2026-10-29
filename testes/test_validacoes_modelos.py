import unittest

from src.modelos.banco_dados import BancoDeDados
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.validacoes import validar_memoria_ram, validar_texto_identificacao


class TesteValidacoes(unittest.TestCase):
    def test_identificacao_remove_espacos_e_aceita_nome_realista(self):
        self.assertEqual(
            validar_texto_identificacao(" TP-Link Archer C6 ", "Modelo"),
            "TP-Link Archer C6",
        )

    def test_identificacao_rejeita_vazio_nao_texto_e_numero_sem_letras(self):
        for valor in ("", "   ", "-2", "123", None, 123):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    validar_texto_identificacao(valor, "Modelo")

    def test_memoria_normaliza_e_aceita_unidades_positivas(self):
        self.assertEqual(validar_memoria_ram("16 gb"), "16GB")
        self.assertEqual(validar_memoria_ram("512mb"), "512MB")

    def test_memoria_rejeita_formatos_invalidos(self):
        for valor in ("-2", "0GB", "abcGB", "16", "", None, 16):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    validar_memoria_ram(valor)

    def test_modelos_aplicam_validacao_diretamente(self):
        with self.assertRaises(ValueError):
            Notebook(1, "Note NB", "Ana", "TI", [], "-2")
        with self.assertRaises(ValueError):
            Roteador(2, "RTR", "Ana", "TI", [], "-2")
        with self.assertRaises(ValueError):
            Servidor(3, "SRV", "Ana", "TI", [], "-2")
        with self.assertRaises(ValueError):
            BancoDeDados(4, "Banco DB", "Ana", "TI", [], "-2")

    def test_nome_curto_ou_vazio_e_recusado_em_qualquer_tipo(self):
        for nome in ("A", "  ", "12"):
            with self.subTest(nome=nome), self.assertRaises(ValueError):
                Notebook(1, nome, "Ana", "TI", [], "8GB")


if __name__ == "__main__":
    unittest.main()
