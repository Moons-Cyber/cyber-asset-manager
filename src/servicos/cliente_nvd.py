"""Cliente da API do NVD (National Vulnerability Database) para buscar CVEs."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

URL_NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# Limites do NVD: 5 requisições/30s sem chave; 50/30s com chave gratuita.
INTERVALO_SEM_CHAVE = 6.1
INTERVALO_COM_CHAVE = 0.7

# Ordem de preferência das versões do CVSS. Usamos sempre a mais recente
# disponível entre as v3.x para manter as notas comparáveis entre CVEs.
VERSOES_CVSS = ("cvssMetricV31", "cvssMetricV30", "cvssMetricV40", "cvssMetricV2")


class ErroNVD(Exception):
    """Classe base para erros de consulta ao NVD."""


class CVENaoEncontrado(ErroNVD):
    """O NVD respondeu, mas não conhece esse CVE."""


class NVDIndisponivel(ErroNVD):
    """Falha de rede, timeout, limite de taxa ou resposta inválida."""


@dataclass
class DadosCVE:
    cve_id: str
    descricao: str
    nota_cvss: float
    versao_cvss: str


def _requisicao_http(url, cabecalhos, timeout):
    """Faz o GET e devolve o JSON. Isolada para poder ser trocada nos testes."""
    requisicao = urllib.request.Request(url, headers=cabecalhos)
    with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
        return json.load(resposta)


class ClienteNVD:
    def __init__(self, arquivo_cache="cache_cve.json", chave_api=None,
                 timeout=15, requisicao=_requisicao_http):
        self.arquivo_cache = Path(arquivo_cache)
        self.chave_api = chave_api or os.environ.get("NVD_API_KEY")
        self.timeout = timeout
        self._requisicao = requisicao
        self._ultima_chamada = 0.0
        self._cache = self._carregar_cache()

    # ---------- cache ----------
    def _carregar_cache(self):
        if not self.arquivo_cache.exists():
            return {}
        try:
            with self.arquivo_cache.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}  # cache corrompido não pode derrubar o programa

    def _salvar_cache(self):
        with self.arquivo_cache.open("w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=4, ensure_ascii=False)

    # ---------- limite de taxa ----------
    def _respeitar_limite(self):
        intervalo = INTERVALO_COM_CHAVE if self.chave_api else INTERVALO_SEM_CHAVE
        espera = intervalo - (time.monotonic() - self._ultima_chamada)
        if espera > 0:
            time.sleep(espera)
        self._ultima_chamada = time.monotonic()

    # ---------- consulta ----------
    def consultar(self, cve_id):
        """Devolve DadosCVE do cache ou do NVD."""
        if cve_id in self._cache:
            return DadosCVE(**self._cache[cve_id])

        self._respeitar_limite()
        url = f"{URL_NVD}?{urllib.parse.urlencode({'cveId': cve_id})}"
        cabecalhos = {"apiKey": self.chave_api} if self.chave_api else {}

        try:
            resposta = self._requisicao(url, cabecalhos, self.timeout)
        except urllib.error.HTTPError as erro:
            if erro.code in (403, 429):
                raise NVDIndisponivel(
                    "Limite de requisições do NVD atingido. Aguarde "
                    "alguns segundos ou configure NVD_API_KEY."
                ) from erro
            raise NVDIndisponivel(f"O NVD respondeu com erro HTTP {erro.code}.") from erro
        except (urllib.error.URLError, TimeoutError, OSError) as erro:
            raise NVDIndisponivel("Não foi possível conectar ao NVD.") from erro
        except json.JSONDecodeError as erro:
            raise NVDIndisponivel("Resposta inválida do NVD.") from erro

        dados = self._interpretar(cve_id, resposta)
        self._cache[cve_id] = dados.__dict__
        self._salvar_cache()
        return dados

    @staticmethod
    def _interpretar(cve_id, resposta):
        """Extrai descrição e nota da resposta, sem assumir que os campos existem.

        Nem todo CVE tem nota (ex.: recém-publicados ainda sem análise),
        então cada nível do JSON é acessado de forma defensiva.
        """
        itens = resposta.get("vulnerabilities") or []
        if not itens:
            raise CVENaoEncontrado(f"{cve_id} não foi encontrado no NVD.")

        cve = itens[0].get("cve", {})

        descricao = ""
        for item in cve.get("descriptions", []):
            if item.get("lang") == "en":
                descricao = item.get("value", "")
                break

        metricas = cve.get("metrics", {})
        for versao in VERSOES_CVSS:
            entradas = metricas.get(versao)
            if not entradas:
                continue
            # Prefere a avaliação "Primary" (do NIST) à "Secondary" (do fornecedor).
            escolhida = next(
                (e for e in entradas if e.get("type") == "Primary"), entradas[0]
            )
            nota = escolhida.get("cvssData", {}).get("baseScore")
            if nota is not None:
                return DadosCVE(cve_id, descricao, float(nota), versao)

        raise CVENaoEncontrado(
            f"{cve_id} existe no NVD, mas ainda não tem nota CVSS publicada."
        )
