"""
Componente EMERGENCIAS: implementación.

Es el único que accede al schema `emergencias`. No depende de ningún otro
componente de dominio.
"""
from app.comun.db import transaccion
from app.comun.errores import Conflicto, ErrorDominio, NoEncontrado
from app.contratos.emergencias import (
    ESTADOS_EMERGENCIA, PRIORIDADES, Emergencia,
    IEstadoEmergencia, IRegistroEmergencias,
)

_COLUMNAS = "id, descripcion, direccion, latitud, longitud, prioridad, estado, creada_en"


def _a_emergencia(fila: dict) -> Emergencia:
    return Emergencia(**fila)


class ServicioEmergencias(IRegistroEmergencias, IEstadoEmergencia):

    # ---------------------- IRegistroEmergencias ----------------------
    def registrar(self, descripcion, direccion, latitud, longitud, prioridad):
        if prioridad not in PRIORIDADES:
            raise ErrorDominio(f"Prioridad inválida: {prioridad}. Valores: {PRIORIDADES}")
        with transaccion() as cx:
            fila = cx.execute(
                f"""INSERT INTO emergencias.emergencias
                        (descripcion, direccion, latitud, longitud, prioridad)
                    VALUES (%s, %s, %s, %s, %s) RETURNING {_COLUMNAS}""",
                (descripcion, direccion, latitud, longitud, prioridad),
            ).fetchone()
        return _a_emergencia(fila)

    def listar(self, estado=None):
        if estado is not None and estado not in ESTADOS_EMERGENCIA:
            raise ErrorDominio(f"Estado inválido: {estado}. Valores: {ESTADOS_EMERGENCIA}")
        with transaccion() as cx:
            if estado:
                filas = cx.execute(
                    f"SELECT {_COLUMNAS} FROM emergencias.emergencias WHERE estado = %s ORDER BY id",
                    (estado,),
                ).fetchall()
            else:
                filas = cx.execute(
                    f"SELECT {_COLUMNAS} FROM emergencias.emergencias ORDER BY id"
                ).fetchall()
        return [_a_emergencia(f) for f in filas]

    def obtener(self, emergencia_id):
        with transaccion() as cx:
            fila = cx.execute(
                f"SELECT {_COLUMNAS} FROM emergencias.emergencias WHERE id = %s", (emergencia_id,)
            ).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe la emergencia {emergencia_id}")
        return _a_emergencia(fila)

    # ----------------------- IEstadoEmergencia ------------------------
    def bloquear_pendiente(self, emergencia_id):
        with transaccion() as cx:
            fila = cx.execute(
                f"SELECT {_COLUMNAS} FROM emergencias.emergencias WHERE id = %s FOR UPDATE",
                (emergencia_id,),
            ).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe la emergencia {emergencia_id}")
        if fila["estado"] != "PENDIENTE":
            raise Conflicto(f"La emergencia {emergencia_id} está {fila['estado']}, no PENDIENTE")
        return _a_emergencia(fila)

    def marcar_asignada(self, emergencia_id):
        self._transicionar(emergencia_id, desde="PENDIENTE", hacia="ASIGNADA")

    def cerrar(self, emergencia_id):
        self._transicionar(emergencia_id, desde="ASIGNADA", hacia="CERRADA")

    def _transicionar(self, emergencia_id, desde, hacia):
        with transaccion() as cx:
            cur = cx.execute(
                "UPDATE emergencias.emergencias SET estado = %s WHERE id = %s AND estado = %s",
                (hacia, emergencia_id, desde),
            )
            if cur.rowcount != 1:
                raise Conflicto(f"La emergencia {emergencia_id} no está {desde}")
