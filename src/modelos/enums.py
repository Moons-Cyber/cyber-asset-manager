"""Enumerações do sistema de inventário."""

from enum import Enum, IntEnum


class TipoAtivo(IntEnum):
    """Tipos de ativo. Cada tipo tem um código inteiro (requisito 2 do T1)."""

    NOTEBOOK = 1
    SERVIDOR = 2
    ROTEADOR = 3
    BANCO_DADOS = 4

    @property
    def rotulo(self):
        """Nome para exibir ao usuário (ex.: 'Banco de dados')."""
        return _ROTULOS_TIPO[self]


_ROTULOS_TIPO = {
    TipoAtivo.NOTEBOOK: "Notebook",
    TipoAtivo.SERVIDOR: "Servidor",
    TipoAtivo.ROTEADOR: "Roteador",
    TipoAtivo.BANCO_DADOS: "Banco de dados",
}


class Severidade(Enum):
    """Classificação textual de severidade, derivada da nota CVSS.

    As faixas seguem a tabela oficial do CVSS v3.x:
    0.1-3.9 baixa | 4.0-6.9 média | 7.0-8.9 alta | 9.0-10.0 crítica
    """

    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"

    @classmethod
    def a_partir_da_nota(cls, nota):
        if nota >= 9.0:
            return cls.CRITICA
        if nota >= 7.0:
            return cls.ALTA
        if nota >= 4.0:
            return cls.MEDIA
        return cls.BAIXA


class StatusVulnerabilidade(Enum):
    """Situação de tratamento da vulnerabilidade."""

    
    

    ABERTA = "Aberta"
    EM_TRATAMENTO = "Em tratamento"
    CORRIGIDA = "Corrigida"
    RISCO_ACEITO = "Risco aceito"