def get_user_role(user) -> str:
    return user.get("role") or "user"


ADMIN_PERMISSIONS = ["manage_users", "manage_own", "manage_notes", "manage_own_notes"]
USER_PERMISSIONS = ["manage_own", "manage_own_notes"]


def get_user_permissions(user) -> list[str]:
    if isinstance(user.get("permissions"), list):
        return user["permissions"]

    role = get_user_role(user)
    if role == "admin":
        return ADMIN_PERMISSIONS
    if role == "user":
        return USER_PERMISSIONS
    return []


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

    if user.get("avatarUrl"):
        serialized_user["avatarUrl"] = user.get("avatarUrl")

    if "isEmailActivated" in user:
        serialized_user["isEmailActivated"] = user.get("isEmailActivated")

    return serialized_user
