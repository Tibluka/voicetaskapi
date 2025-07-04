import jwt
import datetime

SECRET_KEY = "sua_chave_secreta_super_segura"  # Troque por algo seguro e confidencial


class TokenService:
    @staticmethod
    def generate_token(payload, expires_in_minutes=1440):  # 24 horas = 1440 minutos
        payload_copy = payload.copy()
        payload_copy["exp"] = datetime.datetime.utcnow() + datetime.timedelta(
            minutes=expires_in_minutes
        )
        token = jwt.encode(payload_copy, SECRET_KEY, algorithm="HS256")
        return token

    @staticmethod
    def verify_token(token):
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return decoded
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
