# CRIBA SHADOW + SUPRA: puertas de integración, ejecutable y valor

Estado del documento: **trabajo de desarrollo, NO aceptación de producto**.
Branch base: `codex/interpreter-hardening-20261004` (`2dc0094`).
BLACKFORGE permanece en `HARD_PAUSE` y no depende de este recorrido.
No modificar la política causal, los umbrales anti-Goodhart ni el estado científico
para conseguir un PASS cosmético.

## Puerta 1: interfaz y comunicación

- `criba gui` apunta al lanzador `criba_shadow_main.py` cuando existe el
  árbol de fuentes, y falla explícitamente cuando una distribución no incluye
  Shadow. Nunca arranca la antigua GUI como fallback.
- La distribución de Windows tiene su propio `CribaShadow.exe`, generado desde
  `criba-blackforge/CribaShadow.spec`. No se presume que un paquete pip incluya
  el entrypoint de escritorio.
- La apertura de la aplicación adopta SUPRA externo **sólo** con
  `SUPRA_ENDPOINT` explícito y `/health` verificado: HTTP loopback,
  `status=healthy`, `service=supra-agentic-taskmaster`, estructura
  `storage` válida y sin redirecciones.
- Sin endpoint explícito arranca SUPRA propio, asociado a
  `CRIBASHADOW_HOME/supra_state`, con un puerto local disponible. No se une
  por accidente a otro proceso que ocupe el puerto fijo.
- `CribaShadow.lock` se mantiene como guardia estable: la exclusión es
  el bloqueo del sistema operativo vivo, no el PID declarativo del JSON. Un
  archivo huérfano se recupera sin que dos procesos escriban en paralelo.
- Las pruebas de comunicación M2 y M3 anteriores existen, pero las pruebas de
  esta rama no sustituyen una aceptación visible independiente.

## Puerta 2: Windows y recorrido completo

Verificación del código (en el entorno de CRIBA):

```powershell
uv run --locked pytest -q tests/unit/test_shadow_runtime_boundary.py tests/unit/test_shadow_cli_entry.py tests/unit/test_shadow_release_preflight.py tests/integration/test_m2_vertical_slice_e2e.py
```

Después de construir el **mismo HEAD**, ejecutar en Windows:

```powershell
uv run --locked pyinstaller CribaShadow.spec --noconfirm
uv run --locked python scripts/verify_shadow_windows.py dist/CribaShadow/CribaShadow.exe --output shadow-smoke.json
```

El segundo comando abre y cierra el .exe real con estado temporal aislado.
Sólo comprueba arranque, hilo SUPRA, Qt construido, flag de ventana visible,
restauración iniciada y supervivencia del proceso. Un resultado
`STARTUP_SMOKE_PASS` **no equivale** a `M2_ACCEPTED`, calidad visual ni
funcionalidad de negocio completa. El operador debe probar además, en escritorio
real y sobre un proyecto aislado:

1. Abrir la ventana, introducir problema, generar e interpretar una idea.
2. Enviar el dossier real a SUPRA, comprobar HTTP/estado y lectura de
   provenance; ningún recibo `NOT_EXECUTED` puede decir `EXECUTED`.
3. Comprobar loading, error visible, cancelación, reintento y doble clic.
4. Cerrar/reabrir, comprobar reconstrucción desde disco y origen tras reinicio.
5. Comprobar ausencia de lanzamiento accidental de BLACKFORGE y error real
   ante un backend caído. Registrar el SHA del .exe y el HEAD del código.

Hasta ejecutar estos pasos con evidencia, `M2_ACCEPTANCE=PENDING`,
`M3_ACCEPTANCE=PENDING` y `VISIBLE_DESKTOP=PENDING`.

## Puerta 3: utilidad incremental frente a un LLM

Herramienta de **contabilidad descriptiva**, sin llamadas automáticas a modelos:

```powershell
uv run --locked python scripts/evaluate_product_value.py manifest.json reviews.json --output paired-report.json
```

`manifest.json` debe contener `schema=criba-llm-paired/1`,
`protocol_sha256` y una colección de `cases`, cada uno con
`case_id`, `domain`, `split` (`exploratory` o `confirmatory`) y dos
`arms` A/B. Cada brazo tiene `system` (`CRIBA_SUPRA` o
`DIRECT_LLM`) y `artifact_sha256` real del resultado completo.
Un caso debe contener **ambos sistemas** bajo condiciones comparables.

