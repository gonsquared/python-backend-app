from fastapi import Request, HTTPException, Depends
import re

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

async def validate_email(request: Request):
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()

            if "email" not in body:
                raise HTTPException(
                    status_code=422,
                    detail="Email field is required."
                )

            email = body["email"]

            if not EMAIL_REGEX.match(email):
                raise HTTPException(
                    status_code=422,
                    detail="Invalid email format."
                )

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid request body. Expected JSON payload."
            )
