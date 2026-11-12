"""Padrão Repository: o resto do sistema guarda e lê ativos sem saber onde ficam.

GerenciadorAtivos conversa com um RepositorioAtivos (listar / salvar). Hoje
a implementação é um arquivo JSON; trocar por SQLite, ou por uma lista em
memória nos testes, não exige mexer no gerenciador.
"""

from abc import ABC, abstractmethod
import json
from pathlib import Path

from src.modelos.dependencia import Dependencia
from src.persistencia.erros import ErroDados
from src.persistencia.persistencia import Persistencia, gravar_json_atomico


class RepositorioAtivos(ABC):
    @abstractmethod
    def listar(self):
        """Devolve todos os ativos guardados (lista vazia se não há nada)."""

    @abstractmethod
    def salvar(self, ativos):
        """Substitui o conteúdo guardado pela lista recebida."""


class RepositorioAtivosJson(RepositorioAtivos):
    """Guarda os ativos num arquivo JSON (gravação atômica)."""

    def __init__(self, caminho, persistencia=None):
        self.caminho = Path(caminho)
        self.persistencia = persistencia or Persistencia()

    def listar(self):
        if not self.caminho.exists():
            return []
        return self.persistencia.carregar_dados(self.caminho)

    def salvar(self, ativos):
        self.persistencia.salvar_dados(ativos, self.caminho)


class RepositorioAtivosMemoria(RepositorioAtivos):
    """Guarda em memória, sem arquivo: serve para testes e demonstrações."""

    def __init__(self, ativos=()):
        self._ativos = list(ativos)

    def listar(self):
        return list(self._ativos)

    def salvar(self, ativos):
        self._ativos = list(ativos)


class RepositorioDependencias(ABC):
    """O mesmo padrão, para as dependências entre ativos."""

    @abstractmethod
    def listar(self):
        """Devolve todas as dependências guardadas (lista vazia se não há nada)."""

    @abstractmethod
    def salvar(self, dependencias):
        """Substitui o conteúdo guardado pela lista recebida."""


class RepositorioDependenciasJson(RepositorioDependencias):
    """Guarda as dependências num arquivo JSON (gravação atômica)."""

    def __init__(self, caminho):
        self.caminho = Path(caminho)

    def listar(self):
        if not self.caminho.exists():
            return []
        try:
            with self.caminho.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            return [Dependencia(**dado) for dado in dados]
        except (ValueError, TypeError) as erro:
            # ValueError cobre JSON inválido e também um peso inválido gravado.
            raise ErroDados(f"Arquivo '{self.caminho}' inválido: {erro}") from erro

    def salvar(self, dependencias):
        gravar_json_atomico([d.para_dict() for d in dependencias], self.caminho)
