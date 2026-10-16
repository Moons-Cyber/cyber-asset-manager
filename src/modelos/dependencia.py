"""Modelo de uma dependência entre dois equipamentos."""

import math


class Dependencia:
    """Representa a transmissão de risco entre dois ativos."""

    def __init__(
        self,
        ativo_origem_id,
        ativo_destino_id,
        peso,
    ):
        if not isinstance(ativo_origem_id, int) or ativo_origem_id <= 0:
            raise ValueError("O ID de origem deve ser um inteiro positivo.")

        if not isinstance(ativo_destino_id, int) or ativo_destino_id <= 0:
            raise ValueError("O ID de destino deve ser um inteiro positivo.")

        if ativo_origem_id == ativo_destino_id:
            raise ValueError("Um ativo não pode depender de si mesmo.")

        if (
            isinstance(peso, bool)
            or not isinstance(peso, (int, float))
            or not math.isfinite(peso)
            or not 0 <= peso < 1
        ):
            raise ValueError(
                "O peso deve ser um número finito entre 0 e 1, "
                "excluindo 1."
            )

        self.ativo_origem_id = ativo_origem_id
        self.ativo_destino_id = ativo_destino_id
        self.peso = float(peso)

    def para_dict(self):
        """Converte a dependência para um dicionário serializável."""
        return {
            "ativo_origem_id": self.ativo_origem_id,
            "ativo_destino_id": self.ativo_destino_id,
            "peso": self.peso,
        }

    def __str__(self):
        """Retorna uma representação legível da dependência."""
        return (
            f"Ativo {self.ativo_origem_id} -> "
            f"Ativo {self.ativo_destino_id} "
            f"(peso: {self.peso:.2f})"
        )
