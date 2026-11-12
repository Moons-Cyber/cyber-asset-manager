"""Gera o relatório do S4_07 a partir do banco do projeto (imprime e grava relatorio_sql.txt).

Uso:  python scripts/relatorio_sql.py [--pasta PASTA] [--limite 10] [--top 5]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.persistencia.fabrica_repositorios import NOME_BANCO
from src.servicos.relatorios_sql import gerar_relatorio

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pasta", default=".")
    ap.add_argument("--limite", type=float, default=10.0, help="limite de soma CVSS do HAVING")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    banco = Path(args.pasta) / NOME_BANCO
    if not banco.exists():
        raise SystemExit(f"Banco não encontrado: {banco}. Rode antes scripts/migrar_json_para_sqlite.py")
    texto = gerar_relatorio(banco, args.limite, args.top)
    print(texto)
    (Path(args.pasta) / "relatorio_sql.txt").write_text(texto, encoding="utf-8")
