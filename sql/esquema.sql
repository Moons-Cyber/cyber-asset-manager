-- Esquema relacional do inventário (S4_06). Equivale ao ativos.json + dependencias.json.
-- Cada instrução é idempotente (IF NOT EXISTS): rodar duas vezes não quebra nada.

CREATE TABLE IF NOT EXISTS ativos (
    id            INTEGER PRIMARY KEY,
    tipo          TEXT NOT NULL,          -- Notebook, Servidor, Roteador, BancoDeDados
    nome          TEXT NOT NULL,
    responsavel   TEXT NOT NULL,
    setor         TEXT NOT NULL,
    campo_extra   TEXT NOT NULL           -- valor do campo próprio do tipo (RAM, processador, modelo, SGBD)
);

CREATE TABLE IF NOT EXISTS vulnerabilidades (
    id                 TEXT PRIMARY KEY,  -- CVE-AAAA-NNNN ou LOCAL-xxxxxxxx
    descricao          TEXT NOT NULL,
    categoria          TEXT NOT NULL,
    severidade         REAL NOT NULL CHECK (severidade BETWEEN 0 AND 10),   -- nota CVSS
    fonte              TEXT NOT NULL,
    descricao_original TEXT
);

-- Tabela associativa N:N. O status pertence ao PAR (a mesma CVE pode estar
-- "Aberta" num ativo e "Corrigida" em outro). 'posicao' preserva a ordem da lista.
CREATE TABLE IF NOT EXISTS ativo_vulnerabilidade (
    ativo_id  INTEGER NOT NULL REFERENCES ativos(id),
    vuln_id   TEXT    NOT NULL REFERENCES vulnerabilidades(id),
    status    TEXT    NOT NULL,
    posicao   INTEGER NOT NULL,
    PRIMARY KEY (ativo_id, vuln_id)
);

-- Dependência entre ativos (alimenta a matriz A do risco efetivo).
CREATE TABLE IF NOT EXISTS dependencias (
    ativo_origem_id  INTEGER NOT NULL REFERENCES ativos(id),
    ativo_destino_id INTEGER NOT NULL REFERENCES ativos(id),
    peso             REAL    NOT NULL CHECK (peso >= 0 AND peso < 1),
    PRIMARY KEY (ativo_origem_id, ativo_destino_id),
    CHECK (ativo_origem_id <> ativo_destino_id)
);
