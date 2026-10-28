from src.modelos.ativo import Ativo
from src.modelos.validacoes import validar_texto_identificacao


class Roteador(Ativo):
    campo_especifico = "modelo"
    rotulo_campo = "Modelo"

    def __init__(self, id, nome, responsavel, setor, vulnerabilidades, modelo):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.modelo = self.validar_campo_especifico(modelo)

    @staticmethod
    def validar_campo_especifico(valor):
        return validar_texto_identificacao(valor, "Modelo")

    def exibir_detalhes(self):
        super().exibir_detalhes_comuns()
        print(f"Modelo: {self.modelo}")

    def obter_tipo(self):
        return "Roteador"

    def para_dict(self):
        data = super().para_dict()
        data["modelo"] = self.modelo
        return data

    def obter_fator_exposicao(self):
        return 1.2  # borda da rede, mas com poucas portas de serviço