"""
Demo interactiva del TFU UT3 - Gestión de flota de ambulancias.

Corre DENTRO de un contenedor, así el único requisito es Docker
(funciona igual en Linux, Windows y macOS):

    docker compose run --rm demo          -> menú
    docker compose run --rm demo 4        -> directo a la demo 4

Solo usa la biblioteca estándar de Python.
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter

BASE = os.getenv("BASE", "http://gateway/api/v1")
AUTO = os.getenv("AUTO") == "1"   # sin pausas (para pruebas automáticas)

# Colores ANSI (Windows Terminal, PowerShell, consolas de Linux/macOS).
# Si se ven códigos raros:  docker compose run --rm -e NO_COLOR=1 demo
if os.getenv("NO_COLOR"):
    AZUL = VERDE = AMARILLO = ROJO = GRIS = NEGRITA = FIN = ""
else:
    AZUL, VERDE, AMARILLO, ROJO, GRIS, NEGRITA, FIN = (
        "\033[1;36m", "\033[1;32m", "\033[1;33m", "\033[1;31m", "\033[2m", "\033[1m", "\033[0m")

EMERGENCIA_ALTA = {"descripcion": "Politraumatismo", "direccion": "Rambla y Sarmiento",
                   "latitud": -34.9150, "longitud": -56.1600, "prioridad": "ALTA"}


# ------------------------------------------------------------------ utilidades
def titulo(texto):
    print(f"\n{AZUL}{'=' * 72}\n  {texto}\n{'=' * 72}{FIN}")


def paso(texto):
    print(f"\n{VERDE}>> {texto}{FIN}")


def nota(texto):
    print(f"{GRIS}   {texto}{FIN}")


def pausa(texto="Enter para continuar"):
    if AUTO:
        return
    try:
        input(f"{GRIS}   [{texto}] {FIN}")
    except EOFError:
        pass


def en_otra_terminal(*comandos):
    """Pide al presentador que ejecute comandos de Docker en otra terminal."""
    print(f"\n{AMARILLO}   +-- Ejecutá en OTRA terminal, en la carpeta del proyecto:")
    for c in comandos:
        print(f"   |      {NEGRITA}{c}{FIN}{AMARILLO}")
    print(f"   +-- (iguales en PowerShell, CMD y bash){FIN}")
    pausa("Enter cuando haya terminado")


def http(metodo, ruta, cuerpo=None, timeout=30):
    """Devuelve (codigo, instancia, json|texto, segundos)."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    inicio = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            codigo, cabeceras, raw = r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        codigo, cabeceras, raw = e.code, e.headers, e.read()
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        return 0, "-", f"sin conexión: {e}", time.time() - inicio
    try:
        contenido = json.loads(raw)
    except ValueError:
        contenido = raw.decode(errors="replace")
    return codigo, cabeceras.get("X-Instancia", "?"), contenido, time.time() - inicio


def mostrar(metodo, ruta, cuerpo=None):
    codigo, inst, contenido, _ = http(metodo, ruta, cuerpo)
    color = VERDE if 200 <= codigo < 300 else ROJO
    print(f"   {metodo} {ruta}  ->  {color}HTTP {codigo}{FIN}   {GRIS}(atendió réplica {inst}){FIN}")
    texto = json.dumps(contenido, ensure_ascii=False) if not isinstance(contenido, str) else contenido
    print(f"   {texto[:700]}")
    return codigo, inst, contenido


def flota():
    _, _, amb, _ = http("GET", "/ambulancias")
    for a in amb:
        color = {"DISPONIBLE": VERDE, "EN_SERVICIO": ROJO}.get(a["estado"], AMARILLO)
        print(f"   {a['codigo']}  {a['tipo']:<9} {color}{a['estado']}{FIN}")