`reviews.json` contiene `schema` y `reviews`: cada registro aporta
`case_id`, `reviewer_id`, `choice` A/B/TIE/ABSTAIN,
`blind_declared` booleano y `evidence_ref` de la revisión. Las revisiones
deben realizarse sin conocer las etiquetas ocultas A/B, con criterios y costes
prerregistrados e idealmente evaluadores independientes.

El análisis sólo cuenta consenso de al menos dos revisores distintos
declarados ciegos en casos confirmatorios. Disenso, falta de revisiones,
parcialidad declarada, casos exploratorios y resultados sin evidencia quedan
separados. El programa nunca rellena `UNKNOWN` con 0, nunca publica
superioridad y no usa jueces sintéticos para fabricar una victoria.
`paired_win_rate` tiene denominador únicamente sobre victorias confirmatorias
descriptivas, sin empates ni desconocidos.

**Límites:** el hash no demuestra verdad del artefacto; la
`blind_declared` no verifica independencia; el `protocol_sha256` sin
anclaje externo no acredita preregistro. Sin experimentos reales, resultados
ciegos y criterios causales no se promocionan D3/D4/D6/D8 ni se altera
AntiGoodhart OFF. El informe sigue diciendo `scientific_advantage:
NOT_ESTABLISHED` aunque CRIBA gane todas las revisiones declaradas.

La última aceptación exige beneficio medible en casos nuevos, mismo
presupuesto, baseline directo fuerte, asignación balanceada, efectos adversos,
coste de ejecución e intervalos de incertidumbre publicados sin cherry-pick.

## Estado de evidencia

- Implementado en esta rama: routing Shadow, seguridad de arranque SUPRA,
  bloqueo SO, sentinels y herramienta descriptiva.
- Verificado por CI: sólo si la ejecución de GitHub Actions del HEAD exacto
  termina correctamente.
- No verificado por esta rama: build Windows real, observación humana de
  la interfaz, eficacia causal superior, independencia de evaluadores.

## Nueva puerta automatizada: recorrido del ejecutable entre procesos

La rama `chatgpt/shadow-exe-journey-20261008` añade un recorrido de
*ejecución del EXE real*, separado del smoke de arranque:

```powershell
uv run --no-sync python scripts/verify_shadow_bundle_journey.py `
  dist/CribaShadow/CribaShadow.exe --artifacts bundle-verification
```

En un directorio temporal aislado y sin modelo configurado, el primer proceso
crea un problema mediante el input real de Shadow, pulsa el botón **Generar
ideas**, espera al núcleo CRIBA, pulsa el botón **Ejecutar en SUPRA (real)**,
comprueba el HTTP GET y el receipt de planificación, verifica el archivo
persistido y pinta capturas de Qt. El proceso debe terminar con código cero.
El segundo proceso arranca desde cero sobre el mismo directorio aislado,
restaura por LIST+GET y comprueba proyecto, provenance y la UI. La comparación
de ambos se rechaza si no coincide el mismo `project_id`, si desaparece el
archivo, el status o la captura, o si se promociona la recepción a ejecución o
validación científica.

**No se ejecuta BLACKFORGE**. El probe requiere una ruta de datos temporal
específica; si se apunta a la carpeta normal del usuario, rechaza arrancar.
La rama de producción sólo importa ese módulo cuando
`CRIBASHADOW_BUNDLE_PROBE` está expresamente definido y en caso contrario
arranca exactamente por la ruta normal.

`bundle-verification/` contiene `journey-report.json`,
`restore-report.json`, `bundle-e2e-result.json` y capturas PNG de
`QWidget.grab()`. Son imágenes del *buffer de pintado Qt* en el runner
Windows, no capturas verificadas del monitor de un usuario. El veredicto
`BUNDLED_E2E_PASS`, si aparece, sólo acredita la ruta automatizada con
un backend local real, no revisión visual humana, ausencia de recortes o
accesibilidad, ni valor novedoso de las ideas.

**Aceptación visible independiente y comparativa LLM:** siguen
`NOT_VERIFIED` y `NOT_EXECUTED`, respectivamente, hasta que existan pruebas
correspondientes. No trasladar el PASS técnico al estado científico.
