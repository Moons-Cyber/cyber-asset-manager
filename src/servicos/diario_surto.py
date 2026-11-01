"""Diário do surto: o container roda uma simulação a cada hora e anota.

Serve para o teste de 24 horas: no fim, o diário mostra uma entrada por
hora (o servidor ficou no ar) e, em cada uma, o Monte Carlo concordando com
a álgebra linear.

Fica num JSON (diario_surto.json) na pasta de dados, ou seja, no volume do
Docker. Tem tamanho máximo e, se o arquivo estragar, recomeça vazio em vez
de derrubar o servidor: o diário é um extra, não pode quebrar o sistema.
"""

import json
import logging
import threading
import time
from pathlib import Path

from src.persistencia.persistencia import gravar_json_atomico
from src.servicos.contagio import analisar_surto

log = logging.getLogger(__name__)

MAX_ENTRADAS_PADRAO = 1000        # ~41 dias com uma entrada por hora


def anotar(ativos, dependencias, motivo, rodadas=2000, agora=None):
    """Roda um surto e resume o resultado numa entrada do diário (função pura)."""
    entrada = {
        "t": int(agora if agora is not None else time.time()),
        "motivo": motivo,
        "ativos": len(ativos),
        "dependencias": len(dependencias),
        "risco_global": None,
        "monte_carlo": None,
        "rodadas": 0,
        "erro_relativo": None,
        "rho": None,
        "erro": None,
    }
    try:
        resultado = analisar_surto(ativos, dependencias, rodadas=rodadas)
    except ValueError as erro:
        entrada["erro"] = str(erro)
        return entrada

    entrada.update({
        "risco_global": resultado["risco_global"],
        "monte_carlo": round(resultado["monte_carlo"]["global"], 4),
        "rodadas": resultado["monte_carlo"]["rodadas"],
        "erro_relativo": resultado["erro_relativo"],
        "rho": round(resultado["rho"], 6),
    })
    return entrada


class Diario:
    """Lista de entradas, em memória e no disco, com tamanho máximo."""

    def __init__(self, caminho, max_entradas=MAX_ENTRADAS_PADRAO):
        self.caminho = Path(caminho)
        self.max_entradas = max(10, int(max_entradas))
        self._trava = threading.Lock()
        self._entradas = self._carregar()

    def _carregar(self):
        if not self.caminho.exists():
            return []
        try:
            with self.caminho.open("r", encoding="utf-8") as arquivo:
                entradas = json.load(arquivo)["entradas"]
            return [e for e in entradas if isinstance(e, dict) and "t" in e][-self.max_entradas:]
        except (OSError, ValueError, KeyError, TypeError):
            log.warning("diario_surto.json ilegível; o diário recomeça vazio.")
            return []

    def adicionar(self, entrada):
        with self._trava:
            self._entradas.append(entrada)
            del self._entradas[:-self.max_entradas]
            gravar_json_atomico({"entradas": self._entradas}, self.caminho)

    def listar(self, limite=None):
        with self._trava:
            entradas = list(self._entradas)
        return entradas[-limite:] if limite else entradas


class GravadorPeriodico:
    """Thread de fundo que chama `tarefa("periódica")` a cada `intervalo` s.

    Só é ligada em produção (servidor.py); nos testes fica desligada.
    """

    def __init__(self, tarefa, intervalo):
        self._tarefa = tarefa
        self.intervalo = intervalo
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._rodar, name="diario-do-surto", daemon=True)

    def iniciar(self):
        self._thread.start()

    def parar(self):
        self._parar.set()

    def _rodar(self):
        # wait() devolve True se mandaram parar; False quando o tempo acaba.
        while not self._parar.wait(self.intervalo):
            try:
                self._tarefa("periódica")
            except Exception:                   # o diário nunca derruba o servidor
                log.exception("Falha ao anotar o surto periódico")
