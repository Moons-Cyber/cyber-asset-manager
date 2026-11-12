# Banco de dados relacional (S4_06 e S4_07)

O projeto guarda os dados em **JSON** (padrão) ou em **SQLite**. A escolha é uma variável de ambiente; o
restante do sistema não percebe a troca, porque `GerenciadorAtivos` e `GerenciadorDependencias` conversam
com um *repositório* (padrão Repository) e a fábrica `criar_repositorios` entrega o certo (padrão Factory).

| | JSON (padrão) | SQLite |
|---|---|---|
| Liga com | nada | `PERSISTENCIA=sqlite` |
| Arquivos | `ativos.json`, `dependencias.json` | `inventario.db` |
| Gravação | arquivo temporário + `os.replace` | uma transação (tudo ou nada) |

## Modelo

```
ativos 1───N ativo_vulnerabilidade N───1 vulnerabilidades        dependencias: ativos N───N ativos
```

- `ativo_vulnerabilidade` é a **tabela associativa** do N:N (chave primária composta `ativo_id + vuln_id`).
  É a matriz de incidência do S3_09 guardada de forma esparsa: só as células que valem 1.
- O `status` fica nessa tabela porque pertence ao **par** (a mesma CVE pode estar Aberta num ativo e Corrigida em outro).
- `dependencias` liga dois ativos (origem → destino, com peso): o **risco da origem chega ao destino**, que passa a depender dela. É a matriz A do risco efetivo (`A[destino][origem] = peso`) e permite a autojunção.
- Chaves estrangeiras ligadas (`PRAGMA foreign_keys = ON`) e `CHECK` na nota (0–10) e no peso (0 ≤ p < 1).
- Esquema em `src/persistencia/esquema.sql` (cópia em `sql/esquema.sql`).

## Como usar

```bash
python scripts/migrar_json_para_sqlite.py              # copia os JSON para inventario.db (não altera os JSON)
PERSISTENCIA=sqlite python servidor.py                 # API usando o banco (no PowerShell: $env:PERSISTENCIA="sqlite")
python scripts/relatorio_sql.py --limite 10 --top 5    # relatório do S4_07
```

No Docker, `PERSISTENCIA=sqlite` no `.env`; o `inventario.db` fica no mesmo volume `/dados`.

## Consultas (`sql/consultas.sql` e `src/servicos/relatorios_sql.py`)

| Consulta | Técnica |
|---|---|
| Vulnerabilidade com os ativos afetados | INNER JOIN em 3 tabelas |
| Ativos sem vulnerabilidade / CVE sem ativo | LEFT JOIN + `IS NULL` |
| Origem do risco e o ativo que o recebe | autojunção (`ativos` duas vezes) |
| Faixas do CVSS | `CASE` + `GROUP BY` |
| Soma CVSS por ativo | `SUM` + `COALESCE`; equivale a **M·v** (Corrigida fica fora) |
| Ativos acima de um limite | `HAVING` (filtra grupos; `WHERE` filtra linhas) |
| Cinco maiores somas | `ORDER BY ... LIMIT ?` |

O relatório compara a soma do SQL × fator de exposição com o risco próprio calculado pelos objetos
Python (`b = F·M·v`): a coluna `confere` deve ser `ok` em todas as linhas.

Todo valor variável entra por `?`, nunca por concatenação de texto (evita SQL injection, CWE-89).

## Limitações conhecidas

- A linha da CVE é única no banco. Se o mesmo CVE tiver categoria ou nota diferentes em dois ativos
  (por exemplo "Security" e "Segurança"), vale a primeira; o script de migração avisa.
- `salvar()` regrava tudo numa transação, como o JSON. Para milhares de ativos, o próximo passo seria
  gravar só o que mudou.
