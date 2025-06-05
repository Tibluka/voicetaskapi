from werkzeug.security import generate_password_hash, check_password_hash

class AuthService:
    def __init__(self, user_collection):
        self.user_collection = user_collection

    def create_user(self, email, password, name, phone):
        if self.user_collection.find_one({"email": email}):
            raise ValueError("User already exists")
        
        hashed_password = generate_password_hash(password)
        user = {
            "email": email,
            "password": hashed_password,
            "name": name,
            "phone": phone
        }

        result = self.user_collection.insert_one(user)

        return {
            "message": "User created successfully",
            "id": str(result.inserted_id)
        }

    def authenticate(self, email, password):
        user = self.user_collection.find_one({"email": email})
        if not user:
            return None
        
        if check_password_hash(user["password"], password):
            return user
        return None
