import json
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade


class Persistencia:
    def salvar_dados(self, ativos, nome_arquivo):
        with open(nome_arquivo, 'w') as arquivo:
            dados = [ativo.para_dict() for ativo in ativos]
            json.dump(dados, arquivo, indent=4)

    def carregar_dados(self, nome_arquivo):
        with open(nome_arquivo, 'r') as arquivo:
            dados = json.load(arquivo)
            tipos = {
                "Notebook": Notebook,   
                "Roteador": Roteador,
                "Servidor": Servidor
            }

            ativos = []

            for dado in dados:
                classe = tipos[dado["tipo"]]
                dados_ativo = dado.copy()
                dados_ativo.pop("tipo")
                dados_ativo["vulnerabilidades"] = [
                    Vulnerabilidade(**vuln) for vuln in dado["vulnerabilidades"]
                ]
                ativo = classe(**dados_ativo)
                ativos.append(ativo)
            return ativos