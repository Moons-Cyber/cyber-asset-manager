# 🛡️ Cyber Asset Manager (Inventário de Ativos e Análise de Risco)

Bem-vindo ao **Cyber Asset Manager**! Este é um sistema criado para gerenciar a segurança digital de uma rede de computadores. Com ele, você pode cadastrar equipamentos (**ativos**), registrar falhas de segurança (**vulnerabilidades / CVEs**) — buscando a gravidade delas automaticamente na internet (base oficial do NVD) — e mapear como um equipamento depende de outro.

A partir dessas informações, o programa usa **álgebra linear** para diagnosticar a rede e calcular o **risco efetivo** de cada equipamento, salvando tudo automaticamente em arquivos JSON (`ativos.json`, `dependencias.json` e `cache_cve.json`).

O sistema pode ser usado de três jeitos, todos sobre o mesmo núcleo:

* **Interface web Surto** (`/surto`): o risco da rede mostrado como uma epidemia em pixel art, com cadastro completo de ativos, falhas e dependências.
* **API REST em Flask** (`servidor.py`): conversa em JSON; é o que roda no container Docker.
* **Menu interativo no terminal** (`main.py`).

---

## 💻 Passo 1: Como abrir o Terminal e baixar o projeto

Para executar os comandos deste guia, você precisa abrir o **Terminal** (Prompt de Comando) do seu computador:
* **No Windows:** Aperte a tecla `Windows` no teclado, digite `cmd` e aperte `Enter`.
* **No Linux ou Mac:** Procure pelo aplicativo chamado `Terminal` e abra-o.

