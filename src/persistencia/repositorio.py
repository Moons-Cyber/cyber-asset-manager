"""Padrão Repository: o resto do sistema guarda e lê ativos sem saber onde ficam.

GerenciadorAtivos conversa com um RepositorioAtivos (listar / salvar). Hoje
a implementação é um arquivo JSON; trocar por SQLite, ou por uma lista em
memória nos testes, não exige mexer no gerenciador.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from src.persistencia.persistencia import Persistencia


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
