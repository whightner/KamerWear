from fastapi import APIRouter, Response, status

from app.api.deps import CurrentAuth, DbSession
from app.schemas.auth import ChangePasswordRequest, ProfileUpdate, UserResponse
from app.schemas.catalog import ErrorResponse
from app.services import auth

router = APIRouter(prefix="/users", tags=["account"])

AUTH_ERRORS = {
    401: {"model": ErrorResponse, "description": "authentication_required / invalid_token"}
}


@router.get("/me", summary="Get the signed-in user", responses=AUTH_ERRORS)
def read_me(current: CurrentAuth) -> UserResponse:
    return UserResponse.model_validate(current.user)


@router.patch(
    "/me",
    summary="Update my profile",
    description="Only first_name, last_name and phone can change. "
    "Email, role and account status are read-only here (other fields are rejected).",
    responses=AUTH_ERRORS,
)
def update_me(data: ProfileUpdate, current: CurrentAuth, db: DbSession) -> UserResponse:
    user = auth.update_profile(db, current.user, data)
    db.commit()
    return UserResponse.model_validate(user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change my password",
    description="Requires the current password. Signs out all other sessions; "
    "the current session stays signed in.",
    responses={
        **AUTH_ERRORS,
        400: {"model": ErrorResponse, "description": "invalid_current_password"},
    },
)
def change_password(data: ChangePasswordRequest, current: CurrentAuth, db: DbSession) -> Response:
    auth.change_password(db, current.user, current.session.id, data)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
