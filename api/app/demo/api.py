"""Endpoints auxiliares SOLO para las demos (se habilitan con DEMO_HABILITADA=true)."""
import psycopg
from fastapi import APIRouter

from app.comun.db import transaccion


def _intentar(descripcion: str, sql: str, params: tuple) -> dict:
    """Ejecuta SQL que viola un invariante y devuelve cómo lo rechazó la base."""
    try:
        with transaccion() as cx:
            cx.execute(sql, params)
        return {"intento": descripcion, "resultado": "ACEPTADO (¡no debería pasar!)"}
    except psycopg.DatabaseError as e:  # restricciones violadas (CHECK, UNIQUE, FK...)
        return {
            "intento": descripcion,
            "resultado": "RECHAZADO por la base de datos",
            "restriccion": e.diag.constraint_name,
            "error": e.diag.message_primary,
        }


def crear_router() -> APIRouter:
    r = APIRouter(prefix="/demo", tags=["Demo"])

    @r.post("/reset")
    def reset():
        with transaccion() as cx:
            cx.execute("CALL public.demo_reset()")
        return {"mensaje": "Datos reiniciados: 6 ambulancias, sin emergencias ni despachos"}

    @r.post("/consistencia")
    def consistencia():
        """Intenta, saltándose la lógica de la API, dejar la base en estados inválidos."""
        with transaccion() as cx:
            activo = cx.execute(
                "SELECT ambulancia_id FROM despacho.despachos WHERE estado = 'ACTIVO' LIMIT 1"
            ).fetchone()
            emergencia = cx.execute("SELECT id FROM emergencias.emergencias LIMIT 1").fetchone()
        intentos = []
        if activo and emergencia:
            intentos.append(_intentar(
                f"Crear un 2do despacho ACTIVO para la ambulancia {activo['ambulancia_id']}",
                "INSERT INTO despacho.despachos (emergencia_id, ambulancia_id, distancia_km) VALUES (%s, %s, 1.0)",
                (emergencia["id"], activo["ambulancia_id"]),
            ))
        intentos.append(_intentar(
            "Poner el estado inexistente 'VOLANDO' a una ambulancia",
            "UPDATE flota.ambulancias SET estado = 'VOLANDO' WHERE id = %s", (2,),
        ))
        intentos.append(_intentar(
            "Registrar una emergencia con prioridad inexistente 'CRITICA'",
            "INSERT INTO emergencias.emergencias (descripcion, direccion, latitud, longitud, prioridad) "
            "VALUES ('x', 'y', 0, 0, %s)", ("CRITICA",),
        ))
        return intentos

    return r
