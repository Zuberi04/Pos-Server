from hashlib import shake_256
from random import choice


class Password:
    def __init__(self):
        self.chars = {"point", "of", "sales", "1234567890", "!@#$%^&*()_-+="}

    def password(self, l=16):
        return self._create_password(l)

    def _create_password(self, l: int):
        p = ""
        while len(p) < l:
            for item in self.chars:
                if len(item) > 2:
                    max = len(item) * 0.7 - 1
                    while len(p) < max:
                        char = choice(item)
                        if char in p and p.count(char) >= 3:
                            continue
                        p = p + char
                    continue
                p = p + choice(item)

        return self.hash_password(p.encode("utf-8"))

    @staticmethod
    def hash_password(pwd: bytes):
        return shake_256(pwd).hexdigest(32)


pwd = Password()
