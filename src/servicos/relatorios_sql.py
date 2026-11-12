"""S4_06/S4_07: consultas relacionais do inventário, sempre parametrizadas ('?').

Recebe o caminho do banco SQLite (o mesmo que RepositorioAtivosSqlite usa).
Cada função é uma consulta comentada; gerar_relatorio() junta todas num texto.
"""

import sqlite3
from contextlib import closing

from src.persistencia.repositorio_sqlite import RepositorioAtivosSqlite, abrir_banco

SQL = {
    # INNER JOIN: só os pares que existem na tabela associativa.
    "vulnerabilidades_x_ativos": """
        SELECT v.id AS cve, v.severidade, a.nome AS ativo, av.status
        FROM vulnerabilidades v
        INNER JOIN ativo_vulnerabilidade av ON av.vuln_id = v.id
        INNER JOIN ativos a                 ON a.id = av.ativo_id
        ORDER BY v.severidade DESC, a.nome""",
    # LEFT JOIN + IS NULL: registros SEM correspondência.
    "ativos_sem_vulnerabilidade": """
        SELECT a.id, a.nome
        FROM ativos a
        LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id
        WHERE av.ativo_id IS NULL""",
    # Autojunção: a tabela ativos entra duas vezes (o = origem, que transmite o risco; d = destino, que depende dela).
    "dependencias": """
        SELECT o.nome AS origem, d.nome AS destino_depende_dela, dep.peso
        FROM dependencias dep
        INNER JOIN ativos o ON o.id = dep.ativo_origem_id
        INNER JOIN ativos d ON d.id = dep.ativo_destino_id
        ORDER BY o.nome""",
    # CASE: faixas do CVSS e contagem por faixa.
    "faixas_cvss": """
        SELECT CASE WHEN severidade >= 9.0 THEN 'Crítica'
                    WHEN severidade >= 7.0 THEN 'Alta'
                    WHEN severidade >= 4.0 THEN 'Média'
                    ELSE 'Baixa' END AS faixa,
               COUNT(*) AS quantidade
        FROM vulnerabilidades
        GROUP BY faixa
        ORDER BY MIN(severidade) DESC""",
    # SUM por ativo = M·v (matriz de incidência × notas); Corrigida não entra, como no modelo.
    # COUNT(coluna) ignora NULL; COALESCE troca o NULL da soma de quem não tem vulnerabilidade por 0.
    "soma_cvss_por_ativo": """
        SELECT a.id, a.nome, a.tipo,
               COUNT(v.id) AS vulnerabilidades_ativas,
               COALESCE(SUM(v.severidade), 0) AS soma_cvss
        FROM ativos a
        LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id AND av.status <> 'Corrigida'
        LEFT JOIN vulnerabilidades v       ON v.id = av.vuln_id
        GROUP BY a.id, a.nome, a.tipo
        ORDER BY soma_cvss DESC, a.id""",
    # HAVING filtra GRUPOS (depois de somar); WHERE filtra linhas (antes).
    "acima_do_limite": """
        SELECT a.nome, SUM(v.severidade) AS soma_cvss
        FROM ativos a
        INNER JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id AND av.status <> 'Corrigida'
        INNER JOIN vulnerabilidades v       ON v.id = av.vuln_id
        GROUP BY a.id, a.nome
        HAVING SUM(v.severidade) > ?
        ORDER BY soma_cvss DESC""",
    "top_ativos": """
        SELECT a.nome, COALESCE(SUM(v.severidade), 0) AS soma_cvss
        FROM ativos a
        LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id AND av.status <> 'Corrigida'
        LEFT JOIN vulnerabilidades v       ON v.id = av.vuln_id
        GROUP BY a.id, a.nome
        ORDER BY soma_cvss DESC, a.id
        LIMIT ?""",
    "vulnerabilidades_do_ativo": """
        SELECT a.nome, v.id, v.severidade, av.status
        FROM ativos a
        INNER JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id
        INNER JOIN vulnerabilidades v       ON v.id = av.vuln_id
        WHERE a.id = ?
        ORDER BY av.posicao""",
    "estatisticas_por_tipo": """
        SELECT a.tipo, COUNT(DISTINCT a.id) AS ativos, COUNT(v.id) AS vulnerabilidades,
               ROUND(AVG(v.severidade), 2) AS media_cvss, MIN(v.severidade) AS menor, MAX(v.severidade) AS maior
        FROM ativos a
        LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id
        LEFT JOIN vulnerabilidades v       ON v.id = av.vuln_id
        GROUP BY a.tipo
        ORDER BY a.tipo""",
}


def consultar(caminho_banco, nome, parametros=()):
    """Roda uma das consultas de SQL[nome] e devolve (colunas, linhas)."""
    with closing(abrir_banco(caminho_banco)) as con:
        cur = con.execute(SQL[nome], parametros)
        return [c[0] for c in cur.description], cur.fetchall()


def risco_proprio_em_python(caminho_banco):
    """b = F·(M·v) calculado pelos OBJETOS do projeto, para comparar com o SUM do SQL."""
    return {a.id: sum(v.severidade for v in a.vulnerabilidades if v.afeta_risco) * a.obter_fator_exposicao()
            for a in RepositorioAtivosSqlite(caminho_banco).listar()}


def _tabela(titulo, colunas, linhas):
    larg = [max(len(str(x)) for x in [c] + [l[i] for l in linhas]) for i, c in enumerate(colunas)]
    fmt = lambda l: " | ".join(str(x).ljust(w) for x, w in zip(l, larg))
    saida = [f"\n== {titulo}", fmt(colunas), "-+-".join("-" * w for w in larg)]
    saida += [fmt(l) for l in linhas] or ["(nenhum registro)"]
    return "\n".join(saida)


def gerar_relatorio(caminho_banco, limite=10.0, n=5):
    p = []
    p.append(_tabela("Vulnerabilidades x ativos (INNER JOIN)", *consultar(caminho_banco, "vulnerabilidades_x_ativos")))
    p.append(_tabela("Ativos sem vulnerabilidade (LEFT JOIN)", *consultar(caminho_banco, "ativos_sem_vulnerabilidade")))
    p.append(_tabela("Dependências entre ativos (autojunção)", *consultar(caminho_banco, "dependencias")))
    p.append(_tabela("Faixas do CVSS (CASE)", *consultar(caminho_banco, "faixas_cvss")))
    p.append(_tabela("Por tipo de ativo (COUNT, AVG, MIN, MAX)", *consultar(caminho_banco, "estatisticas_por_tipo")))
    colunas, linhas = consultar(caminho_banco, "soma_cvss_por_ativo")
    esperado = risco_proprio_em_python(caminho_banco)
    fatores = {a.id: a.obter_fator_exposicao() for a in RepositorioAtivosSqlite(caminho_banco).listar()}
    comparacao = [(i, nome, tipo, soma, round(soma * fatores[i], 2), round(esperado[i], 2),
                   "ok" if abs(soma * fatores[i] - esperado[i]) < 1e-9 else "DIFERENTE")
                  for i, nome, tipo, _, soma in linhas]
    p.append(_tabela("Soma CVSS (SQL) x risco próprio b = F·(M·v) calculado em Python",
                     ["id", "ativo", "tipo", "soma_cvss", "b (SQL x F)", "b (Python)", "confere"], comparacao))
    p.append(_tabela(f"Ativos com soma CVSS > {limite} (HAVING)", *consultar(caminho_banco, "acima_do_limite", (limite,))))
    p.append(_tabela(f"Top {n} ativos por soma CVSS", *consultar(caminho_banco, "top_ativos", (n,))))
    return "\n".join(p) + "\n"
