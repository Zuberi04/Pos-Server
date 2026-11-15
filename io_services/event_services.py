class IOServices:
    def __init__(self, sio: any):
        self.sio = sio
        print("Socket intialized successfully!!")

    @staticmethod
    async def timestamp():
        from datetime import datetime

        return datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

    async def no_data_sent(self):
        return {"error": "No data passed for processing!", "ts": await self.timestamp()}

    async def check_if_authenticated(self, user: str, sid: str):
        saved = await self.sio.get_session(sid)
        if not saved or not user in saved.values():
            return {"error": "False session connection"}
        from services.auth.validate import auth_validate, read_stmt

        for m in auth_validate.user_m:
            data = await read_stmt.read_stmt(m, user, flag="upd")
            if data:
                return data.__tablename__
        return {"error": "invalid credentials received for access!!"}

    async def generic_error(self, sid: str):
        return await self.sio.emit(
            "gen-error",
            {
                "message": "Server error occured try again in a min or two!",
                "ts": await self.timestamp(),
            },
            to=sid,
        )

    async def broadcast_emergency(
        self,
    ):
        return None
