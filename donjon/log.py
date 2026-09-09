"""Journal de messages. L'UI et les tests lisent la même source."""


class MessageLog:
    def __init__(self, limit=400):
        self.entries = []
        self.limit = limit

    def add(self, text, turn=0):
        self.entries.append((turn, text))
        if len(self.entries) > self.limit:
            del self.entries[: len(self.entries) - self.limit]

    def tail(self, count=6):
        return [text for _, text in self.entries[-count:]]

    def texts(self):
        return [text for _, text in self.entries]

    def __len__(self):
        return len(self.entries)
