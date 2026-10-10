from pathlib import Path

from src.persistencia.persistencia import Persistencia

class GerenciadorAtivos:
    def __init__(self, caminho_arquivo="ativos.json"):
        self.caminho_arquivo = Path(caminho_arquivo)
        self.persistencia = Persistencia()

    def listar_ativos(self):
        if not self.caminho_arquivo.exists():
            return []

        return self.persistencia.carregar_dados(self.caminho_arquivo)

    def cadastrar_ativo(self, ativo):
        ativos = self.listar_ativos()

        for ativo_existente in ativos:
            if ativo_existente.id == ativo.id:
                raise ValueError(f"Já existe um ativo com ID {ativo.id}.")

        ativos.append(ativo)
        self.persistencia.salvar_dados(ativos, self.caminho_arquivo)

        return ativo

    def buscar_ativo_por_id(self, idenficador):
        ativos = self.listar_ativos()

        for ativo in ativos:
            if ativo.id == idenficador:
                return ativo
        
        return None