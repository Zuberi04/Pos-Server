import jwt
import datetime
from utils.stmt import read_stmt
from utils.extras import hash_jwt_key_for_user



class JwtTokens:
    def __init__(self):
        pass

    def generate_token(self, creds: dict):
        data = creds
        data["id"] = read_stmt.convert_id(data["id"])
        data["expiry"] = self.create_expiry_ts(data).isoformat()

        token = jwt.encode(payload=data, key=hash_jwt_key_for_user(data["id"]), algorithm='HS512')
        if not token:
            raise ValueError("Error, failed generating token!!")

        del data["expiry"]
        data["token"] = token

        return data

    def validate_token(self, creds: dict):
        if not creds:
            raise ValueError("Error, no data passed for token validation!!")
        elif not "token" in creds:
            return self.generate_token(creds)
        try:
            decoded = jwt.decode(creds["token"], key=hash_jwt_key_for_user(creds["id"]), algorithms='HS512')
            print("Decoded with values: \n\t", decoded)
            return creds
        except jwt.DecodeError as e:
            print("Authentication failed with value: \n\t", str(e))
            token = self.generate_token(creds)
            if not token:
                return {'error': 'Invalid credentials passed for authorization!'}
            try: 
                decoded = jwt.decode(token['token'], key=hash_jwt_key_for_user(token['id']), algorithms='HS512')
            except jwt.InvalidSignatureError as e:
                print('Invalid signature with value e: ', e)
            return {'error': 'Invalid user!!'}
        except jwt.ExpiredSignatureError as e:
            print("Authentication expired with value: \n\t", str(e))
            return {'warning': 'Token expired'}

    @staticmethod
    def create_expiry_ts(creds: dict):
        if not "token" in creds:
            return datetime.datetime.now() + datetime.timedelta(hours=24)

        return datetime.datetime.now() + datetime.timedelta(hours=(24 * 30))
    


auth_token = JwtTokens()
