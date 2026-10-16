import json
import os
from pathlib import Path

from src.modelos.banco_dados import BancoDeDados
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.modelos.vulnerabilidades import Vulnerabilidade


class Persistencia:
    TIPOS = {
        "Notebook": Notebook,
        "Roteador": Roteador,
        "Servidor": Servidor,
        "BancoDeDados": BancoDeDados,
    }

    def salvar_dados(self, ativos, nome_arquivo):
        """Grava o JSON de forma atômica.

        Escreve num arquivo temporário e só então o troca pelo definitivo
        (os.replace é atômico). Se o programa ou o computador cair no meio
        da escrita, o arquivo antigo continua inteiro, em vez de ficar pela
        metade e inválido.
        """
        caminho = Path(nome_arquivo)
        temporario = caminho.with_name(caminho.name + ".tmp")

        # Serializa antes de abrir qualquer arquivo: se falhar, nada é tocado.
        dados = [ativo.para_dict() for ativo in ativos]

        try:
            with open(temporario, "w", encoding="utf-8") as arquivo:
                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                arquivo.flush()
                os.fsync(arquivo.fileno())  # força a ida ao disco

            os.replace(temporario, caminho)
        except BaseException:
            temporario.unlink(missing_ok=True)
            raise

    def carregar_dados(self, nome_arquivo):
        try:
            with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except json.JSONDecodeError as erro:
            raise ValueError(f"Arquivo '{nome_arquivo}' com JSON inválido: {erro}") from erro

        if not isinstance(dados, list):
            raise ValueError("O arquivo de ativos deve conter uma lista JSON.")

        ativos = []
        for dado in dados:
            tipo = dado.get("tipo") if isinstance(dado, dict) else None
            if tipo not in self.TIPOS:
                raise ValueError(f"Tipo de ativo desconhecido no arquivo: {tipo!r}")

            try:
                dados_ativo = dado.copy()
                dados_ativo.pop("tipo")
                dados_ativo["vulnerabilidades"] = [
                    Vulnerabilidade.de_dict(v) for v in dado.get("vulnerabilidades", [])
                ]
                ativos.append(self.TIPOS[tipo](**dados_ativo))
            except (KeyError, TypeError) as erro:
                raise ValueError(
                    f"Registro de ativo inválido (campo ausente ou inesperado: {erro})."
                ) from erro
        return ativos