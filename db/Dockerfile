# Imagen de PostgreSQL con el esquema y los datos iniciales INCLUIDOS.
# Se copian a la imagen (en lugar de montarlos desde el host) para que funcione
# igual en Windows, macOS y Linux con SELinux (Fedora), sin permisos especiales.
FROM postgres:16-alpine
COPY 01_esquema.sql 02_datos_iniciales.sql /docker-entrypoint-initdb.d/
