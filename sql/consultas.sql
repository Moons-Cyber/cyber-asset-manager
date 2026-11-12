-- =====================================================================
-- S4_06 – JOINs  |  S4_07 – Agregações e relatórios
-- Banco: inventario.db do projeto (esquema em sql/esquema.sql)
-- Os valores variáveis aparecem como ? : o Python os envia separados do SQL.
-- =====================================================================

-- ---------------------------------------------------------------- S4_06
-- 1) INNER JOIN – cada vulnerabilidade com os ativos afetados.
--    Só aparecem pares que existem na tabela associativa.
SELECT v.id AS cve, v.severidade, a.nome AS ativo, av.status
FROM vulnerabilidades v
INNER JOIN ativo_vulnerabilidade av ON av.vuln_id = v.id
INNER JOIN ativos a                 ON a.id = av.ativo_id
ORDER BY v.severidade DESC, a.nome;

-- 2) LEFT JOIN – ativos SEM vulnerabilidade (registros sem correspondência).
--    O LEFT JOIN mantém todos os ativos; onde não há par, av.* vem NULL.
SELECT a.id, a.nome
FROM ativos a
LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id
WHERE av.ativo_id IS NULL;

-- 2b) LEFT JOIN – vulnerabilidades ainda não associadas a nenhum ativo.
SELECT v.id, v.severidade
FROM vulnerabilidades v
LEFT JOIN ativo_vulnerabilidade av ON av.vuln_id = v.id
WHERE av.vuln_id IS NULL;

-- 3) Autojunção – quem transmite o risco (origem) e quem o recebe (destino depende da origem).
--    A tabela ativos aparece duas vezes, com apelidos diferentes (o = origem, d = destino).
SELECT o.nome AS origem, d.nome AS destino_depende_dela
FROM dependencias dep
INNER JOIN ativos o ON o.id = dep.ativo_origem_id
INNER JOIN ativos d ON d.id = dep.ativo_destino_id
ORDER BY o.nome;

-- 4) Junção de 3 tabelas filtrada por parâmetro – vulnerabilidades de um ativo.
SELECT a.nome, v.id, v.severidade, av.status
FROM ativos a
INNER JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id
INNER JOIN vulnerabilidades v       ON v.id = av.vuln_id
WHERE a.id = ?;

-- 5) Subconsulta (introdutória) – ativos com ao menos uma vulnerabilidade crítica (>= 9).
SELECT nome
FROM ativos
WHERE id IN (SELECT av.ativo_id
             FROM ativo_vulnerabilidade av
             INNER JOIN vulnerabilidades v ON v.id = av.vuln_id
             WHERE v.severidade >= 9);

-- ---------------------------------------------------------------- S4_07
-- 6) COUNT + GROUP BY – quantas vulnerabilidades afetam cada ativo.
--    COUNT(av.vuln_id) ignora NULL: ativo sem vulnerabilidade dá 0 (COUNT(*) daria 1).
SELECT a.nome, COUNT(av.vuln_id) AS qtd_vulnerabilidades
FROM ativos a
LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id
GROUP BY a.id, a.nome
ORDER BY qtd_vulnerabilidades DESC;

-- 7) CASE – faixas do CVSS e quantas vulnerabilidades há em cada faixa.
SELECT CASE
         WHEN severidade >= 9.0 THEN 'Crítica'
         WHEN severidade >= 7.0 THEN 'Alta'
         WHEN severidade >= 4.0 THEN 'Média'
         ELSE 'Baixa'
       END AS faixa,
       COUNT(*) AS quantidade
FROM vulnerabilidades
GROUP BY faixa
ORDER BY MIN(severidade) DESC;

-- 8) SUM – soma das notas CVSS por ativo, ignorando as Corrigidas.
--    Corresponde a M·v (matriz de incidência × vetor das notas, S3_09);
--    o risco próprio b = F·M·v multiplica pelo fator de exposição do tipo.
--    COALESCE troca NULL por 0 (ativo sem vulnerabilidade).
SELECT a.id, a.nome, a.tipo,
       COALESCE(SUM(v.severidade), 0) AS soma_cvss
FROM ativos a
LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id AND av.status <> 'Corrigida'
LEFT JOIN vulnerabilidades v       ON v.id = av.vuln_id
GROUP BY a.id, a.nome, a.tipo
ORDER BY soma_cvss DESC;

-- 9) HAVING – só ativos cuja soma CVSS passa de um limite (?).
--    WHERE filtra linhas ANTES de agrupar; HAVING filtra os grupos DEPOIS.
SELECT a.nome, SUM(v.severidade) AS soma_cvss
FROM ativos a
INNER JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id AND av.status <> 'Corrigida'
INNER JOIN vulnerabilidades v       ON v.id = av.vuln_id
GROUP BY a.id, a.nome
HAVING SUM(v.severidade) > ?
ORDER BY soma_cvss DESC;

-- 10) Top N – os ativos de maior soma CVSS (LIMIT parametrizado).
SELECT a.nome, COALESCE(SUM(v.severidade), 0) AS soma_cvss
FROM ativos a
LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id AND av.status <> 'Corrigida'
LEFT JOIN vulnerabilidades v       ON v.id = av.vuln_id
GROUP BY a.id, a.nome
ORDER BY soma_cvss DESC
LIMIT ?;

-- 11) Estatísticas por tipo de ativo (AVG, MIN, MAX) – cobre as demais funções de agregação.
SELECT a.tipo, COUNT(DISTINCT a.id) AS ativos, AVG(v.severidade) AS media_cvss,
       MIN(v.severidade) AS menor, MAX(v.severidade) AS maior
FROM ativos a
LEFT JOIN ativo_vulnerabilidade av ON av.ativo_id = a.id
LEFT JOIN vulnerabilidades v       ON v.id = av.vuln_id
GROUP BY a.tipo;
