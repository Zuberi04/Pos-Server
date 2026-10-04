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

        creds = clean_data(creds)
        for k in self.r_matches.keys():
            if not k in creds or not self.r_matches[k].match(creds[k]):
                return {
                    "error": f"Missing or Invalid format for prop: {k.capitalize()}"
                }
        stmt = read_stmt.read_stmt(
            AdminUser, query=creds["id" if "id" in creds else "email"]
        )
        if not stmt:
            return await self.sign_up_user(creds)
        return await self.validate_authentication(creds, stmt)

    async def validate_authentication(self, creds: dict | str, stmt: dict = None):
        if not stmt and isinstance(creds, str):
            stmt = read_stmt.read_stmt(AdminUser, creds)
            if not stmt or not "otp" in stmt:
                return {"error": "Invalid user accessing system features!!"}
            return None
        elif not "token" in creds:
            return await self.validate_otp(creds, stmt)
        elif "password" in creds and not self.hash_or_compare(
            creds["password"], stmt["password"]
        ):
            return {"error": "Invalid user credentials passed!!"}
        token = await auth_token.validate_token(creds)
        if not isinstance(token, bool):
            return token
        elif not token:
            return await self.validate_otp(creds, stmt)
        return creds

    @staticmethod
    async def validate_otp(creds: dict, stmt: dict):
        creds["otp"] = await gen_otp.check_if_validate_or_create(creds, stmt)
        if isinstance(creds["otp"], dict):
            return creds["otp"]
        return auth_token.generate_token(
            await read_stmt.update_db_entries(
                read_stmt.read_stmt(AdminUser, stmt["id"], "upd"), creds
            )
        )

    async def sign_up_user(self, creds: dict):
        from r_services.service import r_service

        creds["password"] = self.hash_or_compare(creds["password"])
        hash, used = await gen_otp.check_if_validate_or_create(creds)
        creds["otp"] = hash
        wrote = read_stmt.write_items_to_db(AdminUser, creds)
        r_service.cache_data(wrote["id"], {"used": used})
        return auth_token.generate_token(wrote)

    @staticmethod
    def hash_or_compare(password: str, db_pass: bytes = None):
        from bcrypt import checkpw, hashpw, gensalt

        if db_pass:
            return checkpw(password.encode("utf-8", errors="replace"), db_pass)
        return hashpw(
            password.encode("utf-8", errors="replace"), salt=gensalt(rounds=10)
        )


auth_validate = ValidateCreds()
