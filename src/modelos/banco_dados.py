from src.modelos.ativo import Ativo


class BancoDeDados(Ativo):
    campo_especifico = "sgbd"
    rotulo_campo = "SGBD"

    def __init__(self, id, nome, responsavel, setor, vulnerabilidades, sgbd):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.sgbd = sgbd

    def exibir_detalhes(self):
        super().exibir_detalhes_comuns()
        print(f"SGBD: {self.sgbd}")

    def obter_tipo(self):
        return "BancoDeDados"

    def para_dict(self):
        data = super().para_dict()
        data["sgbd"] = self.sgbd
        return data

    def obter_fator_exposicao(self):
        return 1.0  # normalmente atrás da aplicação; o risco vem pela dependência