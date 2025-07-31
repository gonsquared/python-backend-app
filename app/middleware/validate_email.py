from fastapi import Request
from fastapi.responses import JSONResponse
import re

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

async def validate_email(request: Request, call_next):
    """
    Middleware to ensure all POST, PUT, PATCH requests contain a valid email.
    """
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()

            if "email" not in body:
                return JSONResponse(
                    status_code=422,
                    content={"detail": "Email field is required."}
                )

            email = body["email"]

            if not EMAIL_REGEX.match(email):
                return JSONResponse(
                    status_code=422,
                    content={"detail": "Invalid email format."}
                )

        except Exception:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request body. Expected JSON payload."}
            )

    response = await call_next(request)
    return response
