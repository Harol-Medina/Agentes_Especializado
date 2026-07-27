# Frontend — Software Archaeologist

Interfaz web para análisis inteligente de repositorios.

---

## Propósito

El Frontend proporciona la experiencia de usuario para:

- Enviar repositorios de GitHub para análisis
- Visualizar progreso en tiempo real (polling por agente)
- Explorar el grafo de dependencias interactivo
- Chatear con el código usando RAG (SSE streaming)
- Consultar reportes de arquitectura, calidad y seguridad
- Exportar Kiro Specs para modernización

---

## Tech Stack

| Tecnología | Versión | Propósito |
|---|---|---|
| Next.js | 14.2.5 | Framework React con App Router + SSR |
| React | 18.3.1 | UI library |
| TypeScript | 5.5.3 | Tipado estático |
| Tailwind CSS | 4.x | Framework utilitario (v4 con `@import "tailwindcss"`) |
| shadcn/ui | latest | Componentes UI (Radix primitives) |
| react-force-graph-2d | 1.25.4 | Grafo interactivo de dependencias |
| Lucide React | 0.400.0 | Iconos |
| Radix UI | latest | Primitivas accesibles (Dialog, Tabs, Tooltip, etc.) |
| Node.js | 20 | Runtime |

---

## Estructura del Proyecto (App Router)

```
apps/frontend/
├── components.json            # Configuración shadcn/ui
├── Dockerfile.prod            # Dockerfile para Amplify (standalone)
├── next.config.mjs            # Config Next.js (output: standalone)
├── package.json               # Dependencias y scripts
├── postcss.config.js          # PostCSS con Tailwind
├── tailwind.config.ts         # Config Tailwind (tema, fuentes)
├── tsconfig.json              # TypeScript config
├── public/                    # Assets estáticos
└── src/
    ├── app/                   # App Router (file-based routing)
    │   ├── layout.tsx         # Root layout (fonts, metadata, dark theme)
    │   ├── page.tsx           # Home — formulario de submission
    │   ├── api/               # API routes (reservado)
    │   └── analysis/
    │       └── [jobId]/
    │           ├── page.tsx   # Progreso del análisis (polling)
    │           ├── chat/      # Chat RAG con el código
    │           ├── export/    # Export Kiro Spec
    │           ├── graph/     # Grafo de dependencias
    │           └── report/    # Reporte de arquitectura
    ├── components/
    │   ├── chat/
    │   │   ├── ChatInterface.tsx   # Interfaz completa de chat
    │   │   └── ChatMessage.tsx     # Burbuja de mensaje individual
    │   ├── graph/
    │   │   ├── DependencyGraph.tsx  # Grafo interactivo (force-graph-2d)
    │   │   └── GraphControls.tsx    # Filtros y controles del grafo
    │   ├── report/
    │   │   ├── ArchitectureReport.tsx  # Vista principal del reporte
    │   │   ├── KiroExport.tsx          # Botón y preview de Kiro Spec
    │   │   ├── MetricsGrid.tsx         # Grid de métricas
    │   │   └── ReportSection.tsx       # Sección genérica de reporte
    │   ├── shared/
    │   │   ├── AnalysisProgress.tsx  # Barra de progreso por agente
    │   │   ├── Header.tsx            # Navbar sticky con tabs
    │   │   └── SubmissionForm.tsx    # Formulario de URL de GitHub
    │   └── ui/                       # shadcn/ui primitivas
    │       ├── badge.tsx
    │       ├── button.tsx
    │       ├── card.tsx
    │       ├── input.tsx
    │       ├── label.tsx
    │       ├── progress.tsx
    │       ├── scroll-area.tsx
    │       ├── separator.tsx
    │       ├── tabs.tsx
    │       └── tooltip.tsx
    ├── hooks/
    │   ├── useChat.ts         # SSE streaming para chat RAG
    │   ├── useGraphData.ts    # Fetch y transformación de datos del grafo
    │   ├── useJobPolling.ts   # Polling de estado del job cada 5s
    │   ├── useKiroExport.ts   # Descarga de Kiro Spec markdown
    │   └── useReport.ts      # Fetch del reporte de arquitectura
    ├── lib/
    │   ├── api.ts             # HTTP client wrapper (fetch)
    │   ├── constants.ts       # API URL, polling interval, agent stages
    │   └── utils.ts           # Utilidades (cn, etc.)
    └── styles/
        └── globals.css        # Design system CSS variables + base styles
```

---

## Design System

El frontend implementa un design system dark-first definido en `.kiro/steering/design-system.md`:

### Tipografía (Google Fonts)

| Variable | Fuente | Uso |
|---|---|---|
| `--font-display` | Roboto Slab | Títulos, headings, métricas |
| `--font-body` | Inter | Cuerpo, UI, botones |
| `--font-mono` | JetBrains Mono | Código, labels, status badges |

### Paleta (CSS Variables)

| Token | Color | Uso |
|---|---|---|
| `--background` | `#080D18` | Fondo principal |
| `--primary` | `#F59E0B` | Acento amber/dorado |
| `--secondary` | `#06B6D4` | Acento cyan |
| `--card` | `#0F1624` | Fondo de tarjetas |
| `--border` | `#1E2D45` | Bordes |
| `--muted-foreground` | `#6B7A99` | Texto secundario |

