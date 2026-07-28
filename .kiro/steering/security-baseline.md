# Security Baseline — Universal

Estándares mínimos de seguridad aplicables a cualquier proyecto. Adaptados de ECC's security-review skill y OWASP Top 10.

---

## Checklist por PR (Obligatorio)

Antes de aprobar cualquier cambio de código, verificar:

- [ ] No secrets hardcodeados (API keys, passwords, tokens, private keys)
- [ ] Input validation en boundaries (controllers, route handlers, API endpoints)
- [ ] Queries parametrizadas (no concatenación de strings para SQL/NoSQL)
- [ ] Output sanitizado antes de render (prevención XSS)
- [ ] Auth verificada en endpoints no-públicos
- [ ] Error responses no exponen stack traces ni info interna
- [ ] Dependencias nuevas revisadas (mantenimiento, CVEs, popularidad)

---

## OWASP Top 10 — Mitigaciones

| # | Riesgo | Mitigación |
|---|--------|-----------|
| A01 | Broken Access Control | Verificar auth + authz en cada endpoint. Default deny. |
| A02 | Cryptographic Failures | HTTPS everywhere. Bcrypt/Argon2 para passwords. No MD5/SHA1 para secrets. |
| A03 | Injection | Queries parametrizadas. No `eval()`. No string interpolation para commands. |
| A04 | Insecure Design | Threat model antes de implementar features sensibles. |
| A05 | Security Misconfiguration | CORS explícito (no wildcard en prod). Headers de seguridad. Debug off en prod. |
| A06 | Vulnerable Components | Pin versions. Audit regular. No deps abandonadas. |
| A07 | Auth Failures | Rate limiting en login. MFA donde posible. Session invalidation. |
| A08 | Data Integrity Failures | Verificar signatures (HMAC, JWT). CI/CD pipeline seguro. |
| A09 | Logging Failures | Log auth events. No log secrets. Structured logging. |
| A10 | SSRF | Validar URLs antes de fetch. Whitelist de dominios. No redirect abierto. |

---

## Gestión de Secrets

### Reglas
- Secrets viven en variables de entorno, nunca en código fuente.
- `.gitignore` incluye: `.env`, `*.key`, `*.pem`, `credentials.*`, `*secret*`.
- Si un secret se expone (incluso en dev): rotar inmediatamente.
- No logging de secrets. Referenciar por nombre, no por valor.
- En CI/CD: usar secret managers del proveedor (GitHub Secrets, AWS SSM, etc).

### Detección (patrones a buscar)
```
sk-...           # OpenAI / Stripe
ghp_...          # GitHub PAT
AKIA...          # AWS Access Key
-----BEGIN.*KEY  # Private keys
password\s*=     # Hardcoded passwords
```

---

## Dependencias

### Al agregar una dependencia nueva
1. ¿Está activamente mantenida? (último commit < 6 meses)
2. ¿Tiene CVEs conocidos? (`npm audit` / `pip audit` / `cargo audit`)
3. ¿Es el nombre correcto? (typosquatting: `lodash` vs `l0dash`)
4. ¿Es necesaria o se puede hacer con stdlib?
5. Versión pinneada exacta (no `^` ni `~` en prod).

### Auditoría regular
- Node: `npm audit --production`
- Python: `pip-audit` o `safety check`
- Java: `./gradlew dependencyCheckAnalyze` (OWASP dependency-check)
- Rust: `cargo audit`
- Go: `govulncheck ./...`

---

## Auth & Authz

### Principios
- Default deny: todo está protegido a menos que explícitamente sea público.
- Verify auth en cada request (middleware/filter), no en cada endpoint manual.
- Separation of auth (quién eres) y authz (qué puedes hacer).
- Session tokens: HttpOnly, Secure, SameSite=Strict.
- Tokens JWT: validar signature, expiry, issuer. No confiar en payload sin verificar.

### Rate Limiting
- Login: max 5 intentos / 15 min por IP.
- API: limits según tier del usuario.
- Endpoints públicos: limit agresivo contra abuse.

---

## Infrastructure Security

### Docker
- Non-root USER en runtime stage.
- No secrets en Dockerfile o docker-compose (usar env_file).
- Imagen base oficial y pinneada.
- Solo exponer puertos necesarios.

### Cloud
- IAM mínimo privilegio (no `*` en actions/resources).
- Databases no publicly accessible.
- S3 buckets private by default.
- Encryption at rest habilitado.
- VPC para servicios internos.

### CI/CD
- No secrets en logs de pipeline.
- Dependency audit como step obligatorio.
- Branch protection rules en main.
- Signed commits cuando posible.

---

## Cuando Escalar

Estos escenarios requieren revisión de seguridad explícita (no solo el baseline):

- Nuevo sistema de autenticación o cambio en auth flow.
- Integración con servicios externos que reciben datos sensibles.
- Manejo de datos PII (nombres, emails, tarjetas).
- Endpoints que aceptan file uploads.
- Funcionalidad que ejecuta código dinámico o user-provided.
- Cambios en IAM policies o permisos de cloud.
