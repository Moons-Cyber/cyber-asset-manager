"""Gera um diário de 24 horas FICTÍCIO, só para ver a aba "Diário 24h".

Uso (na raiz do projeto):
    python ferramentas/gerar_diario_ficticio.py dados_ficticios

Simula: uma anotação por hora, o servidor fora do ar por 2 horas, e uma
correção de vulnerabilidade 6 horas atrás (o risco cai). Os números de cada
hora são calculados de verdade com os dados da pasta; só os horários são
inventados. NÃO use isto na pasta de dados real do teste de 24 h.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.modelos.enums import StatusVulnerabilidade  # noqa: E402
from src.persistencia.persistencia import gravar_json_atomico  # noqa: E402
from src.servicos.contagio import ranking_correcoes, montar_contagio  # noqa: E402
from src.servicos.diario_surto import anotar  # noqa: E402
from src.servicos.gerenciador_ativos import GerenciadorAtivos  # noqa: E402
from src.servicos.gerenciador_dependencias import GerenciadorDependencias  # noqa: E402


def main():
    pasta = Path(sys.argv[1] if len(sys.argv) > 1 else "dados_ficticios")
    ativos = GerenciadorAtivos(pasta / "ativos.json").listar_ativos()
    deps = GerenciadorDependencias(pasta / "dependencias.json").listar_dependencias()

    agora = int(time.time())
    entradas = []
    melhor = ranking_correcoes(ativos, montar_contagio(ativos, deps)[0])[:1]
    for h in range(24, -1, -1):
        if h in (10, 11):                       # servidor fora do ar
            continue
        if h == 6 and melhor:                   # alguém corrigiu a pior falha
            alvo = melhor[0]
            for a in ativos:
                for v in a.vulnerabilidades:
                    if a.id == alvo["ativo_id"] and v.id == alvo["vulnerabilidade_id"]:
                        v.status = StatusVulnerabilidade.CORRIGIDA
        motivo = "inicialização" if h == 24 else "periódica"
        entradas.append(anotar(ativos, deps, motivo, agora=agora - h * 3600 - 120))

    gravar_json_atomico({"entradas": entradas}, pasta / "diario_surto.json")
    print(f"{len(entradas)} anotações gravadas em {pasta / 'diario_surto.json'}")


if __name__ == "__main__":
    main()
