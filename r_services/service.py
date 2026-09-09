import redis
from utils.extras import create_user_cache_key

r_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)


class RedisServices:
    def __init__(self):
        self.ex: float = 3600

    def cache_data(self, key: str, data: dict, expire: float = None):
        self.ex = 3600
        if not expire is None:
            self.ex = expire
        for k, v in data.items():
            if not isinstance(v, str):
                data[k] = str(v)
                continue
            continue
        cache = r_client.hset(create_user_cache_key(key), mapping=data)
        if not cache:
            raise ValueError("Error, failed to cache passed data!!")
        return r_client.expire(create_user_cache_key(key), expire) if expire else cache

    @staticmethod
    async def collect_cache(key: str):
        return r_client.hgetall(create_user_cache_key(key))


r_service = RedisServices()
