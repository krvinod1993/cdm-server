"""
trial.py – Automatic trial-expiry enforcement.

Checks whether the authenticated user's dealer has an expired trial.
If so, marks the subscription as EXPIRED and deactivates all vehicles.

Also provides ``require_active_subscription`` — a FastAPI dependency that
blocks requests from dealers whose subscription has expired.
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.car import Vehicle
from app.models.dealer import Dealer


def enforce_trial_expiry(dealer_id: int | None, db: Session) -> None:
    """
    Check and enforce trial expiry for a dealer.

    Parameters
    ----------
    dealer_id : int | None
        The dealer ID linked to the current user.
        If None (e.g. super-admin with no dealer), the check is skipped.
    db : Session
        Active SQLAlchemy session — changes are committed if expiry is detected.
    """
    if dealer_id is None:
        return

    dealer = db.query(Dealer).filter(Dealer.id == dealer_id).first()
    if not dealer:
        return

    now = datetime.now(timezone.utc)

    if (
        dealer.subscription_status == "TRIAL"
        and dealer.trial_end_date is not None
        and now > dealer.trial_end_date
    ):
        # Mark subscription as expired
        dealer.subscription_status = "EXPIRED"

        # Deactivate all vehicles belonging to this dealer
        db.query(Vehicle).filter(Vehicle.dealer_id == dealer.id).update(
            {"status": "inactive"}
        )

        db.commit()

    elif (
        dealer.subscription_status == "EXPIRED"
        and dealer.trial_end_date is not None
        and now < dealer.trial_end_date
    ):
        # Trial was extended — reinstate subscription
        dealer.subscription_status = "TRIAL"

        # Reactivate all vehicles belonging to this dealer
        db.query(Vehicle).filter(Vehicle.dealer_id == dealer.id).update(
            {"status": "active"}
        )

        db.commit()


# ── Subscription gate (deferred imports to avoid circular refs) ────────
def _build_require_active_subscription():
    from app.core.security import get_current_user
    from app.db.session import get_db

    def require_active_subscription(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        """
        FastAPI dependency — blocks the request if the dealer's
        subscription is EXPIRED.

        Must be added to protected endpoints via ``Depends()``.
        Read-only check; does NOT mutate data (expiry transition is
        handled by ``enforce_trial_expiry`` inside ``get_current_user``).
        """
        if current_user.dealer_id is None:
            return

        dealer = db.query(Dealer).filter(Dealer.id == current_user.dealer_id).first()
        if not dealer:
            return

        # If status is EXPIRED but trial_end_date was extended, reinstate
        if (
            dealer.subscription_status == "EXPIRED"
            and dealer.trial_end_date is not None
            and datetime.now(timezone.utc) < dealer.trial_end_date
        ):
            dealer.subscription_status = "TRIAL"
            db.query(Vehicle).filter(Vehicle.dealer_id == dealer.id).update(
                {"status": "active"}
            )
            db.commit()
            return

        if dealer.subscription_status == "EXPIRED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription expired. Please subscribe to continue.",
            )

    return require_active_subscription


require_active_subscription = _build_require_active_subscription()
