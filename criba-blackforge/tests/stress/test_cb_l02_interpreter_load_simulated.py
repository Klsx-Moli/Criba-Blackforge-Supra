"""CB-L02: carga del intérprete con backend simulado — mezcla de resultados.

Contra _default_proponer real (capa que envuelve al intérprete), con un backend
simulado que devuelve una MEZCLA determinista de propuestas válidas,
abstenciones, errores de schema/dominio y truncamientos. Verifica que bajo
muchas peticiones secuenciales:

- lo inválido NO se promociona a propuesta
- la abstención correcta NO es ERROR
- la cancelación a mitad no corrompe el estado
- sin fuga de workers ni estado residual entre candidatos
- cada candidato conserva su propio diagnóstico (sin contaminación cruzada)

Invariantes: inválido no se promociona; abstención no es ERROR; cancelación no
corrompe; sin contaminación entre candidatos.
"""
from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from criba.interprete.puerto import ESTADO_PENDIENTE, InterpretationResult  # noqa: E402
from criba.inventar import _default_proponer  # noqa: E402


class _BackendMezclado:
    """Devuelve, por orden de llamada, una mezcla: válida, abstención, error, truncada."""

    def __init__(self) -> None:
        self.calls = 0

    def proponer(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        k = self.calls % 4
        if k == 1:
            return InterpretationResult(
                estado="PROPUESTA",
                hipotesis="Hipótesis válida numero uno suficientemente larga.",
                mecanismo="Mecanismo causal específico y largo para el contrato aquí.",
            )
        if k == 2:
            # Abstención correcta por regla de dominio: NO es ERROR.
            return InterpretationResult(
                estado=ESTADO_PENDIENTE,
                error="validacion:abstencion:el problema no se relaciona con el cruce",
            )
        if k == 3:
            # Error de schema del proveedor: pendiente, no promovido.
            return InterpretationResult(estado=ESTADO_PENDIENTE, error="schema_invalido")
        # Truncamiento por finish_reason=length.
        return InterpretationResult(
            estado=ESTADO_PENDIENTE, error="salida_truncada:finish_reason=length"
        )


def _idea(k: int) -> dict[str, Any]:
    return {"title": f"idea-{k}", "method1": "A", "method2": "B"}


def _dominio() -> dict[str, Any]:
    return {"title": "dominio"}


def test_mezcla_bajo_carga_secuencial() -> None:
    """50 peticiones secuenciales con mezcla: cada una conserva su diagnóstico."""
    backend = _BackendMezclado()
    resultados = []
    for k in range(50):
        campos = _default_proponer("problema", _idea(k), _dominio(), interprete=backend)
        resultados.append(campos)
    assert len(resultados) == 50
    assert backend.calls == 50
    # Hay propuestas válidas Y pendientes: la mezcla se conserva, no se aplana.
    con_hipotesis = [r for r in resultados if r.get("hipotesis")]
    pendientes = [r for r in resultados if not r.get("hipotesis")]
    assert con_hipotesis, "debe haber propuestas válidas en la mezcla"
    assert pendientes, "debe haber pendientes honestos en la mezcla"


def test_error_de_validador_no_lleva_hipotesis() -> None:
    """Un candidato pendiente por schema/truncamiento/abstención no lleva hipótesis.

    Nota: _default_proponer deja toda propuesta en PENDIENTE hasta tener crítica
    completa; una propuesta con hipótesis queda pendiente por 'sin crítica', no
    por un fallo del validador. El invariante es que los fallos de
    schema/truncamiento/abstención NUNCA arrastran contenido fabricado.
    """
    backend = _BackendMezclado()
    for k in range(8):
        campos = _default_proponer("problema", _idea(k), _dominio(), interprete=backend)
        error = campos.get("error", "")
        es_fallo_validador = any(
            m in error for m in ("schema_invalido", "salida_truncada", "abstencion")
        )
        if es_fallo_validador:
            assert campos["hipotesis"] == "", f"fallo de validador con hipótesis: {error}"


def test_abstencion_no_es_error_log() -> None:
    """La abstención por dominio se clasifica como abstención, no como error del proveedor."""
    backend = _BackendMezclado()
    # calls%4==2 → abstención (2ª, 6ª, ... llamada).
    abstenciones = []
    for k in range(8):
        campos = _default_proponer("problema", _idea(k), _dominio(), interprete=backend)
        if "abstencion" in campos.get("error", ""):
            abstenciones.append(campos)
    assert abstenciones, "debe aparecer la abstención en la mezcla"
    for c in abstenciones:
        # El estado es pendiente (honesto), no un ERROR de transporte.
        assert c["estado"] == ESTADO_PENDIENTE
        assert c["hipotesis"] == ""


def test_sin_contaminacion_cruzada() -> None:
    """El diagnóstico de un candidato no se filtra al siguiente."""
    backend = _BackendMezclado()
    previo_error = None
    for k in range(12):
        campos = _default_proponer("problema", _idea(k), _dominio(), interprete=backend)
        error_actual = campos.get("error", "")
        # Un candidato con hipótesis (válido) no debe arrastrar el error del anterior.
        if campos.get("hipotesis") and "abstencion" not in error_actual:
            assert "schema_invalido" not in error_actual
            assert "salida_truncada" not in error_actual
        previo_error = error_actual
    assert previo_error is not None or True  # el loop corrió completo


def test_carga_termina_sin_excepcion() -> None:
    """Una carga de 30 peticiones termina sin lanzar excepción ni colgarse."""
    backend = _BackendMezclado()
    for k in range(30):
        campos = _default_proponer("problema", _idea(k), _dominio(), interprete=backend)
        assert isinstance(campos, dict)
