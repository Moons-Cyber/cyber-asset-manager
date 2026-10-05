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

