# Design System — Estilos del Proyecto

Sistema de diseño basado en el prototipo de Figma Make ("Software Archaeologist"). Todo código frontend debe respetar estos tokens, patrones y convenciones.

---

## Paleta de Colores

| Token | Hex | Uso |
|-------|-----|-----|
| `--background` | `#080D18` | Fondo principal de la app |
| `--foreground` | `#F0F4FF` | Texto principal sobre fondo oscuro |
| `--card` | `#0F1624` | Fondo de tarjetas y contenedores |
| `--card-foreground` | `#E2E8F0` | Texto dentro de tarjetas |
| `--primary` | `#F59E0B` | Color de acento principal (amber/dorado) |
| `--primary-foreground` | `#080D18` | Texto sobre elementos primary |
| `--secondary` | `#06B6D4` | Color de acento secundario (cyan) |
| `--secondary-foreground` | `#080D18` | Texto sobre elementos secondary |
| `--muted` | `#1E2A3A` | Fondos sutiles, elementos deshabilitados |
| `--muted-foreground` | `#6B7A99` | Texto secundario / placeholder |
| `--accent` | `#F59E0B` | Igual que primary, para highlights |
| `--accent-foreground` | `#080D18` | Texto sobre accent |
| `--border` | `#1E2D45` | Bordes y separadores |
| `--ring` | `#F59E0B` | Focus rings y outlines de interacción |

### Colores Semánticos Extendidos (no variables, uso directo)
| Color | Hex | Uso |
|-------|-----|-----|
| Éxito / Activo | `#10B981` | Status badges activos, progreso completado |
| Peligro / Seguridad | `#EF4444` | Alertas, errores, agente de seguridad |
| Púrpura | `#8B5CF6` | Datos, categorías secundarias |
| Naranja | `#F97316` | Orquestación, tiempos, alertas medias |

### Reglas de Color
- El tema es **dark-first**. No generar variantes light a menos que se pida explícitamente.
- Usar siempre las variables CSS (`var(--nombre)`) para los tokens principales.
- Los colores semánticos extendidos se usan con opacidad para fondos: `${color}15` (fondo), `${color}20` (hover), `${color}40` (borde), `${color}50` (borde activo).
- Contraste mínimo: texto principal sobre fondo debe cumplir WCAG AA (4.5:1).

---

## Tipografía

| Variable | Fuente | Uso |
|----------|--------|-----|
| `--font-display` | `'Roboto Slab', serif` | Títulos, headings, hero text, métricas grandes |
| `--font-body` | `'Inter', sans-serif` | Cuerpo de texto, UI general, botones |
| `--font-mono` | `'JetBrains Mono', monospace` | Código, labels técnicos, badges, status, metadata |

### Pesos Disponibles
- **Roboto Slab**: 300, 400, 600, 700
- **Inter**: 300, 400, 500, 600, 700
- **JetBrains Mono**: 400, 500

### Escala Tipográfica
| Elemento | Fuente | Tamaño | Peso | Extra |
|----------|--------|--------|------|-------|
| Hero title (h1) | display | `clamp(28px, 4vw, 48px)` | 700 | `letter-spacing: -0.02em`, `line-height: 1.1` |
| Section title (h2) | display | 20px | 700 | — |
| Card title | display | 16px | 700 | — |
| Métricas grandes | display | 20-28px | 700 | color del contexto |
| Body text | body | 16px | 400 | `line-height: 1.7` |
| UI text / descripciones | body | 13px | 400-500 | `color: --muted-foreground` |
| Botones | body | 12-13px | 600-700 | `letter-spacing: 0.04em` |
| Labels / metadata | mono | 10-11px | 400-500 | `uppercase`, `letter-spacing: 0.08-0.1em` |
| Code badges / tags | mono | 10-11px | 400 | con fondo de color al 15% |
| Nav items | body | 13px | 400 (inactivo) / 600 (activo) | — |

### Reglas de Tipografía
- Headings (`h1`-`h3`): usar `font-display` con peso 600-700.
- Cuerpo y UI: usar `font-body` con peso 400-500.
- Labels técnicos, status y metadata: `font-mono` en 10-11px, UPPERCASE con letter-spacing amplio.
- Importar fuentes desde Google Fonts con el subset correcto.

---

## Espaciado y Bordes

| Token | Valor | Uso |
|-------|-------|-----|
| `--radius` | `6px` | Border-radius por defecto para tarjetas, inputs, botones |

### Escala de Radius
| Valor | Uso |
|-------|-----|
| 3px | Tags pequeños, badges de código |
| 4px | Botones small, logo container |
| 6px | Cards, inputs, botones estándar |
| 8px | Cards medianas, tablas |
| 12px | Cards grandes, hero containers |
| 20px | Pills / badges redondeados |
| 50% | Dots de status, avatares |

### Reglas de Espaciado
- Layout contenedor: `max-width: 1280px`, `margin: 0 auto`, `padding: 0 24px`.
- Secciones principales separadas por `gap: 48px`.
- Cards internas: `padding: 20-24px`.
- Grid de cards: `gap: 16px`.
- Bordes: `1px solid var(--border)`.

