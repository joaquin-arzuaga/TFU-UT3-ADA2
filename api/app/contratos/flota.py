"""
Interfaces expuestas por el componente FLOTA.

Se separan en dos interfaces pequeñas (Principio de Interfaces Pequeñas /
CRP) porque tienen clientes distintos:
  - IGestionFlota: la usan los operadores (vía API REST) para administrar
    la flota y actualizar su estado/ubicación en tiempo real.
  - IDisponibilidadFlota: la usa el componente Despacho para reservar y
    liberar unidades. Despacho no necesita (ni debe) ver el resto.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

TIPOS_AMBULANCIA = ("BASICA", "AVANZADA")
ESTADOS_AMBULANCIA = ("DISPONIBLE", "EN_SERVICIO", "EN_MANTENIMIENTO")


@dataclass(frozen=True)
class Ambulancia:
    id: int
    codigo: str
    tipo: str
    estado: str
    latitud: float
    longitud: float
    actualizada_en: datetime


class IGestionFlota(ABC):
    @abstractmethod
    def registrar(self, codigo: str, tipo: str, latitud: float, longitud: float) -> Ambulancia: ...

    @abstractmethod
    def listar(self, estado: str | None = None) -> list[Ambulancia]: ...

    @abstractmethod
    def obtener(self, ambulancia_id: int) -> Ambulancia: ...

    @abstractmethod
    def cambiar_estado_operativo(self, ambulancia_id: int, nuevo_estado: str) -> Ambulancia:
        """Solo DISPONIBLE <-> EN_MANTENIMIENTO. EN_SERVICIO lo decide Despacho."""

    @abstractmethod
    def actualizar_ubicacion(self, ambulancia_id: int, latitud: float, longitud: float) -> Ambulancia: ...


class IDisponibilidadFlota(ABC):
    @abstractmethod
    def bloquear_disponibles(self, tipos: list[str]) -> list[Ambulancia]:
        """Devuelve las unidades DISPONIBLES de los tipos pedidos y las
        bloquea hasta el fin de la transacción en curso (aislamiento)."""

    @abstractmethod
    def marcar_en_servicio(self, ambulancia_id: int) -> None: ...

    @abstractmethod
    def liberar(self, ambulancia_id: int) -> None: ...
