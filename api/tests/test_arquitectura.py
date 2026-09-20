"""
Tests de arquitectura: verifican que las dependencias entre componentes
respeten el modelo de componentes documentado.

Ejecutar desde la carpeta api/:  python -m pytest -q
"""
import ast
from datetime import datetime
from pathlib import Path

from app.contratos.flota import Ambulancia
from app.despacho.servicio import elegir_mas_adecuada, tipos_admitidos

APP = Path(__file__).resolve().parents[1] / "app"
COMPONENTES = {"flota", "emergencias", "despacho"}


def _imports(componente: str) -> set[str]:
    modulos = set()
    for archivo in (APP / componente).glob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos.add(nodo.module)
            elif isinstance(nodo, ast.Import):
                modulos.update(a.name for a in nodo.names)
    return modulos


def _componentes_usados(componente: str) -> set[str]:
    usados = set()
    for m in _imports(componente):
        partes = m.split(".")
        if len(partes) >= 2 and partes[0] == "app" and partes[1] in COMPONENTES and partes[1] != componente:
            usados.add(partes[1])
    return usados


def test_ningun_componente_importa_implementaciones_de_otro():
    """Solo se permite depender de app.contratos.* (interfaces), nunca de otra implementación."""
    for c in COMPONENTES:
        assert _componentes_usados(c) == set(), f"{c} depende de la implementación de {_componentes_usados(c)}"


def test_flota_y_emergencias_no_conocen_a_despacho():
    """Sin ciclos (ADP): las dependencias van de Despacho hacia Flota/Emergencias y no vuelven."""
    for c in ("flota", "emergencias"):
        assert not any("despacho" in m for m in _imports(c))


def test_despacho_consume_las_interfaces_requeridas():
    assert {"app.contratos.flota", "app.contratos.emergencias"} <= _imports("despacho")


def _amb(id_, tipo, lat, lon):
    return Ambulancia(id_, f"AMB-{id_}", tipo, "DISPONIBLE", lat, lon, datetime.now())


def test_prioridad_alta_exige_unidad_avanzada():
    assert tipos_admitidos("ALTA") == ["AVANZADA"]
    assert set(tipos_admitidos("BAJA")) == {"BASICA", "AVANZADA"}


def test_elige_la_mas_cercana():
    lejana, cercana = _amb(1, "BASICA", -34.80, -56.00), _amb(2, "BASICA", -34.90, -56.19)
    elegida, km = elegir_mas_adecuada([lejana, cercana], -34.905, -56.19)
    assert elegida.id == 2 and km < 1


def test_ante_empate_prefiere_basica():
    avanzada, basica = _amb(1, "AVANZADA", -34.9, -56.19), _amb(2, "BASICA", -34.9, -56.19)
    elegida, _ = elegir_mas_adecuada([avanzada, basica], -34.9, -56.19)
    assert elegida.tipo == "BASICA"
