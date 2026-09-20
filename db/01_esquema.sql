-- =====================================================================
-- Sistema de gestión de flotas de ambulancias - Esquema de datos
-- Cada componente de dominio es DUEÑO de su propio schema:
--   flota        -> componente Flota
--   emergencias  -> componente Emergencias
--   despacho     -> componente Despacho
-- Ningún componente lee ni escribe las tablas de otro: solo accede
-- a través de las interfaces que ese otro componente expone.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS flota;
CREATE SCHEMA IF NOT EXISTS emergencias;
CREATE SCHEMA IF NOT EXISTS despacho;

-- ---------------------------------------------------------------------
-- Componente FLOTA
-- ---------------------------------------------------------------------
CREATE TABLE flota.ambulancias (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(20)  NOT NULL UNIQUE,
    tipo            VARCHAR(10)  NOT NULL CHECK (tipo IN ('BASICA', 'AVANZADA')),
    estado          VARCHAR(20)  NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'EN_SERVICIO', 'EN_MANTENIMIENTO')),
    latitud         DOUBLE PRECISION NOT NULL CHECK (latitud  BETWEEN -90  AND 90),
    longitud        DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    actualizada_en  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Componente EMERGENCIAS
-- ---------------------------------------------------------------------
CREATE TABLE emergencias.emergencias (
    id           SERIAL PRIMARY KEY,
    descripcion  VARCHAR(500) NOT NULL,
    direccion    VARCHAR(200) NOT NULL,
    latitud      DOUBLE PRECISION NOT NULL CHECK (latitud  BETWEEN -90  AND 90),
    longitud     DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    prioridad    VARCHAR(10)  NOT NULL CHECK (prioridad IN ('ALTA', 'MEDIA', 'BAJA')),
    estado       VARCHAR(10)  NOT NULL DEFAULT 'PENDIENTE'
                 CHECK (estado IN ('PENDIENTE', 'ASIGNADA', 'CERRADA')),
    creada_en    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Componente DESPACHO
-- ---------------------------------------------------------------------
CREATE TABLE despacho.despachos (
    id             SERIAL PRIMARY KEY,
    emergencia_id  INT NOT NULL REFERENCES emergencias.emergencias (id),
    ambulancia_id  INT NOT NULL REFERENCES flota.ambulancias (id),
    distancia_km   DOUBLE PRECISION NOT NULL,
    estado         VARCHAR(12) NOT NULL DEFAULT 'ACTIVO'
                   CHECK (estado IN ('ACTIVO', 'FINALIZADO')),
    asignado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_en  TIMESTAMPTZ
);

-- Invariantes del negocio garantizados por la BD (la "C" de ACID):
-- una ambulancia no puede tener dos despachos activos a la vez,
-- y una emergencia no puede ser atendida por dos despachos activos.
CREATE UNIQUE INDEX ux_despacho_activo_por_ambulancia
    ON despacho.despachos (ambulancia_id) WHERE estado = 'ACTIVO';
CREATE UNIQUE INDEX ux_despacho_activo_por_emergencia
    ON despacho.despachos (emergencia_id) WHERE estado = 'ACTIVO';

-- ---------------------------------------------------------------------
-- Datos iniciales (y reinicio para las demos)
-- Ubicaciones aproximadas en barrios de Montevideo.
-- ---------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE public.demo_reset()
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE despacho.despachos, emergencias.emergencias, flota.ambulancias
        RESTART IDENTITY CASCADE;

    INSERT INTO flota.ambulancias (codigo, tipo, estado, latitud, longitud) VALUES
        ('AMB-01', 'AVANZADA', 'DISPONIBLE',       -34.9058, -56.1913),  -- Centro
        ('AMB-02', 'BASICA',   'DISPONIBLE',       -34.9147, -56.1508),  -- Pocitos
        ('AMB-03', 'AVANZADA', 'DISPONIBLE',       -34.8836, -56.0561),  -- Carrasco
        ('AMB-04', 'BASICA',   'DISPONIBLE',       -34.8847, -56.2556),  -- Cerro
        ('AMB-05', 'BASICA',   'EN_MANTENIMIENTO', -34.8900, -56.1000),  -- Malvín
        ('AMB-06', 'AVANZADA', 'DISPONIBLE',       -34.8580, -56.2050);  -- Prado
END;
$$;
