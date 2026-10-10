# S3_06 — Qualidade de Software e Análise Estática

## 1. Objetivo

Aplicar ferramentas de análise estática e formatação automática para identificar problemas de qualidade, refatorar um código Python e comparar os resultados antes e depois das melhorias.

## 2. Ferramentas utilizadas

- **Flake8:** verifica problemas de estilo e possíveis erros no código Python.
- **Pylint:** avalia aspectos como nomes, documentação, organização e práticas de programação.
- **Black:** padroniza automaticamente a formatação do código.

As ferramentas foram executadas em um ambiente virtual Python, isolando suas dependências do ambiente principal do sistema.

## 3. Análise inicial

O arquivo `src/qualidade/exemplo_antes.py` executava duas operações: calcular o risco próprio de um ativo a partir das severidades das vulnerabilidades e localizar um ativo pelo identificador.

A execução produziu o risco `18.6` e encontrou o servidor solicitado. Apesar de funcionar, o código apresentava problemas de legibilidade e padronização.

### Problemas identificados pelo Flake8

- Indentação fora do padrão.
- Espaços ausentes após vírgulas e ao redor de operadores.
- Linhas excessivamente longas.
- Múltiplas instruções na mesma linha.
- Separação inadequada entre funções.
- Ausência de quebra de linha no final do arquivo.

### Problemas identificados pelo Pylint

- Ausência de documentação do módulo e das funções.
- Nomes pouco descritivos.
- Uso de `id` como nome de parâmetro, redefinindo um nome embutido do Python.
- Indentação inadequada e linhas excessivamente longas.
- Múltiplas instruções na mesma linha.

**Pontuação inicial do Pylint: 0,00/10.**

As saídas completas foram registradas em `docs/s3_06_flake8_antes.txt` e `docs/s3_06_pylint_antes.txt`.

## 4. Refatoração realizada

Foi criado o arquivo `src/qualidade/exemplo_depois.py`, preservando o comportamento do exemplo original.

### Antes

```python
def calc(v,f):
 r=0
 for x in v:
  r+=x["severidade"]*f
 return r

def find(a,id):
 for x in a:
  if x["id"]==id:return x
 return None
```

### Depois

```python
def calcular_risco_proprio(
    vulnerabilidades: list[dict[str, float]],
    fator_exposicao: float,
) -> float:
    """Calcula o risco próprio a partir das severidades das vulnerabilidades."""
    risco_total = 0.0

    for vulnerabilidade in vulnerabilidades:
        risco_total += (
            vulnerabilidade["severidade"] * fator_exposicao
        )

    return risco_total
```

A refatoração incluiu:

- Nomes mais claros e relacionados ao domínio.
- Indentação e espaçamento padronizados.
- Documentação das funções e do módulo.
- Anotações de tipos para facilitar a compreensão das interfaces.
- Separação das instruções em blocos legíveis.
- Organização das estruturas de dados em múltiplas linhas.

O Black foi executado para padronizar a formatação do arquivo refatorado.

## 5. Validação após a refatoração

O programa continuou produzindo os resultados esperados: risco `18.6` e os dados do servidor identificado.

| Verificação | Antes | Depois |
|---|---|---|
| Flake8 | Vários problemas de estilo | Nenhum aviso após a correção final |
| Pylint | 0,00/10 | 10,00/10 |
| Black | Formatação irregular | Arquivo formatado automaticamente |
| Execução | Resultado correto | Mesmo resultado correto |

O resultado do Pylint demonstra que os problemas de qualidade identificados nessa amostra foram corrigidos. A aprovação do Flake8 confirma que o arquivo final atende às verificações de estilo configuradas pela ferramenta.

As evidências estão registradas em:

- `docs/s3_06_flake8_antes.txt`
- `docs/s3_06_pylint_antes.txt`
- `docs/s3_06_flake8_depois.txt`
- `docs/s3_06_pylint_depois.txt`

## 6. Conclusão

A atividade demonstrou que um programa funcional ainda pode apresentar problemas de legibilidade e manutenção. A análise estática permitiu localizar problemas concretos, enquanto a refatoração melhorou os nomes, a documentação, a organização e a padronização do código.

O uso combinado de Flake8, Pylint e Black contribuiu para tornar o exemplo mais legível e consistente. A comparação entre os resultados mostrou a importância de validar o código tanto pela execução quanto por ferramentas automatizadas de qualidade.

A análise foi realizada sobre um exemplo didático isolado, sem alterar o comportamento do sistema principal de inventário de ativos.