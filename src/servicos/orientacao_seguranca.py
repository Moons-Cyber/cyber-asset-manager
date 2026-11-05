"""Orientação de segurança: o que é cada falha e como prevenir.

O Assistente da interface usa isto para explicar uma vulnerabilidade
cadastrada. Funciona sem internet e sem inteligência artificial: o tipo da
falha é reconhecido por palavras-chave na categoria e na descrição (em
português ou no texto oficial do NVD, em inglês), e cada tipo tem um texto
fixo, escrito com antecedência.

Cada tipo traz a referência CWE (Common Weakness Enumeration), o catálogo
público de tipos de fraqueza de software mantido pelo MITRE.
"""

import re
import unicodedata
from dataclasses import dataclass

from src.modelos.enums import Severidade, StatusVulnerabilidade
from src.servicos.analise_risco import explicar_calculo


def normalizar(texto):
    """Minúsculas e sem acentos: "Injeção" e "injecao" viram a mesma coisa."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


@dataclass(frozen=True)
class Orientacao:
    """Um tipo de falha, com a explicação e a prevenção."""

    chave: str
    titulo: str
    cwe: str
    padroes: tuple          # expressões regulares, já sem acento e em minúsculas
    o_que_e: str
    por_que_perigoso: str
    como_prevenir: tuple
    como_corrigir_agora: tuple

    def encontrar(self, texto):
        """Devolve o primeiro termo que reconhece este tipo em `texto`, ou None."""
        for padrao in self.padroes:
            achado = re.search(padrao, texto)
            if achado:
                return achado.group(0)
        return None


# A ordem importa: os tipos mais específicos vêm antes dos mais gerais
# (por exemplo, "injeção de SQL" antes de "execução remota").
ORIENTACOES = (
    Orientacao(
        "injecao_sql", "Injeção de SQL", "CWE-89",
        (r"\bsql ?injection\b", r"\binjec\w* (de )?sql\b", r"\bsqli\b", r"\binjec\w*\b.*\bsql\b"),
        "O sistema monta um comando para o banco de dados juntando pedaços de texto digitados pelo usuário. "
        "Um texto preparado de propósito muda o sentido do comando.",
        "Quem explora pode ler, alterar ou apagar dados do banco sem ter permissão, inclusive senhas e dados de clientes.",
        ("Usar consultas parametrizadas (prepared statements) em vez de juntar texto no comando SQL.",
         "Validar a entrada: aceitar só o formato esperado (números, datas, listas fechadas).",
         "Dar ao usuário do banco usado pela aplicação só as permissões de que ela precisa.",
         "Não mostrar mensagens de erro do banco para o usuário final."),
        ("Aplicar a atualização do fornecedor, se a falha for de um produto pronto.",
         "Revisar as consultas da tela afetada e trocar por consultas parametrizadas.",
         "Conferir nos registros (logs) do banco se houve acessos estranhos."),
    ),
    Orientacao(
        "injecao_comando", "Injeção de comandos do sistema", "CWE-78",
        (r"\bcommand injection\b", r"\bos command\b", r"\binjec\w* de comando", r"\bcomandos? do sistema\b"),
        "O programa repassa um texto vindo de fora para o terminal do sistema operacional, "
        "e esse texto pode carregar comandos extras.",
        "Os comandos rodam com as permissões do programa, então quem explora pode assumir o equipamento.",
        ("Evitar chamar o terminal; usar as funções próprias da linguagem para a mesma tarefa.",
         "Se for inevitável, passar os argumentos em lista, nunca montando uma linha de comando com texto.",
         "Rodar o serviço com um usuário sem privilégios de administrador."),
        ("Atualizar o software afetado.",
         "Desativar a funcionalidade vulnerável até a correção, se ela não for essencial."),
    ),
    Orientacao(
        "xss", "Cross-site scripting (XSS)", "CWE-79",
        (r"\bxss\b", r"\bcross.site scripting\b", r"\bscript malicioso\b"),
        "Uma página mostra um texto vindo do usuário sem tratá-lo, e o navegador executa esse texto como código.",
        "O código roda no navegador de quem abre a página: pode roubar a sessão, ler dados da tela ou agir em nome da vítima.",
        ("Tratar (escapar) todo texto antes de mostrar na página; nunca inserir texto do usuário como HTML.",
         "Usar textContent em vez de innerHTML no JavaScript (é o que a interface deste projeto faz).",
         "Ativar a política de segurança de conteúdo (Content-Security-Policy) no servidor web.",
         "Marcar os cookies de sessão como HttpOnly."),
        ("Atualizar o sistema web afetado.",
         "Encerrar as sessões ativas, se houver suspeita de roubo de sessão."),
    ),
    Orientacao(
        "csrf", "Requisição forjada (CSRF)", "CWE-352",
        (r"\bcsrf\b", r"\bcross.site request forgery\b", r"\brequisic\w* forjada\b"),
        "Um site malicioso faz o navegador da vítima enviar um pedido para outro sistema em que ela já está logada.",
        "O sistema acha que foi a própria vítima que pediu: troca de senha, transferência, exclusão de dados.",
        ("Exigir um token anti-CSRF em todo formulário que altera dados.",
         "Usar cookies com SameSite=Lax ou Strict.",
         "Pedir confirmação (ou a senha de novo) em ações importantes."),
        ("Atualizar o sistema afetado.",
         "Revisar as ações sensíveis feitas recentemente pelos usuários."),
    ),
    Orientacao(
        "caminho", "Acesso a arquivos fora da pasta (path traversal)", "CWE-22",
        (r"\bpath traversal\b", r"\bdirectory traversal\b", r"\btravessia de diretorio\b", r"\.\./"),
        "O sistema abre um arquivo pelo nome que veio no pedido, sem conferir se ele está dentro da pasta permitida.",
        "Quem explora consegue ler arquivos do servidor que não deveriam ser públicos, como configurações e senhas.",
        ("Servir só arquivos de uma lista permitida (a interface deste projeto faz isso em /aero/<nome>).",
         "Resolver o caminho completo e conferir que ele continua dentro da pasta permitida.",
         "Rodar o serviço com um usuário que só enxerga as pastas de que precisa."),
        ("Atualizar o software afetado.",
         "Trocar senhas e chaves que estavam em arquivos que podem ter sido lidos."),
    ),
    Orientacao(
        "desserializacao", "Desserialização insegura", "CWE-502",
        (r"\bdeserializ\w*", r"\bdesserializ\w*"),
        "O programa reconstrói objetos a partir de dados vindos de fora, e o formato usado permite embutir comandos.",
        "Na maioria dos casos, permite executar código no servidor.",
        ("Não desserializar dados de fontes não confiáveis com formatos que carregam código (como pickle).",
         "Preferir formatos só de dados, como JSON, e validar os campos (como a Factory deste projeto faz).",
         "Manter as bibliotecas atualizadas."),
        ("Atualizar a biblioteca ou o produto afetado.",
         "Bloquear a entrada desse tipo de dado até a correção."),
    ),
    Orientacao(
        "memoria", "Estouro de memória (buffer overflow)", "CWE-787",
        (r"\bbuffer overflow\b", r"\bout.of.bounds\b", r"\buse.after.free\b", r"\bmemory corruption\b",
         r"\bestouro de (memoria|buffer)\b", r"\bheap overflow\b", r"\bstack overflow\b"),
        "O programa escreve ou lê fora do espaço de memória reservado. É comum em softwares escritos em C e C++.",
        "Pode travar o programa ou, no pior caso, permitir executar código no equipamento.",
        ("Manter o software atualizado: esse tipo de falha é corrigido pelo fornecedor.",
         "Deixar ativas as proteções do sistema operacional (como ASLR e DEP).",
         "Reduzir a exposição: só deixar acessíveis pela rede os serviços necessários."),
        ("Aplicar a atualização de segurança do fornecedor.",
         "Enquanto não atualiza, limitar quem consegue alcançar o serviço pela rede."),
    ),
    Orientacao(
        "execucao_remota", "Execução remota de código", "CWE-94",
        (r"\bremote code execution\b", r"\brce\b", r"\bexecuc\w* remota\b", r"\barbitrary code\b",
         r"\bcodigo arbitrario\b", r"\bexecute (arbitrary )?code\b"),
        "Alguém pela rede consegue fazer o equipamento rodar um programa escolhido por ele.",
        "É uma das falhas mais graves: quem explora passa a controlar o equipamento e pode usá-lo para atacar o resto da rede.",
        ("Aplicar as atualizações de segurança assim que forem publicadas.",
         "Não expor serviços na internet sem necessidade; usar firewall.",
         "Rodar os serviços com usuários sem privilégios de administrador.",
         "Separar a rede em partes, para que um equipamento invadido não alcance todos os outros."),
        ("Aplicar a correção do fornecedor com prioridade máxima.",
         "Se não houver correção, isolar o equipamento da rede ou desligar o serviço afetado.",
         "Verificar se há sinais de invasão (processos, usuários ou conexões estranhas)."),
    ),
    Orientacao(
        "privilegio", "Elevação de privilégio", "CWE-269",
        (r"\bprivilege escalation\b", r"\belevation of privilege\b", r"\bescalat\w* (de )?privileg\w*",
         r"\belevac\w* de privilegio", r"\bprivilegio"),
        "Um usuário comum, ou um programa, consegue ganhar permissões de administrador sem ter direito.",
        "Com permissão de administrador, quem explora pode desativar proteções, instalar programas e esconder o que fez.",
        ("Seguir o princípio do menor privilégio: cada usuário e serviço só com as permissões necessárias.",
         "Manter o sistema operacional atualizado.",
         "Não usar a conta de administrador no dia a dia."),
        ("Aplicar a atualização do sistema operacional ou do programa afetado.",
         "Revisar quem tem permissão de administrador no equipamento."),
    ),
    Orientacao(
        "autenticacao", "Falha de autenticação", "CWE-287",
        (r"\bauthentication bypass\b", r"\bbypass\w* (de )?autentica\w*", r"\bimproper authentication\b",
         r"\bautentica\w*", r"\bauthentica\w*", r"\bsess(ao|ion) (fixation|hijack\w*)\b"),
        "O sistema não confere direito quem está entrando, e dá para acessar sem a senha correta.",
        "Quem explora entra como outro usuário, às vezes como administrador.",
        ("Usar autenticação em dois fatores, principalmente para administradores.",
         "Bloquear ou atrasar depois de várias tentativas erradas.",
         "Usar componentes de login prontos e atualizados, em vez de criar o próprio."),
        ("Atualizar o sistema afetado.",
         "Trocar as senhas e encerrar as sessões abertas."),
    ),
    Orientacao(
        "credenciais", "Senha padrão, fraca ou escrita no código", "CWE-798",
        (r"\bsenha\w*", r"\bpassword\w*", r"\bcredencia\w*", r"\bcredential\w*", r"\bhard.?coded\b",
         r"\bdefault (password|credential|account)\b"),
        "O equipamento aceita uma senha que vem de fábrica, uma senha fácil de adivinhar, ou uma senha gravada dentro do programa.",
        "Senhas de fábrica são públicas (estão nos manuais). Quem tenta, entra.",
        ("Trocar todas as senhas de fábrica na instalação.",
         "Exigir senhas longas e diferentes para cada sistema; usar um gerenciador de senhas.",
         "Nunca gravar senhas no código; usar variáveis de ambiente ou um cofre de segredos (este projeto lê a chave do NVD de uma variável de ambiente).",
         "Ativar a autenticação em dois fatores onde houver."),
        ("Trocar a senha agora, por uma longa e única.",
         "Conferir se a mesma senha é usada em outros equipamentos e trocar lá também.",
         "Verificar nos registros se houve acessos que ninguém reconhece."),
    ),
    Orientacao(
        "dados_expostos", "Exposição de dados sensíveis", "CWE-200",
        (r"\binformation disclosure\b", r"\bsensitive information\b", r"\bcleartext\b", r"\bvazamento\b",
         r"\bexposic\w* de dados\b", r"\btexto (puro|claro)\b", r"\bsem criptografia\b", r"\bcriptografi\w*",
         r"\bencrypt\w*", r"\b(ssl|tls)\b"),
        "Dados que deveriam ser protegidos ficam visíveis: trafegam sem criptografia, ou o sistema mostra mais do que devia.",
        "Senhas, dados pessoais e dados de clientes podem ser lidos por quem não deveria, o que também é problema perante a LGPD.",
        ("Usar HTTPS/TLS em toda comunicação com dados sensíveis.",
         "Guardar senhas com hash próprio para senhas (como bcrypt ou Argon2), nunca em texto.",
         "Mostrar e devolver só os dados necessários em cada tela e em cada resposta da API."),
        ("Ativar a criptografia na comunicação afetada.",
         "Avaliar quais dados podem ter vazado e, se forem pessoais, avisar o responsável pela LGPD."),
    ),
    Orientacao(
        "negacao_servico", "Negação de serviço (DoS)", "CWE-400",
        (r"\bdenial of service\b", r"\bddos\b", r"\bnegac\w* de servico\b", r"\bresource exhaustion\b",
         r"\besgotamento de recursos\b", r"\btravamento\b", r"\bcrash\w*\b"),
        "Um pedido malformado, ou muitos pedidos de uma vez, fazem o serviço travar ou ficar lento demais.",
        "O sistema fica fora do ar para quem precisa dele. Não rouba dados, mas para o trabalho.",
        ("Limitar a quantidade de pedidos por cliente (rate limiting).",
         "Definir tempo máximo e tamanho máximo para cada pedido.",
         "Monitorar a disponibilidade (como o diário de 24 horas deste projeto) e reiniciar sozinho se cair (restart: unless-stopped)."),
        ("Atualizar o software afetado.",
         "Enquanto isso, filtrar os pedidos problemáticos no firewall ou no proxy."),
    ),
    Orientacao(
        "desatualizado", "Software desatualizado ou sem suporte", "CWE-1104",
        (r"\bdesatualizad\w*", r"\bsem atualizac\w*", r"\boutdated\b", r"\bend.of.life\b", r"\beol\b",
         r"\bsem suporte\b", r"\bunsupported\b", r"\bversao antiga\b", r"\bfalta de (patch|atualizac\w*)"),
        "O equipamento roda uma versão antiga de um programa ou do sistema operacional, que já tem falhas conhecidas e publicadas.",
        "As falhas de versões antigas são públicas, e existem ferramentas prontas que as exploram automaticamente.",
        ("Ativar as atualizações automáticas de segurança.",
         "Manter um inventário com a versão de cada software (como este projeto faz com os ativos).",
         "Trocar sistemas que não recebem mais atualizações do fornecedor."),
        ("Atualizar para a versão mais recente com suporte.",
         "Se não der para atualizar logo, isolar o equipamento e limitar quem acessa."),
    ),
    Orientacao(
        "configuracao", "Configuração insegura", "CWE-16",
        (r"\bmisconfigur\w*", r"\bconfigurac\w*", r"\bporta aberta\b", r"\bopen port\b", r"\bexposto\b",
         r"\bpainel (de )?admin\w*", r"\bservico desnecessario\b"),
        "O equipamento funciona, mas está configurado de um jeito inseguro: serviços desnecessários ligados, portas abertas, painéis acessíveis.",
        "Cada serviço ligado sem necessidade é mais uma porta de entrada.",
        ("Partir de uma configuração mínima: desligar o que não é usado.",
         "Documentar a configuração esperada e revisar de tempos em tempos.",
         "Publicar serviços só para quem precisa (este projeto só abre a porta em 127.0.0.1)."),
        ("Desligar o serviço ou fechar a porta que não é necessária.",
         "Restringir o acesso ao painel de administração à rede interna."),
    ),
)

GENERICA = Orientacao(
    "generica", "Vulnerabilidade", "",
    (),
    "É uma fraqueza no equipamento ou em um programa dele que pode ser usada para causar dano. "
    "Pela descrição cadastrada, não deu para reconhecer de que tipo ela é.",
    "Depende do tipo. A nota de gravidade (0 a 10) indica o tamanho do estrago possível.",
    ("Manter o sistema e os programas atualizados.",
     "Seguir o princípio do menor privilégio.",
     "Expor na rede só os serviços necessários.",
     "Descrever melhor a falha (ou informar o CVE) para receber uma orientação específica."),
    ("Procurar o boletim do fornecedor ou o CVE da falha e aplicar a correção indicada.",
     "Se não houver correção, reduzir quem consegue alcançar o equipamento."),
)

POR_CHAVE = {o.chave: o for o in ORIENTACOES + (GENERICA,)}

# Dica que depende do tipo do ativo (polimorfismo seria exagero aqui:
# é só um texto por tipo, então um dicionário resolve).
DICA_POR_TIPO = {
    "Servidor": "Servidores publicam serviços na rede (fator de exposição 1,5): costumam ser o primeiro alvo. "
                "Priorize a correção e confira quais portas ele deixa abertas.",
    "Roteador": "O roteador é a porta de entrada da rede (fator 1,2). Troque as senhas do painel, "
                "desative a administração pela internet e mantenha o firmware atualizado.",
    "Notebook": "Notebooks ficam com uma pessoa e saem da empresa. Mantenha as atualizações automáticas, "
                "use uma conta sem administrador no dia a dia e cuidado com anexos e links.",
    "BancoDeDados": "O banco de dados guarda as informações mais valiosas. Deixe-o acessível só pela aplicação, "
                    "com um usuário de permissões mínimas, e mantenha backups testados.",
}

PRAZO_POR_GRAVIDADE = {
    Severidade.CRITICA: "Crítica (9,0 a 10): corrigir imediatamente, de preferência no mesmo dia.",
    Severidade.ALTA: "Alta (7,0 a 8,9): corrigir em poucos dias.",
    Severidade.MEDIA: "Média (4,0 a 6,9): planejar a correção nas próximas semanas.",
    Severidade.BAIXA: "Baixa (até 3,9): acompanhar e corrigir na próxima manutenção.",
}

TEXTO_POR_STATUS = {
    StatusVulnerabilidade.ABERTA: "Está aberta: ainda conta no cálculo do risco.",
    StatusVulnerabilidade.EM_TRATAMENTO: "Está em tratamento: alguém já está cuidando, mas ela continua contando no risco até ser corrigida.",
    StatusVulnerabilidade.CORRIGIDA: "Já foi corrigida e não conta mais no risco. As dicas de prevenção servem para ela não voltar.",
    StatusVulnerabilidade.RISCO_ACEITO: "Foi marcada como risco aceito: a empresa decidiu conviver com ela. Ela continua contando no risco.",
}


def reconhecer(vulnerabilidade):
    """Descobre o tipo da falha. Devolve (orientacao, onde_achou, termo).

    Procura primeiro na categoria (o que a pessoa escolheu), depois na
    descrição e, por último, no texto original do NVD.
    """
    fontes = (
        ("categoria", vulnerabilidade.categoria),
        ("descrição", vulnerabilidade.descricao),
        ("descrição do NVD", getattr(vulnerabilidade, "descricao_original", None)),
    )
    for onde, texto in fontes:
        texto = normalizar(texto)
        if not texto:
            continue
        for orientacao in ORIENTACOES:
            termo = orientacao.encontrar(texto)
            if termo:
                return orientacao, onde, termo
    return GENERICA, None, None


def orientar(ativo, vulnerabilidade):
    """Monta a orientação completa de uma falha de um ativo (sem o efeito no risco)."""
    orientacao, onde, termo = reconhecer(vulnerabilidade)
    return {
        "tipo": orientacao.chave,
        "titulo": orientacao.titulo,
        "cwe": orientacao.cwe or None,
        "reconhecido_por": onde,
        "termo": termo,
        "o_que_e": orientacao.o_que_e,
        "por_que_perigoso": orientacao.por_que_perigoso,
        "como_prevenir": list(orientacao.como_prevenir),
        "como_corrigir_agora": list(orientacao.como_corrigir_agora),
        "neste_ativo": DICA_POR_TIPO.get(ativo.obter_tipo()),
        "gravidade": PRAZO_POR_GRAVIDADE[vulnerabilidade.classificacao],
        "situacao": TEXTO_POR_STATUS[vulnerabilidade.status],
    }


def efeito_no_risco(ativos, dependencias, ativo, vulnerabilidade):
    """Quanto o risco próprio do ativo cai se esta falha for corrigida.

    Usa o mesmo cálculo oficial (explicar_calculo). Corrigir a falha tira a
    nota dela da soma do ativo, então o risco próprio cai fator × nota.
    Devolve None se o risco não puder ser calculado com os dados atuais.
    """
    try:
        passos = explicar_calculo(ativos, dependencias)
    except ValueError:
        return None

    i = next(k for k, a in enumerate(ativos) if a.id == ativo.id)
    fator = passos["ativos"][i]["fator"]
    # Uma falha repetida no mesmo ativo (mesmo ID e mesma nota) conta uma vez só
    # na matriz M; corrigir só uma das cópias não muda a soma.
    repetida = any(
        v is not vulnerabilidade and v.afeta_risco
        and (v.id, v.severidade) == (vulnerabilidade.id, vulnerabilidade.severidade)
        for v in ativo.vulnerabilidades
    )
    reducao = fator * vulnerabilidade.severidade if vulnerabilidade.afeta_risco and not repetida else 0.0
    return {
        "conta_no_risco": vulnerabilidade.afeta_risco,
        "fator": fator,
        "risco_proprio_atual": passos["b"][i],
        "reducao": reducao,
        "risco_proprio_sem_ela": passos["b"][i] - reducao,
        "risco_efetivo_atual": passos["x"][i] if passos["x"] else None,
        "passa_risco_para": [
            passos["ativos"][k]["nome"]
            for k, linha in enumerate(passos["A"]) if linha[i] > 0
        ],
    }
