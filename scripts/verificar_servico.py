#!/usr/bin/env python3
"""Verifica um serviço do inventário que já está em execução.

Serve para o container no seu computador e, depois, para o servidor do professor:
o script só precisa do endereço e usa apenas a biblioteca padrão do Python.

Uso:
    python scripts/verificar_servico.py http://localhost:5000
    python scripts/verificar_servico.py http://SERVIDOR:PORTA --testar-nvd
    python scripts/verificar_servico.py http://localhost:5000 --monitorar 24 --intervalo 60

Verificação (padrão): cria dois ativos de teste, exercita vulnerabilidade,
dependência e risco, e REMOVE tudo no final (mesmo se algo falhar no meio).
Os ativos de teste usam IDs altos (900001 e 900002); se já existirem, o script
para sem tocar neles.

Monitoramento (--monitorar HORAS): consulta /api/saude a cada --intervalo
segundos e grava um CSV com o horário, o código HTTP e a latência. Serve como
evidência do tempo no ar.

Código de saída: 0 tudo certo | 1 alguma verificação falhou | 2 sem conexão.
"""

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

ID_A, ID_B = 900001, 900002


def chamar(base, metodo, caminho, corpo=None, timeout=10):
    """Faz a requisição e devolve (status, corpo_json_ou_None)."""
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    requisicao = urllib.request.Request(
        base + caminho, data=dados, method=metodo,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
            texto = resposta.read().decode("utf-8")
            return resposta.status, json.loads(texto) if texto else None
    except urllib.error.HTTPError as erro:
        try:
            return erro.code, json.loads(erro.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return erro.code, None


class Relatorio:
    def __init__(self):
        self.falhas = 0

    def checar(self, nome, condicao, detalhe=""):
        marca = "OK   " if condicao else "FALHA"
        extra = f"  -> {detalhe}" if detalhe and not condicao else ""
        print(f"  [{marca}] {nome}{extra}")
        if not condicao:
            self.falhas += 1
        return condicao


def verificar(base, testar_nvd):
    rel = Relatorio()
    print(f"Verificando {base}\n")

    # Falha cedo e com mensagem clara se o serviço não responde.
    try:
        status, corpo = chamar(base, "GET", "/api/saude")
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        print(f"Não foi possível conectar a {base}: {erro}")
        return 2

    rel.checar("saúde responde 200 com status ok",
               status == 200 and (corpo or {}).get("status") == "ok",
               f"HTTP {status}: {corpo}")

    _, tipos = chamar(base, "GET", "/api/tipos")
    rel.checar("quatro tipos de ativo disponíveis",
               isinstance(tipos, list) and len(tipos) == 4, f"{tipos}")

    for identificador in (ID_A, ID_B):
        codigo = chamar(base, "GET", f"/api/ativos/{identificador}")[0]
        if codigo == 200:
            print(f"\nO ID de teste {identificador} já existe no servidor; "
                  "nada foi alterado.")
            return 1
        if codigo != 404:
            print(f"\nNão foi possível confirmar que o ID de teste {identificador} "
                  f"está livre (HTTP {codigo}); nada foi alterado.")
            return 1

    try:
        base_ativo = {"responsavel": "Teste", "setor": "Verificação"}

        s, c = chamar(base, "POST", "/api/ativos", {
            "id": ID_A, "tipo": 1, "nome": "TESTE notebook",
            "memoria_ram": "8GB", **base_ativo})
        rel.checar("cria notebook (201)", s == 201, f"HTTP {s}: {c}")

        s, c = chamar(base, "POST", "/api/ativos", {
            "id": ID_B, "tipo": 4, "nome": "TESTE banco",
            "sgbd": "PostgreSQL", **base_ativo})
        rel.checar("cria banco de dados (201)", s == 201, f"HTTP {s}: {c}")

        s, _ = chamar(base, "POST", "/api/ativos", {
            "id": ID_A, "tipo": 1, "nome": "x", "memoria_ram": "8GB", **base_ativo})
        rel.checar("ID repetido é recusado (409)", s == 409, f"HTTP {s}")

        s, _ = chamar(base, "POST", "/api/ativos", {
            "id": "texto", "tipo": 1, "nome": "x", "memoria_ram": "8GB", **base_ativo})
        rel.checar("entrada inválida é recusada (400)", s == 400, f"HTTP {s}")

        s, c = chamar(base, "POST", f"/api/ativos/{ID_A}/vulnerabilidades", {
            "descricao": "Vulnerabilidade de teste", "categoria": "Teste",
            "severidade": 8.0})
        rel.checar("adiciona vulnerabilidade manual (201, classificação Alta)",
                   s == 201 and (c or {}).get("classificacao") == "Alta",
                   f"HTTP {s}: {c}")
        id_vuln = (c or {}).get("id", "")

        s, _ = chamar(base, "POST", "/api/dependencias",
                      {"origem": ID_A, "destino": ID_B, "peso": 0.5})
        rel.checar("cadastra dependência (201)", s == 201, f"HTTP {s}")

        def riscos():
            s, c = chamar(base, "GET", "/api/risco")
            if s != 200:
                return s, None
            return s, {r["id"]: r for r in c["resultados"]}

        s, r = riscos()
        ok = (s == 200 and r[ID_A]["risco_proprio"] == 8.0
              and abs(r[ID_B]["risco_efetivo"] - 4.0) < 1e-9)
        rel.checar("risco: A próprio 8,0 e B efetivo 4,0 (= 0,5 × 8,0)", ok, f"HTTP {s}")

        s, _ = chamar(base, "PATCH",
                      f"/api/ativos/{ID_A}/vulnerabilidades/{id_vuln}",
                      {"status": "Corrigida"})
        rel.checar("marca a vulnerabilidade como Corrigida (200)", s == 200, f"HTTP {s}")

        s, r = riscos()
        ok = s == 200 and r[ID_A]["risco_efetivo"] == 0.0 and r[ID_B]["risco_efetivo"] == 0.0
        rel.checar("risco cai a zero depois de corrigir", ok, f"HTTP {s}")
    finally:
        # Limpeza SEMPRE: nada de teste pode sobrar nos dados do servidor.
        for identificador in (ID_A, ID_B):
            try:
                chamar(base, "DELETE", f"/api/ativos/{identificador}")
            except (urllib.error.URLError, TimeoutError, OSError):
                pass

    removidos = all(chamar(base, "GET", f"/api/ativos/{i}")[0] == 404 for i in (ID_A, ID_B))
    rel.checar("ativos de teste removidos (nada sobrou)", removidos)

    if testar_nvd:
        print("\nConsulta ao NVD (informativa; não conta como falha):")
        s, c = chamar(base, "GET", "/api/cve/CVE-2021-44228", timeout=40)
        if s == 200:
            print(f"  [INFO ] NVD acessível; nota do Log4Shell = {c.get('severidade')}")
        else:
            print(f"  [AVISO] NVD indisponível (HTTP {s}). O servidor tem internet "
                  "de saída? Sem ela, a nota do CVE precisa ser digitada.")

    print()
    if rel.falhas:
        print(f"RESULTADO: {rel.falhas} verificação(ões) falharam.")
        return 1
    print("RESULTADO: tudo certo.")
    return 0


def monitorar(base, horas, intervalo, arquivo):
    print(f"Monitorando {base}/api/saude por {horas} h, a cada {intervalo} s.")
    print(f"Registro em {arquivo}. Ctrl+C encerra e mostra o resumo.\n")

    total = falhas = sequencia = pior_sequencia = 0
    inicio = time.time()
    fim = inicio + horas * 3600

    with open(arquivo, "a", newline="", encoding="utf-8") as saida:
        escritor = csv.writer(saida, lineterminator="\n")
        if saida.tell() == 0:
            escritor.writerow(["momento", "http", "latencia_ms"])

        try:
            while time.time() < fim:
                t0 = time.time()
                try:
                    codigo, _ = chamar(base, "GET", "/api/saude", timeout=10)
                except (urllib.error.URLError, TimeoutError, OSError):
                    codigo = 0                       # 0 = sem resposta
                latencia = round((time.time() - t0) * 1000)

                total += 1
                if codigo == 200:
                    sequencia = 0
                else:
                    falhas += 1
                    sequencia += 1
                    pior_sequencia = max(pior_sequencia, sequencia)

                escritor.writerow([datetime.now().isoformat(timespec="seconds"),
                                   codigo, latencia])
                saida.flush()
                time.sleep(intervalo)
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário.")

    duracao = (time.time() - inicio) / 3600
    disponibilidade = 100 * (total - falhas) / total if total else 0
    print(f"\nResumo: {total} consultas em {duracao:.2f} h | falhas: {falhas} | "
          f"disponibilidade: {disponibilidade:.2f}% | maior sequência de falhas: "
          f"{pior_sequencia}")
    return 0 if falhas == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Verifica um serviço do inventário.")
    parser.add_argument("url", help="ex.: http://localhost:5000")
    parser.add_argument("--testar-nvd", action="store_true",
                        help="testa também a consulta ao NVD (precisa de internet)")
    parser.add_argument("--monitorar", type=float, metavar="HORAS",
                        help="em vez de verificar, monitora /api/saude por N horas")
    parser.add_argument("--intervalo", type=float, default=60, metavar="SEG",
                        help="segundos entre consultas no monitoramento (padrão 60)")
    parser.add_argument("--saida", default="monitoramento.csv",
                        help="CSV do monitoramento (padrão monitoramento.csv)")
    args = parser.parse_args()

    base = args.url.rstrip("/")

    if args.monitorar:
        return monitorar(base, args.monitorar, args.intervalo, args.saida)

    return verificar(base, args.testar_nvd)


if __name__ == "__main__":
    sys.exit(main())
