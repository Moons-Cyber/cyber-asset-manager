import json
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade


class Persistencia:
    TIPOS = {
        "Notebook": Notebook,
        "Roteador": Roteador,
        "Servidor": Servidor,
    }

    def salvar_dados(self, ativos, nome_arquivo):
        dados = [ativo.para_dict() for ativo in ativos]
        with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, indent=4, ensure_ascii=False)

    def carregar_dados(self, nome_arquivo):
        try:
            with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except json.JSONDecodeError as erro:
            raise ValueError(f"Arquivo '{nome_arquivo}' com JSON inválido: {erro}") from erro

        if not isinstance(dados, list):
            raise ValueError("O arquivo de ativos deve conter uma lista JSON.")

        ativos = []
        for dado in dados:
            tipo = dado.get("tipo")
            if tipo not in self.TIPOS:
                raise ValueError(f"Tipo de ativo desconhecido no arquivo: {tipo!r}")

            dados_ativo = dado.copy()
            dados_ativo.pop("tipo")
            dados_ativo["vulnerabilidades"] = [
                Vulnerabilidade.de_dict(v) for v in dado.get("vulnerabilidades", [])
            ]
            ativos.append(self.TIPOS[tipo](**dados_ativo))
        return ativos