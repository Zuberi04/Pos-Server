from re import compile

from utils.stmt import read_stmt
from database.models import AdminUser
from services.auth.token import auth_token
from services.auth.otp import gen_otp


class ValidateCreds:
    def __init__(self):
        self.r_matches = {
            "password": compile(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={}\[\]|\\:;\"'<>,.?/~`\-]).{8,}$"
            ),
            "email": compile(r"[A-Za-z0-9\@/a-z\./a-z/]"),
            "fullnames": compile(r"[A-Za-z]"),
        }

    async def clean_credentials(self, creds: dict, out: bool = False):
        from utils.extras import clean_data

        print("Credentials received: \n", creds)
        creds = clean_data(creds, flag="auth")
        if out:
            for k in creds.copy().keys():
                if not k in self.r_matches:
                    del creds[k]
        elif "fullnames" in creds:
            try:
                del creds["token"]
            except KeyError:
                print("No token found in creds!!")
        elif not "token" in creds:
            for k in self.r_matches.keys():
                if k in creds:
                    if not self.r_matches[k].fullmatch(creds[k]):
                        if not self.r_matches[k].match(creds[k]):
                            return {
                                "error": f"Missing or Invalid format for {k.capitalize()}"
                            }
        return await self.validate_authentication(creds)

    async def validate_authentication(
        self, creds: dict | str, stmt: dict | None = None
    ):
        stmt = await read_stmt.read_stmt(
            AdminUser,
            (
                creds["email" if "email" in creds else "id"]
                if isinstance(creds, dict)
                else creds
            ),
        )
        if not stmt:
            if "fullnames" in creds:
                try:
                    return await self.sign_up_user(creds)
                except TypeError:
                    return await self.clean_credentials(creds, True)
            return {"error": "Unknown user accessing system!!"}
        elif isinstance(creds, str):
            return None
        elif "password" in creds and not self.hash_or_compare(
            creds["password"].encode("utf-8", errors="replace"),
            stmt["password"],
        ):
            if not "reset" or "fullnames" in creds:
                return {"error": "Invalid user credentials passed!!"}
        elif "password" in creds:
            creds["password"] = self.hash_or_compare(creds["password"])
        elif "token" in creds:
            token = await auth_token.validate_token(creds)
            if token:
                return await read_stmt.delete_unneeded_data(token)
        try:
            return await self.validate_otp(creds, stmt)
        except Exception as e:
            raise ValueError(f"Error occurred with val: {e}") from e

    @staticmethod
    async def validate_otp(creds: dict, stmt: dict):
        creds["otp"] = await gen_otp.check_if_validate_or_create(creds, stmt)
        if isinstance(creds["otp"], str):
            return auth_token.generate_token(
                await read_stmt.update_db_entries(
                    await read_stmt.read_stmt(AdminUser, stmt["id"], flag="upd"),
                    creds,
                )
            )
        elif isinstance(creds["otp"], dict):
            return creds["otp"]
        raise ValueError("System error with malformed value otp tuple")

    async def sign_up_user(self, creds: dict):
        creds["password"] = self.hash_or_compare(creds["password"])
        hash = await gen_otp.check_if_validate_or_create(creds)
        if not isinstance(hash, tuple):
            raise TypeError(f"System error with type value: {type(hash), hash}")
        creds["otp"] = hash[0]
        wrote = await read_stmt.write_items_to_db(AdminUser, creds)
        from r_services.service import r_service

        r_service.cache_data(wrote["id"], {"used": hash[1]})
        return auth_token.generate_token(wrote)

    @staticmethod
    def hash_or_compare(password: str | bytes, db_pass: bytes = None):
        from bcrypt import checkpw, hashpw, gensalt

        if db_pass:
            try:
                return checkpw(password, db_pass)
            except Exception:
                if password.decode("utf-8", errors="replace") != db_pass:
                    return False
                return True
        elif isinstance(password, str):
            return hashpw(
                (password.encode("utf-8", errors="replace")),
                salt=gensalt(rounds=12),
            )
        return password


auth_validate = ValidateCreds()
