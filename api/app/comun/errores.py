"""
Errores de dominio compartidos por todos los componentes.

Forman parte del contrato de las interfaces: cada error se traduce a un
código HTTP predefinido (manejo de errores por indicador de estado).
"""


class ErrorDominio(Exception):
    status_http = 400
    codigo = "SOLICITUD_INVALIDA"

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class NoEncontrado(ErrorDominio):
    status_http = 404
    codigo = "NO_ENCONTRADO"


class Conflicto(ErrorDominio):
    """La operación no es válida para el estado actual del recurso."""
    status_http = 409
    codigo = "CONFLICTO"


class SinAmbulanciasDisponibles(Conflicto):
    codigo = "SIN_AMBULANCIAS_DISPONIBLES"


class FallaSimulada(ErrorDominio):
    """Solo para la demo de atomicidad: fuerza un ROLLBACK a mitad de camino."""
    status_http = 500
    codigo = "FALLA_SIMULADA"
