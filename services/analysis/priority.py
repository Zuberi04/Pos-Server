from heapq import heapify, heappop, heappush


class priority_queue:

    def __init__(self):
        self.queue = list()
        heapify(self.queue)
        self.index = dict()

    def push(self, priority, label):
        if label in self.index:
            self.queue = [(w, l) for w, l in self.queue if l != label]
            heapify(self.queue)
        heappush(self.queue, (priority, label))
        self.index[label] = priority
        return None

    def pop(self):
        return heappop(self.queue) if self.queue else None

    def __contains__(self):
        return self.index

    def __len__(self):
        return len(self.queue)


queue = priority_queue()
