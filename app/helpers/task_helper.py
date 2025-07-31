VALID_STATUS = ["pending", "on-going", "done"]

def serialize_task(task) -> dict:
    return {
        "id": str(task["_id"]),
        "user": str(task["user"]),
        "label": task["label"],
        "status": task["status"],
        "createdAt": task["createdAt"],
        "updatedAt": task["updatedAt"]
    }
