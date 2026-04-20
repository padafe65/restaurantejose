from fastapi import FastAPI
from app.database import engine, Base
from app.routers import user, reservation, table, customer
from fastapi.middleware.cors import CORSMiddleware # IMPORTAR ESTO

# Esto crea las tablas en MySQL/XAMPP automáticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Gestión Restaurante Don Juan",
    description="API para administrar usuarios, mesas y reservaciones",
    version="1.0.0"
)

# --- CONFIGURACIÓN DE CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite que cualquier navegador se conecte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluimos los routers (el orden no afecta, pero es bueno ser organizado)
app.include_router(user.router)
app.include_router(customer.router)
app.include_router(table.router)
app.include_router(reservation.router)

@app.get("/")
def read_root():
    return {
        "mensaje": "Backend MVC del Restaurante Juan listo",
        "documentacion": "/docs"
    }