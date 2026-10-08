# S3_05 — Algoritmos de Busca e Ordenação

## 1. Objetivo

Implementar e comparar algoritmos clássicos de busca e ordenação em Python, analisando sua complexidade temporal, estabilidade, vantagens, limitações e comportamento em diferentes cenários.

## 2. Algoritmos implementados

Foram implementados cinco algoritmos:

- Busca linear;
- Busca binária;
- Bubble Sort;
- Selection Sort;
- Insertion Sort.

As implementações permitem contabilizar comparações e testar diferentes entradas. Os algoritmos de ordenação criam uma cópia da lista recebida, preservando a lista original.

## 3. Complexidade teórica

| Algoritmo | Melhor caso | Caso médio | Pior caso |
|---|---|---|---|
| Busca linear | O(1) | O(n) | O(n) |
| Busca binária | O(1) | O(log n) | O(log n) |
| Bubble Sort otimizado | O(n) | O(n²) | O(n²) |
| Selection Sort | O(n²) | O(n²) | O(n²) |
| Insertion Sort | O(n) | O(n²) | O(n²) |

A busca binária exige que a lista esteja ordenada pela mesma chave usada na pesquisa. A complexidade de melhor caso O(1) ocorre quando o elemento está exatamente na posição central examinada na primeira etapa.

O Bubble Sort implementado interrompe a execução antecipadamente quando uma passagem completa não realiza trocas. Por isso, apresenta melhor caso O(n) para uma lista já ordenada.

## 4. Estabilidade e características

| Algoritmo | Estável? | Vantagens | Limitações |
|---|---|---|---|
| Busca linear | Não se aplica | Funciona em dados não ordenados | Pode precisar percorrer todos os elementos |
| Busca binária | Não se aplica | Poucas comparações em listas ordenadas | Exige dados previamente ordenados |
| Bubble Sort | Sim | Simples e eficiente para detectar listas já ordenadas nesta implementação | Pode realizar muitas comparações e trocas |
| Selection Sort | Não, em geral | Número previsível de comparações e poucas trocas | Mantém custo quadrático mesmo em entradas ordenadas |
| Insertion Sort | Sim | Simples e eficiente para listas pequenas ou quase ordenadas | Pode realizar muito trabalho em listas grandes e invertidas |

Nesta implementação, Bubble Sort e Insertion Sort preservam a ordem relativa de elementos com chaves iguais, pois somente deslocam ou trocam elementos quando a chave do primeiro é estritamente maior.

Selection Sort não é estável em geral: uma troca pode modificar a ordem relativa de elementos com chaves iguais.

## 5. Metodologia do benchmark

Foram testadas listas de 10, 50, 100 e 200 elementos em três situações: ordenada, invertida e aleatória.

O benchmark contabilizou comparações entre chaves realizadas pelos algoritmos de ordenação. Para as buscas, contabilizou as verificações realizadas de acordo com a implementação, incluindo igualdade e comparação de ordem na busca binária.

A busca linear e a busca binária foram testadas com o alvo no final da lista ordenada. Os índices retornados foram verificados para confirmar que ambas encontraram o mesmo elemento.

Os resultados representam esta implementação e estes conjuntos de teste; não são medições universais de desempenho.

## 6. Resultados da ordenação

| Tamanho | Cenário | Bubble | Selection | Insertion |
|---:|---|---:|---:|---:|
| 10 | Ordenado | 9 | 45 | 9 |
| 10 | Invertido | 45 | 45 | 45 |
| 10 | Aleatório | 44 | 45 | 32 |
| 50 | Ordenado | 49 | 1.225 | 49 |
| 50 | Invertido | 1.225 | 1.225 | 1.225 |
| 50 | Aleatório | 1.197 | 1.225 | 597 |
| 100 | Ordenado | 99 | 4.950 | 99 |
| 100 | Invertido | 4.950 | 4.950 | 4.950 |
| 100 | Aleatório | 4.674 | 4.950 | 2.329 |
| 200 | Ordenado | 199 | 19.900 | 199 |
| 200 | Invertido | 19.900 | 19.900 | 19.900 |
| 200 | Aleatório | 19.897 | 19.900 | 9.274 |

### Interpretação

O Selection Sort apresentou a mesma quantidade de comparações para os três cenários de cada tamanho, pois percorre toda a região não ordenada em cada etapa.

Bubble Sort e Insertion Sort tiveram desempenho melhor em entradas ordenadas. Em entradas invertidas, ambos atingiram o custo quadrático esperado.

Nos dados aleatórios deste experimento, Insertion Sort realizou menos comparações que os outros dois algoritmos de ordenação.

## 7. Resultados da busca

| Tamanho | Busca linear | Busca binária | Índice encontrado |
|---:|---:|---:|---:|
| 10 | 10 | 7 | 9 |
| 50 | 50 | 11 | 49 |
| 100 | 100 | 13 | 99 |
| 200 | 200 | 15 | 199 |

Os dados mostram que a busca linear aumenta seu número de verificações proporcionalmente à quantidade de elementos quando o alvo está no final.

A busca binária precisa examinar muito menos posições porque reduz repetidamente o intervalo de pesquisa. O crescimento observado é compatível com a diferença teórica entre O(n) e O(log n).

Os contadores utilizados contabilizam operações de comparação específicas da implementação e não devem ser interpretados como uma medida absoluta de tempo.

## 8. Aplicação ao inventário de ativos de TI

Considere um inventário de notebooks, servidores e roteadores.

A busca linear pode localizar um ativo em uma lista mesmo quando ela não está ordenada. A busca binária pode ser útil para localizar um ativo por ID em uma lista ordenada por esse identificador.

No caso de ordenação, Insertion Sort é adequado para demonstrar o tratamento de listas pequenas ou quase ordenadas. Para conjuntos maiores, normalmente é preferível utilizar os algoritmos de ordenação eficientes oferecidos pela própria linguagem, como `sorted()`.

Os algoritmos implementados nesta atividade são educativos e permitem observar diretamente as estratégias e os custos das operações.

## 9. Conclusão

Os experimentos mostram que o desempenho de um algoritmo depende tanto da sua complexidade quanto das características dos dados de entrada.

A busca binária é vantajosa quando os dados já estão ordenados. Entre os algoritmos de ordenação estudados, Bubble Sort e Insertion Sort conseguem explorar entradas ordenadas, enquanto Selection Sort mantém o mesmo número de comparações para cada tamanho de entrada.

A escolha de um algoritmo deve considerar o volume de dados, o estado inicial da entrada, os requisitos de estabilidade e a frequência das operações.