# API REST do Inventário de Ativos de TI

Documentação dos recursos REST do Trabalho 2. A API cadastra ativos de TI, suas vulnerabilidades e as
dependências entre eles, e calcula o risco efetivo de cada ativo resolvendo `(I − A)x = b`.

- **Base URL:** `http://HOST:PORTA` (local: `http://127.0.0.1:5000`; no container, a porta definida no `.env`).
- **Formato:** JSON em UTF-8. Nas requisições com corpo, envie `Content-Type: application/json`.
- **Autenticação:** nenhuma (limitação conhecida, ver o fim deste documento).
- **IDs de ativo:** inteiros positivos, escolhidos por quem cadastra.

## Convenções

### Códigos de status

| Código | Significado | Quando acontece |
|---|---|---|
| 200 OK | sucesso | leitura, alteração ou remoção |
| 201 Created | recurso criado | `POST` de ativo, vulnerabilidade ou dependência (com header `Location` no caso de ativo) |
| 400 Bad Request | entrada inválida | JSON quebrado, campo faltando ou do tipo errado, nota fora de 0–10, peso inválido |
| 404 Not Found | não existe | ativo, vulnerabilidade, dependência ou rota |
| 405 Method Not Allowed | método não aceito na rota | `DELETE /api/saude`, por exemplo |
| 409 Conflict | conflito com o estado atual | ID de ativo repetido; vulnerabilidade já cadastrada no ativo |
| 422 Unprocessable Entity | pedido correto, mas os dados guardados impedem o cálculo | matriz `I − A` singular ou mal condicionada em `/api/risco` e `/api/risco/passos` |
| 500 Internal Server Error | erro inesperado | sem detalhes técnicos no corpo; o traceback vai só para o log |
| 503 Service Unavailable | dependência indisponível | arquivos de dados ilegíveis, ou NVD fora do ar |

### Formato de erro

Todo erro devolve JSON com a mensagem, e algumas respostas trazem uma dica:

```json
{"erro": "O campo 'nome' é obrigatório."}
```

As mensagens de rota inexistente (404) e de método não permitido (405) vêm do framework, em inglês.

### Tipos de ativo (polimorfismo)

Cada tipo tem um **campo específico** obrigatório e um **fator de exposição** que multiplica o risco próprio.

| `tipo` | Nome | Campo específico | Fator de exposição |
|---|---|---|---|
| 1 | Notebook | `memoria_ram` (ex.: `"8GB"`) | 1,0 |
| 2 | Servidor | `processador` | 1,5 |
| 3 | Roteador | `modelo` | 1,2 |
| 4 | Banco de dados | `sgbd` | 1,0 |

### Status e classificação de vulnerabilidades

- Status: `Aberta`, `Em tratamento`, `Corrigida`, `Risco aceito`. Só `Corrigida` deixa de contar no risco.
- Classificação pela nota (tabela CVSS): 0–3,9 Baixa · 4,0–6,9 Média · 7,0–8,9 Alta · 9,0–10 Crítica.

---

## Geral

### `GET /api/saude`
Verifica se o serviço responde. Usado pelo `HEALTHCHECK` do Docker.
- **200:** `{"status": "ok", "ativos": 2}`
- **503:** `{"status": "erro", "detalhe": "..."}` se os arquivos de dados estiverem ilegíveis.

### `GET /api/tipos`
Lista os tipos de ativo. **200:**
```json
[{"codigo": 1, "nome": "Notebook", "campo": "memoria_ram", "rotulo_campo": "Memória RAM"}, "..."]
```

### `GET /api/status`
Lista os status de vulnerabilidade. **200:** `["Aberta", "Em tratamento", "Corrigida", "Risco aceito"]`

---

## Ativos

### `GET /api/ativos`
Lista os ativos.

| Parâmetro (query) | Efeito |
|---|---|
| `q` | filtra pelo nome (contém o texto, sem diferenciar maiúsculas) |
| `tipo` | filtra pelo código do tipo (1 a 4); valor inválido dá **400** |
| `ordem` | ordena pelo critério: `nome`, `id`, `setor`, `responsavel` ou `falhas` (padrão Strategy); inválido dá **400** |
| `sentido` | `asc` (padrão) ou `desc`; só vale junto com `ordem` |

### `POST /api/ativos`
Cria um ativo.

```json
{"id": 1, "tipo": 1, "nome": "Notebook RH", "responsavel": "Ana", "setor": "RH", "memoria_ram": "8GB"}
```

- **201** com o ativo e o header `Location: /api/ativos/1`.
- **400** campo obrigatório ausente, tipo inexistente, `id` que não é inteiro (booleano é recusado), corpo que não é JSON.
- **409** já existe ativo com esse ID.

Resposta (201):
```json
{"id": 1, "tipo": "Notebook", "nome": "Notebook RH", "responsavel": "Ana", "setor": "RH",
 "vulnerabilidades": [], "memoria_ram": "8GB", "tipo_codigo": 1, "tipo_nome": "Notebook",
 "campo_especifico": "memoria_ram", "rotulo_campo": "Memória RAM", "valor_campo": "8GB"}
```

### `GET /api/ativos/{id}`
Devolve um ativo. **200**, ou **404** se não existir.

### `PATCH /api/ativos/{id}`
Altera **só os campos enviados**. Permitidos: `nome`, `responsavel`, `setor` e o campo específico do tipo.
O `id` e o tipo nunca mudam (por isso a API usa `PATCH`, e não `PUT`).
- **200** com o ativo atualizado.
- **400** campo não permitido, corpo vazio ou valor inválido. **404** ativo inexistente.

```json
{"nome": "Notebook RH (alterado)", "setor": "Financeiro"}
```

### `DELETE /api/ativos/{id}`
Remove o ativo **e as dependências em que ele aparece**. **200:** `{"removido": 2, "dependencias_removidas": 1}`. **404** se não existir.

---

## Vulnerabilidades (recurso aninhado em um ativo)

### `GET /api/ativos/{id}/vulnerabilidades`
Lista as vulnerabilidades do ativo. **200**, ou **404** se o ativo não existir.

### `POST /api/ativos/{id}/vulnerabilidades`
Adiciona uma vulnerabilidade, de dois jeitos:

**Manual** (informa a nota):
```json
{"descricao": "Sistema sem atualizacao", "categoria": "Sistema", "severidade": 8.0}
```
**Por CVE** (sem `severidade`, a API consulta a nota e a descrição reais no NVD; se você enviar `severidade`, o NVD não é consultado e `descricao` passa a ser obrigatória):
```json
{"cve": "CVE-2021-44228", "categoria": "Aplicação"}
```
O campo opcional `status` (padrão `Aberta`) também é aceito.

- **201** com a vulnerabilidade:
```json
{"id": "LOCAL-12b58e0c", "descricao": "Sistema sem atualizacao", "categoria": "Sistema", "severidade": 8.0,
 "status": "Aberta", "fonte": "manual", "descricao_curta": "Sistema sem atualizacao",
 "classificacao": "Alta", "afeta_risco": true}
```
- **400** nota fora de 0–10, sem nota e sem CVE, formato de CVE inválido (`CVE-AAAA-NNNN`).
- **404** ativo ou CVE inexistente. **409** o ativo já possui essa vulnerabilidade.
- **503** NVD indisponível (a resposta traz uma `dica`: envie `severidade` manualmente).

Sem CVE, o ID da vulnerabilidade é `LOCAL-` + um código calculado a partir de descrição e categoria; com CVE, é o próprio CVE.

### `PATCH /api/ativos/{id}/vulnerabilidades/{id_vulnerabilidade}`
Altera **somente o status**.
```json
{"status": "Corrigida"}
```
- **200** com a vulnerabilidade (`afeta_risco` passa a `false` se `Corrigida`).
- **400** status inválido ou outro campo no corpo. **404** ativo ou vulnerabilidade inexistente.

### `GET /api/ativos/{id}/vulnerabilidades/{id_vulnerabilidade}/orientacao`
O que é a falha, por que é perigosa e como prevenir. É o que o Assistente de Segurança da interface mostra.
Só lê; não altera nada.

O tipo é reconhecido por palavras-chave (em português ou em inglês) na categoria, depois na descrição e,
por último, no texto original do NVD. São 15 tipos, cada um com a referência CWE; se nenhum combina,
a resposta traz uma orientação genérica (`"tipo": "generica"`).

```json
{"ativo": {"id": 3, "nome": "Roteador central", "tipo": "Roteador"},
 "vulnerabilidade": {"id": "LOCAL-8f4739d3", "categoria": "Senha padrão", "severidade": 8.1, "status": "Aberta", "...": "..."},
 "tipo": "credenciais", "titulo": "Senha padrão, fraca ou escrita no código", "cwe": "CWE-798",
 "reconhecido_por": "categoria", "termo": "senha",
 "o_que_e": "...", "por_que_perigoso": "...",
 "como_prevenir": ["Trocar todas as senhas de fábrica na instalação.", "..."],
 "como_corrigir_agora": ["Trocar a senha agora, por uma longa e única.", "..."],
 "neste_ativo": "O roteador é a porta de entrada da rede (fator 1,2). ...",
 "gravidade": "Alta (7,0 a 8,9): corrigir em poucos dias.",
 "situacao": "Está aberta: ainda conta no cálculo do risco.",
 "efeito_no_risco": {"conta_no_risco": true, "fator": 1.2, "risco_proprio_atual": 9.72, "reducao": 9.72,
                     "risco_proprio_sem_ela": 0.0, "risco_efetivo_atual": 9.72,
                     "passa_risco_para": ["Notebook Ana", "Servidor de arquivos"]}}
```
- `efeito_no_risco.reducao` = fator de exposição × nota: quanto o risco próprio do ativo cai se a falha for corrigida
  (0 se ela já estiver corrigida). Vem `null` se o risco não puder ser calculado com os dados atuais.
- **404** se o ativo ou a vulnerabilidade não existir.

### `GET /api/cve/{cve}`
Prévia da nota de um CVE no NVD, sem cadastrar nada. **200** com `id`, `severidade`, `versao_cvss`,
`descricao_curta` e `descricao_original`; **400** formato inválido; **404** CVE inexistente; **503** NVD fora do ar.

---

## Dependências

Uma dependência é uma aresta do grafo: **o risco da origem chega ao destino multiplicado pelo `peso`**.
Regras: `0 ≤ peso < 1`, origem diferente do destino, e a **soma dos pesos recebidos por um mesmo ativo deve ser menor que 1**
(isso garante que `I − A` seja invertível).

### `GET /api/dependencias`
**200:**
```json
[{"ativo_origem_id": 1, "ativo_destino_id": 2, "peso": 0.5,
  "origem_nome": "Notebook RH", "destino_nome": "Banco de clientes"}]
```

### `POST /api/dependencias`
```json
{"origem": 1, "destino": 2, "peso": 0.5}
```
- **201** com `{"ativo_origem_id": 1, "ativo_destino_id": 2, "peso": 0.5}`.
- **400** ativo inexistente, dependência repetida, ativo dependendo de si mesmo, peso fora da faixa ou soma dos pesos recebidos ≥ 1.

### `DELETE /api/dependencias/{origem}/{destino}`
**200:** `{"removida": {"origem": 1, "destino": 2}}`. **404** se não existir.

---

## Risco

### `GET /api/risco`
Resolve `(I − A)x = b` e devolve o risco próprio e o efetivo de cada ativo, com o diagnóstico da matriz.

```json
{"resultados": [
   {"id": 1, "nome": "Notebook RH", "risco_proprio": 8.0, "fator_exposicao": 1.0, "risco_efetivo": 8.0},
   {"id": 2, "nome": "Banco de clientes", "risco_proprio": 0.0, "fator_exposicao": 1.0, "risco_efetivo": 4.0}],
 "diagnostico": {"ordem": 2, "posto": 2, "determinante": 1.0, "condicao": 1.64, "invertivel": true, "fragil": false}}
```
- `risco_proprio` = fator de exposição × soma das notas das vulnerabilidades que afetam o risco.
- `risco_efetivo` = risco próprio + risco que chega pelas dependências.
- Se a matriz `I − A` for singular, a resposta é **422** com a mensagem de erro; `fragil: true` avisa que o número de condição está alto (restam poucos dígitos de precisão).

---

### `GET /api/risco/passos`
As mesmas contas de `/api/risco`, etapa por etapa, com os números. É o que o Assistente da interface usa para explicar o cálculo. A janela **Matrizes e Gráfico** também usa esta rota: desenha `A`, `I_menos_A`, `b` e `x` como mapa de calor e barras.

| Campo | O que é |
|---|---|
| `ativos` | `id`, `nome`, `tipo` e `fator` de exposição, na ordem das linhas das matrizes |
| `vulnerabilidades` | as falhas abertas, na ordem das colunas de `M` |
| `M`, `v` | matriz de incidência (ativos × falhas) e vetor das notas |
| `Mv`, `b` | soma das notas de cada ativo e risco próprio `b = F · Mv` |
| `A`, `somas_recebidas` | matriz de dependências (linha recebe da coluna) e a soma de cada linha |
| `I_menos_A`, `diagnostico` | a matriz do sistema e o diagnóstico (posto, determinante, condição, invertível) |
| `x`, `residuo`, `risco_global` | a solução, a maior diferença ao conferir `(I − A)x = b` e a soma dos `x` |

Se `I − A` não for invertível, a resposta é **200** com `x: null` (o diagnóstico explica o motivo).
**422** quando os dados guardados são inconsistentes (por exemplo, dependência para um ativo que não existe).

### `GET /api/diario`
Histórico gravado pelo servidor para o teste de 24 horas: uma entrada por hora com `t`, `motivo`, `ativos`,
`dependencias`, `risco_global`, `invertivel`, `condicao` e `erro`. **200** com `intervalo_s`, `agora` e `entradas`;
**404** se o diário estiver desligado no servidor.

---

## Interface web

### `GET /aero`
A interface (desktop no estilo Windows XP). Os arquivos estáticos ficam em `/aero/{arquivo}`; só os da lista
permitida são servidos, qualquer outro nome dá **404**.

---

## Exemplo de fluxo completo

```bash
B=http://127.0.0.1:5000; H='Content-Type: application/json'
curl -X POST $B/api/ativos -H "$H" -d '{"id":1,"tipo":1,"nome":"Notebook RH","responsavel":"Ana","setor":"RH","memoria_ram":"8GB"}'
curl -X POST $B/api/ativos -H "$H" -d '{"id":2,"tipo":4,"nome":"Banco de clientes","responsavel":"Bruno","setor":"TI","sgbd":"PostgreSQL"}'
curl -X POST $B/api/ativos/1/vulnerabilidades -H "$H" -d '{"descricao":"Sistema sem atualizacao","categoria":"Sistema","severidade":8.0}'
curl -X POST $B/api/dependencias -H "$H" -d '{"origem":1,"destino":2,"peso":0.5}'
curl $B/api/risco        # notebook: 8,0 | banco: 0,5 × 8,0 = 4,0
```

## Limitações e melhorias futuras

- Sem autenticação (não há 401/403) e sem HTTPS: a porta do container fica presa a `127.0.0.1`.
- Listas sem paginação e sem versionamento de rota (`/api/v1/...`).
- Alteração de ativo só por `PATCH`; `PUT` (substituição completa) não foi implementado porque o `id` e o tipo são imutáveis.
- O 405 não envia o header `Allow` com os métodos aceitos (o handler de erros genérico descarta os headers do framework).
- Mensagens de 404 de rota e 405 vêm em inglês, do Flask.
