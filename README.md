# 🛡️ Cyber Asset Manager (Inventário de Ativos e Análise de Risco)

**Identificador do trabalho:** `trab02_2026_2_12621cbs213`

Bem-vindo ao **Cyber Asset Manager**! Este é um sistema criado para gerenciar a segurança digital de uma rede de computadores. Com ele, você pode cadastrar equipamentos (**ativos**), registrar falhas de segurança (**vulnerabilidades / CVEs**) — buscando a gravidade delas automaticamente na internet (base oficial do NVD) — e mapear como um equipamento depende de outro.

A partir dessas informações, o programa usa **álgebra linear** para diagnosticar a rede e calcular o **risco efetivo** de cada equipamento, salvando tudo automaticamente em arquivos JSON (`ativos.json`, `dependencias.json` e `cache_cve.json`). Opcionalmente, os ativos, as vulnerabilidades e as dependências podem ficar em um banco **SQLite** (veja a seção *Persistência*).

O sistema pode ser usado de três jeitos, todos sobre o mesmo núcleo:

* **Interface web** (`/aero`): um desktop no estilo Windows XP, com o mapa da rede, o cadastro completo e um **Assistente** que explica a conta do risco com os seus dados e mostra onde cada parte está no código.
* **API REST em Flask** (`servidor.py`): conversa em JSON; é o que roda no container Docker.
* **Menu interativo no terminal** (`main.py`).

---

## 💻 Passo 1: Como abrir o Terminal e baixar o projeto

Para executar os comandos deste guia, você precisa abrir o **Terminal** (Prompt de Comando) do seu computador:
* **No Windows:** Aperte a tecla `Windows` no teclado, digite `cmd` e aperte `Enter`.
* **No Linux ou Mac:** Procure pelo aplicativo chamado `Terminal` e abra-o.

