from src.modelos.ativo import Ativo
from src.modelos.validacoes import validar_texto_identificacao


class Servidor(Ativo):
    campo_especifico = "processador"
    rotulo_campo = "Processador"

    def __init__(self, id, nome, responsavel, setor, vulnerabilidades, processador):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.processador = self.validar_campo_especifico(processador)

    @staticmethod
    def validar_campo_especifico(valor):
        return validar_texto_identificacao(valor, "Processador")

    def exibir_detalhes(self):
        super().exibir_detalhes_comuns()
        print(f"Processador: {self.processador}")

    def obter_tipo(self):
        return "Servidor"

    def para_dict(self):
        data = super().para_dict()
        data["processador"] = self.processador
        return data

    def obter_fator_exposicao(self):
        return 1.5  # serviços publicados na rede