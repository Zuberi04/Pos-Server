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

    async def generic_error(self, sid: str):
        return await self.sio.emit(
            "gen-error",
            {
                "message": "Server error occured handling error routine!",
                "ts": await self.timestamp(),
            },
            to=sid,
        )
