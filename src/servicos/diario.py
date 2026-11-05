"""Diário do serviço: o container calcula o risco a cada hora e anota.

Serve para o teste de 24 horas: no fim, o diário mostra uma entrada por hora
(prova de que o servidor ficou no ar) e, em cada uma, o risco global da rede
calculado por (I - A)x = b naquele momento.

Fica num JSON (diario.json) na pasta de dados, ou seja, no volume do Docker.
Tem tamanho máximo e, se o arquivo estragar, recomeça vazio em vez de
derrubar o servidor: o diário é um extra, não pode quebrar o sistema.
"""

import json
import logging
import threading
import time
from pathlib import Path

from src.persistencia.persistencia import gravar_json_atomico
from src.servicos.analise_risco import calcular_risco_efetivo, diagnosticar_sistema

log = logging.getLogger(__name__)

MAX_ENTRADAS_PADRAO = 1000        # ~41 dias com uma entrada por hora


def anotar(ativos, dependencias, motivo, agora=None):
    """Calcula o risco e resume o resultado numa entrada do diário (função pura)."""
    entrada = {
        "t": int(agora if agora is not None else time.time()),
        "motivo": motivo,
        "ativos": len(ativos),
        "dependencias": len(dependencias),
        "risco_global": None,
        "invertivel": None,
        "condicao": None,
        "erro": None,
    }
    try:
        diagnostico = diagnosticar_sistema(ativos, dependencias)
        resultados = calcular_risco_efetivo(ativos, dependencias)
    except ValueError as erro:
        entrada["erro"] = str(erro)
        return entrada

    entrada["risco_global"] = round(sum(r["risco_efetivo"] for r in resultados), 4)
    if diagnostico is not None:
        entrada["invertivel"] = diagnostico["invertivel"]
        entrada["condicao"] = round(diagnostico["condicao"], 4)
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
            log.warning("diario.json ilegível; o diário recomeça vazio.")
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
        self._thread = threading.Thread(target=self._rodar, name="diario", daemon=True)

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
                log.exception("Falha ao anotar o diário")
