import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db
from app.db import models

router = APIRouter(prefix="/users", tags=["users"])


class GuestUserOut(BaseModel):
    user_id: str
    name: str


@router.post("/guest", response_model=GuestUserOut)
def create_guest_user(db: Session = Depends(get_db)):
    guest_id = uuid.uuid4().hex[:8]
    user = models.User(
        name=f"Guest-{guest_id}",
        email=f"guest-{guest_id}@rungline.local",
        password_hash="guest",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return GuestUserOut(user_id=user.id, name=user.name)