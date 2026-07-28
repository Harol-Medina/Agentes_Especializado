# Verification Loop — Universal

Patrón de verificación continua adaptado de ECC's verification-loop skill. Aplicable a cualquier stack — los comandos concretos se determinan por el proyecto activo.

---

## El Loop

```
Write Code → Build → Test → Lint → Type-check → Security → Done
     ↑                                                    |
     └────────────── Fix & Retry (if any step fails) ────┘
```

---

## Pasos Genéricos

| Step | Objetivo | Pass Criteria |
|------|----------|---------------|
| **Build** | Compilar sin errores | Exit 0, zero compilation errors |
| **Test** | Comportamiento correcto | All tests pass, 80%+ coverage en código nuevo |
| **Lint** | Estilo consistente | Zero violations |
| **Type-check** | Tipos correctos | Zero errors en strict mode |
| **Security** | Sin vulnerabilidades | No HIGH/CRITICAL CVEs en dependencias |

---

## Modos de Verificación

### Continuo (durante desarrollo)
Ejecutar después de cada cambio significativo:
- Build + Test solamente
- Feedback loop rápido (~30s)

### Full Gate (antes de PR/commit)
Ejecutar antes de marcar trabajo como hecho:
- Los 5 pasos completos
- Debe pasar 100% para proceder

### Checkpoint (en milestones)
Guardar estado de verificación como referencia:
- Qué tests pasan
- Números de cobertura
- Estado de dependencias
- Útil para comparación "antes/después"

---

## Detección de Comandos

Antes de ejecutar el loop, detectar el stack del proyecto:

| Indicador | Stack | Build | Test | Lint |
|-----------|-------|-------|------|------|
| `package.json` | Node.js | `npm run build` | `npm test` | `npm run lint` |
| `pom.xml` | Java/Maven | `mvn compile` | `mvn test` | `mvn checkstyle:check` |
| `build.gradle` | Java/Gradle | `./gradlew build -x test` | `./gradlew test` | `./gradlew spotlessCheck` |
| `pyproject.toml` / `requirements.txt` | Python | `pip install -e .` | `pytest` | `ruff check .` |
| `Cargo.toml` | Rust | `cargo build` | `cargo test` | `cargo clippy` |
| `go.mod` | Go | `go build ./...` | `go test ./...` | `golangci-lint run` |
| `Gemfile` | Ruby | `bundle exec rake` | `bundle exec rspec` | `bundle exec rubocop` |

Si el proyecto tiene un `Makefile` o scripts customizados (`scripts/`), preferir esos.

---

## Protocolo de Fallo

Cuando un paso falla:

1. **Leer el error**. No adivinar — parsear el mensaje real.
2. **Arreglar en la fuente**. No workarounds a errores de lint; arreglar el código.
3. **Re-ejecutar desde el paso fallido**. No re-ejecutar todo el loop.
4. **Si stuck después de 2 intentos**: diagnosticar causa raíz, probar approach diferente.

---

## Skip Conditions

| Tipo de cambio | Se puede omitir |
|----------------|----------------|
| Solo documentación | Build, Test, Lint, Type-check |
| Solo config (env vars, docker) | Test, Lint, Type-check |
| Solo tests | Security |
| Cambio de dependencias | **Nunca** omitir Security |

---

## Integración con Hooks

El verification loop se complementa con hooks automatizados:

```
Task Complete → Verification Loop → Code Review (hook) → Commit
```

Esto asegura que el reviewer (humano o agente) solo ve código que ya compila, pasa tests y cumple estilo.
