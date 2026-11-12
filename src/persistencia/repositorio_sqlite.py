"""Repositórios em SQLite (S4_06): mesma interface do JSON, outro lugar para guardar.

GerenciadorAtivos e GerenciadorDependencias não percebem a troca: continuam
chamando listar() e salvar(). Duas decisões de projeto:

* Cada salvar() é UMA transação (apaga tudo e regrava): ou o banco fica com o
  conteúdo novo inteiro, ou com o antigo inteiro. É o equivalente, no SQL, da
  gravação atômica do JSON (arquivo temporário + os.replace).
* Todo valor entra na instrução por marcador '?', nunca concatenado ao texto.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

from src.modelos.vulnerabilidades import Vulnerabilidade
from src.modelos.dependencia import Dependencia
from src.persistencia.erros import ErroDados
from src.persistencia.fabrica_ativos import FabricaAtivos
from src.persistencia.repositorio import RepositorioAtivos, RepositorioDependencias

ESQUEMA = Path(__file__).with_name("esquema.sql")


def abrir_banco(caminho):
    """Abre (e cria, se preciso) o banco com as chaves estrangeiras ligadas."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho, timeout=10)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(ESQUEMA.read_text(encoding="utf-8"))
    except BaseException:
        # Se o arquivo não for um banco (ou o esquema falhar), fecha antes de propagar o erro:
        # no Windows, uma conexão esquecida aberta trava o arquivo (WinError 32).
        con.close()
        raise
    return con


class RepositorioAtivosSqlite(RepositorioAtivos):
    def __init__(self, caminho):
        self.caminho = Path(caminho)

    def listar(self):
        try:
            with closing(abrir_banco(self.caminho)) as con:
                vulns = {}
                for ativo_id, vid, desc, cat, sev, fonte, orig, status in con.execute(
                    """SELECT av.ativo_id, v.id, v.descricao, v.categoria, v.severidade,
                              v.fonte, v.descricao_original, av.status
                       FROM ativo_vulnerabilidade av
                       INNER JOIN vulnerabilidades v ON v.id = av.vuln_id
                       ORDER BY av.ativo_id, av.posicao"""):
                    vulns.setdefault(ativo_id, []).append({
                        "id": vid, "descricao": desc, "categoria": cat, "severidade": sev,
                        "status": status, "fonte": fonte, "descricao_original": orig})
                ativos = []
                for id_, tipo, nome, resp, setor, extra in con.execute(
                        "SELECT id, tipo, nome, responsavel, setor, campo_extra FROM ativos ORDER BY id"):
                    classe = FabricaAtivos.TIPOS.get(tipo)
                    if classe is None:
                        raise ErroDados(f"Tipo de ativo desconhecido no banco: {tipo!r}")
                    ativos.append(FabricaAtivos.reconstruir({
                        "id": id_, "tipo": tipo, "nome": nome, "responsavel": resp, "setor": setor,
                        "vulnerabilidades": vulns.get(id_, []), classe.campo_especifico: extra}))
                return ativos
        except sqlite3.Error as erro:
            raise ErroDados(f"Banco '{self.caminho}' ilegível: {erro}") from erro

    def salvar(self, ativos):
        # Serializa antes de abrir o banco: se algo falhar, nada é tocado.
        registros = [a.para_dict() for a in ativos]
        try:
            with closing(abrir_banco(self.caminho)) as con:
                with con:   # transação: commit se tudo der certo, rollback se der erro
                    # As dependências apontam para ativos; a checagem das chaves
                    # só vale no commit, depois de regravar todos os ativos.
                    con.execute("PRAGMA defer_foreign_keys = ON")
                    con.execute("DELETE FROM ativo_vulnerabilidade")
                    con.execute("DELETE FROM ativos")
                    for r in registros:
                        classe = FabricaAtivos.TIPOS[r["tipo"]]
                        con.execute("INSERT INTO ativos VALUES (?,?,?,?,?,?)",
                                    (r["id"], r["tipo"], r["nome"], r["responsavel"], r["setor"],
                                     str(r[classe.campo_especifico])))
                        for pos, v in enumerate(r["vulnerabilidades"]):
                            # A mesma CVE pode estar em vários ativos: a linha da CVE é
                            # única (a primeira a chegar vale); o status é de cada par.
                            con.execute("INSERT OR IGNORE INTO vulnerabilidades VALUES (?,?,?,?,?,?)",
                                        (v["id"], v["descricao"], v["categoria"], v["severidade"],
                                         v.get("fonte", "manual"), v.get("descricao_original")))
                            con.execute("INSERT INTO ativo_vulnerabilidade VALUES (?,?,?,?)",
                                        (r["id"], v["id"], v["status"], pos))
                    con.execute("""DELETE FROM vulnerabilidades WHERE id NOT IN
                                   (SELECT vuln_id FROM ativo_vulnerabilidade)""")
        except sqlite3.Error as erro:
            raise ErroDados(f"Não foi possível gravar no banco '{self.caminho}': {erro}") from erro


class RepositorioDependenciasSqlite(RepositorioDependencias):
    def __init__(self, caminho):
        self.caminho = Path(caminho)

    def listar(self):
        try:
            with closing(abrir_banco(self.caminho)) as con:
                linhas = con.execute(
                    "SELECT ativo_origem_id, ativo_destino_id, peso FROM dependencias ORDER BY rowid").fetchall()
            return [Dependencia(o, d, p) for o, d, p in linhas]
        except (sqlite3.Error, ValueError) as erro:
            raise ErroDados(f"Banco '{self.caminho}' inválido: {erro}") from erro

    def salvar(self, dependencias):
        dados = [(d.ativo_origem_id, d.ativo_destino_id, d.peso) for d in dependencias]
        try:
            with closing(abrir_banco(self.caminho)) as con:
                with con:
                    con.execute("DELETE FROM dependencias")
                    con.executemany("INSERT INTO dependencias VALUES (?,?,?)", dados)
        except sqlite3.Error as erro:
            raise ErroDados(f"Não foi possível gravar no banco '{self.caminho}': {erro}") from erro
