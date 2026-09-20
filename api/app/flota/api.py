"""Interfaz REST del componente Flota (expone IGestionFlota al exterior)."""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.contratos.flota import IGestionFlota


class AltaAmbulancia(BaseModel):
    codigo: str = Field(min_length=1, max_length=20, examples=["AMB-07"])
    tipo: Literal["BASICA", "AVANZADA"]
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class CambioEstado(BaseModel):
    # Se aceptan los 3 estados para que la regla de negocio (y no la validación)
    # explique por qué EN_SERVICIO no se asigna manualmente.
    estado: Literal["DISPONIBLE", "EN_SERVICIO", "EN_MANTENIMIENTO"]


class Ubicacion(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


def crear_router(flota: IGestionFlota) -> APIRouter:
    r = APIRouter(prefix="/ambulancias", tags=["Flota"])

    @r.post("", status_code=201)
    def registrar(body: AltaAmbulancia):
        return flota.registrar(body.codigo, body.tipo, body.latitud, body.longitud)

    @r.get("")
    def listar(estado: str | None = None):
        return flota.listar(estado)

    @r.get("/{ambulancia_id}")
    def obtener(ambulancia_id: int):
        return flota.obtener(ambulancia_id)

    @r.patch("/{ambulancia_id}/estado")
    def cambiar_estado(ambulancia_id: int, body: CambioEstado):
        return flota.cambiar_estado_operativo(ambulancia_id, body.estado)

    @r.patch("/{ambulancia_id}/ubicacion")
    def actualizar_ubicacion(ambulancia_id: int, body: Ubicacion):
        return flota.actualizar_ubicacion(ambulancia_id, body.latitud, body.longitud)

    return r
