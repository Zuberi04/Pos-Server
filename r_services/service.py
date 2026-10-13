import redis
from dotenv import load_dotenv
from os import getenv
from utils.extras import create_user_key

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
            if not isinstance(v, (str, float, int)):
                data[k] = str(v)
        cache = r_client.hset(create_user_key(key), mapping=data)
        return r_client.expire(create_user_key(key), expire) if expire else cache

    @staticmethod
    async def collect_cache(key: str, flag: str = None):
        return (
            r_client.hgetall(create_user_key(key))
            if not flag
            else r_client.hget(create_user_key(key), flag)
        )


r_service = RedisServices()
