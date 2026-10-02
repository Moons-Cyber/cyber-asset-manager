from src.modelos.ativo import Ativo


class Roteador (Ativo):
    def __init__(self, id, nome, responsavel, setor, vulnerabilidades, modelo):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.modelo = modelo
    def exibir_detalhes(self):
        super().exibir_detalhes_comuns()
        print(f"Modelo: {self.modelo}")
    def obter_tipo(self):
        return "Roteador"
    def para_dict(self):
        data = super().para_dict()
        data["modelo"] = self.modelo
        return data