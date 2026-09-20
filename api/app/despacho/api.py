"""Interfaz REST del componente Despacho (expone IDespacho)."""
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.contratos.despacho import IDespacho, OpcionesDemo


class SolicitudDespacho(BaseModel):
    emergencia_id: int


def crear_router(despacho: IDespacho) -> APIRouter:
    r = APIRouter(prefix="/despachos", tags=["Despacho"])

    @r.post("", status_code=201)
    def asignar(
        body: SolicitudDespacho,
        simular_falla: bool = Query(False, description="Solo demo ACID: fuerza un rollback"),
        demora_ms: int = Query(0, ge=0, le=15000, description="Solo demo ACID: retiene los bloqueos"),
    ):
        return despacho.asignar(body.emergencia_id, OpcionesDemo(simular_falla, demora_ms))

    @r.post("/{despacho_id}/finalizar")
    def finalizar(despacho_id: int):
        return despacho.finalizar(despacho_id)

    @r.get("")
    def listar(estado: str | None = None):
        return despacho.listar(estado)

    @r.get("/{despacho_id}")
    def obtener(despacho_id: int):
        return despacho.obtener(despacho_id)

    return r
