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
            elif creds["token"]:
                return creds
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
        if "id" in creds:
            r_service.cache_data(creds["id"], {"used": otp})
        return (
            (self.create_otp_hash(otp), otp)
            if not "id" in creds
            else self.create_otp_hash(otp)
        )

    def create_otp_hash(self, otp: list, hash_t: dict = {}):
        t = ""
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


gen_otp = OtpGeneration()
