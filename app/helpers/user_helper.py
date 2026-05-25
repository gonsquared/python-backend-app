def serialize_user(user) -> dict:
    serialized_user = {
        "id": str(user["_id"]),
        "firstName": user.get("firstName"),
        "lastName": user.get("lastName"),
        "email": user.get("email"),
    }

    if "isEmailActivated" in user:
        serialized_user["isEmailActivated"] = user.get("isEmailActivated")

    return serialized_user
