"""Padrão Factory: reconstrói o ativo da subclasse certa a partir de um registro JSON.

O JSON guarda o nome da classe no campo "tipo" (ex.: "Servidor"). Quem lê
o arquivo não precisa saber que Servidor, Notebook etc. existem: pede à
fábrica e recebe o objeto pronto. Um tipo novo entra só em registro_tipos.py.
"""

from src.modelos.registro_tipos import CLASSE_POR_TIPO
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.erros import ErroDados


class FabricaAtivos:
    # O nome da classe é o mesmo texto que obter_tipo() grava no JSON.
    # Derivado do registro central para não manter uma terceira lista de tipos.
    TIPOS = {classe.__name__: classe for classe in CLASSE_POR_TIPO.values()}

    @classmethod
    def reconstruir(cls, dado):
        """Recebe um dict lido do JSON e devolve o objeto da subclasse certa."""
        tipo = dado.get("tipo") if isinstance(dado, dict) else None
        if tipo not in cls.TIPOS:
            raise ErroDados(f"Tipo de ativo desconhecido no arquivo: {tipo!r}")

        try:
            campos = dado.copy()
            campos.pop("tipo")
            campos["vulnerabilidades"] = [
                Vulnerabilidade.de_dict(v) for v in dado.get("vulnerabilidades", [])
            ]
            return cls.TIPOS[tipo](**campos)
        except (KeyError, TypeError) as erro:
            raise ErroDados(
                f"Registro de ativo inválido (campo ausente ou inesperado: {erro})."
            ) from erro
