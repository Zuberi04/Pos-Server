from re import compile

from utils.stmt import read_stmt
from database.models import AdminUser, Users
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
        self.user_m = (AdminUser, Users)

    async def clean_credentials(self, creds: dict):
        from utils.extras import clean_data

        print("Credentials received: \n", creds)
        creds = clean_data(creds, flag="auth")
        if "fullnames" in creds:
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

    @staticmethod
    def auth_error(err: str = "invalid"):
        return {"error": f"Authentication {err}"}

    async def validate_authentication(
        self, creds: dict | str, stmt: dict | None = None
    ):
        for m in self.user_m:
            stmt = await read_stmt.read_stmt(
                m,
                (
                    creds["email" if "email" in creds else "id"]
                    if isinstance(creds, dict)
                    else creds
                ),
            )
            if stmt:
                if isinstance(creds, dict):
                    for k in self.r_matches:
                        if k in creds and stmt:
                            if isinstance(creds[k], type(stmt[k])):
                                if creds[k] != stmt[k] and k != "password":
                                    if "password" in creds:
                                        return self.auth_error()
                                    return await self.add_sub_client(creds)
                            elif not self.hash_or_compare(
                                creds[k].encode("utf-8", errors="replace"), stmt[k]
                            ):
                                try:
                                    if creds["reset"]:
                                        creds[k] = self.hash_or_compare(creds[k])
                                        return await self.validate_otp(creds, stmt)
                                except KeyError:
                                    return self.auth_error()
                    if "token" in creds:
                        token = await auth_token.validate_token(creds)
                        if token:
                            return token
                    return await self.validate_otp(creds, stmt)
                return m.__tablename__
        if self.r_matches.keys() == creds.keys() and not stmt:
            return await self.sign_up_user(creds)
        return self.auth_error("non-exist")

    async def validate_otp(self, creds: dict, stmt: dict):
        creds["otp"] = gen_otp.check_if_validate_or_create(creds, stmt)
        if not isinstance(creds["otp"], dict):
            return auth_token.generate_token(
                await read_stmt.update_db_entries(
                    await read_stmt.read_stmt(AdminUser, stmt["id"], flag="upd"),
                    creds,
                )
            )
        return creds["otp"]

    async def sign_up_user(self, creds: dict):
        creds["password"] = self.hash_or_compare(creds["password"])
        creds["otp"] = gen_otp.check_if_validate_or_create(creds)
        return auth_token.generate_token(
            await read_stmt.write_items_to_db(AdminUser, creds)
        )

    async def add_sub_client(user: dict):
        from utils.rel import relshp

        user[relshp.check_if_model_contains_relations(Users)[1]] = user["id"]
        del user["id"]
        stmt = await read_stmt.read_stmt(Users, user["id"], flag="upd")
        return await read_stmt.write_items_to_db(Users, user)

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
