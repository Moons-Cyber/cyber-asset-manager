from abc import ABC, abstractmethod


class Ativo(ABC):
    def __init__(self, id, nome, responsavel,setor,vulnerabilidades):
        self.id = id
        self.nome = nome
        self.responsavel = responsavel
        self.setor = setor
        self.vulnerabilidades = vulnerabilidades

    @abstractmethod
    def exibir_detalhes(self):
        pass

    def exibir_detalhes_comuns(self):
        print(f"ID: {self.id}")
        print(f"Nome: {self.nome}")
        print(f"Responsável: {self.responsavel}")
        print(f"Setor: {self.setor}")
        print("Vulnerabilidades:")
        for vulnerabilidade in self.vulnerabilidades:
            print(f"- {vulnerabilidade}")

    def para_dict(self):
        return {
            "id": self.id,
            "tipo": self.obter_tipo(),
            "nome": self.nome,
            "responsavel": self.responsavel,
            "setor": self.setor,
            "vulnerabilidades": self.vulnerabilidades
        }

    @abstractmethod
    def obter_tipo(self):
        pass