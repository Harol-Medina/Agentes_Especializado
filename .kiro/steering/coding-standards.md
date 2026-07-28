# Coding Standards — Universal

Principios de código aplicables a cualquier stack. Adaptados de ECC rules/common. Para convenciones específicas de proyecto, usar el steering local del workspace.

---

## Estilo de Código

### Principios Universales
- Inmutabilidad por defecto. Usar `final`, `const`, `readonly`, `val` donde sea posible.
- Funciones hacen una cosa. Si la descripción tiene "y", dividir.
- Max 300 líneas por archivo (excluyendo imports/comentarios). Dividir si excede.
- Max 40 líneas por función. Extraer helper si excede.
- Explícito sobre implícito. Parámetros nombrados, tipos de retorno claros, no magic numbers.
- No código muerto. Borrar, no comentar. Git tiene historial.
- Nombres que comunican intención. Si necesitas un comentario para explicar qué hace una variable, renómbrala.

### Organización de Archivos
1. Imports (std lib → third-party → internal → relative)
2. Constants / Types / Interfaces
3. Main logic (exported functions/classes)
4. Private helpers
5. No mezclar concerns en el mismo archivo

### Naming Conventions (Cross-language)
| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Clases / Componentes | PascalCase | `UserService`, `DashboardCard` |
| Funciones / Métodos | camelCase o snake_case (según lenguaje) | `getUser()`, `get_user()` |
| Constantes | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Variables | camelCase o snake_case (según lenguaje) | `userId`, `user_id` |
| Archivos de código | Según convención del lenguaje | `UserService.java`, `user_service.py`, `UserCard.tsx` |
| Config / infra | kebab-case | `docker-compose.yml` |

---

## Git Workflow

### Formato de Commit
```
<type>: <description>

[optional body]
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

Reglas:
- Subject: imperative mood, max 72 chars, sin punto final.
- Body: wraps at 72 chars, explica "por qué" no "qué".
- Un cambio lógico por commit.

### Branches
- `main` / `master` — producción, nunca push directo.
- `feature/<name>` — nuevas features.
- `fix/<name>` — bug fixes.
- `docs/<name>` — solo documentación.

### PRs
- Pequeños y enfocados: un feature/fix por PR.
- Título < 70 chars, descripción con resumen + qué se testeó.
- Squash merge para historial lineal.
- Code review antes de merge (agente o humano).

---

## Testing

### Cobertura
- Mínimo 80% en código nuevo.
- Paths críticos (auth, pagos, mutaciones de datos): 95%+.
- Zero tolerancia a código security-sensitive sin tests.

### TDD (Red-Green-Improve)
1. **RED**: Test que falla, define el comportamiento esperado.
2. **GREEN**: Código mínimo que pasa el test.
3. **IMPROVE**: Refactorizar sin cambiar comportamiento. Tests siguen pasando.

### Principios
- Testear comportamiento, no implementación. Tests deben sobrevivir refactors.
- No mockear lo que no controlas (APIs externas → integration test con stub server).
- Cada bug reportado → regression test antes del fix.
- Tests independientes del orden de ejecución.
- No `sleep()` — usar polling/awaitility.

### Estructura AAA
```
// Arrange — setup preconditions
// Act — execute behavior under test  
// Assert — verify outcome
```

---

## Seguridad (Baseline)

### En cada PR verificar:
- No secrets hardcodeados (API keys, passwords, tokens).
- Input validation en todos los endpoints user-facing.
- SQL injection prevention: queries parametrizadas.
- XSS prevention: sanitizar antes de render.
- Autenticación verificada en endpoints no-públicos.
- Dependencias sin CVEs HIGH/CRITICAL conocidos.

### Secrets
- Variables de entorno para secrets, nunca archivos en el repo.
- `.gitignore` incluye `.env`, `*.key`, `*.pem`, `credentials.*`.
- Si un secret se expuso: rotar inmediatamente, incluso en desarrollo.

### Dependencias
- Versiones pinneadas (no `^` ni `~` en producción).
- Revisar dependencias nuevas: mantenimiento activo, descargas, CVEs.
- Auditoría regular: `npm audit` / `pip audit` / equivalente del stack.

---

## Performance

### Código
- No N+1 queries. Usar eager loading o batch queries.
- Paginar todos los endpoints de lista. Default 20, max 100.
- Async para I/O: HTTP calls, DB queries, file operations no deben bloquear.
- Cache para operaciones costosas e idempotentes.
- Connection pools para bases de datos.

### Para el AI Agent
- Archivos < 300 líneas son mejor comprendidos.
- Boundaries de módulo claros reducen necesidad de leer archivos adyacentes.
- Nombres descriptivos permiten navegación por búsqueda (grep > tree traversal).
- Index files exportan limpio sin lógica.

---

## Patterns

### Arquitectura
- Separar concerns: no mezclar I/O con lógica de negocio.
- Dependency Injection sobre imports directos de implementaciones.
- Repository pattern para acceso a datos.
- Error handling explícito: no catches vacíos, no swallow de excepciones.

### APIs
- REST: verbos HTTP correctos, status codes semánticos, JSON.
- Endpoints versionados: `/api/v1/...`
- Error responses consistentes: `{ error: string, code: string, details?: any }`.
- Paginación: `{ data: T[], meta: { page, pageSize, total } }`.

### Frontend
- Componentes hacen una cosa (display o logic, no ambos).
- Estado del servidor separado del estado de UI.
- Loading → Error → Empty → Success: manejar todos los estados.
- Accesibilidad como requisito, no como extra.
