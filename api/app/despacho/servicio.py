"""
Componente DESPACHO: implementación.

Es el único que accede al schema `despacho`. Consume (requiere) dos
interfaces: IEstadoEmergencia e IDisponibilidadFlota. Importa SOLO los
contratos (app.contratos.*), nunca las implementaciones: las recibe por
inyección de dependencias en el constructor. Esto mantiene las
dependencias apuntando hacia abstracciones estables (SDP + SAP) y sin
ciclos (ADP): Despacho -> Flota, Despacho -> Emergencias, y nada vuelve.
"""
import math
import time

from app.comun.db import transaccion
from app.comun.errores import FallaSimulada, NoEncontrado, SinAmbulanciasDisponibles, ErrorDominio
from app.contratos.despacho import ESTADOS_DESPACHO, Despacho, IDespacho, OpcionesDemo
from app.contratos.emergencias import IEstadoEmergencia
from app.contratos.flota import Ambulancia, IDisponibilidadFlota

_COLUMNAS = "id, emergencia_id, ambulancia_id, distancia_km, estado, asignado_en, finalizado_en"


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta (fórmula de Haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def tipos_admitidos(prioridad: str) -> list[str]:
    """Regla de negocio: una emergencia ALTA requiere unidad AVANZADA."""
    return ["AVANZADA"] if prioridad == "ALTA" else ["BASICA", "AVANZADA"]


def elegir_mas_adecuada(candidatas: list[Ambulancia], lat: float, lon: float) -> tuple[Ambulancia, float]:
    """La más cercana; ante empate preferimos BASICA para reservar las AVANZADAS."""
    def criterio(a: Ambulancia):
        return (round(distancia_km(a.latitud, a.longitud, lat, lon), 3), 0 if a.tipo == "BASICA" else 1)

    elegida = min(candidatas, key=criterio)
    return elegida, round(distancia_km(elegida.latitud, elegida.longitud, lat, lon), 2)


def _a_despacho(fila: dict) -> Despacho:
    return Despacho(**fila)


class ServicioDespacho(IDespacho):

    def __init__(self, flota: IDisponibilidadFlota, emergencias: IEstadoEmergencia):
        self._flota = flota
        self._emergencias = emergencias

    def asignar(self, emergencia_id, opciones=OpcionesDemo()):
        # TODO lo que ocurre dentro de este bloque es UNA transacción:
        # si cualquier paso falla, PostgreSQL deshace todos los anteriores.
        with transaccion() as cx:
            # 1. Tomar la emergencia (bloqueada: nadie más puede asignarla ahora)
            emergencia = self._emergencias.bloquear_pendiente(emergencia_id)

            # 2. Obtener y bloquear las unidades candidatas
            candidatas = self._flota.bloquear_disponibles(tipos_admitidos(emergencia.prioridad))
            if not candidatas:
                raise SinAmbulanciasDisponibles(
                    f"No hay ambulancias disponibles de tipo {tipos_admitidos(emergencia.prioridad)}"
                )

            # 3. Elegir la más adecuada
            elegida, km = elegir_mas_adecuada(candidatas, emergencia.latitud, emergencia.longitud)

            if opciones.demora_ms > 0:   # demo de aislamiento: mantiene los bloqueos tomados
                time.sleep(min(opciones.demora_ms, 15000) / 1000)

            # 4. Cambiar estados en los otros componentes (vía sus interfaces)
            self._flota.marcar_en_servicio(elegida.id)
            self._emergencias.marcar_asignada(emergencia.id)

            if opciones.simular_falla:   # demo de atomicidad: los pasos 4 se deshacen
                raise FallaSimulada(
                    f"Falla simulada luego de marcar {elegida.codigo} EN_SERVICIO y la "
                    f"emergencia {emergencia.id} ASIGNADA. Se hizo ROLLBACK de todo."
                )

            # 5. Registrar el despacho
            fila = cx.execute(
                f"""INSERT INTO despacho.despachos (emergencia_id, ambulancia_id, distancia_km)
                    VALUES (%s, %s, %s) RETURNING {_COLUMNAS}""",
                (emergencia.id, elegida.id, km),
            ).fetchone()
        return _a_despacho(fila)   # llegar aquí = COMMIT realizado (durable)

    def finalizar(self, despacho_id):
        with transaccion() as cx:
            fila = cx.execute(
                f"SELECT {_COLUMNAS} FROM despacho.despachos WHERE id = %s FOR UPDATE", (despacho_id,)
            ).fetchone()
            if fila is None:
                raise NoEncontrado(f"No existe el despacho {despacho_id}")
            if fila["estado"] != "ACTIVO":
                raise ErrorDominio(f"El despacho {despacho_id} ya está {fila['estado']}")
            self._flota.liberar(fila["ambulancia_id"])
            self._emergencias.cerrar(fila["emergencia_id"])
            fila = cx.execute(
                f"""UPDATE despacho.despachos SET estado = 'FINALIZADO', finalizado_en = now()
                    WHERE id = %s RETURNING {_COLUMNAS}""",
                (despacho_id,),
            ).fetchone()
        return _a_despacho(fila)

    def listar(self, estado=None):
        if estado is not None and estado not in ESTADOS_DESPACHO:
            raise ErrorDominio(f"Estado inválido: {estado}. Valores: {ESTADOS_DESPACHO}")
        with transaccion() as cx:
            if estado:
                filas = cx.execute(
                    f"SELECT {_COLUMNAS} FROM despacho.despachos WHERE estado = %s ORDER BY id", (estado,)
                ).fetchall()
            else:
                filas = cx.execute(f"SELECT {_COLUMNAS} FROM despacho.despachos ORDER BY id").fetchall()
        return [_a_despacho(f) for f in filas]

    def obtener(self, despacho_id):
        with transaccion() as cx:
            fila = cx.execute(
                f"SELECT {_COLUMNAS} FROM despacho.despachos WHERE id = %s", (despacho_id,)
            ).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe el despacho {despacho_id}")
        return _a_despacho(fila)
