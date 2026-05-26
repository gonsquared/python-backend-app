def get_user_role(user) -> str:
    return user.get("role") or "user"


def get_user_permissions(user) -> list[str]:
    role = get_user_role(user)
    if role == "admin":
        return ["manage_users", "manage_own"]
    return ["manage_own"]


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
        "role": get_user_role(user),
        "permissions": get_user_permissions(user),
    }

    if "isEmailActivated" in user:
        serialized_user["isEmailActivated"] = user.get("isEmailActivated")

    return serialized_user
