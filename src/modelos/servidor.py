from src.modelos.ativo import Ativo


class Servidor (Ativo):
    def __init__(self, id , nome, responsavel, setor, vulnerabilidades, processador):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.processador = processador
    def exibir_detalhes(self):
        super().exibir_detalhes_comuns()
        print(f"Processador: {self.processador}")
    def obter_tipo(self):
        return "Servidor"
    def para_dict(self):
        data = super().para_dict()
        data["processador"] = self.processador
        return data
