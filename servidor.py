
import os

from src.api.aplicacao import criar_app

app = criar_app(os.environ.get("DADOS_DIR", "."))

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )