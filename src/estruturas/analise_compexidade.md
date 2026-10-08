# Análise de Complexidade — Estruturas Lineares

## 1. Fila com list

| Operação | Complexidade |
|---|---|
| enqueue | O(1) |
| dequeue | O(n) |
| is_empty | O(1) |

O enqueue utiliza `append()`, que normalmente possui custo O(1).

O dequeue utiliza `pop(0)`. Como o primeiro elemento é removido, os demais elementos precisam ser deslocados, resultando em custo O(n).

---

## 2. Fila com deque

| Operação | Complexidade |
|---|---|
| enqueue | O(1) |
| dequeue | O(1) |
| is_empty | O(1) |

A estrutura `deque` foi projetada para inserções e remoções eficientes nas duas extremidades.

Por isso, `append()` e `popleft()` possuem custo O(1).

---

## 3. Lista encadeada

| Operação | Complexidade |
|---|---|
| append | O(n) |
| exibir | O(n) |
| buscar | O(n) |
| remover | O(n) |

Na implementação utilizada, `append()` percorre a lista até encontrar o último nó.

As operações `buscar()` e `remover()` também podem precisar percorrer todos os nós até encontrar o elemento desejado.

---

## 4. Comparação

| Estrutura | Inserção | Remoção | Busca |
|---|---:|---:|---:|
| list | O(1)* | O(n)** | O(n) |
| Lista encadeada | O(n)*** | O(n) | O(n) |
| deque | O(1) | O(1) | — |

\* Considerando inserção no final com `append()`.

\** Considerando remoção no início com `pop(0)`.

\*** Nesta implementação, pois é necessário percorrer a lista até o último nó.

A complexidade depende da operação realizada e da implementação utilizada.

---

## 5. Conclusão

A escolha da estrutura de dados deve considerar o tipo de operação que será realizada com maior frequência.

A `deque` é mais adequada para implementar filas porque permite remoção eficiente no início da estrutura.

A lista encadeada demonstra como os elementos podem ser organizados por meio de nós conectados, permitindo compreender o funcionamento de estruturas dinâmicas.