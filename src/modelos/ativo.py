from abc import ABC, abstractmethod


class Ativo(ABC):
    # Cada subclasse declara o seu campo próprio (ex.: memoria_ram) e o rótulo
    # exibido ao usuário. Menu e gerenciador consultam estes atributos, em vez
    # de manter dicionários paralelos "tipo -> campo" espalhados pelo código.
    campo_especifico = None
    rotulo_campo = None

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
            "vulnerabilidades": [
                vulnerabilidade.para_dict()
                for vulnerabilidade in self.vulnerabilidades
            ]
        }

    @abstractmethod
    def obter_tipo(self):
        pass

    @abstractmethod
    def obter_fator_exposicao(self):
        """Fator que pondera o risco próprio deste tipo de ativo.

        1.0 é a exposição de referência; acima de 1.0, mais exposto à rede.
        Cada subclasse define o seu (polimorfismo).
        """
        pass