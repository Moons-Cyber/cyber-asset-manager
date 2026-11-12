"""Copia ativos.json + dependencias.json para o banco inventario.db (os JSON não são alterados).

Uso:  python scripts/migrar_json_para_sqlite.py [--pasta PASTA] [--forcar]
Depois: PERSISTENCIA=sqlite python servidor.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.persistencia.fabrica_repositorios import criar_repositorios


def migrar(pasta, forcar=False):
    origem_a, origem_d = criar_repositorios(pasta, "json")
    destino_a, destino_d = criar_repositorios(pasta, "sqlite")
    if destino_a.listar() and not forcar:
        raise SystemExit("O banco já tem ativos. Use --forcar para substituí-los pelo conteúdo dos JSON.")
    ativos, dependencias = origem_a.listar(), origem_d.listar()
    # A linha da CVE é única no banco: avisa se o mesmo CVE tem textos diferentes em ativos diferentes.
    vistas = {}
    for a in ativos:
        for v in a.vulnerabilidades:
            ref = vistas.setdefault(v.id, (v.categoria, v.severidade, a.nome))
            if ref[:2] != (v.categoria, v.severidade):
                print(f"AVISO: {v.id} tem categoria/nota diferente em '{ref[2]}' e em '{a.nome}'; "
                      f"vale a primeira ({ref[0]!r}, {ref[1]}).")
    destino_a.salvar(ativos)
    destino_d.salvar(dependencias)
    return len(ativos), len(dependencias)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pasta", default=".", help="pasta com os JSON; o banco é criado nela")
    ap.add_argument("--forcar", action="store_true")
    args = ap.parse_args()
    n_a, n_d = migrar(args.pasta, args.forcar)
    print(f"Migrados: {n_a} ativos e {n_d} dependências para {Path(args.pasta) / 'inventario.db'}")
