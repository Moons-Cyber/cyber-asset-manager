"""Ponto de entrada da API.

Desenvolvimento:   python servidor.py
Produção (Docker): gunicorn servidor:app   (configurado no passo do Docker)

Configuração por variáveis de ambiente:
    DADOS_DIR  pasta onde ficam ativos.json, dependencias.json e cache_cve.json
               (padrão: pasta atual; no Docker, aponte para o volume)
    HOST       endereço de escuta (padrão 127.0.0.1; no Docker use 0.0.0.0)
    PORT       porta (padrão 5000)
    NVD_API_KEY (opcional) chave gratuita do NVD, para consultas mais rápidas
"""

import os

from src.api.aplicacao import criar_app

app = criar_app(os.environ.get("DADOS_DIR", "."))

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