Se você tiver o [Git](https://git-scm.com/downloads) instalado, copie e cole os comandos abaixo (um por linha, apertando `Enter` ao final de cada um):

```bash
git clone https://github.com/Moons-Cyber/trab02_2026_2_12621cbs213.git
cd trab02_2026_2_12621cbs213
```
*(Se preferir não usar o Git, clique no botão verde **`<> Code`** no topo da página do GitHub, escolha **`Download ZIP`**, extraia a pasta no seu computador e abra o Terminal dentro dela).*

---

## 🚀 Passo 2: Como ligar o programa (Escolha a Opção A ou B)

### Opção A: Rodando com Docker (Mais fácil — Recomendado!)
Com o [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e aberto no seu computador, você não precisa instalar o Python nem configurar nada manualmente.

1. No Terminal aberto dentro da pasta do projeto, digite:
   ```bash
   docker compose up -d --build
   ```
2. O Docker vai preparar o ambiente Python 3.14 e ligar o servidor **Gunicorn** automaticamente. Dentro do container ele escuta na porta 5000, que é publicada no computador como **2213** (`2213:5000`).
3. Para ter certeza de que funcionou, confira se o container está saudável (`healthy`):
   ```bash
   docker ps
   ```
   e abra no navegador:
   ```text
   http://localhost:2213/api/saude     (a API respondendo)
   http://localhost:2213/aero          (a interface web)
   ```
4. **Para desligar o servidor quando terminar:**
   ```bash
   docker compose down
   ```
   Os dados ficam guardados no volume `dados` (pasta `/dados` dentro do container) e continuam lá na próxima vez que você ligar. O volume se chama `trab02_2026_2_12621cbs213_dados`; só um `docker compose down -v` o apaga.

> 💡 **Padronização (servidor da faculdade):** o `compose.yaml` usa o identificador `trab02_2026_2_12621cbs213` para o projeto Compose, a imagem, o container e o volume, e a porta externa é `2000 + 3 últimos dígitos da matrícula` (`2213`). Para consultas de vulnerabilidades mais rápidas, crie um arquivo `.env` com uma chave gratuita do NVD: `NVD_API_KEY=sua_chave`.

> 🔓 **Atenção:** a porta `2213` é publicada para a rede (sem `127.0.0.1`), para que o professor consiga acessar. A API **não tem autenticação**; veja as *Limitações conhecidas*.

---

### Opção B: Rodando direto no Computador (Para usar o Menu no Terminal ou a API sem Docker)

1. **Instale o Python 3.14** (versão em que o projeto foi desenvolvido e testado): baixe em [python.org](https://www.python.org/downloads/). *(No Windows, marque a caixinha **"Add python.exe to PATH"** na primeira tela da instalação!)*
2. **Crie e ative o ambiente isolado (só precisa fazer na 1ª vez):**
   ```bash
   python -m venv .venv
   ```
   * Ative no **Windows (`cmd`)**:
     ```bash
     .venv\Scripts\activate
     ```
   * Ative no **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   * Ative no **Linux ou Mac**:
     ```bash
     source .venv/bin/activate
     ```
3. **Instale as bibliotecas necessárias**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Inicie o modo desejado:**
   * Para usar o **Menu Interativo** (respondendo perguntas com números no teclado):
     ```bash
     python main.py
     ```
   * Para ligar o **Servidor da API e a interface web** localmente:
     ```bash
     python servidor.py
     ```
     Depois abra `http://localhost:5000/aero` no navegador (sem Docker a porta é a 5000; no Docker, use a 2213).

### Quer ver a interface com dados de exemplo?
A pasta `dados_ficticios/` traz uma rede de exemplo (10 ativos e 11 dependências). Para não misturar com os seus dados reais, aponte o servidor para ela:

* **Windows (PowerShell):** `$env:DADOS_DIR="dados_ficticios"; python servidor.py`
* **Linux ou Mac:** `DADOS_DIR=dados_ficticios python servidor.py`

### Configurações por variável de ambiente

| Variável | Para que serve | Padrão |
| :--- | :--- | :--- |
| `DADOS_DIR` | Pasta onde ficam `ativos.json`, `dependencias.json`, `cache_cve.json`, `diario.json` e, no modo SQLite, `inventario.db` | pasta atual (no Docker: `/dados`) |
| `PERSISTENCIA` | Onde guardar ativos e dependências: `json` ou `sqlite` | `json` |
| `HOST` / `PORT` | Endereço e porta do servidor de desenvolvimento | `127.0.0.1` / `5000` |
| `NVD_API_KEY` | Chave gratuita do NVD (consultas mais rápidas) | vazia |
| `DIARIO_INTERVALO_S` | Segundos entre os cálculos anotados no diário (`0` = só ao ligar, `-1` = desliga) | `3600` (1 hora) |
| `DIARIO_MAX_ENTRADAS` | Máximo de anotações guardadas no diário | `1000` |

---

## 🫧 A interface web

Abra `/aero` (`http://localhost:2213/aero` no Docker ou `http://localhost:5000/aero` rodando direto). É um desktop no estilo Frutiger Aero / Windows XP, com janelas arrastáveis, barra de tarefas, menu iniciar e um escudo na bandeja que mostra se o serviço está no ar. Os ícones, o fundo e o mascote foram desenhados do zero (SVG e canvas); a página usa só fontes do sistema e não baixa nada da internet, então funciona até num servidor sem acesso externo.

| Janela | O que faz |
| :--- | :--- |
| **Mapa da Rede** | Cada ativo é uma esfera com a cor do risco efetivo; os canos são as dependências, com o peso. Clicando numa esfera, aparece de onde vem o risco dela (risco próprio + o que chega de cada vizinho). |
| **Matrizes e Gráfico** | Mapa de calor da matriz de dependências **A** (cada quadradinho é o peso de um ativo sobre outro, com a soma que cada um recebe), da matriz **I − A** com o diagnóstico de invertibilidade, e barras do risco próprio (b) e efetivo (x) de cada ativo. Clicar num quadradinho mostra a conta daquela dependência. Lê só `/api/risco/passos`. |
| **Gerenciador de Ativos** | Cadastro completo: **Novo**, **Editar** e **Excluir** ativos; adicionar falhas (com ou sem CVE) e mudar o status; criar e remover dependências. |
| **Monitor do Serviço** | A saúde da API e o diário das 24 horas: uma marca por hora em que o servidor esteve no ar. |
| **Assistente** | A **Gota**, no canto da tela. Fica quieta até ser chamada (só oferece um tour na primeira visita) e responde: como o risco é calculado, por que um ativo tem aquele risco, **o que é uma falha e como prevenir**, o que é a verificação de invertibilidade, como cadastrar, e onde cada parte está no código. |

O passo a passo do cálculo é um assistente no estilo do XP (**Voltar** / **Avançar**) que refaz a conta com os dados cadastrados naquele momento, usando a rota `/api/risco/passos`. Cada passo tem uma caixa **No código** com o arquivo, a função e a linha que fazem aquilo; um teste automatizado confere que essas linhas existem mesmo no código.

O **Assistente de Segurança** explica uma falha cadastrada (botão **Explicar** no Gerenciador, link "o que é?" no Mapa, ou pela Gota) em quatro passos: o que ela é, por que é perigosa naquele tipo de ativo, como prevenir e o que fazer agora, com botões para marcar a falha como *Em tratamento* ou *Corrigida*. Ele reconhece 15 tipos de falha (injeção de SQL, XSS, execução remota, senha padrão, software desatualizado, entre outros), cada um com a referência CWE, por palavras-chave na categoria, na descrição ou no texto do NVD. Tudo funciona sem internet: os textos ficam em `src/servicos/orientacao_seguranca.py`. As orientações são gerais para o tipo de falha; a correção exata de um CVE está no boletim do fornecedor.

No celular, as janelas abrem em tela cheia e o Assistente fica no ícone da área de trabalho e no menu iniciar.

## 🧮 A matemática do risco (resumo)

1. **Risco próprio:** `b = F · (M · v)`. A matriz `M` marca quais falhas abertas cada ativo tem, `v` traz as notas CVSS e `F` é o fator de exposição de cada tipo (servidor 1,5; roteador 1,2; notebook e banco de dados 1,0).
2. **Dependências:** `A[destino][origem] = peso` — a fração do risco da origem que chega no destino.
3. **Risco efetivo:** `x = b + A·x`, ou seja, **`(I − A)·x = b`**, resolvido com `np.linalg.solve` (fatoração LU, sem calcular a inversa). Antes de resolver, o sistema confere:
   * o **posto** de `I − A` (precisa ser cheio);
   * o **número de condição κ**: rejeita se κ > 1/ε (≈ 4,5·10¹⁵, singular para o computador) e avisa se κ > 10⁸ (sobram menos de 8 dos 16 dígitos do `float64`);
   * o **determinante**, só como informação (ele não decide sozinho).

   Depois, coloca `x` de volta na equação e compara `(I − A)·x` com `b` usando `allclose`. No código, o produto de matrizes é `@`: em NumPy, `*` multiplicaria elemento a elemento.
4. **Por que a soma dos pesos recebidos precisa ser menor que 1:** isso dá à matriz `I − A` dominância diagonal estrita, o que garante que ela é invertível. A soma precisa ficar abaixo de 1 com uma folga de `1e-9`, porque em ponto flutuante `0,7 + 0,2 + 0,1` dá `0,9999999999999999`, e uma comparação exata deixaria passar uma linha que na verdade soma 1. O fator de exposição multiplica só `b`: ele não altera `A`, então não muda a invertibilidade nem o número de condição.

---

## 🗄️ Persistência: JSON (padrão) ou SQLite

Os dados podem ser guardados de duas formas, escolhidas pela variável `PERSISTENCIA`. O restante do sistema não muda, porque ele só conhece a interface `RepositorioAtivos` / `RepositorioDependencias` (padrões **Repository** e **Factory**; veja `docs/PADROES.md`).

| Modo | Onde ficam os dados | Quando usar |
| :--- | :--- | :--- |
| `json` (padrão) | `ativos.json` e `dependencias.json`, com gravação atômica | Requisito do trabalho: arquivo em formato JSON |
| `sqlite` | `inventario.db`, com 4 tabelas: `ativos`, `vulnerabilidades`, `ativo_vulnerabilidade` (N:N, com o status da falha naquele ativo) e `dependencias` | Consultas com `JOIN`, `GROUP BY` e relatórios |

```bash
# Rodando direto (PowerShell)
$env:PERSISTENCIA="sqlite"; python servidor.py

# Migrar os dados do JSON para o banco (só copia, não apaga o JSON)
python scripts/migrar_json_para_sqlite.py

# Relatórios feitos só com SQL (JOINs, agregações e risco)
python scripts/relatorio_sql.py
```

No Docker, `PERSISTENCIA` já aparece no `compose.yaml` com o padrão `json`; para usar o SQLite, defina `PERSISTENCIA=sqlite` no `.env`. As consultas ficam em `sql/consultas.sql`, o esquema em `sql/esquema.sql` e a explicação completa em `docs/BANCO_DE_DADOS.md`. As consultas usam parâmetros (`?`), nunca texto montado à mão, para evitar *SQL injection* (CWE-89).

---

## 🌐 Passo 3: Como usar a API passo a passo (Para Iniciantes)

Quando o servidor da API está ligado, você pode interagir com ele de duas formas. Os exemplos abaixo usam a porta `5000` (execução direta com `python servidor.py`); **no Docker, troque `5000` por `2213`**.

### 1. Consultas rápidas direto pelo Navegador de Internet (`GET`)
Basta abrir o Google Chrome, Edge ou Firefox e colar qualquer um dos endereços abaixo na barra de endereços:

| O que você quer ver | Endereço para colar no Navegador | O que aparece na tela |
| :--- | :--- | :--- |
| **Interface web** | `http://localhost:5000/aero` | O desktop com o Mapa, o cadastro e o Assistente (veja a seção acima). |
| **Página inicial da API** | `http://localhost:5000/` | Mostra o nome do serviço e os atalhos de saúde e da interface. |
| **Saúde do sistema** | `http://localhost:5000/api/saude` | Confirma se os arquivos estão íntegros e quantos ativos existem. |
| **Tipos de equipamentos** | `http://localhost:5000/api/tipos` | Lista os códigos de tipos aceitos e qual campo extra cada um pede. |
| **Status de falhas aceitos** | `http://localhost:5000/api/status` | Mostra os status válidos: `Aberta`, `Em tratamento`, `Corrigida` e `Risco aceito`. |
| **Listar todos os ativos** | `http://localhost:5000/api/ativos` | Lista todos os equipamentos cadastrados. |
| **Buscar ativo por nome** | `http://localhost:5000/api/ativos?q=Servidor` | Filtra apenas ativos que tenham a palavra buscada no nome. |
| **Filtrar ativo por tipo** | `http://localhost:5000/api/ativos?tipo=1` | Filtra equipamentos pelo número do código do tipo. |
| **Ver 1 ativo específico** | `http://localhost:5000/api/ativos/1` | Mostra os dados do ativo de ID `1`. |
| **Ver falhas de 1 ativo** | `http://localhost:5000/api/ativos/1/vulnerabilidades` | Lista as vulnerabilidades do ativo de ID `1`. |
| **Consultar um CVE oficial** | `http://localhost:5000/api/cve/CVE-2021-44228` | Busca a nota de gravidade e descrição direto na base mundial NVD. |
| **Listar dependências** | `http://localhost:5000/api/dependencias` | Mostra quais equipamentos dependem uns dos outros. |
| **Relatório de Risco Geral** | `http://localhost:5000/api/risco` | Calcula o risco efetivo de cada equipamento e o diagnóstico da rede. |
| **Como prevenir uma falha** | `http://localhost:5000/api/ativos/1/vulnerabilidades/ID_DA_FALHA/orientacao` | O que é a falha, por que é perigosa, como prevenir e quanto o risco cai se ela for corrigida. |
| **Cálculo passo a passo** | `http://localhost:5000/api/risco/passos` | Cada etapa da conta: `M`, `v`, `b`, `A`, `I − A`, o diagnóstico e o `x`. É o que o Assistente usa. |
| **Ordenar ativos** | `http://localhost:5000/api/ativos?ordem=nome&sentido=desc` | Ordena por `nome`, `id`, `setor`, `responsavel` ou `falhas` (padrão Strategy). |
| **Diário das 24 horas** | `http://localhost:5000/api/diario` | As anotações de hora em hora (responde 404 se o diário estiver desligado). |

---

### 2. Cadastrando e alterando dados pelo Terminal (`POST`, `PATCH`, `DELETE`)

A aba **Ativos** da interface faz tudo isso com botões. Se preferir o terminal, use o comando `curl` (ou programas visuais gratuitos como *Postman* ou *Insomnia*).

Veja a sequência completa para testar todas as funções do sistema:

#### A) Descobrir os tipos de ativos disponíveis
Primeiro, acesse `http://localhost:5000/api/tipos` no navegador. Você verá o `codigo` de cada tipo (`1` Notebook, `2` Servidor, `3` Roteador, `4` Banco de dados) e o nome do `campo` específico que aquele tipo exige.

#### B) Cadastrar um novo Ativo (`POST /api/ativos`)
Cada tipo exige um campo próprio (veja em `/api/tipos`). No exemplo abaixo, o tipo `2` (Servidor) exige o campo `processador`. O nome precisa ter pelo menos 3 caracteres:

```bash
curl -X POST http://localhost:5000/api/ativos ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": 1, \"tipo\": 2, \"nome\": \"Servidor Principal\", \"responsavel\": \"Equipe TI\", \"setor\": \"Infraestrutura\", \"processador\": \"Intel Xeon\"}"
```
*(Nota: os exemplos usam a sintaxe do `cmd` do Windows. No Linux ou Mac, troque o `^` no fim das linhas por uma barra invertida `\` e use aspas simples por fora do JSON, sem as barras antes das aspas internas: `-d '{"id": 1, "tipo": 2, ...}'`).*

#### C) Adicionar uma Vulnerabilidade a um Ativo (`POST /api/ativos/<id>/vulnerabilidades`)
Você pode cadastrar uma vulnerabilidade de duas formas:

* **Forma 1 — Automática pelo código CVE (busca a nota sozinho no NVD):**
  Basta enviar o código `cve` (no formato `CVE-AAAA-NNNN`) e a `categoria`:
  ```bash
  curl -X POST http://localhost:5000/api/ativos/1/vulnerabilidades ^
    -H "Content-Type: application/json" ^
    -d "{\"cve\": \"CVE-2021-44228\", \"categoria\": \"Execucao Remota\"}"
  ```
* **Forma 2 — Manual (você mesmo define a nota de severidade e descrição):**
  Se não tiver código CVE (ou se o site do NVD estiver fora do ar), envie a `severidade` e a `descricao` manualmente:
  ```bash
  curl -X POST http://localhost:5000/api/ativos/1/vulnerabilidades ^
    -H "Content-Type: application/json" ^
    -d "{\"descricao\": \"Senha fraca no painel\", \"categoria\": \"Acesso\", \"severidade\": 7.5}"
  ```

#### D) Atualizar o status de uma Vulnerabilidade (`PATCH /api/ativos/<id>/vulnerabilidades/<id_vuln>`)
Quando uma falha for corrigida, mude o `status` dela. Os valores aceitos são exatamente `Aberta`, `Em tratamento`, `Corrigida` e `Risco aceito`. Uma falha `Corrigida` deixa de contar no risco:

```bash
curl -X PATCH http://localhost:5000/api/ativos/1/vulnerabilidades/CVE-2021-44228 ^
  -H "Content-Type: application/json" ^
  -d "{\"status\": \"Corrigida\"}"
```

#### E) Criar uma Dependência entre dois Ativos (`POST /api/dependencias`)
Se você cadastrou o ativo `1` e o ativo `2`, pode informar que **parte do risco do `1` passa para o `2`** (ou seja, o `2` depende do `1`) com um `peso`:

```bash
curl -X POST http://localhost:5000/api/dependencias ^
  -H "Content-Type: application/json" ^
  -d "{\"origem\": 1, \"destino\": 2, \"peso\": 0.5}"
```
O peso vai de `0` até menos de `1`, e a soma dos pesos que **chegam** em um mesmo ativo também precisa ficar abaixo de `1` (é isso que garante que o cálculo de risco tem solução).

#### F) Calcular o Risco da Rede (`GET /api/risco`)
Agora basta abrir no navegador `http://localhost:5000/api/risco` para ver o cálculo completo de propagação de risco (`resultados`) e o diagnóstico de fragilidade da rede (`diagnostico`)!

#### G) Atualizar ou Remover Ativos e Dependências (`PATCH` e `DELETE`)
* **Editar dados de um ativo (`PATCH /api/ativos/<id>`):**
  ```bash
  curl -X PATCH http://localhost:5000/api/ativos/1 ^
    -H "Content-Type: application/json" ^
    -d "{\"setor\": \"Seguranca da Informacao\"}"
  ```
* **Apagar uma dependência (`DELETE /api/dependencias/<origem>/<destino>`):**
  ```bash
  curl -X DELETE http://localhost:5000/api/dependencias/1/2
  ```
* **Apagar um ativo e suas dependências (`DELETE /api/ativos/<id>`):**
  ```bash
  curl -X DELETE http://localhost:5000/api/ativos/1
  ```

### 3. Códigos de resposta da API

| Código | Significado |
| :--- | :--- |
| `200` / `201` | Tudo certo / criado |
| `400` | Pedido inválido (ex.: nome com menos de 3 caracteres, peso fora da faixa) |
| `404` | Não encontrado |
| `409` | Conflito (ex.: ID repetido) |
| `422` | Dados inconsistentes para o cálculo de risco |
| `503` | Arquivos de dados ilegíveis ou NVD indisponível |

---

## 🧪 Passo 4: Como rodar os Testes Automatizados

O projeto possui uma pasta `testes` com **mais de 270 testes** que garantem que nenhuma regra de negócio, cálculo de risco ou rota da API quebre após alterações no código. Para executá-los (com o `.venv` ativado), **na pasta raiz do projeto**:

```bash
python -m unittest discover -s testes -t .
```

Entre eles, `test_passos.py` confere o cálculo etapa por etapa contra uma conta feita à mão, e `test_aero.py` confere que cada trecho de código citado pelo Assistente existe mesmo no arquivo e na função que ele diz.

---

## ⏱️ Teste de 24 horas (Docker no servidor)

1. Suba o container (no servidor, dentro da pasta `trab02_2026_2_12621cbs213`): `docker compose up -d --build`
2. Confira que está saudável: `docker ps` (deve aparecer `healthy`)
3. Rode a verificação completa (cria ativos de teste, confere vulnerabilidade, dependência e risco, e apaga tudo no final; código de saída `0` = tudo certo). Com `--testar-nvd`, testa também a consulta ao NVD:
   ```bash
   python scripts/verificar_servico.py http://127.0.0.1:2213
   ```
4. Monitore por 24 horas (uma consulta por minuto, gravada em `monitoramento.csv`):
   ```bash
   python scripts/verificar_servico.py http://127.0.0.1:2213 --monitorar 24 --intervalo 60
   ```
   Ao final, ele mostra a disponibilidade e a maior sequência de falhas.
5. Confira quando o container ligou e quantas vezes reiniciou:
   ```bash
   docker inspect -f '{{.State.StartedAt}} reinícios={{.RestartCount}}' trab02_2026_2_12621cbs213
   ```
6. No fim, o **Monitor do Serviço** da interface mostra uma marca por hora em que o servidor esteve no ar.

O container reinicia sozinho se cair (`restart: unless-stopped`), os dados ficam no volume e toda gravação é atômica (um arquivo temporário substitui o antigo de uma vez só). Ele roda **um processo com 8 threads** de propósito: os ativos ficam num dicionário em memória, e vários processos teriam cópias diferentes dos dados.

> 💡 Num servidor compartilhado, **nunca** use comandos em massa (`docker rm $(docker ps -aq)`, `prune`): eles atingem os containers dos colegas. Pare só o seu: `docker compose down` (sem `-v`, para não apagar o volume).

---

## 📂 Estrutura de Pastas do Projeto

```text
trab02_2026_2_12621cbs213/   (Cyber Asset Manager)
│
├── main.py                      # Menu interativo para usar pelo Terminal
├── servidor.py                  # Ponto de entrada da API (lê as variáveis de ambiente)
├── requirements.txt             # Bibliotecas necessárias (Flask, Gunicorn, NumPy, etc.)
├── Dockerfile                   # Imagem Docker segura (Python 3.14, usuário sem privilégios)
├── compose.yaml                 # Projeto trab02_2026_2_12621cbs213: container, porta 2213:5000, volume /dados e reinício automático
├── .dockerignore                # Arquivos que nunca entram na imagem (dados, testes, .env)
│
├── src/
│   ├── api/
│   │   ├── aplicacao.py         # Rotas REST (Flask), validações e o diário
│   │   └── aero/                # Interface web (HTML, CSS e JavaScript, sem dependências externas)
│   │       ├── index.html       #   o desktop: papel de parede, barra de tarefas e menu iniciar
│   │       ├── aero.css         #   visual (vidro, gradientes, janelas no estilo XP)
│   │       ├── nucleo.js        #   chamadas à API e dados compartilhados
│   │       ├── janelas.js       #   abrir, arrastar, minimizar e fechar janelas; diálogos
│   │       ├── icones.js        #   ícones desenhados em SVG (e a Gota)
│   │       ├── desenho.js       #   desenho do mapa em canvas
│   │       ├── app_mapa.js      #   Mapa da Rede
│   │       ├── app_matrizes.js  #   Matrizes (mapa de calor) e gráfico de barras
│   │       ├── app_ativos.js    #   Gerenciador de Ativos (CRUD)
│   │       ├── app_monitor.js   #   Monitor do Serviço e diário
│   │       ├── explicacoes.js   #   o que o Assistente explica (cálculo, guia e código)
│   │       ├── app_assistente.js #  a Gota: menu, tour e o passo a passo
│   │       └── desktop.js       #   ícones, menu iniciar, bandeja e tela de entrada
│   ├── modelos/                 # Classes de Ativo, Vulnerabilidade, Dependência e Enums
│   ├── persistencia/            # JSON com gravação atômica, Factory (fabrica_ativos.py) e Repository (repositorio.py)
│   │   ├── repositorio_sqlite.py   #   repositórios em SQLite (mesma interface do JSON)
│   │   ├── fabrica_repositorios.py #   escolhe JSON ou SQLite pela variável PERSISTENCIA
│   │   └── esquema.sql             #   as 4 tabelas
│   └── servicos/
│       ├── analise_risco.py     # Monta M, v, F e A; resolve (I − A)x = b, diagnostica e explica as etapas
│       ├── diario.py            # Anotação periódica do risco (prova das 24 h)
│       ├── ordenacao.py         # Critérios de ordenação (padrão Strategy)
│       ├── orientacao_seguranca.py # O que é cada tipo de falha e como prevenir (CWE)
│       ├── cliente_nvd.py       # Consulta ao NVD com cache e limite de requisições
│       ├── gerenciador_*.py     # Cadastro de ativos e de dependências
│       ├── relatorios_sql.py    # Relatórios feitos com SQL (JOIN, GROUP BY) sobre o SQLite
│       └── consultas.py         # Consultas com map, filter, sorted e reduce
│
├── testes/                      # Testes automatizados do sistema, da API e do SQLite (test_sqlite.py)
├── sql/                         # esquema.sql e consultas.sql (JOINs, agregações)
├── scripts/                     # verificar_servico.py (24 h), cliente_requests.py, migrar_json_para_sqlite.py e relatorio_sql.py
├── docs/                        # API.md (rotas REST), PADROES.md (padrões de projeto), ARQUITETURA.md (cliente-servidor, com diagrama) e BANCO_DE_DADOS.md (SQLite, JOINs e relatórios)
└── dados_ficticios/             # Rede de exemplo para visualizar a interface (fora do Git)
```

Os arquivos de dados (`ativos.json`, `dependencias.json`, `cache_cve.json`, `diario.json` e `inventario.db`) são criados pelo próprio programa durante o uso, ficam na pasta de `DADOS_DIR` (no Docker, dentro do volume) e não devem ir para o repositório.

---

## ⚠️ Limitações conhecidas

- A API **não tem autenticação**: qualquer pessoa que alcance a porta `2213` pode alterar os dados. O acesso fica limitado pela rede do servidor; o controle de usuários e perfis está previsto como trabalho futuro.
- **Não rode o menu de terminal e a API ao mesmo tempo sobre os mesmos arquivos:** cada um guarda os dados na memória por conta própria, e um sobrescreveria as mudanças do outro.
- A "descrição curta" de um CVE é a primeira frase do texto do NVD, cortada em tamanho fixo e em inglês; não é um resumo nem uma tradução.

---

## 🗺️ Próximas Melhorias (Roadmap)

- [x] **Interface Web Completa (Front-end):** desktop no estilo Windows XP consumindo as rotas do `aplicacao.py`.
- [x] **Visualização de Grafos de Dependência:** o Mapa da Rede, com o risco efetivo de cada ativo.
- [x] **Assistente explicativo:** o cálculo passo a passo com os dados reais e o mapa do código.
- [x] **Persistência em SQLite (opcional):** repositório, migração a partir do JSON e relatórios com JOIN e GROUP BY.
- [ ] **Autenticação na API:** exigir login ou chave para alterar dados.
- [ ] **Exportar relatórios:** baixar o risco e o diário em CSV pela interface.