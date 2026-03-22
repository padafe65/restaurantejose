from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.table import Table
from app.models.user import User
from app.schemas.table import TableCreate, TableOut, TableUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/tables", tags=["Mesas"])

@router.get("/", response_model=List[TableOut])
def get_tables(db: Session = Depends(get_db)):
    return db.query(Table).all()

@router.post("/", response_model=TableOut, status_code=status.HTTP_201_CREATED)
def create_table(table_data: TableCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede crear mesas")
    
    new_table = Table(**table_data.model_dump())
    db.add(new_table)
    db.commit()
    db.refresh(new_table)
    return new_table

# En app/routers/table.py

@router.patch("/{table_id}/release")
def release_table(table_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "mesero"]:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    # Cambiamos el estado a libre
    table.status = "libre"
    db.commit()
    return {"message": f"Mesa {table.number} liberada correctamente"}

@router.put("/{table_id}", response_model=TableOut)
def update_table(table_id: int, updated_data: TableUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede editar mesas")
    
    table_query = db.query(Table).filter(Table.id == table_id)
    if not table_query.first():
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    table_query.update(updated_data.model_dump(exclude_unset=True), synchronize_session=False)
    db.commit()
    return table_query.first()

@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(table_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede eliminar mesas")
    
    table_query = db.query(Table).filter(Table.id == table_id)
    if not table_query.first():
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    table_query.delete(synchronize_session=False)
    db.commit()
    return None