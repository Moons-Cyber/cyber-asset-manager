"""Padrão Factory: escolhe onde os dados ficam (JSON ou SQLite) a partir de um nome.

O resto do sistema recebe os repositórios prontos e não sabe qual foi escolhido.
"""

import os
from pathlib import Path

from src.persistencia.repositorio import RepositorioAtivosJson, RepositorioDependenciasJson
from src.persistencia.repositorio_sqlite import RepositorioAtivosSqlite, RepositorioDependenciasSqlite

MODOS = ("json", "sqlite")
NOME_BANCO = "inventario.db"


def modo_do_ambiente():
    """Lê PERSISTENCIA do ambiente (padrão: json)."""
    modo = os.environ.get("PERSISTENCIA", "json").strip().lower()
    if modo not in MODOS:
        raise ValueError(f"PERSISTENCIA deve ser uma de {MODOS}, recebi {modo!r}.")
    return modo


def criar_repositorios(pasta, modo="json"):
    """Devolve (repositório de ativos, repositório de dependências) para a pasta de dados."""
    pasta = Path(pasta)
    if modo == "sqlite":
        banco = pasta / NOME_BANCO
        return RepositorioAtivosSqlite(banco), RepositorioDependenciasSqlite(banco)
    if modo == "json":
        return RepositorioAtivosJson(pasta / "ativos.json"), RepositorioDependenciasJson(pasta / "dependencias.json")
    raise ValueError(f"Modo de persistência desconhecido: {modo!r} (use {MODOS}).")
