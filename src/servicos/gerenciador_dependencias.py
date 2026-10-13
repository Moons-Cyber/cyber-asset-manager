"""Gerencia as dependências entre ativos."""

import json
from pathlib import Path

from src.modelos.dependencia import Dependencia


class GerenciadorDependencias:
    """Cadastra, lista e persiste dependências entre ativos."""

    def __init__(self, caminho_arquivo="dependencias.json"):
        self.caminho_arquivo = Path(caminho_arquivo)

    def listar_dependencias(self):
        """Carrega as dependências persistidas."""
        if not self.caminho_arquivo.exists():
            return []

        with self.caminho_arquivo.open(
            "r",
            encoding="utf-8",
        ) as arquivo:
            dados = json.load(arquivo)

        return [
            Dependencia(**dado)
            for dado in dados
        ]

    def salvar_dependencias(self, dependencias):
        """Salva a lista de dependências em formato JSON."""
        dados = [
            dependencia.para_dict()
            for dependencia in dependencias
        ]

        with self.caminho_arquivo.open(
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                dados,
                arquivo,
                indent=4,
                ensure_ascii=False,
            )

    def cadastrar_dependencia(self, dependencia, ativos):
        """Cadastra uma dependência após validar sua consistência."""
        ids_ativos = {ativo.id for ativo in ativos}

        if dependencia.ativo_origem_id not in ids_ativos:
            raise ValueError("O ativo de origem não existe.")

        if dependencia.ativo_destino_id not in ids_ativos:
            raise ValueError("O ativo de destino não existe.")

        dependencias = self.listar_dependencias()

        for existente in dependencias:
            if (
                existente.ativo_origem_id
                == dependencia.ativo_origem_id
                and existente.ativo_destino_id
                == dependencia.ativo_destino_id
            ):
                raise ValueError(
                    "Essa dependência já está cadastrada."
                )

        peso_recebido = sum(
            existente.peso
            for existente in dependencias
            if existente.ativo_destino_id
            == dependencia.ativo_destino_id
        )

        novo_total = peso_recebido + dependencia.peso

        if novo_total >= 1:
            raise ValueError(
                "A soma dos pesos recebidos pelo ativo "
                "deve ser menor que 1."
            )

        dependencias.append(dependencia)
        self.salvar_dependencias(dependencias)

        return dependencia
