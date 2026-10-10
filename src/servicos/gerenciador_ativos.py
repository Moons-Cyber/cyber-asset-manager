"""Serviço responsável pelo gerenciamento dos ativos."""

from pathlib import Path

from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.persistencia import Persistencia


class GerenciadorAtivos:
    """Gerencia cadastro, consulta, atualização e remoção de ativos."""

    def __init__(self, caminho_arquivo="ativos.json"):
        self.caminho_arquivo = Path(caminho_arquivo)
        self.persistencia = Persistencia()

    def listar_ativos(self):
        """Retorna todos os ativos cadastrados."""
        if not self.caminho_arquivo.exists():
            return []

        return self.persistencia.carregar_dados(
            self.caminho_arquivo
        )

    def buscar_ativo_por_id(self, identificador):
        """Busca um ativo pelo ID ou retorna None."""
        ativos = self.listar_ativos()

        for ativo in ativos:
            if ativo.id == identificador:
                return ativo

        return None

    def cadastrar_ativo(self, ativo):
        """Cadastra um ativo, impedindo IDs duplicados."""
        ativos = self.listar_ativos()

        for ativo_existente in ativos:
            if ativo_existente.id == ativo.id:
                raise ValueError(
                    f"Já existe um ativo com ID {ativo.id}."
                )

        ativos.append(ativo)

        self.persistencia.salvar_dados(
            ativos,
            self.caminho_arquivo,
        )

        return ativo

    def atualizar_ativo(self, identificador, **alteracoes):
        """Atualiza os campos permitidos e salva o JSON."""
        if not alteracoes:
            raise ValueError(
                "Informe pelo menos um campo para atualizar."
            )

        ativos = self.listar_ativos()

        ativo = next(
            (
                item
                for item in ativos
                if item.id == identificador
            ),
            None,
        )

        if ativo is None:
            return None

        campos_permitidos = {
            "nome",
            "responsavel",
            "setor",
            "vulnerabilidades",
        }

        campos_especificos = {
            "Notebook": {"memoria_ram"},
            "Servidor": {"processador"},
            "Roteador": {"modelo"},
        }

        campos_permitidos.update(
            campos_especificos.get(
                ativo.obter_tipo(),
                set(),
            )
        )

        campos_invalidos = (
            set(alteracoes) - campos_permitidos
        )

        if campos_invalidos:
            raise ValueError(
                "Campos não permitidos: "
                + ", ".join(sorted(campos_invalidos))
            )

        if "vulnerabilidades" in alteracoes:
            vulnerabilidades = alteracoes["vulnerabilidades"]

            if not isinstance(vulnerabilidades, list):
                raise TypeError(
                    "Vulnerabilidades deve ser uma lista."
                )

            if not all(
                isinstance(item, Vulnerabilidade)
                for item in vulnerabilidades
            ):
                raise TypeError(
                    "A lista deve conter objetos Vulnerabilidade."
                )

        for campo, valor in alteracoes.items():
            setattr(ativo, campo, valor)

        self.persistencia.salvar_dados(
            ativos,
            self.caminho_arquivo,
        )

        return ativo

    def remover_ativo(self, identificador):
        """Remove um ativo e persiste a alteração."""
        ativos = self.listar_ativos()

        for indice, ativo in enumerate(ativos):
            if ativo.id == identificador:
                ativos.pop(indice)

                self.persistencia.salvar_dados(
                    ativos,
                    self.caminho_arquivo,
                )

                return True

        return False