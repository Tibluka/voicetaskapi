from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime, timedelta
import secrets, hashlib
from services.email_service import send_reset_email_with_template

class AuthService:
    def __init__(self, user_collection, password_resets):
        self.user_collection = user_collection
        self.password_resets = password_resets

    def create_user(self, email, password, name, phone):
        if self.user_collection.find_one({"email": email}):
            raise ValueError("E-mail já cadastrado")
        
        hashed_password = generate_password_hash(password)
        user = {
            "email": email,
            "password": hashed_password,
            "name": name,
            "phone": phone,
            "bio": "",
            "avatar": "",
            "status": "PENDING"
        }

        result = self.user_collection.insert_one(user)

        # Gera código de ativação igual ao fluxo de esqueceu senha
        code = str(secrets.randbelow(900_000) + 100_000)
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        expires = datetime.utcnow() + timedelta(minutes=15)
        self.password_resets.insert_one({
            "userId": result.inserted_id,
            "tokenHash": code_hash,
            "expiresAt": expires,
            "used": False,
            "createdAt": datetime.utcnow()
        })
        # Monta link de ativação
        activation_link = f"https://voicetaskapi.onrender.com/activate?code={code}&email={email}"
        # Envia e-mail de ativação (template 2)
        send_reset_email_with_template(
            to_email=email,
            template_id=2,
            params={"ACTIVATION_LINK": activation_link, "EXPIRATION": "15 minutos"}
        )

        return {
            "message": "Usuário criado com sucesso",
            "id": str(result.inserted_id)
        }

    def authenticate(self, email, password):
        user = self.user_collection.find_one({"email": email})
        if not user:
            return None
        
        if user.get("status") == "PENDING":
            raise ValueError("Usuário está pendente de ativação.")
        
        if check_password_hash(user["password"], password):
            return user
        return None

    def change_user_password(self, user_id: str, current_password: str, new_password: str):
            user = self.user_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise ValueError("User not found.")

            if not check_password_hash(user["password"], current_password):
                raise ValueError("Current password is incorrect.")

            new_password_hash = generate_password_hash(new_password)

            self.user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"password": new_password_hash}}
            )

            return {"message": "Password updated successfully."}
        
    def initiate_reset(self, email: str, force = False):
        user = self.user_collection.find_one({"email": email})
        if not user:
            return {"message": "Se esse e-mail existir, você receberá instruções para reset."}

        # Verifica se já existe um código válido (não expirado e não usado)
        existing_token = self.password_resets.find_one({
            "userId": user["_id"],
            "expiresAt": {"$gt": datetime.utcnow()},
            "used": False
        })

        if existing_token and not force:
            return {"message": "Já existe um código ativo enviado recentemente. Verifique seu e-mail."}

        # Gera novo código de 6 dígitos
        code = str(secrets.randbelow(900_000) + 100_000)
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        expires = datetime.utcnow() + timedelta(minutes=15)

        self.password_resets.insert_one({
            "userId": user["_id"],
            "tokenHash": code_hash,
            "expiresAt": expires,
            "used": False,
            "createdAt": datetime.utcnow()
        })

        send_reset_email_with_template(
            to_email=email,
            template_id=1,
            params={"CODE": code, "EXPIRATION": "15 minutos"}
        )

        return {"message": "Se esse e-mail existir, você receberá instruções para reset."}


    def validate_token(self, email: str, code: str):
        user = self.user_collection.find_one({"email": email})
        if not user:
            raise ValueError("Código inválido ou expirado.")

        code_hash = hashlib.sha256(code.encode()).hexdigest()
        pr = self.password_resets.find_one({
            "userId": user["_id"],
            "tokenHash": code_hash,
            "expiresAt": {"$gt": datetime.utcnow()},
            "used": False
        })
        if not pr:
            raise ValueError("Código inválido ou expirado.")

        return pr

    def reset_password(self, email: str, code: str, new_password: str):
        pr = self.validate_token(email, code)
        new_password_hash = generate_password_hash(new_password)

        self.user_collection.update_one(
            {"_id": pr["userId"]},
            {"$set": {"password": new_password_hash}}
        )
        self.password_resets.update_one(
            {"_id": pr["_id"]},
            {"$set": {"used": True}}
        )
        return {"message": "Senha redefinida com sucesso."}