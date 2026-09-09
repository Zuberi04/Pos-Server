import datetime

from utils.stmt import read_stmt
from database.models import AdminUser
from services.auth.validate import auth_validate
from services.pos.accounts import accounts
from r_services.service import r_service


class IOServices:
    def __init__(self, sio: any):
        self.sio = sio
        print("Socket intialized successfully!!")

    @staticmethod
    async def timestamp():
        return datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

    async def check_otp_validity(self, data: str):
        user = read_stmt.read_stmt(AdminUser, data)
        if not user:
            error = auth_validate.invalid_creds()
            error["ts"] = await self.timestamp()
            return error

        return None

    async def no_data_sent(self):
        return {"error": "No data passed for processing!", "ts": await self.timestamp()}

    async def generic_error(self, sid: str):
        return await self.sio.emit(
            "gen-error",
            {
                "message": "Server error occured handling error routine!",
                "ts": await self.timestamp(),
            },
            to=sid,
        )

    @staticmethod
    async def collect_db_analysis(data: dict):
        if not data:
            raise ValueError("Error, missing credentials from user!!")
        res = await accounts.collect_data_to_process(data)
        if not res:
            raise ValueError("Error, failed to analyse db data and balance accounts!!")
        elif "error" in res:
            return res
        cached = r_service.cache_data(data["id"], res)
        if cached < 0:
            raise ValueError("Error, failed to cache data from analysis")
        return res
