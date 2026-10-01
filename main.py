class Ativo:
    def __init__(self, id, nome, responsavel,setor,vulnerabilidades):
        self.id = id
        self.nome = nome
        self.responsavel = responsavel
        self.setor = setor
        self.vulnerabilidades = vulnerabilidades

    def exibir_detalhes(self): 
        print(f"ID: {self.id}")
        print(f"Nome: {self.nome}")
        print(f"Responsável: {self.responsavel}")
        print(f"Setor: {self.setor}")
        print("Vulnerabilidades:")
        for vulnerabilidade in self.vulnerabilidades:
            print(f"- {vulnerabilidade}")

       
        
class Notebook (Ativo):
    def __init__(self, id, nome, responsavel, setor, vulnerabilidades, memoria_ram):
        super().__init__(id, nome, responsavel, setor, vulnerabilidades)
        self.memoria_ram = memoria_ram
    def exibir_detalhes(self):
        super().exibir_detalhes()
        print(f"Memória RAM: {self.memoria_ram}")

notebook1 = Notebook(1, "Notebook Dell", "João", "TI", ["Vulnerabilidade 1", "Vulnerabilidade 2"], "16GB")
notebook1.exibir_detalhes()
