"""Ponto de entrada da API.

Desenvolvimento:   python servidor.py
Produção (Docker): gunicorn servidor:app   (configurado no passo do Docker)

Configuração por variáveis de ambiente:
    DADOS_DIR  pasta onde ficam ativos.json, dependencias.json e cache_cve.json
               (padrão: pasta atual; no Docker, aponte para o volume)
    HOST       endereço de escuta (padrão 127.0.0.1; no Docker use 0.0.0.0)
    PORT       porta (padrão 5000)
    NVD_API_KEY (opcional) chave gratuita do NVD, para consultas mais rápidas
    DIARIO_INTERVALO_S   segundos entre os cálculos anotados no diário
                         (padrão 3600 = 1 h; 0 anota só ao ligar; -1 desliga)
    DIARIO_MAX_ENTRADAS  máximo de entradas guardadas no diário (padrão 1000)
    PERSISTENCIA         json (padrão) ou sqlite (guarda tudo em DADOS_DIR/inventario.db)
"""

import os

from src.api.aplicacao import criar_app
from src.persistencia.fabrica_repositorios import modo_do_ambiente

_intervalo = int(os.environ.get("DIARIO_INTERVALO_S", "3600"))

app = criar_app(
    os.environ.get("DADOS_DIR", "."),
    diario_intervalo=None if _intervalo < 0 else _intervalo,
    diario_max=int(os.environ.get("DIARIO_MAX_ENTRADAS", "1000")),
    persistencia=modo_do_ambiente(),
)

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
