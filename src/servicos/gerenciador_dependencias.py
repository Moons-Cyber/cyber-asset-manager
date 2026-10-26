"""Gerencia as dependências entre ativos."""

import json
import math
from pathlib import Path

from src.modelos.dependencia import Dependencia, soma_de_pesos_valida
from src.persistencia.erros import ErroDados


class GerenciadorDependencias:
    """Cadastra, lista e persiste dependências entre ativos."""

    def __init__(self, caminho_arquivo="dependencias.json"):
        self.caminho_arquivo = Path(caminho_arquivo)

    def listar_dependencias(self):
        """Carrega as dependências persistidas."""
        if not self.caminho_arquivo.exists():
            return []

        try:
            with self.caminho_arquivo.open(
                "r",
                encoding="utf-8",
            ) as arquivo:
                dados = json.load(arquivo)

            return [
                Dependencia(**dado)
                for dado in dados
            ]
        except (ValueError, TypeError) as erro:
            # ValueError cobre JSON inválido e também um peso inválido gravado.
            raise ErroDados(
                f"Arquivo '{self.caminho_arquivo}' inválido: {erro}"
            ) from erro

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

        # fsum: soma exata, independente da ordem das parcelas.
        novo_total = math.fsum(
            [
                existente.peso
                for existente in dependencias
                if existente.ativo_destino_id
                == dependencia.ativo_destino_id
            ]
            + [dependencia.peso]
        )

        if not soma_de_pesos_valida(novo_total):
            raise ValueError(
                "A soma dos pesos recebidos pelo ativo "
                "deve ser menor que 1."
            )

        dependencias.append(dependencia)
        self.salvar_dependencias(dependencias)

        return dependencia

    def remover_dependencia(self, origem_id, destino_id):
        """Remove uma dependência específica. Devolve True se existia."""
        dependencias = self.listar_dependencias()

        restantes = [
            d for d in dependencias
            if not (
                d.ativo_origem_id == origem_id
                and d.ativo_destino_id == destino_id
            )
        ]

        if len(restantes) == len(dependencias):
            return False

        self.salvar_dependencias(restantes)
        return True

    def remover_dependencias_do_ativo(self, identificador):
        """Remove toda dependência que envolva o ativo, como origem ou destino.

        Chamada quando um ativo é excluído: sem isso sobrariam dependências
        "órfãs" apontando para um ativo que não existe mais, e a análise de
        risco falharia.
        Devolve quantas dependências foram removidas.
        """
        dependencias = self.listar_dependencias()

        restantes = [
            d for d in dependencias
            if identificador not in (d.ativo_origem_id, d.ativo_destino_id)
        ]

        removidas = len(dependencias) - len(restantes)

        if removidas:
            self.salvar_dependencias(restantes)

        return removidas
