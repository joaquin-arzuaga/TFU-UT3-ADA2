"""
Punto de composición de la aplicación (composition root).

Aquí, y SOLO aquí, se crean las implementaciones concretas de cada
componente y se conectan entre sí a través de sus interfaces:

    Despacho  --requiere-->  IDisponibilidadFlota  <--provee--  Flota
    Despacho  --requiere-->  IEstadoEmergencia     <--provee--  Emergencias

SERVICIO SIN ESTADO: la aplicación no guarda nada en memoria entre
solicitudes (ni sesiones, ni cachés, ni contadores). Todo el estado vive
en PostgreSQL. Por eso cualquier réplica puede atender cualquier
solicitud y se pueden agregar o quitar réplicas libremente.
"""
import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.comun import db
from app.comun.errores import ErrorDominio
from app.demo.api import crear_router as router_demo
from app.despacho.api import crear_router as router_despacho
from app.despacho.servicio import ServicioDespacho
from app.emergencias.api import crear_router as router_emergencias
from app.emergencias.servicio import ServicioEmergencias
from app.flota.api import crear_router as router_flota
from app.flota.servicio import ServicioFlota

INSTANCIA = os.getenv("HOSTNAME", socket.gethostname())
PREFIJO = "/api/v1"   # versionado de la interfaz REST (evolución de interfaces)


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    db.iniciar_pool()
    yield
    db.cerrar_pool()


app = FastAPI(
    title="Gestión de flota de ambulancias",
    version="1.0.0",
    description="TFU UT3 - Análisis y Diseño de Aplicaciones II",
    lifespan=ciclo_de_vida,
)

# ---- Ensamblado de componentes (inyección de dependencias) -----------------
flota = ServicioFlota()
emergencias = ServicioEmergencias()
despacho = ServicioDespacho(flota=flota, emergencias=emergencias)

app.include_router(router_flota(flota), prefix=PREFIJO)
app.include_router(router_emergencias(emergencias), prefix=PREFIJO)
app.include_router(router_despacho(despacho), prefix=PREFIJO)
if os.getenv("DEMO_HABILITADA", "false").lower() == "true":
    app.include_router(router_demo(), prefix=PREFIJO)


# ---- Transversales ---------------------------------------------------------
@app.middleware("http")
async def identificar_instancia(request: Request, call_next):
    """Agrega qué réplica atendió la solicitud (para ver el balanceo)."""
    respuesta = await call_next(request)
    respuesta.headers["X-Instancia"] = INSTANCIA
    return respuesta


@app.exception_handler(ErrorDominio)
async def manejar_error_dominio(_request: Request, exc: ErrorDominio):
    return JSONResponse(
        status_code=exc.status_http,
        content={"error": exc.codigo, "detalle": exc.detalle, "instancia": INSTANCIA},
    )


@app.get(f"{PREFIJO}/salud", tags=["Operación"])
def salud():
    with db.transaccion() as cx:
        cx.execute("SELECT 1")
    return {"estado": "OK", "instancia": INSTANCIA}