Se você tiver o [Git](https://git-scm.com/downloads) instalado, copie e cole os comandos abaixo (um por linha, apertando `Enter` ao final de cada um):

```bash
git clone https://github.com/Moons-Cyber/cyber-asset-manager.git
cd cyber-asset-manager
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
2. O Docker vai preparar o ambiente Python 3.14 e ligar o servidor **Gunicorn** na porta **5000** automaticamente.
3. Para ter certeza de que funcionou, confira se o container está saudável (`healthy`):
   ```bash
   docker ps
   ```
   e abra no navegador:
   ```text
   http://localhost:5000/api/saude     (a API respondendo)
   http://localhost:5000/surto         (a interface web)
   ```
4. **Para desligar o servidor quando terminar:**
   ```bash
   docker compose down
   ```
   Os dados ficam guardados no volume `dados` (pasta `/dados` dentro do container) e continuam lá na próxima vez que você ligar. Só um `docker compose down -v` apaga o volume.

> 💡 **Dica para servidores compartilhados ou uso avançado (`.env`):**  
> Você pode criar um arquivo chamado `.env` na pasta do projeto para trocar a porta (`HOST_PORT=5000`), o nome do container (`CONTAINER_NAME=inventario-ativos`) ou adicionar uma chave gratuita do NVD (`NVD_API_KEY=sua_chave`) para deixar as consultas de vulnerabilidades mais rápidas.

> 🔒 **Por segurança, a porta só é publicada em `127.0.0.1`** (o próprio computador). Num servidor remoto, para ver a interface no seu navegador, abra um túnel SSH e acesse `http://127.0.0.1:5000/surto` no seu PC:
> ```bash
> ssh -L 5000:127.0.0.1:5000 SEU_USUARIO@ENDERECO_DO_SERVIDOR
> ```

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
     Depois abra `http://localhost:5000/surto` no navegador.

### Quer ver a interface com dados de exemplo?
A pasta `dados_ficticios/` traz uma rede de exemplo (10 ativos e 11 dependências). Para não misturar com os seus dados reais, aponte o servidor para ela:

* **Windows (PowerShell):**
  ```powershell
  python ferramentas\gerar_diario_ficticio.py dados_ficticios
  $env:DADOS_DIR="dados_ficticios"; python servidor.py
  ```
* **Linux ou Mac:**
  ```bash
  python ferramentas/gerar_diario_ficticio.py dados_ficticios
  DADOS_DIR=dados_ficticios python servidor.py
  ```

O primeiro comando é opcional: ele cria um diário de 24 horas **fictício**, só para a aba "Diário 24h" ter o que mostrar. Nunca rode ele na pasta de dados do teste real.

### Configurações por variável de ambiente

| Variável | Para que serve | Padrão |
| :--- | :--- | :--- |
| `DADOS_DIR` | Pasta onde ficam `ativos.json`, `dependencias.json`, `cache_cve.json` e `diario_surto.json` | pasta atual (no Docker: `/dados`) |
| `HOST` / `PORT` | Endereço e porta do servidor de desenvolvimento | `127.0.0.1` / `5000` |
| `NVD_API_KEY` | Chave gratuita do NVD (consultas mais rápidas) | vazia |
| `SURTO_INTERVALO_S` | Segundos entre as simulações anotadas no diário (`0` = só ao ligar, `-1` = desliga) | `3600` (1 hora) |
| `SURTO_MAX_ENTRADAS` | Máximo de anotações guardadas no diário | `1000` |

---

## 🦠 A interface web: Surto

Abra `http://localhost:5000/surto`. A página não baixa nada da internet (fonte, desenhos e sons estão no próprio projeto), então funciona até num servidor sem acesso externo.

| Aba | O que faz |
| :--- | :--- |
| **Surto** | A rede vira uma cidade em pixel art: cada prédio é um ativo, cada estrada é uma dependência. Ao apertar **Iniciar surto**, milhares de epidemias são sorteadas e a média delas vai se aproximando do risco calculado pela álgebra linear. Ao lado ficam o **R0** (raio espectral), o gráfico *sorteio × álgebra*, a tabela ativo por ativo e a matriz A com o diagnóstico. Embaixo, a **Defesa** ordena as correções que mais derrubam o risco global; o botão **Corrigir** grava de verdade pela API (e **Desfazer** volta). |
| **Ativos** | Cadastro completo: criar, editar e excluir ativos; adicionar falhas (com ou sem CVE) e mudar o status; criar e remover dependências. |
| **Diário 24h** | Uma simulação por hora, gravada pelo próprio servidor. É a prova de que o container ficou no ar: hora sem marca = servidor fora do ar. |
| **Como funciona** | A explicação da matemática em linguagem simples. |

Atalhos na aba Surto: `espaço` inicia/pausa, `R` zera. O controle **Pesos** multiplica todos os pesos **só na simulação** (os dados não mudam), para mostrar o surto explodindo quando o R0 passa de 1. O som 8-bit começa desligado.

---

## 🧮 A matemática do risco (resumo)

1. **Risco próprio:** `b = F · (M · v)`. A matriz `M` marca quais falhas abertas cada ativo tem, `v` traz as notas CVSS e `F` é o fator de exposição de cada tipo (servidor 1,5; roteador 1,2; notebook e banco de dados 1,0).
2. **Dependências:** `A[destino][origem] = peso` — a fração do risco da origem que chega no destino.
3. **Risco efetivo:** `x = b + A·x`, ou seja, **`(I − A)·x = b`**, resolvido com `np.linalg.solve` (fatoração LU, sem calcular a inversa). Antes de resolver, o sistema confere:
   * o **posto** de `I − A` (precisa ser cheio);
   * o **número de condição κ**: rejeita se κ > 1/ε (≈ 4,5·10¹⁵, singular para o computador) e avisa se κ > 10⁸ (sobram menos de 8 dos 16 dígitos do `float64`);
   * o **determinante**, só como informação (ele não decide sozinho).

   Depois, coloca `x` de volta na equação e compara `(I − A)·x` com `b` usando `allclose`. No código, o produto de matrizes é `@`: em NumPy, `*` multiplicaria elemento a elemento.
4. **Por que a soma dos pesos recebidos precisa ser menor que 1:** isso dá à matriz `I − A` dominância diagonal estrita, o que garante que ela é invertível. A soma precisa ficar abaixo de 1 com uma folga de `1e-9`, porque em ponto flutuante `0,7 + 0,2 + 0,1` dá `0,9999999999999999`, e uma comparação exata deixaria passar uma linha que na verdade soma 1. O fator de exposição multiplica só `b`: ele não altera `A`, então não muda a invertibilidade nem o número de condição.
5. **A mesma conta como epidemia:** `x = b + A·b + A²·b + …`. Cada infecção atravessa cada dependência com probabilidade igual ao peso; a média de muitas epidemias sorteadas (método de Monte Carlo) chega no mesmo `x`. A série só termina quando o **raio espectral ρ(A)** — o R0 do surto — é menor que 1.
6. **Defesa:** corrigir uma falha de nota `s` no ativo `i` derruba o risco global em `fator_i × s × multiplicador_i`, em que o multiplicador é a soma da coluna `i` de `(I − A)⁻¹`.

---

## 🌐 Passo 3: Como usar a API passo a passo (Para Iniciantes)

Quando o servidor da API está ligado (na porta `5000`), você pode interagir com ele de duas formas:

### 1. Consultas rápidas direto pelo Navegador de Internet (`GET`)
Basta abrir o Google Chrome, Edge ou Firefox e colar qualquer um dos endereços abaixo na barra de endereços:

| O que você quer ver | Endereço para colar no Navegador | O que aparece na tela |
| :--- | :--- | :--- |
| **Interface web** | `http://localhost:5000/surto` | A interface Surto (veja a seção acima). |
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
| **Surto (álgebra × sorteio)** | `http://localhost:5000/api/surto` | Matriz A, vetor b, solução do `solve`, R0, resultado do Monte Carlo e ranking de correções. Aceita `?escala=` (0,1 a 6), `?rodadas=` (100 a 20000) e `?semente=`. |
| **Diário do surto** | `http://localhost:5000/api/surto/diario` | As anotações de hora em hora (responde 404 se o diário estiver desligado). |

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

O projeto possui uma pasta `testes` com **227 testes** que garantem que nenhuma regra de negócio, cálculo de risco ou rota da API quebre após alterações no código. Para executá-los (com o `.venv` ativado), **na pasta raiz do projeto**:

```bash
python -m unittest discover -s testes -t .
```

Entre eles, `test_contagio.py` confere que a média das epidemias sorteadas chega no resultado do `np.linalg.solve`, e que a queda prevista pelo ranking de defesa bate com o recálculo completo.

---

## ⏱️ Teste de 24 horas (Docker no servidor)

1. Suba o container: `docker compose up -d --build`
2. Confira que está saudável: `docker ps` (deve aparecer `healthy`)
3. Rode a verificação completa (cria ativos de teste, confere vulnerabilidade, dependência e risco, e apaga tudo no final; código de saída `0` = tudo certo). Com `--testar-nvd`, testa também a consulta ao NVD:
   ```bash
   python scripts/verificar_servico.py http://127.0.0.1:5000
   ```
4. Monitore por 24 horas (uma consulta por minuto, gravada em `monitoramento.csv`):
   ```bash
   python scripts/verificar_servico.py http://127.0.0.1:5000 --monitorar 24 --intervalo 60
   ```
   Ao final, ele mostra a disponibilidade e a maior sequência de falhas.
5. Confira quando o container ligou e quantas vezes reiniciou:
   ```bash
   docker inspect -f '{{.State.StartedAt}} reinícios={{.RestartCount}}' inventario-ativos
   ```
6. No fim, a aba **Diário 24h** da interface mostra uma marca por hora em que o servidor esteve no ar.

O container reinicia sozinho se cair (`restart: unless-stopped`), os dados ficam no volume e toda gravação é atômica (um arquivo temporário substitui o antigo de uma vez só). Ele roda **um processo com 8 threads** de propósito: os ativos ficam num dicionário em memória, e vários processos teriam cópias diferentes dos dados.

> 💡 Num servidor compartilhado por vários alunos, crie um `.env` ao lado do `docker-compose.yml` para não colidir nome e porta com os dos colegas:
> ```
> HOST_PORT=5217
> CONTAINER_NAME=inventario-meunome
> IMAGE_TAG=1.0
> ```

---

## 📂 Estrutura de Pastas do Projeto

```text
cyber-asset-manager/
│
├── main.py                      # Menu interativo para usar pelo Terminal
├── servidor.py                  # Ponto de entrada da API (lê as variáveis de ambiente)
├── requirements.txt             # Bibliotecas necessárias (Flask, Gunicorn, NumPy, etc.)
├── Dockerfile                   # Imagem Docker segura (Python 3.14, usuário sem privilégios)
├── docker-compose.yml           # Container, porta 5000, volume /dados e reinício automático
├── .dockerignore                # Arquivos que nunca entram na imagem (dados, testes, .env)
│
├── src/
│   ├── api/
│   │   ├── aplicacao.py         # Rotas REST (Flask), validações e o diário do surto
│   │   └── surto/               # Interface web (HTML, CSS e JavaScript, sem dependências externas)
│   │       ├── index.html       #   estrutura das 4 abas
│   │       ├── surto.css        #   visual (paleta Sweetie 16, bordas "pixeladas")
│   │       ├── pixel.js         #   fonte 3x5 e sprites em pixel art
│   │       ├── simulacao.js     #   a epidemia sorteada no navegador
│   │       ├── app.js           #   cidade animada, painel da prova, ranking e diário
│   │       ├── ativos.js        #   cadastro (CRUD) de ativos, falhas e dependências
│   │       └── som.js           #   som 8-bit sintetizado
│   ├── modelos/                 # Classes de Ativo, Vulnerabilidade, Dependência e Enums
│   ├── persistencia/            # Leitura/gravação atômica em JSON e erros de arquivo (ErroDados)
│   └── servicos/
│       ├── analise_risco.py     # Monta M, v, F e A; resolve (I − A)x = b e diagnostica
│       ├── contagio.py          # Monte Carlo, raio espectral, multiplicadores e ranking de defesa
│       ├── diario_surto.py      # Anotação periódica do surto (prova das 24 h)
│       ├── cliente_nvd.py       # Consulta ao NVD com cache e limite de requisições
│       ├── gerenciador_*.py     # Cadastro de ativos e de dependências
│       └── consultas.py         # Consultas com map, filter, sorted e reduce
│
├── testes/                      # 227 testes automatizados do sistema e da API
├── scripts/                     # verificar_servico.py: verificação e monitoramento de 24 h
├── ferramentas/                 # gerar_diario_ficticio.py: diário de exemplo para a interface
└── dados_ficticios/             # Rede de exemplo para visualizar a interface (fora do Git)
```

Os arquivos de dados (`ativos.json`, `dependencias.json`, `cache_cve.json` e `diario_surto.json`) são criados pelo próprio programa durante o uso, ficam na pasta de `DADOS_DIR` (no Docker, dentro do volume) e não devem ir para o repositório.

---

## ⚠️ Limitações conhecidas

- A API **não tem autenticação**: qualquer pessoa que alcance a porta pode alterar os dados. Por isso o Docker publica a porta só em `127.0.0.1`.
- **Não rode o menu de terminal e a API ao mesmo tempo sobre os mesmos arquivos:** cada um guarda os dados na memória por conta própria, e um sobrescreveria as mudanças do outro.
- A "descrição curta" de um CVE é a primeira frase do texto do NVD, cortada em tamanho fixo e em inglês; não é um resumo nem uma tradução.

---

## 🗺️ Próximas Melhorias (Roadmap)

- [x] **Interface Web Completa (Front-end):** interface Surto consumindo as rotas do `aplicacao.py`.
- [x] **Visualização de Grafos de Dependência:** a rede desenhada como cidade, com o diagnóstico de `/api/risco` e o R0.
- [ ] **Autenticação na API:** exigir login ou chave para alterar dados.
- [ ] **Exportar relatórios:** baixar o risco e o diário em CSV pela interface.
