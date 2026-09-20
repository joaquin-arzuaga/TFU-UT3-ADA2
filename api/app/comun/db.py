"""
Acceso a la base de datos y manejo de transacciones (ACID).

Idea central: `transaccion()` abre una transacción y la deja disponible
en el contexto de ejecución actual. Si dentro de esa transacción otro
componente vuelve a llamar a `transaccion()`, NO abre una nueva: se
"une" a la que ya existe. Así, cuando Despacho coordina una asignación
que toca datos de Flota y de Emergencias, todo ocurre en UNA sola
transacción (todo o nada), sin que las interfaces de los componentes
tengan que recibir detalles técnicos como conexiones o cursores.
"""
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://ambulancias:ambulancias@localhost:5432/ambulancias"
)

_pool: ConnectionPool | None = None
_conexion_actual: ContextVar[Connection | None] = ContextVar("conexion_actual", default=None)


def iniciar_pool() -> None:
    global _pool
    _pool = ConnectionPool(
        DATABASE_URL,
        min_size=1,
        max_size=int(os.getenv("DB_POOL_MAX", "10")),
        kwargs={"row_factory": dict_row},
        # Verifica cada conexión antes de entregarla: si la BD se reinició,
        # descarta la conexión rota y abre una nueva (la API se recupera sola).
        check=ConnectionPool.check_connection,
        open=True,
    )
    _pool.wait(timeout=30)


def cerrar_pool() -> None:
    if _pool is not None:
        _pool.close()


def pool_disponible() -> bool:
    return _pool is not None


@contextmanager
def transaccion() -> Iterator[Connection]:
    """Abre una transacción o se une a la que ya está en curso."""
    conexion = _conexion_actual.get()
    if conexion is not None:
        # Ya hay una transacción abierta por quien nos llamó: participamos de ella.
        yield conexion
        return

    if _pool is None:
        raise RuntimeError("El pool de conexiones no fue inicializado")

    with _pool.connection() as conexion:
        # conexion.transaction() hace COMMIT si el bloque termina bien
        # y ROLLBACK si se lanza cualquier excepción (Atomicidad).
        with conexion.transaction():
            token = _conexion_actual.set(conexion)
            try:
                yield conexion
            finally:
                _conexion_actual.reset(token)
