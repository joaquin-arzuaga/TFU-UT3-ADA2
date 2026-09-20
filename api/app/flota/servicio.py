"""
Componente FLOTA: implementación.

Es el único que accede al schema `flota`. Implementa sus dos interfaces
provistas. No conoce a ningún otro componente (no tiene dependencias
salientes hacia el dominio), por eso es estable.
"""
from app.comun.db import transaccion
from app.comun.errores import Conflicto, ErrorDominio, NoEncontrado
from app.contratos.flota import (
    ESTADOS_AMBULANCIA, TIPOS_AMBULANCIA, Ambulancia,
    IDisponibilidadFlota, IGestionFlota,
)

_COLUMNAS = "id, codigo, tipo, estado, latitud, longitud, actualizada_en"


def _a_ambulancia(fila: dict) -> Ambulancia:
    return Ambulancia(**fila)


class ServicioFlota(IGestionFlota, IDisponibilidadFlota):

    # ------------------------- IGestionFlota -------------------------
    def registrar(self, codigo, tipo, latitud, longitud):
        if tipo not in TIPOS_AMBULANCIA:
            raise ErrorDominio(f"Tipo inválido: {tipo}. Valores: {TIPOS_AMBULANCIA}")
        with transaccion() as cx:
            existe = cx.execute("SELECT 1 FROM flota.ambulancias WHERE codigo = %s", (codigo,)).fetchone()
            if existe:
                raise Conflicto(f"Ya existe una ambulancia con código {codigo}")
            fila = cx.execute(
                f"""INSERT INTO flota.ambulancias (codigo, tipo, latitud, longitud)
                    VALUES (%s, %s, %s, %s) RETURNING {_COLUMNAS}""",
                (codigo, tipo, latitud, longitud),
            ).fetchone()
        return _a_ambulancia(fila)

    def listar(self, estado=None):
        if estado is not None and estado not in ESTADOS_AMBULANCIA:
            raise ErrorDominio(f"Estado inválido: {estado}. Valores: {ESTADOS_AMBULANCIA}")
        with transaccion() as cx:
            if estado:
                filas = cx.execute(
                    f"SELECT {_COLUMNAS} FROM flota.ambulancias WHERE estado = %s ORDER BY id", (estado,)
                ).fetchall()
            else:
                filas = cx.execute(f"SELECT {_COLUMNAS} FROM flota.ambulancias ORDER BY id").fetchall()
        return [_a_ambulancia(f) for f in filas]

    def obtener(self, ambulancia_id):
        with transaccion() as cx:
            fila = cx.execute(
                f"SELECT {_COLUMNAS} FROM flota.ambulancias WHERE id = %s", (ambulancia_id,)
            ).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe la ambulancia {ambulancia_id}")
        return _a_ambulancia(fila)

    def cambiar_estado_operativo(self, ambulancia_id, nuevo_estado):
        if nuevo_estado not in ("DISPONIBLE", "EN_MANTENIMIENTO"):
            raise ErrorDominio(
                "Solo se puede pasar manualmente a DISPONIBLE o EN_MANTENIMIENTO; "
                "EN_SERVICIO lo asigna el componente Despacho"
            )
        with transaccion() as cx:
            actual = cx.execute(
                "SELECT estado FROM flota.ambulancias WHERE id = %s FOR UPDATE", (ambulancia_id,)
            ).fetchone()
            if actual is None:
                raise NoEncontrado(f"No existe la ambulancia {ambulancia_id}")
            if actual["estado"] == "EN_SERVICIO":
                raise Conflicto("La ambulancia está EN_SERVICIO: primero debe finalizarse el despacho")
            fila = cx.execute(
                f"""UPDATE flota.ambulancias SET estado = %s, actualizada_en = now()
                    WHERE id = %s RETURNING {_COLUMNAS}""",
                (nuevo_estado, ambulancia_id),
            ).fetchone()
        return _a_ambulancia(fila)

    def actualizar_ubicacion(self, ambulancia_id, latitud, longitud):
        with transaccion() as cx:
            fila = cx.execute(
                f"""UPDATE flota.ambulancias SET latitud = %s, longitud = %s, actualizada_en = now()
                    WHERE id = %s RETURNING {_COLUMNAS}""",
                (latitud, longitud, ambulancia_id),
            ).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe la ambulancia {ambulancia_id}")
        return _a_ambulancia(fila)

    # ---------------------- IDisponibilidadFlota ----------------------
    def bloquear_disponibles(self, tipos):
        with transaccion() as cx:
            # FOR UPDATE: bloquea las filas hasta el COMMIT/ROLLBACK de la
            # transacción de quien llama. Si otra asignación concurrente
            # quiere las mismas unidades, espera; al retomar, PostgreSQL
            # re-evalúa el WHERE y ya no ve las que pasaron a EN_SERVICIO.
            # ORDER BY id => orden de bloqueo fijo, evita deadlocks.
            filas = cx.execute(
                f"""SELECT {_COLUMNAS} FROM flota.ambulancias
                    WHERE estado = 'DISPONIBLE' AND tipo = ANY(%s)
                    ORDER BY id FOR UPDATE""",
                (list(tipos),),
            ).fetchall()
        return [_a_ambulancia(f) for f in filas]

    def marcar_en_servicio(self, ambulancia_id):
        with transaccion() as cx:
            cur = cx.execute(
                """UPDATE flota.ambulancias SET estado = 'EN_SERVICIO', actualizada_en = now()
                   WHERE id = %s AND estado = 'DISPONIBLE'""",
                (ambulancia_id,),
            )
            if cur.rowcount != 1:
                raise Conflicto(f"La ambulancia {ambulancia_id} ya no está DISPONIBLE")

    def liberar(self, ambulancia_id):
        with transaccion() as cx:
            cur = cx.execute(
                """UPDATE flota.ambulancias SET estado = 'DISPONIBLE', actualizada_en = now()
                   WHERE id = %s AND estado = 'EN_SERVICIO'""",
                (ambulancia_id,),
            )
            if cur.rowcount != 1:
                raise Conflicto(f"La ambulancia {ambulancia_id} no estaba EN_SERVICIO")