### Colores Semánticos

- Success/Activo: `#10B981`
- Danger/Error: `#EF4444`
- Purple/Datos: `#8B5CF6`
- Orange/Alerta: `#F97316`

Ver archivo completo: `src/styles/globals.css`

---

## Rutas (Páginas)

| Ruta | Descripción |
|---|---|
| `/` | Home — formulario de submission de repositorio |
| `/analysis/[jobId]` | Progreso del análisis (polling cada 5s) |
| `/analysis/[jobId]/graph` | Grafo interactivo de dependencias |
| `/analysis/[jobId]/chat` | Chat RAG con el código |
| `/analysis/[jobId]/report` | Reporte de arquitectura |
| `/analysis/[jobId]/export` | Export de Kiro Spec |

---

## Variables de Entorno

| Variable | Default | Descripción |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `/api` | URL base del Backend API. En Docker: `http://backend:8080/api`. En prod: URL de Elastic Beanstalk |

---

## Desarrollo Local

### Prerequisitos

- Node.js 20+
- npm 9+

### Ejecutar

```bash
# Desde apps/frontend/

# 1. Instalar dependencias
npm install

# 2. Configurar API URL (opcional — default usa /api con proxy nginx)
export NEXT_PUBLIC_API_URL=http://localhost:8080/api

# 3. Iniciar en modo desarrollo
npm run dev

# Abre http://localhost:3000
```

### Con Docker Compose (recomendado)

```bash
# Desde la raíz del proyecto
docker compose build frontend
docker compose up frontend nginx
# Accede via http://localhost (nginx proxy)
```

### Scripts npm

| Script | Descripción |
|---|---|
| `npm run dev` | Servidor de desarrollo con HMR |
| `npm run build` | Build de producción (standalone) |
| `npm run start` | Inicia el server de producción |
| `npm run lint` | ESLint sobre todo el código |

---

## Agregar Componentes shadcn/ui

```bash
# Ejemplo: agregar un nuevo componente
npx shadcn-ui@latest add sheet

# Los componentes se instalan en src/components/ui/
```

Configuración en `components.json`:
- Style: default
- RSC: true (React Server Components)
- Path aliases: `@/components`, `@/lib`, `@/hooks`

---

## Build Docker

Multi-stage build optimizado para Next.js standalone:

1. **Stage Build**: `node:20-alpine` — `npm install` + `npm run build`
2. **Stage Runtime**: `node:20-alpine` — solo `.next/standalone` + static + public

```bash
# Build manual (desde raíz del proyecto)
docker build -f docker/frontend/Dockerfile -t archaeologist-frontend .
```

Resultado: imagen ~150MB con server.js standalone (no necesita node_modules).

---

## Catálogo de Componentes

### Shared

| Componente | Descripción |
|---|---|
| `Header` | Navbar sticky con backdrop blur, tabs de navegación |
| `SubmissionForm` | Input de URL GitHub con validación regex |
| `AnalysisProgress` | Barra de progreso con status por agente (7 etapas) |

### Chat

| Componente | Descripción |
|---|---|
| `ChatInterface` | Contenedor del chat con input y scroll |
| `ChatMessage` | Burbuja de mensaje (user/assistant) con markdown |

### Graph

| Componente | Descripción |
|---|---|
| `DependencyGraph` | Visualización force-directed con react-force-graph-2d |
| `GraphControls` | Filtros: módulo, tipo de arista, profundidad |

### Report

| Componente | Descripción |
|---|---|
| `ArchitectureReport` | Vista principal con tabs por sección |
| `MetricsGrid` | Grid de métricas (LOC, módulos, complejidad) |
| `ReportSection` | Sección genérica con título e ícono |
| `KiroExport` | Preview del spec + botón de descarga |

---

## Troubleshooting

### SSE (chat) se desconecta

- **Causa**: El proxy nginx cierra conexiones idle después de 600s.
- **Solución**: El chat implementa reconexión automática. Si persiste, verificar que nginx tiene `proxy_buffering off`.

### Grafo no renderiza

- **Causa**: Datos vacíos o formato inesperado del backend.
- **Síntoma**: Canvas en blanco sin nodos.
- **Solución**: Verificar que el job completó exitosamente (`status: completed`) y que `/api/v1/graph/{id}` retorna `nodes` y `edges`.

### Build falla con Tailwind

- **Causa**: Tailwind v4 usa `@import "tailwindcss"` (no `@tailwind base`).
- **Solución**: Verificar que `postcss.config.js` usa `@tailwindcss/postcss` y que `globals.css` tiene la sintaxis v4.

### Fonts no cargan

- **Causa**: Google Fonts se cargan via `next/font/google` en `layout.tsx`.
- **Solución**: Verificar conexión a internet durante build (o usar `font-display: swap` que ya está configurado).

### Hot Module Reload no funciona en Docker

- **Causa**: Next.js HMR usa WebSocket que necesita upgrade.
- **Solución**: El nginx ya tiene configurado `proxy_set_header Upgrade $http_upgrade`. Si no funciona, usar `npm run dev` fuera de Docker.
