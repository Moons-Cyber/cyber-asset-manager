"""Modelo de vulnerabilidade, identificada por um ID próprio."""

import hashlib
import re

from src.modelos.enums import Severidade, StatusVulnerabilidade

PADRAO_CVE = re.compile(r"^CVE-\d{4}-\d{4,}$")


def normalizar_cve(texto):
    """Devolve o ID em maiúsculas se for um CVE válido; senão, None."""
    candidato = texto.strip().upper()
    return candidato if PADRAO_CVE.match(candidato) else None


def _id_local(descricao, categoria):
    """ID determinístico para vulnerabilidades sem CVE."""

    
    base = f"{descricao.strip().lower()}|{categoria.strip().lower()}"
    return "LOCAL-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]


class Vulnerabilidade:
    def __init__(self, descricao, categoria, severidade, status,
                 id=None, fonte="manual"):
        if isinstance(severidade, bool) or not isinstance(severidade, (int, float)):
            raise ValueError("A severidade deve ser um número.")
        if not 0 <= severidade <= 10:
            raise ValueError("A severidade deve estar entre 0 e 10.")

        if not isinstance(status, StatusVulnerabilidade):
            status = StatusVulnerabilidade(status)  # aceita o texto do JSON

        self.descricao = descricao
        self.categoria = categoria
        self.severidade = float(severidade)
        self.status = status
        self.fonte = fonte  # "NVD" ou "manual"
        self.id = id or _id_local(descricao, categoria)

    @property
    def classificacao(self):
        """Severidade textual (baixa/média/alta/crítica) derivada da nota."""
        return Severidade.a_partir_da_nota(self.severidade)

    def para_dict(self):
        return {
            "id": self.id,
            "descricao": self.descricao,
            "categoria": self.categoria,
            "severidade": self.severidade,
            "status": self.status.value,
            "fonte": self.fonte,
        }

    @classmethod
    def de_dict(cls, dados):
        """Recria o objeto; aceita registros antigos sem 'id' nem 'fonte'."""
        return cls(
            descricao=dados["descricao"],
            categoria=dados["categoria"],
            severidade=dados["severidade"],
            status=dados["status"],
            id=dados.get("id"),
            fonte=dados.get("fonte", "manual"),
        )

    def __str__(self):
        return (
            f"[{self.id}] {self.descricao} | Categoria: {self.categoria} | "
            f"Nota: {self.severidade:.1f} ({self.classificacao.value}) | "
            f"Status: {self.status.value}"
        )