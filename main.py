from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor
from src.persistencia.persistencia import Persistencia
from src.servicos.consultas import obter_nomes, filtrar_por_tipo, ordenar_por_nome, contar_vulnerabilidades, buscar_por_nome_recursivo


notebook1 = Notebook(1, "Notebook A", "João", "TI", ["Vuln1", "Vuln2"], "16GB")
roteador1 = Roteador(2, "Roteador B", "Maria", "Redes", ["Vuln3"], "Modelo X")
servidor1 = Servidor(3, "Servidor C", "Carlos", "Infraestrutura", ["Vuln4", "Vuln5"], "Intel Xeon")



persistencia = Persistencia()
persistencia.salvar_dados([notebook1, roteador1, servidor1], "ativos.json")


ativos = persistencia.carregar_dados("ativos.json")


print("=== TODOS OS ATIVOS ===")
for ativo in ativos:
    ativo.exibir_detalhes()
    print(f"Tipo: {ativo.obter_tipo()}")
    print()

print("\n=== NOMES DOS ATIVOS ===")
print(obter_nomes(ativos))


servidores = filtrar_por_tipo(ativos, Servidor)

print("\n=== SERVIDORES ===")
for servidor in servidores:
    servidor.exibir_detalhes()
    print(f"Tipo: {servidor.obter_tipo()}")
    print()


print("\n=== ATIVOS ORDENADOS POR NOME ===")
for ativo in ordenar_por_nome(ativos):
    print(ativo.nome)


print("\n=== TOTAL DE VULNERABILIDADES ===")
print(contar_vulnerabilidades(ativos))

