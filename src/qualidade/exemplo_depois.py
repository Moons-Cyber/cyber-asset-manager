"""Exemplo refatorado para demonstrar boas práticas de Python."""

from typing import Any


def calcular_risco_proprio(
    vulnerabilidades: list[dict[str, float]],
    fator_exposicao: float,
) -> float:
    """Calcula o risco próprio a
    partir das severidades das vulnerabilidades."""
    risco_total = 0.0

    for vulnerabilidade in vulnerabilidades:
        risco_total += vulnerabilidade["severidade"] * fator_exposicao

    return risco_total


def buscar_ativo_por_id(
    ativos: list[dict[str, Any]],
    identificador: int,
) -> dict[str, Any] | None:
    """Retorna o ativo com o identificador informado, se existir."""
    for ativo in ativos:
        if ativo["id"] == identificador:
            return ativo

    return None


def main() -> None:
    """Executa os exemplos de cálculo de risco e busca de ativos."""
    ativos: list[dict[str, Any]] = [
        {
            "id": 1,
            "nome": "Notebook A",
            "vulnerabilidades": [
                {"severidade": 8.5},
                {"severidade": 7.0},
            ],
        },
        {
            "id": 2,
            "nome": "Servidor B",
            "vulnerabilidades": [
                {"severidade": 9.0},
            ],
        },
    ]

    risco = calcular_risco_proprio(
        ativos[0]["vulnerabilidades"],
        1.2,
    )
    servidor = buscar_ativo_por_id(ativos, 2)

    print(risco)
    print(servidor)


if __name__ == "__main__":
    main()
