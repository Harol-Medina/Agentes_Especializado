# Estructura del Proyecto — Convención Global

Convención aplicable a todos los workspaces. Los lenguajes, frameworks y servicios concretos se definen en el steering local de cada workspace.

---

## Principio

Infraestructura Docker vive en la raíz. Código de aplicación vive en `apps/`. Variables de entorno en `.data/`.

---

## Estructura raíz

```
/
├── docker-compose.yml
├── docker/
│   └── <servicio>/Dockerfile    # Uno por servicio, multi-stage
├── nginx/
│   └── default.conf
├── .data/
│   ├── .env                     # Entorno activo
│   ├── .env.dev
│   └── .env.prod
└── README.md
```

## Estructura apps

```
apps/
├── <servicio-1>/
├── <servicio-2>/
└── <servicio-n>/
```

Cada servicio es un directorio independiente con su propio package manager y dependencias.

---

## Docker — Operación

El stack se levanta con:

```
docker compose build
docker compose up
docker compose down
```

Sin parámetros, sin scripts, sin flags adicionales. Estos tres comandos son suficientes en cualquier equipo que tenga Docker instalado.

## Docker — Builds

Cada Dockerfile sigue multi-stage:

1. **Stage build**: descarga dependencias y compila
2. **Stage runtime**: imagen mínima que ejecuta

El Dockerfile copia el código con `COPY apps/<servicio>/ .` — el build es autocontenido y reproducible. Cualquier equipo que clone el repo obtiene el mismo resultado.

> **Contrarresta inercia del modelo:** Por defecto se tiende a generar bind mounts (`volumes: ./apps/x:/app`) para hot-reload. En este proyecto el Dockerfile copia todo internamente. Los bind mounts rompen la portabilidad entre equipos.

## Variables de entorno

- `.data/.env` es lo que Docker Compose consume.
- Cada servicio referencia `env_file: .data/.env` en el compose.
- Para cambiar de entorno: copiar plantilla sobre `.env` y rebuild.

> **Contrarresta inercia del modelo:** Se tiende a crear `.env.local` dentro de cada app o pasar `--env-file` como flag. Aquí toda la config vive centralizada en `.data/` y se inyecta via Docker.

---

## Reglas de ubicación

| Qué | Dónde |
|-----|-------|
| Dockerfiles | `docker/<servicio>/Dockerfile` |
| Código de aplicación | `apps/<servicio>/` |
| Variables de entorno | `.data/.env` |
| Nginx config | `nginx/default.conf` |
| Documentación | `docs/` |
