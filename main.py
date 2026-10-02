from src.modelos.notebook import Notebook
from src.modelos.roteador import Roteador
from src.modelos.servidor import Servidor

notebook1 = Notebook(1, "Notebook A", "João", "TI", ["Vuln1", "Vuln2"], "16GB")
roteador1 = Roteador(2, "Roteador B", "Maria", "Redes", ["Vuln3"], "Modelo X")
servidor1 = Servidor(3, "Servidor C", "Carlos", "Infraestrutura", ["Vuln4", "Vuln5"], "Intel Xeon")


ativos = [notebook1, roteador1, servidor1]
for ativo in ativos:
    ativo.exibir_detalhes()
    print() 
    


