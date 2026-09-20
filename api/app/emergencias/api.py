"""Interfaz REST del componente Emergencias (expone IRegistroEmergencias)."""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.contratos.emergencias import IRegistroEmergencias


class NuevaEmergencia(BaseModel):
    descripcion: str = Field(min_length=3, max_length=500, examples=["Paro cardiorrespiratorio"])
    direccion: str = Field(min_length=3, max_length=200, examples=["Av. 18 de Julio 1200"])
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    prioridad: Literal["ALTA", "MEDIA", "BAJA"]


def crear_router(emergencias: IRegistroEmergencias) -> APIRouter:
    r = APIRouter(prefix="/emergencias", tags=["Emergencias"])

    @r.post("", status_code=201)
    def registrar(body: NuevaEmergencia):
        return emergencias.registrar(
            body.descripcion, body.direccion, body.latitud, body.longitud, body.prioridad
        )

    @r.get("")
    def listar(estado: str | None = None):
        return emergencias.listar(estado)

    @r.get("/{emergencia_id}")
    def obtener(emergencia_id: int):
        return emergencias.obtener(emergencia_id)

    return r
