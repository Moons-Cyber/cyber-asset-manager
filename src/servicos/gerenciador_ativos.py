"""Serviço responsável pelo gerenciamento dos ativos."""


from pathlib import Path

from src.modelos.enums import StatusVulnerabilidade
from src.modelos.vulnerabilidades import Vulnerabilidade
from src.persistencia.persistencia import Persistencia

CAMPOS_COMUNS = {"nome", "responsavel", "setor", "vulnerabilidades"}

CAMPOS_ESPECIFICOS = {
    "Notebook": {"memoria_ram"},
    "Servidor": {"processador"},
    "Roteador": {"modelo"},
}


class GerenciadorAtivos:
    """Gerencia cadastro, consulta, atualização e remoção de ativos.

    Os objetos devolvidos são os mesmos que estão na memória do gerenciador.
    Para alterar um ativo, use os métodos daqui (atualizar_ativo etc.):
    mudar o objeto por fora altera a memória sem gravar no arquivo.
    """

    def __init__(self, caminho_arquivo="ativos.json"):
        self.caminho_arquivo = Path(caminho_arquivo)
        self.persistencia = Persistencia()
        # dict {id: ativo}. None = ainda não carregado (carga sob demanda).
        self._ativos = None

    # ------------------------------------------------------------ memória
    def _indice(self):
        """Devolve o dict de ativos, lendo o arquivo só na primeira vez.

        A carga é preguiçosa de propósito: se o arquivo estiver corrompido,
        o erro aparece quando o usuário usa o menu (onde é tratado), e não
        ao iniciar o programa. Como _ativos só é preenchido quando a leitura
        dá certo, corrigir o arquivo e tentar de novo funciona.
        """
        if self._ativos is None:
            self._ativos = self._ler_do_arquivo()

        return self._ativos

    def _ler_do_arquivo(self):
        if not self.caminho_arquivo.exists():
            return {}

        ativos = {}

        for ativo in self.persistencia.carregar_dados(self.caminho_arquivo):
            # Num dict, um ID repetido sobrescreveria o anterior em silêncio.
            if ativo.id in ativos:
                raise ValueError(
                    f"O arquivo contém o ID {ativo.id} repetido."
                )

            ativos[ativo.id] = ativo

        return ativos

    def recarregar(self):
        """Descarta a memória; a próxima consulta relê o arquivo.

        Útil se o JSON foi editado à mão enquanto o programa estava aberto.
        """
        self._ativos = None

    def _salvar(self):
        """Grava a memória no arquivo.

        Se a gravação falhar, a memória pode ter ficado adiantada em relação
        ao disco. Descartá-la garante que a próxima leitura volte ao estado
        real do arquivo (que a gravação atômica deixa intacto).
        """
        try:
            self.persistencia.salvar_dados(
                list(self._ativos.values()),
                self.caminho_arquivo,
            )
        except Exception:
            self._ativos = None
            raise

    # ----------------------------------------------------------- consultas
    def listar_ativos(self):
        """Retorna todos os ativos cadastrados, na ordem de cadastro."""
        return list(self._indice().values())

    def buscar_ativo_por_id(self, identificador):
        """Busca um ativo pelo ID (acesso direto no dict) ou retorna None."""
        return self._indice().get(identificador)

    def buscar_ativos_por_nome(self, texto):
        """Busca ativos cujo nome contenha o texto, ignorando maiúsculas.

        Devolve uma lista porque o nome, ao contrário do ID, não é único.
        """
        termo = texto.strip().lower()

        if not termo:
            return []

        return [
            ativo
            for ativo in self._indice().values()
            if termo in ativo.nome.lower()
        ]

    # ------------------------------------------------------------- escrita
    def cadastrar_ativo(self, ativo):
        """Cadastra um ativo, impedindo IDs duplicados."""
        indice = self._indice()

        if ativo.id in indice:
            raise ValueError(f"Já existe um ativo com ID {ativo.id}.")

        indice[ativo.id] = ativo
        self._salvar()

        return ativo

    def atualizar_ativo(self, identificador, **alteracoes):
        """Atualiza os campos permitidos e salva o JSON."""
        if not alteracoes:
            raise ValueError("Informe pelo menos um campo para atualizar.")

        ativo = self.buscar_ativo_por_id(identificador)

        if ativo is None:
            return None

        campos_permitidos = CAMPOS_COMUNS | CAMPOS_ESPECIFICOS.get(
            ativo.obter_tipo(), set()
        )

        campos_invalidos = set(alteracoes) - campos_permitidos

        if campos_invalidos:
            raise ValueError(
                "Campos não permitidos: " + ", ".join(sorted(campos_invalidos))
            )

        if "vulnerabilidades" in alteracoes:
            vulnerabilidades = alteracoes["vulnerabilidades"]

            if not isinstance(vulnerabilidades, list):
                raise TypeError("Vulnerabilidades deve ser uma lista.")

            if not all(
                isinstance(item, Vulnerabilidade) for item in vulnerabilidades
            ):
                raise TypeError("A lista deve conter objetos Vulnerabilidade.")

        # Toda a validação acima vem ANTES de mexer no objeto.
        for campo, valor in alteracoes.items():
            setattr(ativo, campo, valor)

        self._salvar()

        return ativo

    def remover_ativo(self, identificador):
        """Remove um ativo e persiste a alteração."""
        indice = self._indice()

        if identificador not in indice:
            return False

        del indice[identificador]
        self._salvar()

        return True

    def adicionar_vulnerabilidade(self, identificador, vulnerabilidade):
        """Acrescenta UMA vulnerabilidade a um ativo já cadastrado.

        Diferente de atualizar_ativo(vulnerabilidades=...), que substitui
        a lista inteira, aqui as existentes são preservadas.
        Devolve o ativo, ou None se o ID não existir.
        """
        if not isinstance(vulnerabilidade, Vulnerabilidade):
            raise TypeError("Informe um objeto Vulnerabilidade.")

        ativo = self.buscar_ativo_por_id(identificador)

        if ativo is None:
            return None

        # O mesmo ID duas vezes no mesmo ativo viraria uma só coluna em M.
        if any(v.id == vulnerabilidade.id for v in ativo.vulnerabilidades):
            raise ValueError(
                f"O ativo '{ativo.nome}' já possui a vulnerabilidade "
                f"{vulnerabilidade.id}."
            )

        ativo.vulnerabilidades.append(vulnerabilidade)
        self._salvar()

        return ativo

    def atualizar_status_vulnerabilidade(
        self, identificador, id_vulnerabilidade, novo_status
    ):
        """Muda o status de uma vulnerabilidade de um ativo.

        Devolve a vulnerabilidade alterada, ou None se o ativo não existir.
        """
        if not isinstance(novo_status, StatusVulnerabilidade):
            raise TypeError("O status deve ser um StatusVulnerabilidade.")

        ativo = self.buscar_ativo_por_id(identificador)

        if ativo is None:
            return None

        for vulnerabilidade in ativo.vulnerabilidades:
            if vulnerabilidade.id == id_vulnerabilidade:
                vulnerabilidade.status = novo_status
                self._salvar()
                return vulnerabilidade

        raise ValueError(
            f"O ativo '{ativo.nome}' não possui a vulnerabilidade "
            f"{id_vulnerabilidade}."
        )