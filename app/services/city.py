from sqlalchemy.orm import Session

from app.models.city import City


def get_active_cities(db: Session) -> list[City]:
    """
    Return all active cities ordered by name (A → Z).

    Always returns a list — empty list if no cities exist.
    """
    return (
        db.query(City)
        .filter(City.is_active == True)
        .order_by(City.name.asc())
        .all()
    )