def esperar_api(segundos=90, silencioso=False):
    if not silencioso:
        print(f"{GRIS}   Esperando la API en {BASE} ", end="", flush=True)
    for _ in range(segundos // 2):
        if http("GET", "/salud", timeout=3)[0] == 200:
            if not silencioso:
                print(f"lista.{FIN}")
            return True
        if not silencioso:
            print(".", end="", flush=True)
        time.sleep(2)
    print(f"\n{ROJO}   La API no responde. ¿Ejecutaste 'docker compose up -d --build'?{FIN}")
    return False


def reiniciar_datos():
    http("POST", "/demo/reset")
    nota("Datos reiniciados: 6 ambulancias, sin emergencias ni despachos.")


def distribucion(n):
    conteo = Counter(http("GET", "/ambulancias")[1] for _ in range(n))
    for inst, cant in sorted(conteo.items()):
        print(f"   réplica {inst}:  {'#' * cant} {cant}")
    return conteo


# ------------------------------------------------------------------ demo 1
def demo_componentes():
    titulo("DEMO 1 - COMPONENTES E INTERFACES")
    reiniciar_datos()

    paso("Componente FLOTA - interfaz IGestionFlota")
    flota()
    nota("Actualizar la ubicación de AMB-02 en tiempo real:")
    mostrar("PATCH", "/ambulancias/2/ubicacion", {"latitud": -34.9100, "longitud": -56.1650})
    nota("Regla propia de Flota: EN_SERVICIO no se asigna a mano, lo decide Despacho:")
    mostrar("PATCH", "/ambulancias/4/estado", {"estado": "EN_SERVICIO"})
    pausa()

    paso("Componente EMERGENCIAS - interfaz IRegistroEmergencias")
    _, _, alta = mostrar("POST", "/emergencias", {
        "descripcion": "Paro cardiorrespiratorio", "direccion": "Av. 18 de Julio 1200",
        "latitud": -34.9055, "longitud": -56.1880, "prioridad": "ALTA"})
    _, _, baja = mostrar("POST", "/emergencias", {
        "descripcion": "Esguince de tobillo", "direccion": "Grecia 3500",
        "latitud": -34.8870, "longitud": -56.2500, "prioridad": "BAJA"})
    pausa()

    paso("Componente DESPACHO - interfaz IDespacho")
    nota("Despacho REQUIERE IEstadoEmergencia (Emergencias) e IDisponibilidadFlota (Flota).")
    nota("Regla: prioridad ALTA exige unidad AVANZADA; se elige la más cercana.")
    nota(f"Emergencia ALTA #{alta['id']} en el Centro -> se espera AMB-01 (AVANZADA, Centro):")
    _, _, d1 = mostrar("POST", "/despachos", {"emergencia_id": alta["id"]})
    nota(f"Emergencia BAJA #{baja['id']} en el Cerro -> se espera AMB-04 (BASICA, Cerro):")
    mostrar("POST", "/despachos", {"emergencia_id": baja["id"]})
    nota("Efecto en Flota (cambiado por Despacho a través de IDisponibilidadFlota):")
    flota()
    nota("Finalizar el despacho: libera la ambulancia y cierra la emergencia:")
    mostrar("POST", f"/despachos/{d1['id']}/finalizar")
    pausa()

    paso("Contrato de errores de las interfaces")
    mostrar("GET", "/ambulancias/999")
    mostrar("POST", "/despachos", {"emergencia_id": baja["id"]})
    mostrar("POST", "/emergencias", {"descripcion": "Prueba", "direccion": "Calle 1",
                                     "latitud": -34.9, "longitud": -56.1, "prioridad": "URGENTISIMA"})
    nota("400/409 = regla de negocio o estado inválido - 404 = no existe - 422 = no cumple el contrato")
    pausa()

    paso("Verificación automática de dependencias entre componentes (tests)")
    subprocess.run([sys.executable, "-m", "pytest", "-v", "--no-header", "-p", "no:cacheprovider", "tests"])
    nota("Ningún componente importa la implementación de otro, solo contratos; y no hay ciclos.")


# ------------------------------------------------------------------ demo 2
def demo_escalabilidad():
    titulo("DEMO 2 - ESCALABILIDAD HORIZONTAL")
    paso("12 solicitudes al gateway: se reparten entre las réplicas (round-robin)")
    distribucion(12)
    pausa()

    paso("Escalamos a 5 réplicas sin tocar el código")
    en_otra_terminal("docker compose up -d --scale api=5",
                     "docker compose restart gateway")
    esperar_api()
    paso("15 solicitudes: ahora se reparten entre 5 réplicas")
    distribucion(15)
    pausa()

    paso("Volvemos a 3 réplicas (la capacidad se ajusta a la demanda)")
    en_otra_terminal("docker compose up -d --scale api=3",
                     "docker compose restart gateway")
    esperar_api()
    distribucion(9)
    nota("Es posible porque la API es SIN ESTADO (demo 3).")
    nota("Escalar VERTICALMENTE sería subir deploy.resources.limits (cpus/memory) de cada réplica.")


# ------------------------------------------------------------------ demo 3
def demo_sin_estado():
    titulo("DEMO 3 - SERVICIOS SIN ESTADO")
    reiniciar_datos()
    paso("Registrar una emergencia (la recibe una réplica cualquiera)")
    _, creadora, em = mostrar("POST", "/emergencias", {
        "descripcion": "Accidente de tránsito", "direccion": "Bv. Artigas y Rivera",
        "latitud": -34.8990, "longitud": -56.1600, "prioridad": "MEDIA"})

    paso("Leerla 6 veces: la atienden réplicas distintas y TODAS devuelven lo mismo")
    for _ in range(6):
        _, inst, c, _ = http("GET", f"/emergencias/{em['id']}")
        print(f"   réplica {inst}  ->  emergencia #{c['id']} estado {c['estado']}")
    paso("Asignarla en una réplica y finalizarla en otra (no hace falta 'sesión pegajosa')")
    _, _, d = mostrar("POST", "/despachos", {"emergencia_id": em["id"]})
    mostrar("POST", f"/despachos/{d['id']}/finalizar")
    pausa()

    paso(f"Caída de una réplica: detenemos la que creó la emergencia ({creadora})")
    en_otra_terminal(f"docker stop {creadora}")
    paso("El sistema sigue respondiendo con las réplicas restantes, sin perder datos")
    for _ in range(6):
        codigo, inst, _, seg = http("GET", f"/emergencias/{em['id']}")
        print(f"   HTTP {codigo}  réplica {inst}  ({seg:.2f}s)")
    nota("La primera solicitud puede demorar ~2 s: el gateway detecta la caída y reintenta en otra réplica.")
    mostrar("POST", "/emergencias", {"descripcion": "Intoxicación", "direccion": "Av. Italia 3000",
                                     "latitud": -34.8950, "longitud": -56.1400, "prioridad": "BAJA"})
    pausa()

    paso("Volvemos a iniciar la réplica")
    en_otra_terminal(f"docker start {creadora}")
    nota("Contraejemplo (clase 08): si la sesión estuviera en la memoria de una réplica,")
    nota("al caer esa réplica o al balancear hacia otra, el usuario perdería su estado.")


# ------------------------------------------------------------------ demo 4
def demo_acid():
    titulo("DEMO 4 - ACID")
    reiniciar_datos()

    paso("A - ATOMICIDAD: todo o nada")
    _, _, e1 = mostrar("POST", "/emergencias", EMERGENCIA_ALTA)
    nota("Asignar con una falla simulada DESPUÉS de marcar la ambulancia y la emergencia:")
    mostrar("POST", "/despachos?simular_falla=true", {"emergencia_id": e1["id"]})
    nota("Resultado: se deshizo todo (ROLLBACK):")
    mostrar("GET", f"/emergencias/{e1['id']}")
    flota()
    mostrar("GET", "/despachos")
    pausa()

    paso("I - AISLAMIENTO: dos operadores compiten por la última unidad AVANZADA")
    http("PATCH", "/ambulancias/3/estado", {"estado": "EN_MANTENIMIENTO"})
    http("PATCH", "/ambulancias/6/estado", {"estado": "EN_MANTENIMIENTO"})
    flota()
    e2 = http("POST", "/emergencias", EMERGENCIA_ALTA)[2]
    e3 = http("POST", "/emergencias", EMERGENCIA_ALTA)[2]
    nota(f"Operador A asigna la #{e2['id']} (su transacción retiene los bloqueos 4 s);")
    nota(f"1 s después, Operador B asigna la #{e3['id']}...")
    resultados = {}

    def operador(nombre, ruta, eid):
        resultados[nombre] = http("POST", ruta, {"emergencia_id": eid})

    a = threading.Thread(target=operador, args=("A", "/despachos?demora_ms=4000", e2["id"]))
    b = threading.Thread(target=operador, args=("B", "/despachos", e3["id"]))
    a.start(); time.sleep(1); b.start(); a.join(); b.join()
    for nombre in ("A", "B"):
        codigo, inst, contenido, seg = resultados[nombre]
        color = VERDE if codigo == 201 else ROJO
        print(f"   Operador {nombre}: {color}HTTP {codigo}{FIN} en {seg:.1f}s (réplica {inst})")
        print(f"      {json.dumps(contenido, ensure_ascii=False)[:300]}")
    nota("B quedó ESPERANDO el bloqueo de A. Cuando A confirmó, B vio la unidad EN_SERVICIO")
    nota("y recibió 409: la misma ambulancia NUNCA se despacha a dos emergencias.")
    pausa()

    paso("C - CONSISTENCIA: la base rechaza estados inválidos aunque se saltee la API")
    _, _, intentos, _ = http("POST", "/demo/consistencia")
    for i in intentos:
        print(f"   {i['intento']}")
        print(f"      -> {ROJO}{i['resultado']}{FIN}  {GRIS}(restricción: {i.get('restriccion')}){FIN}")
    pausa()

    paso("D - DURABILIDAD: lo confirmado sobrevive a la caída de la base de datos")
    mostrar("GET", "/despachos?estado=ACTIVO")
    en_otra_terminal("docker compose restart db")
    esperar_api()
    nota("Después del reinicio, los despachos siguen ahí (volumen datos_db):")
    mostrar("GET", "/despachos?estado=ACTIVO")


# ------------------------------------------------------------------ menú
DEMOS = {"1": ("Componentes e interfaces", demo_componentes),
         "2": ("Escalabilidad horizontal", demo_escalabilidad),
         "3": ("Servicios sin estado", demo_sin_estado),
         "4": ("ACID", demo_acid)}


def main():
    if not esperar_api():
        sys.exit(1)
    elegidas = sys.argv[1:]
    while True:
        if not elegidas:
            titulo("TFU UT3 - Gestion de flota de ambulancias - DEMO")
            for k, (nombre, _) in DEMOS.items():
                print(f"   {k}. {nombre}")
            print("   5. Todas en orden\n   0. Salir")
            try:
                opcion = input(f"\n{NEGRITA}   Opción: {FIN}").strip()
            except EOFError:
                return
            elegidas = list(DEMOS) if opcion == "5" else [opcion]
            if opcion == "0":
                return
        for k in elegidas:
            if k in DEMOS:
                DEMOS[k][1]()
            else:
                print(f"{ROJO}   Opción inválida: {k}{FIN}")
        if len(sys.argv) > 1:
            return
        elegidas = []
        pausa("Enter para volver al menú")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
