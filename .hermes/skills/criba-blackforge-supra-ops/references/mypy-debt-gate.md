# mypy debt gate vs Ruff vs uv.lock

CI en `criba-blackforge/` ejecuta tres checks distintos que se confunden:

## 1. uv.lock (dependency resolution)
- Error: "The lockfile at `uv.lock` needs to be updated, but `--locked` was provided."
- Causa: lock desactualizado — un paquete **declarado** en `pyproject.toml` no
  está en el lock.
- Fix: `uv lock` en el workspace root. Si el diff sólo añade el paquete
  faltante (ya declarado), es *lock completion*, no dependencia nueva.
- NUNCA confundir con un error de código.

## 2. Ruff (lint/format)
- Comando CI: `uv run --locked ruff check .`
- Error típico: "Found N errors" / "F401 unused import" / "I001 import order".
- Fix: `uvx ruff check . --fix` (auto) o fix manual.
- Scope: por workspace. `supra/` y `criba-blackforge/` tienen configs distintos.

## 3. mypy debt gate (type checking)
- Comando CI: ejecuta `mypy` + una gate de "debt" contra un baseline.
- Error típico: "Found 1 error in 1 file" + "mypy debt gate: current=N,
  baseline=M, new=(delta)".
- Causa: un error de tipos NUEVO en el diff (current > baseline).
- Distinción crítica: **mypy es un check de tipos, no de lint**. El workflow
  pasa Ruff y falla en mypy — son checks ortogonales.
- Fix: resolver el error de tipos específico (p. ej. `no-any-return`), no
  relajar el validador. A menudo es un `return self.fallback(...)` donde
  `fallback` no tipifica su retorno como el tipo declarado.

## Cómo diagnosticar rápidamente en CI
```bash
gh run view <run_id> --log
# grep: needs to be updated -> uv.lock
# grep: Ruff / F401 / I001 -> Ruff  
# grep: mypy debt gate / Found N error -> mypy (NO relacionado con Ruff ni lock)
```

## Pitfall
Ver "Found 1 error in 1 file" y asumir que es Ruff. En el workflow de CI,
Ruff y mypy corren en el mismo job (CRIBA / BLACKFORGE) y el error de mypy
parece un error de lint. Siempre verifica cuál check falló leyendo el log.
