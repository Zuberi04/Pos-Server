import re
import bcrypt

from utils.stmt import read_stmt
from database.models import AdminUser
from services.auth.token import auth_token
from services.auth.otp import gen_otp


class ValidateCreds:
    def __init__(self):
        self.r_email = re.compile(r"[A-Za-z0-9\@/a-z\./a-z/]")
        self.r_pass = re.compile(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={}\[\]|\\:;\"'<>,.?/~`\-]).{8,}$"
        )

    async def clean_credentials(self, creds: dict):
        if not "email" in creds:
            return {"error": "Missing credentials for authorization!!"}

        from utils.extras import clean_str

        for k in creds.keys():
            if k.startswith(("pass", "ema")):
                m = False
                for r in [self.r_email, self.r_pass]:
                    if r.match(creds[k]):
                        m = True
                        break
                if not m:
                    return {"error": f"Invalid format for data: {k.capitalize()}"}
            else:
                creds[k] = clean_str(creds[k])

        stmt = read_stmt.read_stmt(
            AdminUser, query=creds["id" if "id" in creds else "email"]
        )
        if not stmt:
            return await self.sign_up_user(creds)
        return await self.validate_authentication(creds, stmt)

    async def validate_authentication(self, creds: dict | str, stmt: dict = None):
        if not stmt and isinstance(creds, str):
            stmt = read_stmt.read_stmt(AdminUser, creds)
            print("Stmt: \n", stmt)
            if not stmt or not "otp" in stmt:
                return {"error": "Invalid user creds passed"}
            return None
        creds["id"] = stmt["id"]
        if not "token" in creds:
            return await self.validate_otp(creds, stmt)
        elif "password" in creds:
            if not bcrypt.checkpw(creds["password"].encode("utf-8"), stmt["password"]):
                return {"error": "Invalid credentials passed!!"}
        token = await auth_token.validate_token(creds)
        if not isinstance(token, bool):
            return token
        elif not token:
            return await self.validate_otp(creds, stmt)
        return creds

    @staticmethod
    async def validate_otp(creds: dict, stmt: dict):
        otp = await gen_otp.check_if_validate_or_create(creds, stmt)
        if not isinstance(otp, (str, tuple)):
            return {"error": "Invalid credentials passed!!"}
        creds["otp"] = otp if isinstance(otp, str) else otp[0]
        return auth_token.generate_token(creds)

    async def sign_up_user(self, creds: dict):
        if not re.search(r"[A-Za-z]", creds["fullnames"]):
            return {"error": "Invalid format for your Fullnames!!"}

        from r_services.service import r_service

        creds["password"] = self.hash_password(creds["password"])
        hash, used = await gen_otp.check_if_validate_or_create(creds)
        creds["otp"] = hash
        wrote = read_stmt.write_items_to_db(AdminUser, creds)
        r_service.cache_data(wrote["id"], {"used": used})
        return auth_token.generate_token(wrote)

    @staticmethod
    def hash_password(password: str):
        return bcrypt.hashpw(password.encode("utf-8"), salt=bcrypt.gensalt())


auth_validate = ValidateCreds()
