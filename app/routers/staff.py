from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.security import get_current_user, hash_password
from app.db.session import get_db
from app.models.permission import Permission
from app.models.user import User
from app.models.user_permission import UserPermission
from app.utils.permissions import require_any_permission, require_permission

router = APIRouter(prefix="/api/staff", tags=["Staff"])


# ── Request / Response schemas ────────────────────────

class StaffCreate(BaseModel):
    email: EmailStr
    password: str
    permissions: list[str] = []


class StaffResponse(BaseModel):
    id: int
    permissions: list[str]


class StaffListItem(BaseModel):
    id: int
    email: str
    name: str | None = None
    phone: str | None = None
    is_active: bool
    is_owner: bool
    role: str
    permissions: list[str]

    model_config = {"from_attributes": True}


class ToggleActiveResponse(BaseModel):
    id: int
    is_active: bool


# ── GET /api/staff ───────────────────────────────────

@router.get("/", response_model=list[StaffListItem])
def list_staff(
    current_user: User = Depends(require_any_permission("VIEW_STAFF", "MANAGE_STAFF")),
    db: Session = Depends(get_db),
):
    if current_user.dealer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be linked to a dealer to view staff",
        )

    # Fetch all users under the same dealer
    users = (
        db.query(User)
        .filter(User.dealer_id == current_user.dealer_id)
        .all()
    )

    # Fetch permissions for all these users via explicit join
    user_ids = [u.id for u in users]
    perm_rows = (
        db.query(UserPermission.user_id, Permission.code)
        .join(Permission, UserPermission.permission_id == Permission.id)
        .filter(UserPermission.user_id.in_(user_ids))
        .all()
    )

    # Group permission codes by user_id
    perm_map: dict[int, list[str]] = {}
    for uid, code in perm_rows:
        perm_map.setdefault(uid, []).append(code)

    return [
        StaffListItem(
            id=u.id,
            email=u.email,
            name=u.name,
            phone=u.phone,
            is_active=u.is_active,
            is_owner=(u.id == current_user.id),
            role=u.global_role or "DEALER_STAFF",
            permissions=perm_map.get(u.id, []),
        )
        for u in users
    ]


# ── GET /api/staff/{staff_id} ─────────────────────────

@router.get("/{staff_id}", response_model=StaffListItem)
def get_staff_member(
    staff_id: int,
    current_user: User = Depends(require_any_permission("VIEW_STAFF", "MANAGE_STAFF")),
    db: Session = Depends(get_db),
):
    if current_user.dealer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be linked to a dealer to view staff",
        )

    staff_user = db.query(User).filter(User.id == staff_id).first()
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found",
        )

    # Ensure staff belongs to the same dealer
    if staff_user.dealer_id != current_user.dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view staff within your own dealership",
        )

    # Fetch permissions via explicit join
    perm_codes = [
        code
        for (code,) in (
            db.query(Permission.code)
            .join(UserPermission, UserPermission.permission_id == Permission.id)
            .filter(UserPermission.user_id == staff_id)
            .all()
        )
    ]

    return StaffListItem(
        id=staff_user.id,
        email=staff_user.email,
        name=staff_user.name,
        phone=staff_user.phone,
        is_active=staff_user.is_active,
        is_owner=(staff_user.global_role == "DEALER_OWNER"),
        role=staff_user.global_role or "DEALER_STAFF",
        permissions=perm_codes,
    )


# ── POST /api/staff ──────────────────────────────────

@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreate,
    current_user: User = Depends(require_permission("MANAGE_STAFF")),
    db: Session = Depends(get_db),
):
    # ── Validate dealer link ─────────────────────────
    if current_user.dealer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be linked to a dealer to manage staff",
        )

    # ── Duplicate email check ────────────────────────
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # ── Create staff user ────────────────────────────
    staff_user = User(
        email=payload.email,
        password=hash_password(payload.password),
        global_role="DEALER_STAFF",
        dealer_id=current_user.dealer_id,
    )

    db.add(staff_user)
    db.flush()

    # ── Assign requested permissions ─────────────────
    assigned_codes: list[str] = []
    for code in payload.permissions:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission '{code}' does not exist",
            )
        db.add(UserPermission(user_id=staff_user.id, permission_id=perm.id))
        assigned_codes.append(code)

    db.commit()
    db.refresh(staff_user)

    return StaffResponse(id=staff_user.id, permissions=assigned_codes)


# ── PATCH /api/staff/{staff_id}/toggle-active ────────

@router.patch("/{staff_id}/toggle-active", response_model=ToggleActiveResponse)
def toggle_staff_active(
    staff_id: int,
    current_user: User = Depends(require_permission("MANAGE_STAFF")),
    db: Session = Depends(get_db),
):
    # Prevent self-deactivation
    if staff_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    # Fetch staff user explicitly
    staff_user = db.query(User).filter(User.id == staff_id).first()
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found",
        )

    # Protect dealer owner from being modified
    if staff_user.global_role == "DEALER_OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dealer Owner cannot be modified",
        )

    # Ensure staff belongs to the same dealer
    if staff_user.dealer_id != current_user.dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage staff within your own dealership",
        )

    # Toggle active status
    staff_user.is_active = not staff_user.is_active
    db.commit()
    db.refresh(staff_user)

    return ToggleActiveResponse(id=staff_user.id, is_active=staff_user.is_active)


# ── PUT /api/staff/{staff_id} — update profile & permissions ─────────

class StaffUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    permissions: list[str] | None = None


class StaffUpdateResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    phone: str | None = None
    permissions: list[str]

    model_config = {"from_attributes": True}


@router.put("/{staff_id}", response_model=StaffUpdateResponse)
def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ── Fetch target user ────────────────────────────
    staff_user = db.query(User).filter(User.id == staff_id).first()
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found",
        )

    # ── Ensure same dealer ───────────────────────────
    if staff_user.dealer_id != current_user.dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage staff within your own dealership",
        )

    # ── Dealer Owner: allow profile updates only ─────
    if staff_user.global_role == "DEALER_OWNER":
        payload.permissions = None  # never touch owner permissions

    is_self_edit = current_user.id == staff_id

    # ── Editing others: require MANAGE_STAFF ─────────
    if not is_self_edit:
        has_manage = (
            db.query(UserPermission)
            .join(Permission)
            .filter(
                UserPermission.user_id == current_user.id,
                Permission.code == "MANAGE_STAFF",
            )
            .first()
        )
        if not has_manage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You need MANAGE_STAFF permission to edit other users",
            )

    # ── Update profile fields (if provided) ──────────
    if payload.name is not None:
        staff_user.name = payload.name
    if payload.phone is not None:
        staff_user.phone = payload.phone

    # ── Update permissions (only when editing others) ─
    if payload.permissions is not None:
        # Delete existing permissions
        db.query(UserPermission).filter(UserPermission.user_id == staff_id).delete()

        # Assign new permissions
        for code in payload.permissions:
            perm = db.query(Permission).filter(Permission.code == code).first()
            if not perm:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission '{code}' does not exist",
                )
            db.add(UserPermission(user_id=staff_id, permission_id=perm.id))

    db.commit()
    db.refresh(staff_user)

    # ── Build response with current permissions ──────
    perm_codes = [
        code
        for (code,) in (
            db.query(Permission.code)
            .join(UserPermission, UserPermission.permission_id == Permission.id)
            .filter(UserPermission.user_id == staff_id)
            .all()
        )
    ]

    return StaffUpdateResponse(
        id=staff_user.id,
        email=staff_user.email,
        name=staff_user.name,
        phone=staff_user.phone,
        permissions=perm_codes,
    )
