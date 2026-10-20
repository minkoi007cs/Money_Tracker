from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .models import BankConnection, User
from .services import bank_service as bank

router = APIRouter(prefix="/api/v1/banks", tags=["Bank connections"])


class LinkRequest(BaseModel):
    connection_id: str | None = None


class ExchangeRequest(BaseModel):
    public_token: str = Field(min_length=1, max_length=1024)


@router.get("")
def connections(user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        env = bank.config()
        configured = True
    except HTTPException:
        env, configured = None, False
    records = db.scalars(select(BankConnection).where(BankConnection.user_id == user.id)).all()
    return {"configured": configured, "environment": env, "connections": [bank.public_connection(c) for c in records]}


@router.post("/link-token")
def link_token(payload: LinkRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    connection = bank.owned_connection(db, user.id, payload.connection_id) if payload.connection_id else None
    return bank.create_link_token(user.id, connection)


@router.post("/exchange")
def exchange(payload: ExchangeRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return bank.exchange(db, user.id, payload.public_token)


@router.post("/{connection_id}/reconnected")
def reconnected(connection_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    connection = bank.owned_connection(db, user.id, connection_id)
    try:
        result = bank.plaid("item/get", access_token=bank.token(connection))
    except bank.PlaidError:
        raise HTTPException(503, "Could not verify bank reconnection")
    if result["item"].get("error"):
        raise HTTPException(409, "Finish bank sign-in before reconnecting")
    connection.status = "connected"
    connection.error_code = None
    db.commit()
    return bank.public_connection(connection)


@router.post("/{connection_id}/sync")
def sync(connection_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    connection = bank.owned_connection(db, user.id, connection_id)
    return bank.sync(db, connection)


@router.delete("/{connection_id}")
def disconnect(connection_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    bank.disconnect(db, bank.owned_connection(db, user.id, connection_id))
    return {"deleted": True}
