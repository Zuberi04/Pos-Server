from hashlib import shake_256


class Password:
    def __init__(self):
        self.name = {"point", "of", "sales", "1234567890", "!@#$%^&*()_-+="}

    def create_password(self, l=16):
        p = ''
        for item in self.name:
            if len(p) >= l:
                break
            max = 0
            if len(item) > 2:
                max = int(len(item) * 0.7)
                if len(p) != max:
                    print('Gen password with max len for item: ', max)
                    if item[-1] not in p:
                        p = p + item[-1]
                    elif item[int(len(item) * 0.63)] not in p:
                        p = p + item[int(len(item) * 0.63)]
                    elif item[0] not in p:
                        p = p + item[0]
                continue
            elif item[0] not in p:
                p = p + item[0]
                continue
            continue


        return self.create_h_table(p)
    def create_h_table(self, p: str):
        table = {}
        for char in p:
            t = ''
            if len(t) != 2:
                t = t + char
            table[t.encode('utf-8')] = t
            t = ''
            continue
        key = b''
        for k in table.keys():
            key = key + k
            continue

        return self.hash_password(key)
    @staticmethod
    def hash_password(pwd: bytes):
        return shake_256(pwd).hexdigest(32)


pwd = Password()


# =======Add env data for postgres db config===============
