import re

from utils.stmt import read_stmt
from database.models import AdminUser
from services.auth.token import auth_token
from services.auth.otp import gen_otp


class ValidateCreds:
    def __init__(self):
        self.r_matches = {
            "password": re.compile(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={}\[\]|\\:;\"'<>,.?/~`\-]).{8,}$"
            ),
            "email": re.compile(r"[A-Za-z0-9\@/a-z\./a-z/]"),
            "fullnames": re.compile(r"[A-Za-z]"),
        }

    async def clean_credentials(self, creds: dict):
        from utils.extras import clean_data

        print("Credentials received: \n", creds)
        creds = clean_data(creds)
        if not "token" in creds:
            for k in self.r_matches.keys():
                if not self.r_matches[k].fullmatch(creds[k]):
                    if not self.r_matches[k].match(creds[k]):
                        return {
                            "error": f"Missing or Invalid format for {k.capitalize()}"
                        }
            if "fullnames" and not "reset" in creds:
                return await self.sign_up_user(creds)
        return await self.validate_authentication(creds)

    async def validate_authentication(self, creds: dict | str):
        stmt = await read_stmt.read_stmt(
            AdminUser,
            (
                creds["id" if "id" in creds else "email"]
                if isinstance(creds, dict)
                else creds
            ),
        )
        if not stmt:
            return {"error": "Invalid user accessing system!!"}
        elif isinstance(creds, str):
            return None
        elif "password" in creds and not self.hash_or_compare(
            creds["password"], stmt["password"]
        ):
            if not "reset" in creds:
                return {"error": "Invalid user credentials passed!!"}
            creds["password"] = self.hash_or_compare(creds["password"])
            return await self.validate_otp(creds, stmt)
        elif not "token" in creds:
            return await self.validate_otp(creds, stmt)
        token = await auth_token.validate_token(creds)
        if not isinstance(token, bool):
            return token
        return await self.validate_otp(creds, stmt) if not token else creds

    @staticmethod
    async def validate_otp(creds: dict, stmt: dict):
        creds["otp"] = await gen_otp.check_if_validate_or_create(creds, stmt)
        if isinstance(creds["otp"], dict):
            return creds["otp"]
        return auth_token.generate_token(
            await read_stmt.update_db_entries(
                await read_stmt.read_stmt(AdminUser, stmt["id"], "upd"), creds
            )
        )

    async def sign_up_user(self, creds: dict):
        from r_services.service import r_service

        creds["password"] = self.hash_or_compare(creds["password"])
        hash = await gen_otp.check_if_validate_or_create(creds)
        if isinstance(hash, tuple):
            creds["otp"] = hash[0]
            wrote = await read_stmt.write_items_to_db(AdminUser, creds)
            r_service.cache_data(wrote["id"], {"used": hash[1]})
            return auth_token.generate_token(wrote)
        raise ValueError(f"Malformed value received from otp: {hash}")

    @staticmethod
    def hash_or_compare(password: str, db_pass: bytes = None):
        from bcrypt import checkpw, hashpw, gensalt

        if db_pass:
            return checkpw(password.encode("utf-8", errors="replace"), db_pass)
        return hashpw(
            password.encode("utf-8", errors="replace"), salt=gensalt(rounds=12)
        )


auth_validate = ValidateCreds()
