from src.modelos.ativo import Ativo


class Notebook (Ativo):
    def __init__(self, id, nome, responsavel, setor, vulnerabilidades, memoria_ram):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.memoria_ram = memoria_ram
    def exibir_detalhes(self):
        super().exibir_detalhes_comuns()
        print(f"Memória RAM: {self.memoria_ram}")
    def obter_tipo(self):
        return "Notebook"
    def para_dict(self):
        data = super().para_dict()
        data["memoria_ram"] = self.memoria_ram
        return data
