import redis
from dotenv import load_dotenv
from os import getenv
from utils.extras import create_user_cache_key

load_dotenv()

# ============Global redis client=====================
r_client = redis.Redis(
    host="localhost",
    # password=getenv("REDIS_PASSWORD", ""),
    port=6379,
    decode_responses=True,
)


class RedisServices:
    def __init__(self):
        pass

    def cache_data(self, key: str, data: dict, expire: float = None):
        for k, v in data.items():
            if not isinstance(v, str):
                data[k] = str(v)

        from utils.stmt import read_stmt

        cache = r_client.hset(
            create_user_cache_key(read_stmt.convert_id(key)), mapping=data
        )
        return (
            r_client.expire(create_user_cache_key(read_stmt.convert_id(key)), expire)
            if expire
            else cache
        )

    @staticmethod
    async def collect_cache(key: str, flag: str = None):
        from utils.stmt import read_stmt

        return (
            r_client.hgetall(create_user_cache_key(read_stmt.convert_id(key)))
            if not flag
            else r_client.hget(create_user_cache_key(read_stmt.convert_id(key)), flag)
        )


r_service = RedisServices()
