from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.permission import Permission
from app.models.user import User
from app.models.user_permission import UserPermission


def require_permission(permission_code: str):
    """
    FastAPI dependency factory — requires a **single** permission.

    Usage:
        current_user: User = Depends(require_permission("ADD_VEHICLE"))

    Returns the authenticated User if the permission check passes.
    Raises 403 if the user lacks the required permission.
    """

    def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        has_perm = (
            db.query(UserPermission)
            .join(Permission)
            .filter(
                UserPermission.user_id == current_user.id,
                Permission.code == permission_code,
            )
            .first()
        )

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have {permission_code} permission",
            )

        return current_user

    return _check


def require_any_permission(*permission_codes: str):
    """
    FastAPI dependency factory — requires **any one** of the listed permissions.

    Usage:
        current_user: User = Depends(require_any_permission("VIEW_STAFF", "MANAGE_STAFF"))

    Returns the authenticated User if they hold at least one of the
    specified permissions.  Raises 403 otherwise.
    """

    def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        has_perm = (
            db.query(UserPermission)
            .join(Permission)
            .filter(
                UserPermission.user_id == current_user.id,
                Permission.code.in_(permission_codes),
            )
            .first()
        )

        if not has_perm:
            codes = ", ".join(permission_codes)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You need one of [{codes}] permissions",
            )

        return current_user

    return _check
