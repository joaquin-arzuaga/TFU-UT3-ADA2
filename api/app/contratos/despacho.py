"""
Interfaz expuesta por el componente DESPACHO.

  - IDespacho: la usan los operadores (vía REST) para asignar la unidad
    más adecuada a una emergencia y para finalizar el servicio.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

ESTADOS_DESPACHO = ("ACTIVO", "FINALIZADO")


@dataclass(frozen=True)
class Despacho:
    id: int
    emergencia_id: int
    ambulancia_id: int
    distancia_km: float
    estado: str
    asignado_en: datetime
    finalizado_en: datetime | None


@dataclass(frozen=True)
class OpcionesDemo:
    """Parámetros SOLO para las demos de ACID (no forman parte del negocio)."""
    simular_falla: bool = False   # lanza un error luego de modificar Flota y Emergencias
    demora_ms: int = 0            # mantiene la transacción abierta para ver el aislamiento


class IDespacho(ABC):
    @abstractmethod
    def asignar(self, emergencia_id: int, opciones: OpcionesDemo = OpcionesDemo()) -> Despacho: ...

    @abstractmethod
    def finalizar(self, despacho_id: int) -> Despacho: ...

    @abstractmethod
    def listar(self, estado: str | None = None) -> list[Despacho]: ...

    @abstractmethod
    def obtener(self, despacho_id: int) -> Despacho: ...
