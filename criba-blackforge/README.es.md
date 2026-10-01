# CRIBA

**Motor de ideación reproducible por contrato.** Determinista, auditable y local-first: las rutas deterministas se reproducen cuando se mantienen fijos código, catálogo, configuración, orden y estado relevante; las dependencias externas también deben fijarse cuando intervienen.

Motor local y determinista para exploración combinatoria, análisis causal e ideación de ciberseguridad defensiva. CRIBA combina un catálogo inmutable y versionado de métodos de innovación y seguridad con un selector reproducible basado en semilla, una pista de auditoría SQLite para cada idea y una interpretación opcional mediante proveedores configurables de modelo (endpoints compatibles con OpenAI, locales o de nube).

> Versión en inglés: [README.md](./README.md).

---

## Por qué CRIBA

La mayoría de herramientas de "ideación con IA" son cajas negras: pides, sale texto, sin forma de saber por qué ni de reproducir el mismo resultado dos veces.

- **Rutas deterministas acotadas** — una semilla explícita hace repetible la selección cuando permanecen fijos código, catálogo, configuración, orden y estado relevante; no es una garantía universal entre máquinas para rutas dependientes de modelos, red o historial.
- **Cada idea queda auditada** — traza SQLite por activación: métodos usados, puntuaciones, orden y versión exacta del catálogo.
- **Local sin fricción** — sin API key, sin red y sin telemetría para ejecutar el núcleo.
- **Interpretación opcional con modelo** — trae tu propio proveedor (GGUF/Ollama local o endpoint de nube compatible con OpenAI); sin proveedor, scoring determinista local y la interpretación queda PENDIENTE en lugar de fabricarse.
- **Catálogo integrado** — más de 130 técnicas de innovación y seguridad (TRIZ, Design Thinking, JTBD, FMEA, MITRE ATT&CK, OWASP, STRIDE, Kill Chain…) congeladas en JSON con esquema versionado.
- **Verificado continuamente** — la suite completa de tests y las comprobaciones estáticas del repositorio se ejecutan en CI.

## Funcionalidades

| Capacidad | Descripción |
|---|---|
| `criba run` / `activate` | Selección determinista de métodos para una consulta, con puntuación reproducible y sesión persistida. |
| `criba lottery` | Doble lotería de ideación (asociativa + pura) con semilla explícita. |
| `criba blackforge` | Pipeline de ciberseguridad defensiva: amenazas, causalidad, propuestas y gates S0–S3. |
| `criba hybrid` | Pipeline completo ensemble → cadena → adversarial, con mejora semántica opcional. |
| `criba explain` / `compare` | Inspecciona por qué una sesión dio un resultado; compara dos sesiones. |
| `criba serve` | API JSON solo loopback (Swagger en `/docs`). |
| `criba mcp` | Servidor MCP por stdio: `activate_current`, `list_currents`, `explain_selection`, `build_model_prompt`, `record_decision`, `compare_runs`. |
| `criba gui` / `blackforge-gui` | Escritorio nativo PySide6 para CRIBA y BLACKFORGE. |
| Diálogo Modelos IA | Registra perfiles locales GGUF (llama.cpp) / Ollama; opción de expandir ideas con modelos cloud gratis. |

## Instalación

### Desde PyPI

```bash
pip install criba
```

o sin instalar nada:

```bash
uvx --from criba criba --help
```

> Las funciones opcionales de escritorio y de modelo requieren extras:
> `pip install "criba[gui,api]"`

### Desde el código fuente

```bash
git clone https://github.com/Klsx-Moli/Criba-Blackforge-Supra.git
cd Criba-Blackforge-Supra/criba-blackforge
uv sync --all-extras --locked
uv run criba --help
```

> En Windows también puedes usar el ejecutable portable precompilado (ver
> [Releases](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/releases)).

## Demo de 60 segundos

```bash
criba lottery --query "¿cómo diseñar aprobaciones seguras para agentes autónomos?" --seed 42 --rounds 3 --batch-size 5
```

Ejecútalo dos veces bajo el mismo código, catálogo, configuración y estado relevante. La ruta determinista sembrada debe reproducir la selección; la semilla por sí sola no fija dependencias externas, de modelo o de historial.

Activación determinista simple:

```bash
criba run --query "reducir la energía de un datacenter en frío" --current auto --mode balanced --json
```

Workbench en Windows:

```powershell
scripts\launch_workbench.bat
```

## Garantía de reproducibilidad

- Los catálogos están congelados y versionados (`CURRENT_CATALOG_VERSION`, `SELECTOR_VERSION`).
- Los selectores deterministas usan semilla y orden estable, pero una semilla es solo una de las dependencias del resultado.
- Cada activación escribe un registro auditable en SQLite (`artifacts/criba.sqlite3` por defecto).

## Expansión cloud gratis (opcional, 0€)

Cuando configuras un perfil GGUF/Ollama local *o* activas las rutas cloud gratuitas, CRIBA
conserva su núcleo determinista y usa el modelo solo para redactar ideas coherentes:

- **Cualquier endpoint compatible con OpenAI** — configura URL base, modelo y clave en el diálogo de modelos o por variables de entorno (p. ej. `NOUS_API_KEY` para el endpoint de Nous).

Si el modelo no responde, CRIBA degrada a su fallback determinista offline — la salida
nunca depende de la red. Las claves de cloud se leen solo de variables de entorno y
jamás se guardan en el repositorio.

## Inteligencia de innovación expandida (IIE)

El motor incluye adaptadores de prior art gratuitos y sin clave — OpenAlex, Crossref,
patentes EPO, fondos NSF, GitHub, Wikipedia — pensados para conectar las ideas generadas
con la evidencia que las apoya o las descarta, con controles de presupuesto y límites de
tasa (sin red en los tests de CI).

## Desarrollo

```bash
uv run pytest -q            # 866 tests
uv run mypy src/criba       # tipado estricto sobre el motor
uv run ruff check src       # lint
```

Las contribuciones son bienvenidas — ver [CONTRIBUTING](./CONTRIBUTING.md) y la
[política de seguridad](./SECURITY.md). Los releases se construyen desde tags y se
publican automáticamente con procedencia SLSA y un SBOM.

## Licencia

Apache License 2.0. Ver [LICENSE](./LICENSE) y [THIRD_PARTY_NOTICES](./THIRD_PARTY_NOTICES.md).