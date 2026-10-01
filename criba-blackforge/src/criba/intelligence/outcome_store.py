"""Memoria experimental técnica→outcome (BLUEPRINT §4.2, multiplicador fundamental).

Cierra el circuito: qué técnica/clase de pensamiento produjo qué resultado
observado, versionado por ``canon_version`` y consultable por el router como
prior UCB. La política de selección deja de ser congelada y pasa a aprender de
la propia experiencia del sistema.

Reglas de honestidad (patrón supra_dossier, ya probado):
- Append-only JSONL, validación de esquema por línea; las líneas malformadas se
  ignoran (nunca rompen el aprendizaje).
- El historial ambiguo se EXCLUYE del cálculo con RuntimeWarning (bytes intactos).
- Una PLANNED con prior alto NUNCA se vuelve ejecutable: el prior solo reordena
  candidatos ya elegibles; el canon sigue decidiendo qué es ejecutable.
- Sin red, sin modelo, determinista. El hash del store se expone para hacerlo
  comprobable (§15.2).

Señal compuesta etiquetada por fuente (§12.2.3): los canales verdict prior-art,
score del juez y resultado_observado se guardan por separado — nunca mezclados
en un solo número (no confundir calidad de generación con novedad).

REPRODUCIBILIDAD: seed, hash del store, fecha de evaluación y versión de
la política son dependencias conocidas de este componente, pero NO constituyen
un cierre universal. La salida global también puede depender de inputs, corpus,
configuración, provider/modelo, ordering, versión de código y estado externo.
Afirmar «mismo seed + mismo hash => mismo output» o cualquier lista fija como
condición suficiente global es incorrecto. Los consumidores deben registrar las
dependencias reales que influyan en la ejecución concreta.

AGREGADO DE FAMILIA (fuente de verdad): el back-off jerárquico lee registros
EXPLÍCITOS ``__family__`` escritos por record_family_outcome (inventar los
emite por cada clase). Los registros finos NO se agregan en lectura: si no hay
registro ``__family__`` explícito, no hay back-off. Cualquier documentación que
afirme lo contrario está desactualizada respecto a este código.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Canales de resultado admitidos, etiquetados por fuente (§12.2.3). Nunca se
# mezclan en un único número: cada prior se calcula sobre UN canal.
CHANNEL_VERDICT = "verdict"          # prior-art: SURVIVED/PARTIAL/UNRESOLVED
CHANNEL_JUDGE = "judge"              # crítica automática: score 0..1
CHANNEL_OBSERVED = "observed"        # dossier resultado_observado: pos/neg/indet

_VALID_OUTCOMES: dict[str, frozenset[str]] = {
    CHANNEL_VERDICT: frozenset({
        "SURVIVED_SEARCH", "PARTIAL_PRIOR_ART", "UNRESOLVED", "INVALID", "NOT_EVALUATED",
    }),
    CHANNEL_OBSERVED: frozenset({
        "positivo", "negativo", "indeterminado", "invalid", "not_evaluated",
    }),
    CHANNEL_JUDGE: frozenset({"score"}),
}

# Only actually evaluated outcomes have numeric reward semantics. UNKNOWN-like
# states remain serializable observations but are excluded from learning.
_VERDICT_VALUE: dict[str, float | None] = {
    "SURVIVED_SEARCH": 1.0,
    "PARTIAL_PRIOR_ART": 0.5,
    "UNRESOLVED": None,
    "INVALID": None,
    "NOT_EVALUATED": None,
}
_OBSERVED_VALUE: dict[str, float | None] = {
    "positivo": 1.0,
    "negativo": 0.0,
    "indeterminado": None,
    "invalid": None,
    "not_evaluated": None,
}

# Decaimiento temporal (§14.3): vida media fija y documentada. El reset por
# cambio de canon_epoch domina al decaimiento.
HALF_LIFE_DAYS: float = 90.0
# B03: only rows written/revalidated under current semantics may affect learning.
OUTCOME_SEMANTICS_VERSION = 2
# Back-off jerárquico (§12.2.1): una celda fina con menos observaciones que esto
# usa el prior del nivel agregado (familia).
BACKOFF_MIN_OBS = 3
# Nivel agregado al que se hace back-off cuando la celda fina no tiene datos.
_AGGREGATE_KEY = "__family__"


def _default_store_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "outcomes" / "technique_outcomes.jsonl"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


class TechniqueOutcomeStore:
    """Store versionado y auditable de outcomes por (técnica, clase).

    Clave de celda fina: (profile, family, technique_id, channel). El back-off
    agrega por (profile, family, channel) usando technique_id == _AGGREGATE_KEY.
    """

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else _default_store_path()

    # -- escritura ---------------------------------------------------------
    def record(
        self,
        *,
        profile: str,
        family: str,
        technique_id: str,
        channel: str,
        outcome: str,
        canon_version: str,
        value: float | None = None,
        run_id: str = "",
        recorded_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Registra un outcome observado. Validación de esquema estricta.

        ``value`` opcional fija el valor numérico (p. ej. score del juez 0..1);
        si se omite se deriva del outcome según el canal.
        """
        if channel not in (CHANNEL_VERDICT, CHANNEL_JUDGE, CHANNEL_OBSERVED):
            raise ValueError(f"canal desconocido: {channel}")
        if channel in _VALID_OUTCOMES and outcome not in _VALID_OUTCOMES[channel]:
            raise ValueError(f"outcome inválido para {channel}: {outcome}")
        if not technique_id.strip():
            raise ValueError("technique_id es obligatorio")
        expected_value: float | None = None
        if channel == CHANNEL_VERDICT:
            expected_value = _VERDICT_VALUE[outcome]
        elif channel == CHANNEL_OBSERVED:
            expected_value = _OBSERVED_VALUE[outcome]

        if channel == CHANNEL_JUDGE:
            if value is None:
                raise ValueError("channel=judge requiere value explícito (score 0..1)")
        elif expected_value is None:
            if value is not None:
                raise ValueError(
                    f"{channel}:{outcome} no admite reward numérico"
                )
            value = None
        else:
            expected = float(expected_value)
            if value is None:
                value = expected
            elif float(value) != expected:
                raise ValueError(
                    f"value incompatible con {channel}:{outcome}; esperado {expected}"
                )

        identity_eligible = bool(str(run_id or "").strip())
        learning_eligible = value is not None and identity_eligible
        if value is not None:
            value = float(value)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"value fuera de [0,1]: {value}")
        ts = recorded_at or _now()
        if ts.tzinfo is None or ts.utcoffset() is None:
            raise ValueError("recorded_at debe incluir zona horaria")
        ts = ts.astimezone(timezone.utc)
        record = {
            "profile": profile,
            "family": family,
            "technique_id": technique_id,
            "channel": channel,
            "outcome": outcome,
            "value": value,
            "learning_eligible": learning_eligible,
            "identity_eligible": identity_eligible,
            "learning_invalidation_reason": (
                "" if identity_eligible or value is None else "STABLE_RUN_ID_REQUIRED"
            ),
            "canon_version": canon_version,
            "outcome_semantics_version": OUTCOME_SEMANTICS_VERSION,
            "run_id": run_id,
            "recorded_at": ts.isoformat(timespec="seconds"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    # -- lectura -----------------------------------------------------------
    def _read_valid(self) -> list[dict[str, Any]]:
        """Lee y valida; el historial ambiguo se excluye con RuntimeWarning."""
        if not self.path.exists():
            return []
        valid: list[dict[str, Any]] = []
        malformed = 0
        semantics_invalidated = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(rec, dict):
                malformed += 1
                continue
            if not all(isinstance(rec.get(k), str) and rec.get(k) for k in
                       ("profile", "family", "technique_id", "channel", "outcome")):
                malformed += 1
                continue
            channel = rec["channel"]
            outcome = rec["outcome"]
            if channel not in (CHANNEL_VERDICT, CHANNEL_JUDGE, CHANNEL_OBSERVED):
                malformed += 1
                continue
            if channel in _VALID_OUTCOMES and outcome not in _VALID_OUTCOMES[channel]:
                malformed += 1
                continue
            recorded_at_raw = rec.get("recorded_at")
            if not isinstance(recorded_at_raw, str) or _parse_ts(recorded_at_raw) is None:
                # New writes always have a parseable timestamp. Legacy/corrupt
                # rows without one are preserved on disk but excluded from
                # learning rather than receiving artificial full recency.
                malformed += 1
                continue
            value = rec.get("value")
            identity_eligible = bool(str(rec.get("run_id") or "").strip())
            learning_eligible = rec.get("learning_eligible", value is not None)
            if not identity_eligible and learning_eligible:
                rec = dict(rec)
                rec["historical_learning_eligible"] = learning_eligible
                rec["learning_eligible"] = False
                rec["learning_invalidation_reason"] = "STABLE_RUN_ID_REQUIRED"
                learning_eligible = False
            semantics_version = rec.get("outcome_semantics_version")
            semantics_current = semantics_version == OUTCOME_SEMANTICS_VERSION
            if not semantics_current:
                semantics_invalidated += 1
                # Historical rows are preserved and remain inspectable, but
                # cannot reactivate rewards/priors after restart merely because
                # an older implementation once considered them valid.
                rec = dict(rec)
                rec["historical_learning_eligible"] = learning_eligible
                rec["learning_eligible"] = False
                rec["value"] = None
                rec["learning_invalidation_reason"] = (
                    "OUTCOME_SEMANTICS_REVALIDATION_REQUIRED"
                )
                learning_eligible = False
                value = None
            if not isinstance(learning_eligible, bool):
                malformed += 1
                continue
            if learning_eligible and not isinstance(value, (int, float)):
                malformed += 1
                continue
            if not learning_eligible and value is not None and identity_eligible:
                malformed += 1
                continue
            if isinstance(value, (int, float)) and not 0.0 <= float(value) <= 1.0:
                malformed += 1
                continue
            expected_value: float | None = None
            if channel == CHANNEL_VERDICT:
                expected_value = _VERDICT_VALUE[outcome]
            elif channel == CHANNEL_OBSERVED:
                expected_value = _OBSERVED_VALUE[outcome]
            if semantics_current:
                if channel != CHANNEL_JUDGE and expected_value is None and (learning_eligible or value is not None):
                    # UNKNOWN/INVALID/NOT_EVALUATED are serializable observations,
                    # never reward-bearing evidence.
                    malformed += 1
                    continue
                if isinstance(expected_value, (int, float)):
                    if not isinstance(value, (int, float)) or float(value) != float(expected_value):
                        malformed += 1
                        continue
                    if identity_eligible and learning_eligible is not True:
                        malformed += 1
                        continue
                    if not identity_eligible and learning_eligible is not False:
                        malformed += 1
                        continue
                if channel == CHANNEL_JUDGE:
                    if outcome != "score" or not isinstance(value, (int, float)):
                        malformed += 1
                        continue
                    if identity_eligible and learning_eligible is not True:
                        malformed += 1
                        continue
                    if not identity_eligible and learning_eligible is not False:
                        malformed += 1
                        continue
            rec["identity_eligible"] = identity_eligible
            rec["learning_eligible"] = learning_eligible
            valid.append(rec)
        if malformed:
            warnings.warn(
                f"OutcomeStore: {malformed} líneas malformadas excluidas del "
                "aprendizaje; registros conservados",
                RuntimeWarning,
                stacklevel=2,
            )
        if semantics_invalidated:
            warnings.warn(
                f"OutcomeStore: {semantics_invalidated} registros históricos "
                "requieren revalidación semántica y no alimentan aprendizaje",
                RuntimeWarning,
                stacklevel=2,
            )
        return valid

    @staticmethod
    def _decay_weight(recorded_at: datetime | None, now: datetime) -> float:
        if recorded_at is None:
            return 1.0
        age_days: float = max(0.0, (now - recorded_at).total_seconds() / 86400.0)
        weight: float = 0.5 ** (age_days / HALF_LIFE_DAYS)
        return weight

    def _cell_stats(
        self,
        records: list[dict[str, Any]],
        *,
        profile: str,
        family: str,
        technique_id: str,
        channel: str,
        canon_version: str | None,
        now: datetime,
    ) -> tuple[float, int]:
        """Return weighted reward and sample count for one cell.

        A non-empty ``run_id`` is the stable episode identity. Rewrites replace
        the episode's value but retain its first observation timestamp, so a
        correction is neither a new sample nor a recency refresh. Ineligible
        outcomes replace prior values while contributing no reward. Records
        produced after ``now`` are unavailable to historical replay.
        """
        wsum = 0.0
        n_eff = 0
        episodes: dict[str, tuple[float | None, datetime | None]] = {}
        for rec in records:
            if rec["profile"] != profile or rec["family"] != family:
                continue
            if rec["technique_id"] != technique_id or rec["channel"] != channel:
                continue
            if canon_version is not None and rec.get("canon_version") != canon_version:
                continue
            recorded_at = _parse_ts(rec.get("recorded_at"))
            if recorded_at is not None and recorded_at > now:
                continue
            value = float(rec["value"]) if rec.get("learning_eligible", True) else None
            run_id = str(rec.get("run_id") or "")
            if not run_id:
                if value is not None:
                    wsum += self._decay_weight(recorded_at, now) * value
                    n_eff += 1
                continue
            first_seen = episodes.get(run_id, (None, recorded_at))[1]
            if first_seen is None or (recorded_at is not None and recorded_at < first_seen):
                first_seen = recorded_at
            episodes[run_id] = (value, first_seen)
        for value, first_seen in episodes.values():
            if value is None:
                continue
            wsum += self._decay_weight(first_seen, now) * value
            n_eff += 1
        return wsum, n_eff

    def _population_episode_count(
        self,
        records: list[dict[str, Any]],
        *,
        profile: str,
        channel: str,
        canon_version: str | None,
        now: datetime,
    ) -> int:
        """Count effective experimental episodes once across all technique cells.

        A non-empty run_id identifies one episode globally for this profile/channel.
        The latest row for each (family, technique, run_id) decides whether that
        cell remains learning-eligible; the same episode across T1/T2/__family__
        still contributes one population observation. Rows without run_id are
        preserved but never counted as independent learning episodes.
        """
        effective_cells: dict[tuple[str, str, str], bool] = {}
        legacy_rows = 0  # kept for compatibility; no-id rows never count
        for rec in records:
            if rec["profile"] != profile or rec["channel"] != channel:
                continue
            if canon_version is not None and rec.get("canon_version") != canon_version:
                continue
            recorded_at = _parse_ts(rec.get("recorded_at"))
            if recorded_at is not None and recorded_at > now:
                continue
            eligible = bool(rec.get("learning_eligible", rec.get("value") is not None))
            run_id = str(rec.get("run_id") or "")
            if not run_id:
                continue
            key = (str(rec["family"]), str(rec["technique_id"]), run_id)
            effective_cells[key] = eligible
        run_ids = {
            run_id
            for (_family, _technique, run_id), eligible in effective_cells.items()
            if eligible
        }
        return len(run_ids) + legacy_rows

    def prior(
        self,
        *,
        profile: str,
        family: str,
        technique_id: str,
        channel: str = CHANNEL_VERDICT,
        canon_version: str | None = None,
        exploration_c: float = 1.0,
        now: datetime | None = None,
    ) -> tuple[float, int, str]:
        """Prior UCB para (técnica, clase) con back-off jerárquico.

        Devuelve (prior, n_efectivo, etiqueta). Si la celda fina tiene menos de
        BACKOFF_MIN_OBS observaciones, hace back-off al nivel agregado (familia).
        Con cero datos el prior es 0.0 (comportamiento congelado, §6 reversible).
        """
        now = now or _now()
        records = self._read_valid()
        wsum, n_eff = self._cell_stats(
            records, profile=profile, family=family, technique_id=technique_id,
            channel=channel, canon_version=canon_version, now=now,
        )
        used_backoff = False
        if n_eff < BACKOFF_MIN_OBS:
            wsum_agg, n_agg = self._cell_stats(
                records, profile=profile, family=family,
                technique_id=_AGGREGATE_KEY, channel=channel,
                canon_version=canon_version, now=now,
            )
            if n_agg > 0:
                wsum, n_eff = wsum_agg, n_agg
                used_backoff = True
        if n_eff == 0:
            return 0.0, 0, "sin_datos"
        mean = wsum / n_eff
        # Count effective EPISODES, not per-cell samples. One experiment may
        # legitimately be attributed to several techniques and __family__, but
        # that must not inflate UCB uncertainty as if they were independent runs.
        total = self._population_episode_count(
            records,
            profile=profile,
            channel=channel,
            canon_version=canon_version,
            now=now,
        )
        bonus = exploration_c * math.sqrt(math.log(max(total, 2)) / n_eff)
        prior = mean + bonus
        # P2: un resultado NEGATIVO debe poder REDUCIR la preferencia, no solo
        # subirla. Con media < 0.5 (la observada es peor que indeterminada), el
        # bonus de exploración se ATENÚA por la evidencia negativa acumulada:
        # explorar fracasos es razonable; tratarlos como incertidumbre favorable
        # no. Con mean >= 0.5 el bonus UCB se conserva íntegro. El factor nunca
        # baja de 0: un historial de fallos acerca el prior a la media observada.
        if mean < 0.5:
            confidence = min(1.0, n_eff / BACKOFF_MIN_OBS)
            bonus *= (2.0 * mean) * confidence
            prior = mean + bonus
        label = f"ucb:{prior:.3f}(n={n_eff},backoff={used_backoff})"
        return prior, n_eff, label

    # -- agregación (back-off) --------------------------------------------
    def record_family_outcome(
        self,
        *,
        profile: str,
        family: str,
        channel: str,
        outcome: str,
        canon_version: str,
        value: float | None = None,
        run_id: str = "",
        recorded_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Registra el outcome a nivel agregado (familia) para el back-off."""
        return self.record(
            profile=profile, family=family, technique_id=_AGGREGATE_KEY,
            channel=channel, outcome=outcome, canon_version=canon_version,
            value=value, run_id=run_id, recorded_at=recorded_at,
        )

    def summary(
        self,
        *,
        profile: str | None = None,
        canon_version: str | None = None,
    ) -> list[dict[str, Any]]:
        """Presentation-only summary deduplicated by stable episode identity.

        For rows with run_id, the latest persisted row for the same
        (profile,family,technique,channel,run_id) is the effective observation.
        Rows without stable identity remain visible as unidentified_records
        but never inflate n or numeric summary values. This display logic
        never feeds learning.
        """
        records = self._read_valid()
        effective: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        unidentified_counts: dict[tuple[str, str, str, str, str], int] = {}
        for rec in records:
            if profile is not None and rec["profile"] != profile:
                continue
            if canon_version is not None and rec.get("canon_version") != canon_version:
                continue
            run_id = str(rec.get("run_id") or "")
            if not run_id:
                key = (
                    rec["profile"],
                    rec["family"],
                    rec["technique_id"],
                    rec["channel"],
                    rec["outcome"],
                )
                unidentified_counts[key] = unidentified_counts.get(key, 0) + 1
                continue
            episode_key = (
                rec["profile"],
                rec["family"],
                rec["technique_id"],
                rec["channel"],
                run_id,
            )
            effective[episode_key] = rec

        cells: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        for rec in effective.values():
            key = (
                rec["profile"],
                rec["family"],
                rec["technique_id"],
                rec["channel"],
                rec["outcome"],
            )
            cell = cells.setdefault(
                key,
                {
                    "profile": rec["profile"],
                    "family": rec["family"],
                    "technique_id": rec["technique_id"],
                    "channel": rec["channel"],
                    "outcome": rec["outcome"],
                    "n": 0,
                    "unidentified_records": unidentified_counts.get(key, 0),
                    "value_sum": 0.0,
                    "value_n": 0,
                },
            )
            cell["n"] += 1
            value = rec.get("value")
            if isinstance(value, (int, float)):
                cell["value_sum"] += float(value)
                cell["value_n"] += 1

        for key, count in unidentified_counts.items():
            if key not in cells:
                profile_v, family_v, technique_v, channel_v, outcome_v = key
                cells[key] = {
                    "profile": profile_v,
                    "family": family_v,
                    "technique_id": technique_v,
                    "channel": channel_v,
                    "outcome": outcome_v,
                    "n": 0,
                    "unidentified_records": count,
                    "value_sum": 0.0,
                    "value_n": 0,
                }

        out: list[dict[str, Any]] = []
        for key in sorted(cells):
            cell = dict(cells[key])
            value_n = cell.pop("value_n")
            value_sum = cell.pop("value_sum")
            cell["value"] = round(value_sum / value_n, 6) if value_n else None
            out.append(cell)
        return out

    # -- auditoría / invariante (§15.2) ------------------------------------
    def state_hash(self) -> str:
        """Return integrity of store bytes relative to this exact reference.

        The hash is one minimum known component dependency. It is not sufficient
        for global reproducibility: consumers may also depend on seed, evaluation
        time/clock, policy and code version, corpus, configuration, provider,
        ordering, and external state.
        """
        if not self.path.exists():
            return hashlib.sha256(b"").hexdigest()
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


def default_store(path: Path | str | None = None) -> TechniqueOutcomeStore:
    """Store por defecto en LOCALAPPDATA (mismo patrón que dossiers/ledger)."""
    return TechniqueOutcomeStore(path)
