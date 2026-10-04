import jwt
import datetime
from utils.extras import hash_jwt_key_for_user
from utils.stmt import read_stmt


class JwtTokens:
    def __init__(self):
        pass

    def generate_token(self, creds: dict):
        if len(creds) > 1:
            creds["token"] = jwt.encode(
                payload={
                    "id": read_stmt.convert_id(creds["id"]),
                    "email": creds["email"],
                    "expiry": self.create_expiry_ts(creds).isoformat(),
                },
                key=hash_jwt_key_for_user(creds["id"]),
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
                key=hash_jwt_key_for_user(creds["id"]),
                algorithms="HS512",
            )
            return True
        except jwt.DecodeError:
            from services.auth.otp import gen_otp
            from database.models import AdminUser

            return self.generate_token(
                await gen_otp.check_if_validate_or_create(
                    creds, read_stmt.read_stmt(AdminUser, creds["id"])
                )
            )

        except jwt.InvalidSignatureError:
            return {"error": "Invalid token presented!!"}
        except jwt.ExpiredSignatureError as e:
            return False

    @staticmethod
    def create_expiry_ts(creds: dict):
        if not "token" in creds:
            return datetime.datetime.now() + datetime.timedelta(hours=24)

        return datetime.datetime.now() + datetime.timedelta(hours=(24 * 30))


auth_token = JwtTokens()
