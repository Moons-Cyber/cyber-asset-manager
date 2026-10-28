# 🛡️ Cyber Asset Manager (Inventário de Ativos e Análise de Risco)

Bem-vindo ao **Cyber Asset Manager**! Este é um sistema criado para gerenciar a segurança digital de uma rede de computadores. Com ele, você pode cadastrar equipamentos (**ativos**), registrar falhas de segurança (**vulnerabilidades / CVEs**) — buscando a gravidade delas automaticamente na internet (base oficial do NVD) — e mapear como um equipamento depende de outro.

A partir dessas informações, o programa realiza cálculos matemáticos para diagnosticar a rede e calcular o **risco efetivo** de cada equipamento, salvando tudo automaticamente em arquivos no computador (`ativos.json`, `dependencias.json` e `cache_cve.json`).

---

## 🚧 Aviso Importante (Status do Projeto)

Este projeto está em desenvolvimento contínuo (a API já está integrada à branch `main`):
* **Ainda não há Interface Web visual (telas com botões):** No momento, todas as ações são feitas pelo **Menu Interativo no Terminal** (`main.py`) ou através da **API REST em Flask** (`servidor.py` e `aplicacao.py`), que conversa através de textos organizados no formato **JSON**.
* **Pronto para a futura Interface Web:** A API já conta com rotas de pré-visualização de CVEs (`/api/cve/<cve_id>`) e listagem dinâmica de tipos (`/api/tipos`), preparadas exatamente para alimentar o futuro painel visual.

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

