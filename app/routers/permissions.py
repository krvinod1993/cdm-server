from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.permission import Permission
from app.models.user import User
from app.utils.permissions import require_any_permission

router = APIRouter(prefix="/api", tags=["Permissions"])


# ── Response schema ─────────────────────────────────

class PermissionOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ── GET /api/permissions ────────────────────────────

@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(
    current_user: User = Depends(require_any_permission("VIEW_STAFF", "MANAGE_STAFF")),
    db: Session = Depends(get_db),
):
    """
    Return all permissions from the permissions table.

    Access: authenticated users with VIEW_STAFF **or** MANAGE_STAFF.
    """
    rows = db.query(Permission).order_by(Permission.id).all()
    return [PermissionOut(id=p.id, name=p.code) for p in rows]
