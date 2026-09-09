import re
import bcrypt

from utils.stmt import read_stmt
from database.models import AdminUser
from services.auth.token import auth_token
from services.auth.otp import gen_otp
from r_services.service import r_service
from utils.extras import create_user_cache_key


class ValidateCreds:
    def __init__(self):
        self.check = ["@", "!", "#", "$", "%", "&", "*", "^"]
        self.comp_email = re.compile(r"[A-Za-z0-9\@/a-z\./a-z/]")

    async def clean_credentials(self, creds: dict):
        if not "email" in creds:
            return {"error": "Missing credentials for authorization!!"}
        elif "id" in creds:
            stmt = read_stmt.read_stmt(AdminUser, query=creds["id"])
        else:
            stmt = read_stmt.read_stmt(AdminUser, creds["email"])

        if not stmt:
            return await self.sign_up_user(creds)
        elif not "id" in creds:
            creds["id"] = stmt["id"]

        return await self.validate_authentication(creds, stmt)

    async def validate_authentication(self, creds: dict, stmt: dict):

        if "password" in creds:
            auth = bcrypt.checkpw(creds["password"].encode("utf-8"), stmt["password"])
            if not auth:
                return self.invalid_creds()

        token = auth_token.validate_token(creds)
        if "error" in token:
            return token
        elif "warning" in token:
            otp, used = await gen_otp.check_if_validate_or_create(creds)
            creds["otp"] = otp
            creds["token"] = auth_token.generate_token(creds)
            r_service.cache_data(creds["id"], {"used": used}, (3600 * 24 * 30))
            return read_stmt.write_items_to_db(AdminUser, creds)
        return token

    async def sign_up_user(self, creds: dict):
        is_format = False
        for item in self.check:
            if creds["password"].find(item) != -1:
                print("required hints found in pass!!")
                is_format = True
                break
            continue
        if not is_format:
            print("Format not found!!")
            return self.invalid_creds()
        elif not re.search(r"[A-Za-z]", creds["fullnames"]):
            print("Unfit fullname for requirement")
            return self.invalid_creds()
        elif not self.comp_email.search(creds["email"]):
            print("Unfit email for requirement")
            return self.invalid_creds()
        data = {}
        for k, v in creds.items():
            if k:
                data[k] = v.lower().strip()
        data["password"] = self.hash_password(data["password"])
        otp, used = await gen_otp.check_if_validate_or_create(creds)
        data["otp"] = otp
        wrote = read_stmt.write_items_to_db(AdminUser, data)
        if not wrote:
            raise ValueError("Error, failed writing to db!!")
        r_service.cache_data(wrote["id"], {"used": used}, (3600 * 24 * 30))

        return read_stmt.delete_unneeded_data(auth_token.generate_token(wrote))

    def check_if_creds_values_exist(self, creds: dict):
        for k, v in creds.items():
            if not k:
                continue
            elif not isinstance(v, str):
                return self.invalid_creds()
            elif v == "":
                return self.invalid_creds()
            continue
        return True

    @staticmethod
    def hash_password(password: str):
        return bcrypt.hashpw(password.encode("utf-8"), salt=bcrypt.gensalt())

    @staticmethod
    def invalid_creds():
        return {"error": "Invalid credentials passed for authorization!!"}


auth_validate = ValidateCreds()
