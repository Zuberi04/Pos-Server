import jwt

from utils.extras import create_user_key


class JwtTokens:
    def __init__(self):
        pass

    def generate_token(self, creds: dict):
        if len(creds) > 1:
            creds["token"] = jwt.encode(
                payload={
                    "id": creds["id"],
                    "email": creds["email"],
                    "expiry": self.create_expiry_ts(creds).isoformat(),
                },
                key=create_user_key(creds["id"], "jwt"),
                algorithm="HS512",
            )
            if not creds["token"]:
                raise ValueError("Error, failed generating token!!")
        return creds

    async def validate_token(
        self,
        creds: dict,
    ):
        if not creds:
            raise ValueError("Error, no data passed for token validation!!")
        try:
            jwt.decode(
                creds["token"],
                key=create_user_key(creds["id"], "jwt"),
                algorithms="HS512",
            )
            return True
        except jwt.DecodeError or jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidSignatureError:
            return {"error": "Invalid token presented!!"}

    @staticmethod
    def create_expiry_ts(creds: dict):
        import datetime

        if not "token" in creds:
            return datetime.datetime.now() + datetime.timedelta(hours=24)
        return datetime.datetime.now() + datetime.timedelta(hours=(24 * 30))


auth_token = JwtTokens()
