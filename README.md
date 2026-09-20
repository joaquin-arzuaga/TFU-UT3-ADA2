# TFU UT3 – Sistema de gestión de flota de ambulancias

API REST que registra emergencias, controla en tiempo real el estado de cada
ambulancia (disponible, en servicio o en mantenimiento) y asigna la unidad
disponible más adecuada a cada emergencia.

**Única dependencia: Docker con Docker Compose v2.** No hace falta instalar
Python, bash, curl ni nada más: la API, la base de datos, el gateway y la demo
corren en contenedores. Funciona igual en Windows, Linux (incluido Fedora) y macOS.

---


### Verificar Docker (cualquier sistema)
```
docker --version
docker compose version
docker run --rm hello-world
```
`docker compose version` debe mostrar **v2.x**

---

## 2. Levantar el sistema

Descomprimir el proyecto, abrir una terminal **en la carpeta del proyecto** y ejecutar:

```
docker compose up -d --build
```

La primera vez tarda 1–3 minutos (descarga imágenes). Levanta:
PostgreSQL + **3 réplicas** de la API + gateway Nginx.

- API: http://localhost:8080/api/v1

---

## 3. Ejecutar la demo

```
docker compose run --rm demo
```

Aparece un menú:

```
   1. Componentes e interfaces
   2. Escalabilidad horizontal
   3. Servicios sin estado
   4. ACID
   5. Todas en orden
```

También se puede ir directo a una demo: `docker compose run --rm demo 4`

**Tener abierta una segunda terminal** en la carpeta del proyecto: en algunos
pasos la demo pide ejecutar un comando de Docker (escalar réplicas, detener una
réplica, reiniciar la base). Los comandos son iguales en PowerShell, CMD y bash.

| Demo | Concepto | Qué muestra | Comandos que pide |
|------|----------|-------------|-------------------|
| 1 | Componentes e interfaces | Uso de cada interfaz; Despacho coordina Flota y Emergencias; contrato de errores; tests de dependencias | — |
| 2 | Escalabilidad horizontal | Reparto de carga con 3 réplicas, escalado a 5 y vuelta a 3 | `docker compose up -d --scale api=5` · `docker compose restart gateway` |
| 3 | Servicios sin estado | Cualquier réplica atiende cualquier solicitud; se cae una y no se pierde nada | `docker stop <réplica>` · `docker start <réplica>` |
| 4 | ACID | Atomicidad (rollback), aislamiento (2 operadores compiten), consistencia (la BD rechaza estados inválidos), durabilidad | `docker compose restart db` |
| — | Contenedores | Todo el sistema corre en contenedores | — |

Cada demo reinicia los datos al empezar, así que se pueden repetir las veces que se quiera.

### Alternativa: Postman
Importar `demo/postman_coleccion.json`. Mirar el header de respuesta
**`X-Instancia`** para ver qué réplica atendió cada solicitud.

---

## 4. Apagar

```
docker compose down        # apaga (conserva los datos)
docker compose down -v     # apaga y borra los datos
```

---

## Problemas frecuentes

| Síntoma | Solución |
|---------|----------|
| `Cannot connect to the Docker daemon` / `error during connect` | Docker no está corriendo. Windows: abrir Docker Desktop. Fedora: `sudo systemctl start docker` |
| `permission denied ... docker.sock` (Fedora) | Falta el grupo docker: `sudo usermod -aG docker $USER` y volver a iniciar sesión (o anteponer `sudo`) |
| `docker: 'compose' is not a docker command` | Falta Compose v2: instalar `docker-compose-plugin` (Fedora) o actualizar Docker Desktop |
| `port is already allocated` (8080) | Otro programa usa el puerto. Cambiar `"8080:80"` por `"8081:80"` en `docker-compose.yaml` |
| Se ven códigos raros en lugar de colores | `docker compose run --rm -e NO_COLOR=1 demo` |
| La demo dice que la API no responde | `docker compose ps` y `docker compose logs api` |
| Datos raros después de muchas pruebas | `docker compose down -v` y volver a levantar |

---

## Arquitectura (resumen)

- **Partición de primer nivel por dominio**: componentes `emergencias`, `flota` y `despacho`
  (`api/app/`). Los contratos (interfaces) están en `api/app/contratos`; Despacho solo depende
  de ellos y las implementaciones se conectan en `api/app/main.py`.
- Cada componente es dueño de su schema en PostgreSQL; nadie toca tablas ajenas.
- La API **no guarda estado en memoria**: por eso escala horizontalmente detrás de Nginx.
- La asignación de una ambulancia es **una transacción ACID** que abarca los tres componentes.
- `api/tests/test_arquitectura.py` verifica automáticamente las reglas de dependencia.
- Diagramas y documento de la Parte 1 en `docs/`.

### Endpoints (`/api/v1`)

| Componente | Método y ruta | Descripción |
|---|---|---|
| Flota | `GET /ambulancias[?estado=]`, `GET /ambulancias/{id}` | Consultar flota |
| Flota | `POST /ambulancias` | Registrar ambulancia |
| Flota | `PATCH /ambulancias/{id}/estado` | DISPONIBLE ⇄ EN_MANTENIMIENTO |
| Flota | `PATCH /ambulancias/{id}/ubicacion` | Actualizar posición |
| Emergencias | `POST /emergencias` | Registrar emergencia |
| Emergencias | `GET /emergencias[?estado=]`, `GET /emergencias/{id}` | Consultar |
| Despacho | `POST /despachos` | Asignar la unidad más adecuada |
| Despacho | `POST /despachos/{id}/finalizar` | Liberar ambulancia y cerrar emergencia |
| Despacho | `GET /despachos[?estado=]`, `GET /despachos/{id}` | Consultar |
| Operación | `GET /salud` | Estado de la réplica |
| Demo | `POST /demo/reset`, `POST /demo/consistencia` | Reinicio de datos y prueba de restricciones |

Parámetros solo para la demo ACID en `POST /despachos`: `simular_falla=true` y `demora_ms=N`.
