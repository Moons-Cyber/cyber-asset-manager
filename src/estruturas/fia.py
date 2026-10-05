from collections import deque


class Fila:
    def __init__(self):
        self.itens = []

    def enqueue(self, item):
        self.itens.append(item)


    def is_empty(self):
        return len(self.itens) == 0

    def dequeue(self):
        if not self.is_empty():
            return self.itens.pop(0)
        else:
            raise IndexError("Dequeue from an empty queue")

class FilaDeque:
    def __init__(self):
        self.itens = deque()

    def enqueue(self, item):
        self.itens.append(item)

    def is_empty(self):
        return len(self.itens) == 0

    def dequeue(self):
        if not self.is_empty():
            return self.itens.popleft()
        else:
            raise IndexError("Dequeue from an empty queue")



fila = Fila()
fila.enqueue("João")
fila.enqueue("Maria")
fila.enqueue("Carlos")

print(fila.dequeue())
print(fila.itens)



fila_deque = FilaDeque()
fila_deque.enqueue("João")
fila_deque.enqueue("Maria")
fila_deque.enqueue("Carlos")

print(fila_deque.dequeue())
print(fila_deque.itens)