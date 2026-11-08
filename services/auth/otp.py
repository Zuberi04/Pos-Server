import hmac


class OtpGeneration:
    def __init__(self):
        self.move = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        self.keys = ["fullnames", "email"]

    def check_if_validate_or_create(self, creds: dict, stmt: dict = None):
        if stmt and stmt["otp"]:
            for k in self.keys:
                if not k in creds:
                    creds[k] = stmt[k]
            return self.validate_otp(self.create_otp(creds), stmt["otp"], creds)
        elif not "id" in creds and not stmt:
            return self.create_otp(creds)
        return {"error": "Invalid authentication detected!!"}

    def create_otp(self, creds: dict, otp: str = None, l: int = 0):
        from math import sqrt

        while (
            not otp or len(otp) < (len(creds["fullnames"]) + len(creds["email"])) * 0.5
        ):
            if not l:
                l = int(sqrt(len(creds["fullnames"]) + len(creds["email"])))
            print(f"Otp with values:{otp} with an l of:{l} ")
            for k in self.keys:
                if k in creds:
                    if l >= len(creds[k]) * 0.65:
                        l = int(sqrt(len(creds[k])) / l * 0.65)
                    elif not otp:
                        otp = creds[k][int(l * 0.5) : int(l * 1.5)]
                    else:
                        y = creds[k].replace(otp, "").strip()
                        otp = otp + y[int(l * 0.3) : int(l * 1.2)]
            l += int(sqrt(len(otp)))
        print("OTP created with value: ", otp)
        return self.create_otp_hash([c for c in otp])

    def create_otp_hash(self, otp: list, hash_t: dict = {}, t: str = ""):
        for item in otp:
            if len(t) < 2:
                t = t + item
            else:
                hash_t[bytes(t.encode("utf-8", errors="replace"))] = t
                t = ""
        return self.create_hash(hash_t.keys())

    @staticmethod
    def create_hash(keys: set[bytes]):
        return "".join([k.hex() for k in keys])

    def validate_otp(self, otp: str, hashed: str, creds: dict):
        if hmac.compare_digest(otp, hashed):
            return self.create_otp(creds)
        return {"error": "invalid authentication!!"}


gen_otp = OtpGeneration()
