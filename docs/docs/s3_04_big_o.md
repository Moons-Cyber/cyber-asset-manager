# S3_04 — Análise de Complexidade e Notação Big-O

## 1. Introdução

A notação Big-O representa como o custo de um algoritmo cresce conforme aumenta a quantidade de dados processados.

Esse custo pode representar o tempo de execução ou o uso de memória. A análise permite comparar algoritmos e escolher soluções que continuem eficientes com conjuntos maiores de dados.

## 2. Principais classes de complexidade

| Complexidade | Nome | Exemplo típico |
|---|---|---|
| O(1) | Constante | Acessar um elemento de uma lista por índice |
| O(log n) | Logarítmica | Busca binária em dados ordenados |
| O(n) | Linear | Percorrer uma lista para encontrar um elemento |
| O(n log n) | Linearítmica | Ordenação por merge sort |
| O(n²) | Quadrática | Comparar todos os pares de elementos |
| O(2ⁿ) | Exponencial | Algoritmo que explora combinações de subconjuntos |

A complexidade O(1) tende a manter seu custo independentemente do tamanho da entrada. Já algoritmos exponenciais podem se tornar inviáveis rapidamente conforme o número de elementos cresce.

## 3. Melhor caso, caso médio e pior caso

**Melhor caso:** situação em que o algoritmo realiza menos trabalho para determinada entrada.

**Caso médio:** custo esperado considerando diferentes entradas possíveis e as hipóteses adotadas sobre sua distribuição.

**Pior caso:** situação em que o algoritmo realiza o maior trabalho possível para entradas de um determinado tamanho.

Por exemplo, em uma busca linear, encontrar o elemento na primeira posição exige apenas uma verificação. Encontrá-lo na última posição, ou descobrir que ele não existe, pode exigir a verificação de todos os elementos.

Assim, a busca linear apresenta melhor caso O(1) e pior caso O(n).

## 4. Análise das estruturas utilizadas na S3_03

| Estrutura ou operação | Complexidade | Justificativa |
|---|---|---|
| `list.append()` | O(1) amortizado | Adiciona um elemento ao final da lista; ocasionalmente pode ocorrer realocação |
| `list.pop(0)` | O(n) | A remoção do primeiro elemento exige deslocar os elementos restantes |
| `deque.append()` | O(1) | Adiciona um elemento ao final da fila de forma eficiente |
| `deque.popleft()` | O(1) | Remove eficientemente o primeiro elemento |
| Busca na lista encadeada | O(n) | Pode ser necessário percorrer todos os nós |
| Inserção no final da lista encadeada implementada | O(n) | A implementação percorre os nós porque não mantém uma referência ao último nó |
| Exibição da lista encadeada | O(n) | Cada nó é visitado uma vez |

As complexidades apresentadas consideram as implementações desenvolvidas no card e o comportamento usual das estruturas do Python.

## 5. Aplicação ao projeto de inventário

No sistema de inventário de ativos, diferentes operações apresentam custos distintos.

- **Busca linear:** percorrer os ativos até encontrar aquele que possui o ID solicitado custa O(n) no pior caso.
- **Busca por ID em um dicionário:** normalmente custa O(1) em média, sendo uma alternativa eficiente para consultas por identificador.
- **Filtragem de ativos:** percorrer todos os ativos para selecionar os que atendem a um critério custa O(n).
- **Ordenação de ativos:** a ordenação por nome com `sorted()` tem custo O(n log n) no pior caso.
- **Contagem de vulnerabilidades:** percorrer os ativos e somar as quantidades de vulnerabilidades possui custo linear no número de ativos e nas vulnerabilidades examinadas.

Essas análises ajudam a justificar a escolha das estruturas e operações, de acordo com as necessidades do inventário.

## 6. Comparação de escalabilidade

Considere o crescimento aproximado do trabalho quando a quantidade de elementos dobra:

| Complexidade | Crescimento aproximado |
|---|---|
| O(1) | Mantém o mesmo custo |
| O(log n) | Aumenta pouco |
| O(n) | Dobra |
| O(n log n) | Cresce um pouco mais que o dobro |
| O(n²) | Quadruplica |
| O(2ⁿ) | Quadruplica a cada aumento de uma unidade de n, em comparação com o valor anterior |

Essa comparação evidencia por que algoritmos quadráticos e exponenciais podem apresentar problemas de desempenho à medida que o volume de dados cresce.

## 7. Conclusão

A análise Big-O ajuda a compreender como algoritmos e estruturas de dados se comportam em diferentes escalas. No inventário, escolher um dicionário para buscas por ID e uma fila baseada em `deque` para remoções no início pode evitar trabalho desnecessário.

A melhor estrutura depende da operação mais frequente, do volume de dados e dos requisitos da aplicação. A complexidade assintótica é uma ferramenta de comparação, mas não substitui testes de desempenho em condições reais.