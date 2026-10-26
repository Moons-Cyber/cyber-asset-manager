"""Registro central: qual classe implementa cada TipoAtivo.

Usado pela API para criar o objeto certo a partir do código do tipo
e para descrever o tipo de um ativo existente.
"""

from src.modelos.banco_dados import BancoDeDados
from src.modelos.enums import TipoAtivo
from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor

CLASSE_POR_TIPO = {
    TipoAtivo.NOTEBOOK: Notebook,
    TipoAtivo.SERVIDOR: Servidor,
    TipoAtivo.ROTEADOR: Roteador,
    TipoAtivo.BANCO_DADOS: BancoDeDados,
}

TIPO_POR_CLASSE = {classe: tipo for tipo, classe in CLASSE_POR_TIPO.items()}
