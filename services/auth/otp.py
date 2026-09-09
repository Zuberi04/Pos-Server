import hmac

from utils.stmt import read_stmt
from database.models import AdminUser
from r_services.service import r_service
from utils.extras import decode_json_objects, create_user_cache_key


class OtpGeneration:
    def __init__(self):
        pass

    async def check_if_validate_or_create(self, creds: dict):
        if 'token' in creds:
            data = read_stmt.read_stmt(AdminUser, creds['id'])
            valid = self.validate_otp(self.create_otp(creds), data['otp'])
            if not valid:
                return {'error': 'invalid user!!'}
            used = await r_service.collect_cache(creds['id'])
            if not used:
                raise ValueError('Error, cache values missing. will fail to renew consumed otp!!')
            elif isinstance(used['used'], str):
                used = decode_json_objects(used['used'])

            return self.create_otp(creds, used)

        return self.create_otp(creds)

    def create_otp(self, creds: dict, used: list = None):
        otp = []
        for char in creds['fullnames']:
            if len(otp) == 6:
                break

            elif not char in otp:
                if used:
                    if char in used:
                        otp.insert(used.index(char) - 1, char)
                        continue
                otp.append(char)
                for t in creds['email']:
                    if not t in otp:
                        if used:
                            if t in used:
                                otp.insert(used.index(t) - 2, t)
                                break
                        otp.append(t)
                        break
                    continue
                continue
            continue
        return (self.create_otp_hash(otp), otp)

    def create_otp_hash(self, otp: list):
        hash_t = {}

        t = ''
        for item in otp:
            if len(t) < 2:
                t = t + item
                continue
            key = self.create_bytes_key(t)
            if not key in hash_t:
                hash_t[key] = t
            t = ''
            continue

        return self.create_hash(hash_t.keys())

    @staticmethod
    def create_bytes_key(data: str):
        return bytes(data.encode('utf-8'))

    @staticmethod
    def create_hash(keys: set[bytes]):
        h = ''
        for key in keys:
            h = h + key.hex()
            continue
        return h

    @staticmethod
    def validate_otp(otp: str, hashed: str):
        return hmac.compare_digest(otp, hashed)


gen_otp = OtpGeneration()
