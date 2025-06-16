def user_to_dto(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "phone": user["phone"],
        "avatar": user["avatar"],
        "bio": user["bio"]
    }