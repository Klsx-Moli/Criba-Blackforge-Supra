"""Tests del harness benchmark (hallazgo 6): C_CRIBA ejecuta CRIBA real y la
semilla se propaga. FALSAN el defecto original (C_CRIBA = solo texto de prompt,
semilla sin llegar al callback)."""
from __future__ import annotations

from benchmarks.innovation.blackforge_adapter import (
    blackforge_fn,
    run_blackforge_selection,
)
from benchmarks.innovation.criba_adapter import criba_fn, run_criba_invention
from benchmarks.innovation.harness import run_condition

_PROBLEMA = {"id": "p1", "texto": "reducir consumo energético de sensores"}


class TestSemillaPropagada:
    def test_model_fn_recibe_semilla(self):
        """El callback recibe la semilla (reproducibilidad de la condición)."""
        recibidas: list[int] = []

        def model_fn(prompt: str, seed: int) -> list[dict]:
            recibidas.append(seed)
            return [{"idea_id": "m0", "title": "x", "genome": {}}]

        run_condition("A_DIRECT", _PROBLEMA, seed=42, model_fn=model_fn)
        assert recibidas and recibidas[0] == 42

    def test_model_fn_un_argumento_compat(self):
        """Un stub de un solo argumento sigue funcionando (degradación)."""
        def model_fn(prompt: str) -> list[dict]:
            return [{"idea_id": "m0", "title": "x", "genome": {}}]
        r = run_condition("A_DIRECT", _PROBLEMA, seed=42, model_fn=model_fn)
        assert r["status"] == "OK"


class TestCribaReal:
    def test_c_criba_sin_criba_fn_unavailable(self):
        """Sin criba_fn, C_CRIBA es UNAVAILABLE honesto (nunca prompt de texto)."""
        r = run_condition("C_CRIBA", _PROBLEMA, seed=42)
        assert r["status"] == "UNAVAILABLE"
        assert "criba_fn" in r["nota"]

    def test_c_criba_con_criba_fn_ejecuta_loop(self):
        """Con criba_fn, C_CRIBA ejecuta el loop real y devuelve candidatos."""
        r = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        assert r["status"] == "OK"
        assert r["nota"] == "loop CRIBA real ejecutado via criba_fn"
        assert r["candidates"], "debe producir candidatos estructurados"
        assert r["metrics"] is not None

    def test_c_criba_reproducible_por_semilla(self):
        """Misma semilla => mismos candidatos (la condición es reproducible)."""
        a = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        b = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        titles_a = [c["title"] for c in a["candidates"]]
        titles_b = [c["title"] for c in b["candidates"]]
        assert titles_a == titles_b and titles_a, (
            "C_CRIBA debe ser reproducible por semilla"
        )

    def test_c_criba_no_es_un_prompt_de_texto(self):
        """El defecto original: C_CRIBA solo cambiaba el prompt. Ahora ejecuta
        el loop; el 'prompt' queda documental pero la fuente es criba_fn."""
        r = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        # los candidatos vienen del loop (tienen methods/classes), no del texto
        for c in r["candidates"]:
            assert "methods" in c or "classes" in c, (
                "candidato sin estructura de cruce: sería prosa de prompt, no CRIBA"
            )


class TestCribaInvention:
    def _sheet(self) -> dict:
        return {
            "entries": [
                {
                    "candidate_id": "invent-42-01",
                    "title": "Reutilizar el flujo sobrante",
                    "mecanismo": "Un desvio recupera el agua inicial.",
                    "hipotesis": "Reduce el desperdicio.",
                    "score": 0.81,
                    "classes": ["generacion", "perspectiva"],
                    "methods": ["Separar suministro", "Reutilizar flujo"],
                    "estado_interpretacion": "PROPUESTA",
                }
            ],
            "selection_audit": {
                "selection_report": {"status": "OK", "finalists": ["invent-42-01"]},
                "opportunity_accounting": {"provider_model_requests": 2},
            },
        }

    def test_adapter_maps_interpreted_entry_and_report(self):
        calls = []

        def fake_invent(problem: str, **kwargs):
            calls.append((problem, kwargs))
            return self._sheet()

        result = run_criba_invention(
            "reducir agua", 42, 3, mode="alternating",
            invent_callable=fake_invent,
        )
        assert result.candidates[0]["idea_id"] == "invent-42-01"
        assert result.candidates[0]["family"] == "generacion"
        assert result.candidates[0]["methods"] == [
            "Separar suministro", "Reutilizar flujo"
        ]
        assert result.selection_report["pipeline"] == "invent_fn"
        assert result.selection_report["opportunity_accounting"] == {
            "provider_model_requests": 2
        }
        assert calls[0][0] == "reducir agua"
        assert calls[0][1]["seed"] == 42
        assert calls[0][1]["mode"] == "alternating"
        assert calls[0][1]["write_ledger"] is False

    def test_harness_uses_interpreted_invent_fn(self):
        def fake_invent(problem: str, **kwargs):
            return self._sheet()

        r = run_condition(
            "C_CRIBA", _PROBLEMA, seed=42,
            invent_fn=lambda p, s, n: run_criba_invention(
                p, s, n, invent_callable=fake_invent
            ),
        )
        assert r["status"] == "OK"
        assert r["pipeline"] == "invent_fn"
        assert r["nota"] == "loop CRIBA interpretado ejecutado via invent_fn"
        assert r["candidates"][0]["description"] == "Un desvio recupera el agua inicial."
        assert r["selection_report"]["pipeline"] == "invent_fn"


class TestBlackforgeReal:
    def test_d_blackforge_sin_callback_unavailable(self):
        r = run_condition("D_BLACKFORGE", _PROBLEMA, seed=42)
        assert r["status"] == "UNAVAILABLE"
        assert "blackforge_fn" in r["nota"]

    def test_d_blackforge_con_callback_ejecuta_loop(self):
        r = run_condition(
            "D_BLACKFORGE", _PROBLEMA, seed=42, blackforge_fn=blackforge_fn
        )
        assert r["status"] == "OK"
        assert r["pipeline"] == "blackforge_fn"
        assert r["candidates"], "debe producir cruces estructurados"
        assert r["metrics"] is not None
        assert all(
            "methods" in candidate and "classes" in candidate
            for candidate in r["candidates"]
        )

    def test_d_blackforge_reproducible_por_semilla(self):
        a = run_condition(
            "D_BLACKFORGE", _PROBLEMA, seed=42, blackforge_fn=blackforge_fn
        )
        b = run_condition(
            "D_BLACKFORGE", _PROBLEMA, seed=42, blackforge_fn=blackforge_fn
        )
        assert [c["title"] for c in a["candidates"]] == [
            c["title"] for c in b["candidates"]
        ]

    def test_adapter_reports_real_pipeline(self):
        result = run_blackforge_selection("reducir agua", 42, 3)
        assert result.candidates
        assert result.selection_report["pipeline"] == "blackforge_fn"
        assert result.candidates[0]["source"] == "BLACKFORGE"
        assert result.candidates[0]["prueba_concreta"] is None
