class Node:

    def __init__(self, dado):
        self.dado = dado
        self.next = None


class ListaEncadeada:

    def __init__(self):
        self.head = None

    def append(self, dado):
        novo_no = Node(dado)

        if self.head is None:
            self.head = novo_no
            return

        atual = self.head

        while atual.next is not None:
            atual = atual.next

        atual.next = novo_no

    def exibir(self):
        atual = self.head

        while atual is not None:
            print(atual.dado)
            atual = atual.next

    def buscar(self, dado):
        atual = self.head

        while atual is not None:
            if atual.dado == dado:
                return atual

            atual = atual.next

        return None

    def remover(self, dado):
        atual = self.head
        anterior = None

        while atual is not None:

            if atual.dado == dado:

                if anterior is None:
                    self.head = atual.next
                else:
                    anterior.next = atual.next

                return atual

            anterior = atual
            atual = atual.next

        return None
    

lista = ListaEncadeada()

lista.append(10)
lista.append(20)
lista.append(30)

print("Antes:")
lista.exibir()

lista.remover(20)

print("Depois:")
lista.exibir()


lista.remover(10)
lista.exibir()

lista.remover(30)
lista.exibir()