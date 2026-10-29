def validar_texto_identificacao(valor, campo, minimo=2):
    """Valida um campo textual que identifica um componente."""
    if not isinstance(valor, str):
        raise ValueError(f"{campo} deve ser um texto.")

    valor = valor.strip()

    if not valor:
        raise ValueError(f"{campo} não pode ficar vazio.")
    
    if len(valor) < minimo:
        raise ValueError(f"{campo} deve ter pelo menos {minimo} caracteres")


    if not any(caractere.isalpha() for caractere in valor):
        raise ValueError(f"{campo} deve conter pelo menos uma letra.")

    return valor


def validar_memoria_ram(valor):
    """Valida a memória RAM em MB ou GB."""
    if not isinstance(valor, str):
        raise ValueError("A memória RAM deve ser informada como texto.")

    valor = valor.strip().upper().replace(" ", "")

    for unidade in ("GB", "MB"):
        if valor.endswith(unidade):
            quantidade = valor[:-len(unidade)]

            if quantidade.isdigit() and int(quantidade) > 0:
                return valor

            break

    raise ValueError(
        "Memória RAM inválida. Use uma quantidade positiva, "
        "como 8GB, 16GB ou 512MB."
    )
