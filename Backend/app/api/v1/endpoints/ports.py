from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.database import get_db
from app.models.port import Port
from app.schemas.port import PortCreate, PortResponse, PortUpdate

router = APIRouter()


@router.get("/", response_model=list[PortResponse])
async def list_ports(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Port).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=PortResponse, status_code=status.HTTP_201_CREATED)
async def create_port(payload: PortCreate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    port = Port(**payload.model_dump())
    db.add(port)
    await db.commit()
    await db.refresh(port)
    return port


@router.get("/{port_id}", response_model=PortResponse)
async def get_port(port_id: int, db: AsyncSession = Depends(get_db)):
    port = await db.get(Port, port_id)
    if port is None:
        raise HTTPException(status_code=404, detail="Port not found")
    return port


@router.patch("/{port_id}", response_model=PortResponse)
async def update_port(port_id: int, payload: PortUpdate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    port = await db.get(Port, port_id)
    if port is None:
        raise HTTPException(status_code=404, detail="Port not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(port, field, value)
    await db.commit()
    await db.refresh(port)
    return port


@router.delete("/{port_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_port(port_id: int, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    port = await db.get(Port, port_id)
    if port is None:
        raise HTTPException(status_code=404, detail="Port not found")
    await db.delete(port)
    await db.commit()
