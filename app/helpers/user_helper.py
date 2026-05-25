def get_user_status(user) -> str:
    if user.get("status"):
        return user["status"]

    if user.get("isEmailActivated") is True:
        return "active"

    return "inactive"


def serialize_user(user) -> dict:
    serialized_user = {
        "id": str(user["_id"]),
        "firstName": user.get("firstName"),
        "lastName": user.get("lastName"),
        "email": user.get("email"),
        "status": get_user_status(user),
    }

    if "isEmailActivated" in user:
        serialized_user["isEmailActivated"] = user.get("isEmailActivated")

    return serialized_user
