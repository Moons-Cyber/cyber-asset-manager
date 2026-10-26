# Inventário de ativos de TI e vulnerabilidades

Aplicação em Python (orientação a objetos) que cadastra ativos de TI e suas
vulnerabilidades, busca a nota CVSS real de cada CVE no NVD e estima o risco
efetivo de cada ativo com álgebra linear, considerando as dependências entre eles.

Tem duas formas de uso, sobre o mesmo núcleo: um **menu de terminal** e uma
**API REST (JSON)**, que é a que roda no container.

## Requisitos

- Python 3.14 (versão em que o projeto foi desenvolvido e testado)
- Dependências em `requirements.txt` (`numpy`, `Flask`; `gunicorn` só é usado no Docker)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Menu de terminal

```bash
python main.py
```

## Testes

Sempre a partir da raiz do projeto:

```bash
python -m unittest discover -s testes -t . -v
```

## API em modo de desenvolvimento

```bash
python servidor.py               # http://127.0.0.1:5000/api/saude
```

Variáveis de ambiente (todas opcionais):

| Variável | Padrão | Uso |
|---|---|---|
| `DADOS_DIR` | pasta atual | onde ficam `ativos.json`, `dependencias.json` e `cache_cve.json` |
| `HOST` | `127.0.0.1` | endereço de escuta |
| `PORT` | `5000` | porta |
| `NVD_API_KEY` | vazio | chave gratuita do NVD (consultas de CVE mais rápidas) |

## Docker

```bash
docker compose up -d --build
docker compose ps                         # aguarde "(healthy)"
curl http://localhost:5000/api/saude
```

Detalhes do container:

- Os dados ficam no volume `dados` (montado em `/dados`), fora da imagem: sobrevivem
  a reinícios e a `docker compose down`. **`docker compose down -v` apaga os dados.**
- `restart: unless-stopped`: o container volta sozinho se o processo cair.
- `HEALTHCHECK` em `/api/saude` (devolve 503 se os arquivos de dados estiverem ilegíveis).
- Roda **um processo com 8 threads** (gunicorn). É intencional: os ativos ficam em um
  `dict` em memória por processo, e vários processos teriam cópias diferentes dos dados.
- Em servidor compartilhado, crie um arquivo `.env` ao lado do `docker-compose.yml`
  para evitar colisão de nome e porta:

```
HOST_PORT=5217
CONTAINER_NAME=inventario-meunome
IMAGE_TAG=1.0
```

## Verificar um serviço em execução

```bash
python scripts/verificar_servico.py http://localhost:5000
python scripts/verificar_servico.py http://SERVIDOR:PORTA --testar-nvd
```

Cria dois ativos de teste, exercita vulnerabilidade, dependência e risco, confere os
resultados e remove tudo no final. Código de saída 0 = tudo certo.

## Evidência do tempo no ar (24 h)

```bash
docker compose ps
docker inspect -f '{{.State.StartedAt}} reinícios={{.RestartCount}}' inventario-ativos

python scripts/verificar_servico.py http://SERVIDOR:PORTA --monitorar 24 --intervalo 60
```

O monitoramento grava `monitoramento.csv` (horário, código HTTP, latência) e, ao
final, mostra a disponibilidade e a maior sequência de falhas.

## Modelo de risco

Para `n` ativos e `m` vulnerabilidades:

- `M` (n×m): `M[i][j] = 1` se o ativo `i` tem a vulnerabilidade `j` (vulnerabilidades
  com status *Corrigida* ficam de fora)
- `v` (m): nota CVSS de cada vulnerabilidade
- `F` (n×n, diagonal): fator de exposição de cada ativo, definido pelo tipo dele (polimorfismo)
- `b = F·M·v`: risco próprio
- `A` (n×n): `A[i][j]` = fração do risco do ativo `j` que chega ao ativo `i`
- Risco efetivo `x`, que satisfaz `x = b + A·x`, isto é, `(I − A)·x = b`

O cadastro de dependências exige que a soma dos pesos recebidos por cada ativo seja
menor que 1, com uma margem de tolerância de 1e-9 (em ponto flutuante, `0,7 + 0,2 + 0,1`
dá `0,9999999999999999`, e uma comparação exata deixaria passar uma linha que na verdade
soma 1 e torna `I − A` singular). Com a soma abaixo de 1, `I − A` é estritamente diagonal
dominante e, portanto, invertível.

Passos do cálculo (`src/servicos/analise_risco.py`):

1. `b = F @ (M @ v)`: soma as notas de cada ativo (`M @ v`) e pondera pelo fator de exposição do
   tipo. Produto matricial do NumPy (em NumPy, `*` multiplicaria elemento a elemento).
2. Verificação antes de resolver: posto de `I − A` e número de condição κ. Rejeita se
   κ > 1/ε (≈ 4,5·10¹⁵, singular para o computador) e avisa se κ > 10⁸ (restam menos de
   8 dos 16 dígitos do `float64`). O determinante é mostrado, mas não decide sozinho.
3. `numpy.linalg.solve` (fatoração LU), e não o cálculo da inversa.
4. Conferência: substitui `x` de volta e compara `(I − A)x` com `b` usando `allclose`.

Fatores de exposição (estimativas do analista, como os pesos das dependências): Notebook 1,0,
Servidor 1,5, Roteador 1,2, Banco de dados 1,0. O fator multiplica só `b`: não altera `A`,
então não muda a invertibilidade nem o número de condição de `I − A`.

## API

| Rota | Função |
|---|---|
| `GET /api/saude` | saúde do serviço (200 ou 503) |
| `GET /api/tipos`, `GET /api/status` | tipos de ativo e status de vulnerabilidade |
| `GET/POST /api/ativos` | listar (`?q=nome`, `?tipo=código`) e criar |
| `GET/PATCH/DELETE /api/ativos/<id>` | obter, alterar e remover (remove as dependências do ativo) |
| `GET/POST /api/ativos/<id>/vulnerabilidades` | listar e adicionar (manual ou por CVE) |
| `PATCH /api/ativos/<id>/vulnerabilidades/<vid>` | alterar o status |
| `GET /api/cve/<cve>` | prévia da nota de um CVE no NVD |
| `GET/POST /api/dependencias` | listar e criar |
| `DELETE /api/dependencias/<origem>/<destino>` | remover |
| `GET /api/risco` | risco próprio e efetivo de cada ativo, com diagnóstico da matriz |

Códigos: 400 entrada inválida, 404 não encontrado, 409 conflito (ID repetido),
422 dados inconsistentes no cálculo de risco, 503 dados armazenados ilegíveis ou
NVD indisponível.

## Estrutura

```
main.py                    menu de terminal
servidor.py                ponto de entrada da API
src/modelos/               Ativo e subclasses, Vulnerabilidade, Dependencia, enums
src/servicos/              gerenciadores, cálculo de risco, cliente do NVD
src/persistencia/          leitura e gravação atômica do JSON
src/api/aplicacao.py       API REST (Flask)
scripts/                   verificação e monitoramento do serviço
testes/                    testes automatizados
Dockerfile, docker-compose.yml
```

## Limitações conhecidas

- A API não tem autenticação.
- A "descrição curta" de um CVE é a primeira frase do texto do NVD, cortada em tamanho
  fixo e em inglês; não é um resumo nem uma tradução.
- Não rode o menu de terminal e a API ao mesmo tempo sobre os mesmos arquivos: cada um
  guarda os dados em memória por conta própria.
