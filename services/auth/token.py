import jwt
from utils.extras import create_user_key


class JwtTokens:
    def __init__(self):
        pass

    def generate_token(self, creds: dict):
        print("Creds passed for token generation!!")
        if len(creds) > 1:
            creds["token"] = jwt.encode(
                payload={
                    "email": creds["email"],
                    "expiry": self.create_expiry_ts(creds),
                },
                key=create_user_key(creds["id"], "jwt"),
                algorithm="HS512",
            )
            if not creds["token"]:
                raise ValueError("Error, failed generating token!!")
        return creds

    async def validate_token(self, creds: dict):
        try:
            jwt.decode(
                creds["token"],
                key=create_user_key(creds["id"], "jwt"),
                algorithms="HS512",
            )
            return creds
        except jwt.DecodeError as e:
            raise ValueError(
                f"Error occured decoding token with value: \n\t {e}"
            ) from e
        except jwt.ExpiredSignatureError:
            return {"error": "Login to activate session token"}
        except jwt.InvalidSignatureError:
            return {"error": "Invalid token authorization passed for signing!!"}

    @staticmethod
    def create_expiry_ts(creds: dict):
        import datetime

        if not "token" in creds:
            return datetime.datetime.now() + datetime.timedelta(hours=12)
        return datetime.datetime.now() + datetime.timedelta(hours=(24 * 2))


auth_token = JwtTokens()
