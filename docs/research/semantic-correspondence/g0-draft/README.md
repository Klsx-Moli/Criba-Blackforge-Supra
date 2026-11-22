# CBS G0 — paquete de decisión offline

Este directorio solo contiene trabajo habilitante. No es la implementación productiva de ASTRA ni sustituye K3. El prerregistro es un borrador para aprobación expresa. El manifiesto tiene referencias provisionales y no debe entrar en prompts; el repositorio es público, por lo que estas preguntas no constituyen holdout ciego.

Desde este directorio, con Python 3.11+ y sin dependencias:

```sh
python -m unittest -v test_pilot_gate.py
python pilot_gate.py plan --phase A
python pilot_gate.py check --phase A --records normalized.json
```

`plan` emite slots internos, no payloads. `check` recibe un array de registros normalizados desde K3 **después** de verificar procedencia, reserva, recibos, versión y consumo real. Cada registro debe tener exactamente: `case_id`, `repetition` (entero 0/1/2), `arm` (S0/S1), `outcome` (SUPPORT/REJECT/UNRESOLVED/ERROR/NOT_RUN), `physical_calls` (0/1). Es un comprobador de umbrales, no un ledger, juez, verificador de autenticidad ni autorización. No deduplicar intentos ni confiar en el contador sin los recibos originales. A=16, B=36, C=108 slots acumulados. No enviar IDs, variantes, etiquetas o manifiestos al modelo.

Validación realizada en sandbox del paquete, no en el checkout Windows: 16 tests unittest; 9 mutantes aislados detectados por aserciones (missing/error, duplicación, omisión de A, UNKNOWN, pérdida transferencias, manifiesto alterado, agregado entre repeticiones, cierre P0 indebido, ocultación de pérdidas). Restaurado: 16 verdes. Laboratorio inicial: 43 tests pytest verdes, no el laboratorio modificado por ASTRA. Los 18 registros coinciden con los digest de los casos originales y las tres preguntas base coinciden literalmente con CRIBA-460 development. No se ejecutaron modelos, CI, Ruff/mypy ni tests de la aplicación completa. P0 sigue OPEN; G0 DRAFT_NOT_APPROVED.

Orden de ERNIE: recuperar el handoff real y su worktree; reconciliar casos y lectura del candidato con estos borradores; no copiar el laboratorio antiguo sobre ASTRA; comprobar los tests; implementar en laboratorio la carrera SQLite entre conexiones y el adaptador de normalización K3; entregar al dueño la versión congelada y las decisiones pendientes del apartado 7; solo ejecutar A tras autorización expresa. B/C, ruta productiva y EXE son puertas distintas. No mezclar main, modificar ASTRA ni activar BLACKFORGE.
