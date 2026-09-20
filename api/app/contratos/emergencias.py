"""
Interfaces expuestas por el componente EMERGENCIAS.

  - IRegistroEmergencias: la usan los operadores de la central (vía REST)
    para registrar y consultar las emergencias que ingresan.
  - IEstadoEmergencia: la usa Despacho para tomar una emergencia pendiente
    y hacer avanzar su ciclo de vida (PENDIENTE -> ASIGNADA -> CERRADA).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

PRIORIDADES = ("ALTA", "MEDIA", "BAJA")
ESTADOS_EMERGENCIA = ("PENDIENTE", "ASIGNADA", "CERRADA")


@dataclass(frozen=True)
class Emergencia:
    id: int
    descripcion: str
    direccion: str
    latitud: float
    longitud: float
    prioridad: str
    estado: str
    creada_en: datetime


class IRegistroEmergencias(ABC):
    @abstractmethod
    def registrar(self, descripcion: str, direccion: str, latitud: float,
                  longitud: float, prioridad: str) -> Emergencia: ...

    @abstractmethod
    def listar(self, estado: str | None = None) -> list[Emergencia]: ...

    @abstractmethod
    def obtener(self, emergencia_id: int) -> Emergencia: ...


class IEstadoEmergencia(ABC):
    @abstractmethod
    def bloquear_pendiente(self, emergencia_id: int) -> Emergencia:
        """Devuelve la emergencia bloqueada; falla si no existe o no está PENDIENTE."""

    @abstractmethod
    def marcar_asignada(self, emergencia_id: int) -> None: ...

    @abstractmethod
    def cerrar(self, emergencia_id: int) -> None: ...
