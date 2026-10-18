"""Mutation accreditation for the ten negative tests.

A sentinel that is only green proves nothing. Each test below reintroduces a
specific defect into the PRODUCT source, asserts that a named test turns RED,
and restores the file. If a mutation cannot kill the expected test, the
contract is not protected and the assertion below fails loudly.

Run with: pytest tests/unit/test_blackforge_v1_mutations.py -q
These tests mutate files on disk and are therefore slower than the sentinels
they defend; they belong to the closure gate, not to the fast loop.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "criba"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).parent))


def _run(test_id: str) -> bool:
    """Return True when the named test FAILS (the mutation was detected)."""
    import subprocess

    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            f"{ROOT / 'tests' / 'unit' / 'test_blackforge_v1_negative10.py'}::{test_id}",
            "-q", "-p", "no:cacheprovider", "--no-header", "-x",
        ],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300,
    )
    return result.returncode != 0


@pytest.fixture
def patched():
    """Restore every touched file even if the assertion fails."""
    touched: dict[Path, str] = {}

    def apply(path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        if old not in text:
            pytest.fail(
                f"ancla no encontrada en {path.name}; el fixture de la sonda "
                f"ha quedado obsoleto y el test meria algo que no existe."
            )
        if path not in touched:
            touched[path] = text
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    yield apply

    for path, text in touched.items():
        path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Negative test 1: dispatch without administrative widening
# ---------------------------------------------------------------------------


def test_mut_01_bypassing_the_capability_switch_is_detected(patched):
    """Re-enabling execution at construction removes the only hard stop."""
    patched(
        SRC / "blackforge_broker.py",
        "        self.policy = policy or Policy()",
        "        self.policy = policy or Policy(execution_enabled=True)",
    )
    assert _run("test_neg_01_dispatch_without_administrative_widening_is_denied"), (
        "bypass de la capacidad no detectado"
    )


# ---------------------------------------------------------------------------
# Negative test 2: widening without a credential
# ---------------------------------------------------------------------------


def test_mut_02_widening_without_credential_is_detected(patched):
    patched(
        SRC / "blackforge_broker.py",
        """        if not self._has_credentialed_grant():
            raise PolicyError(
                "No existe ninguna autorización con credencial enrolada; "
                "habilitar ejecución sin ella fabricaría autoridad."
            )""",
        """        if False:
            raise PolicyError("desactivado")""",
    )
    assert _run("test_neg_02_kernel_cannot_widen_capability_without_a_credential"), (
        "ampliacion sin credencial no detectada"
    )


# ---------------------------------------------------------------------------
# Negative test 3: altered plan digest
# ---------------------------------------------------------------------------


def test_mut_03_plan_digest_check_is_detected(patched):
    patched(
        SRC / "blackforge_case.py",
        """        if authorization.approved_plan_digest != plan_digest:
            raise CaseError(
                "Plan alterado: la autorizacion no corresponde al digest del plan sellado."
            )""",
        """        if False:
            raise CaseError("desactivado")""",
    )
    assert _run("test_neg_03_altered_plan_cannot_attach_to_the_case"), (
        "el digest del plan no protege: un plan alterado heredaria la aprobacion"
    )


# ---------------------------------------------------------------------------
# Negative test 4: target substitution
# ---------------------------------------------------------------------------


def test_mut_04_resolved_target_digest_is_detected(patched):
    """Hashing the step KIND alone loses the target identity."""
    patched(
        SRC / "blackforge_case.py",
        """    def digest(self) -> str:
        return digest_of(self.to_dict())""",
        """    def digest(self) -> str:
        from dataclasses import replace as _r
        return digest_of(
            _r(self, steps=tuple(_r(s, resolved_target="lab://generico") for s in self.steps)).to_dict()
        )""",
    )
    assert _run("test_neg_04_target_substitution_keeping_the_name_is_refused"), (
        "sustituir el objetivo conservando el nombre no se detecta"
    )


# ---------------------------------------------------------------------------
# Negative test 5: revocation cause
# ---------------------------------------------------------------------------


def test_mut_05_revocation_is_detected(patched):
    patched(
        SRC / "blackforge_case.py",
        """        if record.nonce in self._revoked_authorizations:
            # Check revocation BEFORE the axis: revocation is the precise
            # cause, and reporting only the axis value would hide it behind
            # the symptom. Reporting the axis alone also lets a caller infer
            # "it expired" when it was in fact revoked.
            return False, f"autorizacion revocada: {record.nonce}"
