# Ingeniería Agéntica — Mejores Prácticas

Guía global de comportamiento para sesiones de desarrollo. Adaptada del patrón **Research → Plan → Execute → Review → Ship**.

---

## 1. Planificación antes de ejecución

- Siempre comenzar tareas complejas con un plan explícito antes de escribir código.
- Dividir features en **vertical slices** (DB + API + UI en un solo corte) en vez de fases horizontales. Esto da feedback end-to-end desde el primer slice.
- Crear planes por fases con gates: cada fase tiene criterios de verificación (tests, build, revisión) antes de avanzar a la siguiente.
- Si el usuario da un prompt vago, hacer preguntas de clarificación antes de ejecutar. La ambigüedad es el enemigo de la calidad.

## 2. Gestión de contexto

- Usar sub-agentes (context-gatherer, general-task-execution) para exploración pesada. Solo el resultado final sube al contexto principal; las lecturas intermedias quedan en el agente hijo.
- No acumular lecturas de archivos innecesarias. Preguntarse: "¿necesitaré este output otra vez, o solo la conclusión?"
- Cuando una investigación requiera leer >10 archivos, delegar a un sub-agente.
- Si el contexto crece mucho y la tarea cambia, iniciar una nueva sesión en vez de arrastrar contexto obsoleto.

## 3. Prompting efectivo

- Ante un fix mediocre: replantear desde cero con todo el conocimiento adquirido en vez de parchar incrementalmente.
- Ante un bug: pegar el error y pedir "fix" sin microgestionar el cómo. Dejar que el agente explore.
- Desafiar el resultado: "pruébame que esto funciona", "grilla estos cambios" — verificación activa.
- Usar diagramas ASCII para comunicar y entender arquitectura compleja.

## 4. Sesiones y flujo de trabajo

- Tarea nueva = sesión nueva. Reutilizar sesión solo si la tarea siguiente necesita el contexto anterior (ej: escribir docs de lo que acabas de construir).
- Si un approach falla dos veces, diagnosticar la causa raíz y probar un enfoque fundamentalmente diferente.
- Ante decisiones de diseño, presentar opciones con trade-offs y esperar confirmación del usuario antes de actuar.

## 5. Specs y documentación viva

- Las specs viven en `/docs` o en `.kiro/specs/`. Son la fuente de verdad del diseño.
- Usar el flujo Spec de Kiro (requirements → design → tasks) para features complejas.
- Las specs deben actualizarse cuando la implementación diverge. Specs desactualizadas son peores que no tener specs.
- Incluir referencias a archivos relevantes usando `#[[file:ruta]]` en specs y steering para dar contexto progresivo.

## 6. Agents y delegación

- Preferir sub-agentes específicos por feature/dominio (auth-agent, payment-agent) sobre agentes genéricos.
- Usar sub-agentes para separar preocupaciones de contexto: un agente puede causar bugs y otro (mismo modelo, contexto limpio) puede encontrarlos.
- Delegar revisión de código o planes a un sub-agente con rol de "staff engineer" para obtener feedback de calidad.

## 7. Hooks — automatización reactiva

- Usar hooks PostFileSave para linting/formateo automático en archivos modificados.
- Usar hooks PreToolUse para validación de permisos o estándares de código antes de escritura.
- Usar hooks PostTaskExec para correr tests después de completar una tarea del spec.
- Usar hooks Stop para verificación final antes de cerrar turno (¿pasaron los tests? ¿el build compila?).

## 8. Git y PRs

- PRs pequeños y enfocados: un feature por PR. Más fácil de revisar y revertir.
- Commit frecuente: al completar cada sub-tarea, hacer commit. No acumular.
- Squash merge como default para mantener historial lineal.
- Antes de crear PR, correr `/code-review` o pedir al agente que revise sus propios cambios como un reviewer externo.
- Nunca push a main/master directamente. Siempre branch nueva.

## 9. Debugging

- Compartir screenshots y logs cuando se está atascado. El agente trabaja mejor con evidencia visual.
- Correr procesos de debug como background tasks para ver logs en tiempo real.
- Ante un error, leer el archivo antes de proponer cambios. Nunca editar código no visto.
- Búsqueda agéntica (grep + file_search) es más confiable que asumir la ubicación de código.

## 10. Verificación y calidad

- Después de cada cambio de código, correr build. Si el build no incluye tests, correr tests por separado.
- Si la verificación revela errores, corregirlos antes de presentar el resultado.
- Para cambios safety-sensitive (auth, infra, data), declarar explícitamente qué se verificó y qué no se pudo verificar.
- Limpiar archivos temporales creados durante verificación.

## 11. Steering y reglas

- Este archivo (`agentic-engineering.md`) es global — aplica a todos los proyectos.
- Reglas específicas de proyecto van en `.kiro/steering/` del workspace, no aquí.
- Mantener cada archivo de steering bajo 200 líneas. Si crece más, dividir en archivos por dominio.
- Las reglas deben dar **goals y constraints**, no instrucciones prescriptivas paso-a-paso. Dejar libertad al agente para elegir el mejor camino.

## 12. Principios generales

- Prototipar > especificar. El costo de construir es bajo; tomar múltiples intentos es válido.
- No agregar abstracciones, features o código defensivo más allá de lo que la tarea requiere.
- Mantener codebases limpias y terminar migraciones. Frameworks parcialmente migrados confunden al modelo.
- Invertir en verificación end-to-end: skills de signup-flow, checkout-verifier, etc.
- Si haces algo más de una vez al día, convertirlo en un hook, comando o steering.