---

## Layout y Grid

### Contenedor Principal
- Max-width: 1280px, centrado, padding horizontal 24px.

### Patrones de Grid
| Patrón | Columns | Uso |
|--------|---------|-----|
| Hero | `1fr 420px` | Contenido + sidebar visual |
| Main content | `1fr 280px` | Contenido principal + side panels |
| Metrics bar | `repeat(5, 1fr)` | Métricas en fila |
| Cards grid | `repeat(auto-fill, minmax(280px, 1fr))` | Grid responsivo de tarjetas |
| Table | Columns explícitas con fr/px | Tablas de datos |

### Responsive (breakpoint: 900px)
- Hero: colapsa a 1 columna.
- Metrics: colapsa a 2 columnas.
- Main content: colapsa a 1 columna.

---

## Componentes UI — Patrones

### Header / Navbar
- `position: sticky`, `top: 0`, `z-index: 50`.
- Fondo semitransparente: `rgba(8, 13, 24, 0.92)` con `backdrop-filter: blur(12px)`.
- Border-bottom con `var(--border)`.
- Altura: 60px.
- Nav tabs: texto `--muted-foreground` inactivo, `--primary` activo con underline 2px.

### Cards
- Fondo: `var(--card)`, borde: `1px solid var(--border)`, radius: 6-12px.
- Hover: `border-color` cambia al color contextual + `translateY(-2px)`.
- Transiciones suaves: `0.15s`.
- Header de card con icono decorativo (40x40, radius 8, fondo al 20% del color + borde al 40%).

### Status Badges
- Dot de 6px con `border-radius: 50%` y `box-shadow: 0 0 6px {color}` (glow).
- Texto: `font-mono`, 11px, uppercase, letter-spacing 0.08em.
- Animación pulse en estados activos: `opacity 1 → 0.4 → 1` en 2s infinite.

### Progress Bars
- Altura: 3px, fondo: `#1E2D45`, radius: 2px.
- Barra interna con color contextual y `transition: width 0.6s ease`.

### Botones
- **Primary**: `background: var(--primary)`, `color: var(--primary-foreground)`, radius 4px, peso 700, 12px.
- **Ghost/Outline**: `background: transparent`, `border: 1px solid var(--border)`, `color: --muted-foreground`.
- **Action (secondary)**: fondo al 10% del color + borde al 40%, texto del color, peso 600.

### Tablas
- Container: card con overflow hidden.
- Header: fondo `rgba(30, 45, 69, 0.3)`, labels en `font-mono` 10px uppercase.
- Rows: hover con `rgba(245, 158, 11, 0.04)` (primary al 4%).
- Separadores: `border-bottom: 1px solid var(--border)`.

### Tags / Chips
- `font-mono`, 10-11px, color contextual, fondo `${color}15`, padding `2px 6-8px`, radius 3px.

### Pills (version badges, status indicators)
- Border-radius 20px, fondo al 10% del color, borde al 30%, padding `4px 12px`.
- Dot de 6px + texto mono uppercase.

---

## Efectos Visuales

### Glow / Radial Gradient
- Hero: `radial-gradient(ellipse, rgba(245, 158, 11, 0.12) 0%, transparent 70%)`.
- Posición: centrado arriba, 600x300px.

### Grid Background
- Líneas cada 40px con `rgba(30, 45, 69, 0.4)`.
- Mask: `linear-gradient(to bottom, transparent, black 20%, black 80%, transparent)`.

### Scrollbar
- Width: 4px. Track: transparent. Thumb: `var(--border)`, hover: `var(--muted-foreground)`.

---

## Framework CSS

- **Tailwind CSS** como framework utilitario principal.
- Usar `@import 'tailwindcss'` (v4 syntax).
- Las variables CSS custom van en `:root` y se referencian con `var()`.
- Para colores con opacidad variable, usar template literals: `${color}15`, `${color}20`, etc.

---

## Reglas para Generación de Código

1. Nunca usar colores hex directamente para tokens principales — siempre variables CSS.
2. Colores semánticos extendidos se permiten en hex cuando se usan con opacidad dinámica.
3. Priorizar clases de Tailwind sobre CSS custom cuando sea posible.
4. Respetar la jerarquía tipográfica: display para títulos/métricas, body para texto/UI, mono para labels/tags.
5. Todo componente nuevo debe seguir el tema dark por defecto.
6. Inputs y botones deben incluir `focus:ring` con `var(--ring)` para accesibilidad.
7. Cards siempre tienen: fondo card, borde, border-radius, y hover interactivo.
8. Labels de metadata: siempre `font-mono`, uppercase, letter-spacing 0.08-0.1em, tamaño 10-11px.
9. Status indicators: dot con glow + texto mono uppercase.
10. Transiciones: usar `0.15s` para hover UI, `0.6s ease` para progress/data.
11. Layout responsive: breakpoint principal en 900px, colapsar grids a 1 columna.
12. Container global: max-width 1280px, centrado, padding 24px horizontal.
