import json
import os
from pathlib import Path

from src.persistencia.erros import ErroDados
from src.persistencia.fabrica_ativos import FabricaAtivos


def gravar_json_atomico(dados, nome_arquivo):
    """Grava `dados` como JSON de forma atômica.

    Escreve num arquivo temporário e só então o troca pelo definitivo
    (os.replace é atômico). Se o programa ou o computador cair no meio
    da escrita, o arquivo antigo continua inteiro, em vez de ficar pela
    metade e inválido.
    """
    caminho = Path(nome_arquivo)
    temporario = caminho.with_name(caminho.name + ".tmp")

    try:
        with open(temporario, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, indent=4, ensure_ascii=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())  # força a ida ao disco

        os.replace(temporario, caminho)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise


class Persistencia:
    # Mantido por compatibilidade; a lista de tipos agora mora na fábrica.
    TIPOS = FabricaAtivos.TIPOS

    def salvar_dados(self, ativos, nome_arquivo):
        """Grava a lista de ativos no JSON (gravação atômica)."""
        # Serializa antes de abrir qualquer arquivo: se falhar, nada é tocado.
        dados = [ativo.para_dict() for ativo in ativos]
        gravar_json_atomico(dados, nome_arquivo)

    def carregar_dados(self, nome_arquivo):
        try:
            with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except json.JSONDecodeError as erro:
            raise ErroDados(f"Arquivo '{nome_arquivo}' com JSON inválido: {erro}") from erro

        if not isinstance(dados, list):
            raise ErroDados("O arquivo de ativos deve conter uma lista JSON.")

        return [FabricaAtivos.reconstruir(dado) for dado in dados]