### Opção A: Rodando a API com Docker (Mais fácil — Recomendado!)
Com o [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e aberto no seu computador, você não precisa instalar o Python nem configurar nada manualmente.

1. No Terminal aberto dentro da pasta do projeto, digite:
   ```bash
   docker compose up -d --build
   ```
2. O Docker vai preparar o ambiente Python 3.14 e ligar o servidor **Gunicorn** na porta **5000** automaticamente.
3. Para ter certeza de que funcionou, abra o seu navegador de internet e acesse:
   ```text
   http://localhost:5000/api/saude
   ```
   Se a API estiver funcionando, a resposta deve indicar o status ok e a quantidade de ativos encontrados. O número pode variar conforme os dados existentes.
4. **Para desligar o servidor quando terminar:**
   ```bash
   docker compose down
   ```

> 💡 **Dica para servidores compartilhados ou uso avançado (`.env`):**  
> Você pode criar um arquivo chamado `.env` na pasta do projeto para trocar a porta (`HOST_PORT=5000`), o nome do container (`CONTAINER_NAME=inventario-ativos`) ou adicionar uma chave gratuita do NVD (`NVD_API_KEY=sua_chave`) para deixar as consultas de vulnerabilidades mais rápidas.

---

### Opção B: Rodando direto no Computador (Para usar o Menu no Terminal ou API sem Docker)

1. **Instale o Python:** Baixe em [python.org](https://www.python.org/downloads/). *(No Windows, marque a caixinha **"Add python.exe to PATH"** na primeira tela da instalação!)*
2. **Crie e ative o ambiente isolado (só precisa fazer na 1ª vez):**
   ```bash
   python -m venv .venv
   ```
   * Ative no **Windows (`cmd`)**:
     ```bash
     .venv\Scripts\activate
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
   * Para ligar o **Servidor da API** localmente:
     ```bash
     python servidor.py
     ```

---

## 🌐 Passo 3: Como usar a API passo a passo (Para Iniciantes)

Quando o servidor da API está ligado (na porta `5000`), você pode interagir com ele de duas formas:

### 1. Consultas rápidas direto pelo Navegador de Internet (`GET`)
Basta abrir o Google Chrome, Edge ou Firefox e colar qualquer um dos endereços abaixo na barra de endereços:

| O que você quer ver | Endereço para colar no Navegador | O que aparece na tela |
| :--- | :--- | :--- |
| **Página inicial da API** | `http://localhost:5000/` | Mostra o nome do serviço e o atalho de saúde. |
| **Saúde do sistema** | `http://localhost:5000/api/saude` | Confirma se os arquivos estão íntegros e quantos ativos existem. |
| **Tipos de equipamentos** | `http://localhost:5000/api/tipos` | Lista os códigos de tipos aceitos e qual campo extra cada um pede. |
| **Status de falhas aceitos** | `http://localhost:5000/api/status` | Mostra os status válidos (ex: aberta, mitigada, etc.). |
| **Listar todos os ativos** | `http://localhost:5000/api/ativos` | Lista todos os equipamentos cadastrados. |
| **Buscar ativo por nome** | `http://localhost:5000/api/ativos?q=Servidor` | Filtra apenas ativos que tenham a palavra buscada no nome. |
| **Filtrar ativo por tipo** | `http://localhost:5000/api/ativos?tipo=1` | Filtra equipamentos pelo número do código do tipo. |
| **Ver 1 ativo específico** | `http://localhost:5000/api/ativos/1` | Mostra os dados do ativo de ID `1`. |
| **Ver falhas de 1 ativo** | `http://localhost:5000/api/ativos/1/vulnerabilidades` | Lista as vulnerabilidades do ativo de ID `1`. |
| **Consultar um CVE oficial** | `http://localhost:5000/api/cve/CVE-2021-44228` | Busca a nota de gravidade e descrição direto na base mundial NVD. |
| **Listar dependências** | `http://localhost:5000/api/dependencias` | Mostra quais equipamentos dependem uns dos outros. |
| **Relatório de Risco Geral** | `http://localhost:5000/api/risco` | Calcula o risco efetivo de cada equipamento e o diagnóstico da rede. |

---

### 2. Cadastrando e alterando dados pelo Terminal (`POST`, `PATCH`, `DELETE`)

Como o navegador comum só faz consultas de leitura (`GET`), para **cadastrar**, **editar** ou **apagar** informações nós usamos o comando `curl` em uma nova janela do Terminal (ou programas visuais gratuitos como *Postman* ou *Insomnia*).

Veja a sequência completa para testar todas as funções do sistema:

#### A) Descobrir os tipos de ativos disponíveis
Primeiro, acesse `http://localhost:5000/api/tipos` no navegador. Você verá algo indicando o `codigo` de cada tipo (ex: `1`, `2`, etc.) e o nome do `campo` específico que aquele tipo exige.

#### B) Cadastrar um novo Ativo (`POST /api/ativos`)
Cada tipo exige um campo próprio (veja em `/api/tipos`). No exemplo abaixo, o tipo `2` (Servidor) exige o campo `processador`:

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
Quando uma falha for corrigida ou mitigada, você pode mudar o `status` dela (veja os nomes exatos aceitos em `http://localhost:5000/api/status`):

```bash
curl -X PATCH http://localhost:5000/api/ativos/1/vulnerabilidades/CVE-2021-44228 ^
  -H "Content-Type: application/json" ^
  -d "{\"status\": \"MITIGADA\"}"
```

#### E) Criar uma Dependência entre dois Ativos (`POST /api/dependencias`)
Se você cadastrou o ativo `1` e o ativo `2`, pode informar que o `1` depende do `2` com um determinado `peso` (impacto):

```bash
curl -X POST http://localhost:5000/api/dependencias ^
  -H "Content-Type: application/json" ^
  -d "{\"origem\": 1, \"destino\": 2, \"peso\": 0.5}"
```

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

---

## 🧪 Passo 4: Como rodar os Testes Automatizados

O projeto possui uma pasta `testes` para garantir que nenhuma regra de negócio, cálculo de risco ou rota da API quebre após alterações no código. Para executá-los localmente (com o `.venv` ativado):

```bash
python -m unittest discover -s testes
```
---

## 📂 Estrutura de Pastas do Projeto

```text
cyber-asset-manager/
│
├── main.py                      # Menu interativo para usar pelo Terminal
├── servidor.py                  # Ponto de entrada que liga o servidor HTTP da API
├── requirements.txt             # Bibliotecas necessárias (Flask, Gunicorn, NumPy, etc.)
├── Dockerfile                   # Configuração da imagem Docker segura (Python 3.14)
├── docker-compose.yml           # Orquestração do container, porta 5000 e volume /dados
├── .dockerignore                # Arquivos ignorados na criação da imagem Docker
│
├── src/                         # Código-fonte principal do sistema
│   ├── api/
│   │   └── aplicacao.py         # Rotas REST (Flask), validações e integração com serviços
│   ├── modelos/                 # Classes de Ativo, Vulnerabilidade, Dependência e Enums
│   ├── persistencia/            # Tratamento de leitura/gravação e erros de arquivos (ErroDados)
│   └── servicos/                # Gerenciadores, ClienteNVD e cálculo matemático de risco
│
├── testes/                      # Testes automatizados do sistema e da API
├── scripts/                     # Scripts utilitários de apoio
│
└── ativos.json                  # Banco de dados local dos equipamentos cadastrados
```

Os arquivos `dependencias.json` (conexões entre equipamentos) e `cache_cve.json` (cache das consultas ao NVD) são criados pelo próprio programa durante o uso e não fazem parte do repositório (estão no `.gitignore`).

---

## 🗺️ Próximas Melhorias (Roadmap)

- [ ] **Interface Web Completa (Front-end):** Criação de telas visuais no navegador consumindo todas as rotas já prontas do `aplicacao.py`.
- [ ] **Visualização de Grafos de Dependência:** Exibição visual das conexões entre ativos e do diagnóstico de fragilidade retornado por `/api/risco`.