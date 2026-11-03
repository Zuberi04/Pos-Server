import hmac
from r_services.service import r_service
from utils.extras import decode_json_objects


class OtpGeneration:
    def __init__(self):
        pass

    async def check_if_validate_or_create(self, creds: dict, stmt: dict = None):
        if stmt:
            creds["id"] = stmt["id"]
            used = decode_json_objects(
                await r_service.collect_cache(creds["id"], "used")
            )
            print("Used:", used)
            if not used or not self.validate_otp(
                self.create_otp_hash(used), stmt["otp"]
            ):
                return {"error": "Invalid user accessing system"}
            elif "token" in creds:
                creds["upd"] = True
            return self.create_otp(creds, used)
        return self.create_otp(creds)

    def create_otp(self, creds: dict, used: list = None, mx=6 * 2 + 1):
        from random import choice

        otp = []
        while len(otp) < mx:
            for k in creds.keys():
                if isinstance(creds[k], str):
                    l = int((len(creds) / mx) * len(creds[k]) + len(otp))
                    while len(otp) in range(l):
                        c = choice(creds[k])
                        if not used or c not in used:
                            otp.append(c)
                        elif c not in otp:
                            otp.insert(used.count(c) - used.index(c), c)
        try:
            r_service.cache_data(creds["id"], {"used": otp})
            return self.create_otp_hash(otp)
        except KeyError:
            return (self.create_otp_hash(otp), otp)

    def create_otp_hash(self, otp: list, hash_t: dict = {}, t: str = ""):
        for item in otp:
            if len(t) < 2:
                t = t + item
            else:
                hash_t[bytes(t.encode("utf-8"))] = t
                t = ""
        return self.create_hash(hash_t.keys())

    @staticmethod
    def create_hash(keys: set[bytes]):
        return "".join([k.hex() for k in keys])

    @staticmethod
    def validate_otp(otp: str, hashed: str):
        return hmac.compare_digest(otp, hashed)

    def user_key_encrypt(self, key: str, res: str = None, i: int = 0):
        unique = "".join([k for k in key if key.count(k) == 1])
        same = "".join([k for k in key if k not in unique])
        while len(res) < len(key):
            for item in (unique, same):
                if item[i] not in res or item != unique:
                    res, item = self.concat("" if not res else res, item, i)
                    i = len(res)
                break
            i += 1 if len(res) != i else -1
        return res

    @staticmethod
    def concat(res: str, inp: str, x: int):
        return res + inp[x]


gen_otp = OtpGeneration()
