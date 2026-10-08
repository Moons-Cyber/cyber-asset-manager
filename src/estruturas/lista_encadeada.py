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


lista = ListaEncadeada()

lista.append(10)
lista.append(20)
lista.append(30)

print(lista.head.dado)
print(lista.head.next.dado)
print(lista.head.next.next.dado)