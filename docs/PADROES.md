# Padrões de projeto adotados no Trabalho 2

Cada padrão abaixo resolve um problema concreto do projeto. Onde um padrão
**não** era necessário, está dito.

## 1. Factory: `src/persistencia/fabrica_ativos.py`

**Problema.** O JSON guarda cada ativo como um dicionário com `"tipo": "Servidor"`.
Para ler o arquivo, alguém precisa transformar esse texto na classe certa
(`Servidor`, `Notebook`, `Roteador`, `BancoDeDados`) e ainda converter as
vulnerabilidades. Antes, esse `if tipo in ...` ficava dentro da leitura do arquivo.

**Solução.** `FabricaAtivos.reconstruir(dado)` recebe o dicionário e devolve o objeto
da subclasse correta. Quem lê o arquivo (`Persistencia.carregar_dados`) só faz
`FabricaAtivos.reconstruir(dado)` para cada registro e não conhece nenhuma subclasse.

**Ganhos.**
- Um tipo novo entra em um lugar só (`registro_tipos.py`); a fábrica deriva a tabela dele.
- Registro inválido (tipo desconhecido, campo faltando ou sobrando) vira `ErroDados`
  com mensagem clara, no mesmo ponto.
- Dá para testar a reconstrução sem tocar em arquivo (`testes/test_padroes.py`).

É um *Factory Method simplificado* (um `classmethod` com uma tabela), não a versão
com uma hierarquia de fábricas do livro: aqui uma tabela resolve, e Python não exige mais.

## 2. Repository: `src/persistencia/repositorio.py`

**Problema.** `GerenciadorAtivos` sabia que os ativos ficam num arquivo: checava se o
arquivo existia, chamava o `Persistencia` com o caminho, etc. Trocar o armazenamento,
ou testar sem disco, obrigaria a mexer na regra de negócio.

**Solução.** `RepositorioAtivos` define duas operações: `listar()` e `salvar(ativos)`.
Há duas implementações:
- `RepositorioAtivosJson`: o arquivo JSON de sempre (com gravação atômica);
- `RepositorioAtivosMemoria`: uma lista em memória, usada nos testes.

`GerenciadorAtivos(caminho, repositorio=None)` usa o repositório recebido; se nenhum for
passado, cria o JSON. O comportamento do sistema não mudou.

**Ganhos.** O gerenciador cuida só das regras (ID repetido, validações); o repositório
cuida só de onde os dados moram. Trocar por SQLite seria escrever uma terceira classe.

## 3. Strategy: `src/servicos/ordenacao.py`

**Problema.** A lista de ativos precisa sair em ordens diferentes (por nome, ID, setor,
responsável, quantidade de falhas). Um `if/elif` por critério cresceria a cada pedido novo.

**Solução.** O critério é uma estratégia: uma função que recebe um ativo e devolve a chave
de comparação. As estratégias ficam em um dicionário `ESTRATEGIAS`, e `ordenar(ativos, criterio,
decrescente)` só escolhe a estratégia e chama `sorted`. A API expõe isso em
`GET /api/ativos?ordem=nome&sentido=desc`.

**Por que funções e não classes.** O livro mostra uma classe por estratégia. Em Python,
funções são objetos de primeira classe: uma função de uma linha faz o papel de uma classe
com um método. Versão com classes, só para comparar:

```python
class PorNome:
    def chave(self, ativo): return ativo.nome.casefold()
# uso: sorted(ativos, key=PorNome().chave)
```

A versão com função (`_por_nome`) faz o mesmo com menos código; por isso foi a adotada.
Um critério novo é uma função nova mais uma linha no dicionário.

## Padrões considerados e não adotados

**Singleton para o acesso ao arquivo de dados: não adotado.** Um Singleton garante uma única
instância e um ponto global de acesso. O risco é o segundo: estado global escondido, que
dificulta testes (cada teste herda o estado do anterior) e impede ter dois arquivos ao mesmo
tempo. Aqui não é preciso: o sistema já cria **um** `GerenciadorAtivos` na inicialização e o
passa a quem precisa, e os testes criam um por pasta temporária. O que protege o arquivo de
escritas simultâneas é a trava (`com_trava`) da API e a gravação atômica, não a unicidade do objeto.

**Observer:** o front-end consulta a API de tempos em tempos e não há quem precise ser
notificado dentro do servidor; adotá-lo seria enfeite.

## Resumo

| Padrão | Arquivo | Problema que resolve |
|---|---|---|
| Factory | `src/persistencia/fabrica_ativos.py` | Recriar a subclasse certa a partir do `"tipo"` do JSON |
| Repository | `src/persistencia/repositorio.py` | Isolar onde os ativos são guardados da regra de negócio |
| Strategy | `src/servicos/ordenacao.py` | Trocar o critério de ordenação sem `if/elif` |