""",
        "",
    )
    assert _run("test_neg_05_revocation_blocks_and_names_its_cause"), (
        "la revocacion ya no se nombra como causa precisa"
    )


def test_mut_05_expiry_is_detected(patched):
    patched(
        SRC / "blackforge_case.py",
        "        if (moment - start).total_seconds() > record.max_duration_s:",
        "        if False:",
    )
    assert _run("test_neg_05_expired_ttl_blocks_the_case"), (
        "una autorizacion expirada pasa como vigente"
    )


# ---------------------------------------------------------------------------
# Negative test 6: single consumption
# ---------------------------------------------------------------------------


def test_mut_06_nonce_reuse_is_detected(patched):
    """Removing the consumption check lets the same approval dispatch twice."""
    patched(
        SRC / "blackforge_broker.py",
        """            consumed = con.execute(
                "SELECT attempt_id FROM consumptions WHERE nonce=?",
                (grant["nonce"],),
            ).fetchone()
            if consumed is not None:
                raise AuthorizationError(
                    f"El nonce de {grant_id} ya se consumió en el intento "
                    f"{consumed['attempt_id']}; cero despachos."
                )""",
        """            consumed = None""",
    )
    assert _run("test_neg_06_repeated_reservation_yields_exactly_one_dispatch"), (
        "el consumo unico ya no impide el reenvio"
    )


def test_mut_06_concurrent_race_is_detected(patched):
    """Replacing IMMEDIATE with a deferred transaction opens the race."""
    patched(
        SRC / "blackforge_broker.py",
        '            con.execute("BEGIN IMMEDIATE")',
        '            con.execute("BEGIN")',
    )
    assert _run("test_neg_06_concurrent_reservations_produce_at_most_one"), (
        "la carrera concurrente ya no se cierra con BEGIN IMMEDIATE"
    )


# ---------------------------------------------------------------------------
# Negative test 7: boot epoch and schema
# ---------------------------------------------------------------------------


def test_mut_07_boot_epoch_check_is_detected(patched):
    patched(
        SRC / "blackforge_case.py",
        """        if authorization.boot_epoch != current_boot_epoch():
            raise CaseError(
                f"La autorizacion pertenece a otra epoca de arranque "
                f"({authorization.boot_epoch} != {current_boot_epoch()}); "
                f"reiniciar invalida autorizaciones pendientes."
            )""",
        """        if False:
            raise CaseError("desactivado")""",
    )
    assert _run("test_neg_07_authorization_from_another_boot_epoch_is_rejected"), (
        "una autorizacion de otro proceso sobrevive a un reinicio"
    )


def test_mut_07_schema_gate_is_detected(patched):
    patched(
        SRC / "blackforge_case.py",
        """        if raw.get("schema") != CASE_SCHEMA:
            raise CaseError(
                f"Esquema {raw.get('schema')!r} distinto de {CASE_SCHEMA!r}; "
                f"importar sin version rechazada."
            )""",
        """        if False:
            raise CaseError("desactivado")""",
    )
    assert _run("test_neg_07_unknown_schema_is_refused_on_import"), (
        "un esquema desconocido se importaria sin version"
    )


# ---------------------------------------------------------------------------
# Negative test 8: crash after dispatch
# ---------------------------------------------------------------------------


def test_mut_08_outcome_unknown_is_detected(patched):
    """Claiming FAILED on an unknown effect is the false-success bug."""
    patched(
        SRC / "blackforge_broker.py",
        """            self._mark(
                attempt.attempt_id,
                ExecutionAxis.OUTCOME_UNKNOWN,
                reason=f"executor devolvio una excepcion: {type(exc).__name__}: {exc}",
            )""",
        """            self._mark(
                attempt.attempt_id,
                ExecutionAxis.FAILED,
                reason="fallo limpio",
            )""",
    )
    assert _run("test_neg_08_crash_after_dispatch_is_explicit_uncertainty"), (
        "un efecto posible se reporta como fallo limpio en vez de incertidumbre"
    )


# ---------------------------------------------------------------------------
# Negative test 9: hostile evidence
# ---------------------------------------------------------------------------


def test_mut_09_evidence_origin_gate_is_detected(patched):
    """Accepting OBSERVED_ACCREDITED without validation is promotion."""
    patched(
        SRC / "blackforge_case.py",
        """            if self.validated is not True:
                raise CaseError(
                    f"La evidencia {self.evidence_id} se declara observada sin validar; "
                    f"no puede respaldar una conclusion sobre el objetivo."
                )""",
        "",
    )
    assert _run("test_neg_09_observed_evidence_requires_reference_and_validation"), (
        "una evidencia observada sin validar respaldaria una conclusion"
    )


# ---------------------------------------------------------------------------
# Negative test 10: promotion of simulation to validation
# ---------------------------------------------------------------------------


def test_mut_10_supporting_verdict_may_not_cite_missing_evidence(patched):
    patched(
        SRC / "blackforge_case.py",
        """        if conclusion.evaluation is EvaluationAxis.SUPPORTS_H1:
            if conclusion.justifications and not any(
                self.evidence_by_id(j) for j in conclusion.justifications
            ):
                raise CaseError(
                    "Una conclusion SUPPORTS_H1 debe citar evidencia existente; "
                    "promover una justificacion inexistente esta prohibido."
                )""",
        """        if False:
            raise CaseError("desactivado")""",
    )
    assert _run("test_neg_10_supporting_verdict_must_cite_existing_evidence"), (
        "una conclusion puede citar evidencia inexistente"
    )


def test_mut_10_state_machine_cannot_be_skipped(patched):
    """Removing the transition guard lets a DRAFT case be assessed."""
    patched(
        SRC / "blackforge_case.py",
        """    def _require(self, *allowed: WorkflowState) -> None:
        if self.workflow not in allowed:
            raise TransitionError(
                f"Transicion no permitida desde {self.workflow.value}; "
                f"se exige {', '.join(a.value for a in allowed)}."
            )""",
        """    def _require(self, *allowed: WorkflowState) -> None:
        return None""",
    )
    assert _run("test_neg_10_assess_requires_a_recorded_result"), (
        "la maquina de estados deja de proteger: un caso DRAFT podria concluir"
    )


def test_mut_10_execution_axis_can_no_longer_be_forged(patched):
    """Forging COMPLETED on a declarative slice is the promotion to kill."""
    patched(
        SRC / "blackforge_case.py",
        """        elif self.execution is ExecutionAxis.NOT_STARTED:
            # Nothing was executed: keep the axis honest instead of claiming
            # COMPLETED for work that never reached a target.
            self.execution = ExecutionAxis.NOT_STARTED""",
        """        elif self.execution is ExecutionAxis.NOT_STARTED:
            self.execution = ExecutionAxis.COMPLETED""",
    )
    assert _run("test_neg_10_completed_simulation_is_not_execution_and_not_validation"), (
        "una simulacion declarativa se presenta como ejecucion completada"
    )