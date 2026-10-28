from src.modelos.ativo import Ativo
from src.modelos.validacoes import validar_memoria_ram


class Notebook(Ativo):
    campo_especifico = "memoria_ram"
    rotulo_campo = "Memória RAM"

    def __init__(self, id, nome, responsavel, setor, vulnerabilidades, memoria_ram):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.memoria_ram = self.validar_campo_especifico(memoria_ram)

    @staticmethod
    def validar_campo_especifico(valor):
        return validar_memoria_ram(valor)

    def exibir_detalhes(self):
        super().exibir_detalhes_comuns()
        print(f"Memória RAM: {self.memoria_ram}")

    def obter_tipo(self):
        return "Notebook"

    def para_dict(self):
        data = super().para_dict()
        data["memoria_ram"] = self.memoria_ram
        return data

    def obter_fator_exposicao(self):
        return 1.0  # referência: usuário final, atrás da rede interna