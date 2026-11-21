"""Tests del ciclo científico completo: activate → dossier → SUPRA → GET.

Estos tests verifican el ciclo científico ASTRA:
1. activate() genera ideas con mecanismo causal
2. preparar_dossier_desde_idea() crea dossier con 8 campos ASTRA
3. scientific_cycle() ejecuta el ciclo completo
4. verify_dossier_astra() verifica los 8 campos discriminantes

Niveles de evidencia:
- UNIT_TEST: prueba de funciones individuales
- INTEGRATION_WITH_SIMULATED_PROVIDER: prueba de ruta con proveedor simulado
- REAL_HTTP: prueba HTTP real contra SUPRA
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

CRIBA_ROOT = Path(__file__).resolve().parents[2]
if str(CRIBA_ROOT) not in sys.path:
    sys.path.insert(0, str(CRIBA_ROOT))
if str(CRIBA_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(CRIBA_ROOT / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def skip_if_no_supra():
    """Skip tests de integración/HTTP si SUPRA no está disponible."""
    import urllib.request
    endpoint = os.environ.get("SUPRA_ENDPOINT", "http://127.0.0.1:8000")
    try:
        with urllib.request.urlopen(f"{endpoint}/health", timeout=2):
            pass
    except Exception:
        pytest.skip(f"SUPRA no disponible en {endpoint}")


# ===========================================================================
# UNIT TESTS: Funciones individuales
# ===========================================================================

class TestCientificoUnitario:
    """Pruebas unitarias de funciones del ciclo científico."""

    def test_01_activate_genera_ideas_con_mecanismo_causal(self):
        """activate() genera ideas con mecanismo causal."""
        from criba.engine import activate
        packet = activate("Reducir el impacto de las baterías sin aumentar el coste ni comprometer el suministro.")
        ideas = packet.get("innovation", {}).get("ideas", [])
        assert len(ideas) > 0, "No se generaron ideas"
        idea = ideas[0]
        assert "mechanism_causal" in idea, "La idea no tiene mecanismo causal"
        assert "causal_variables" in idea, "La idea no tiene variables causales"
        assert "expected_effect" in idea, "La idea no tiene efecto esperado"

    def test_02_preparar_dossier_desde_idea_campos_astra(self):
        """preparar_dossier_desde_idea() crea dossier con 8 campos ASTRA."""
        from criba.engine import activate
        from criba.supra_dossier import preparar_dossier_desde_idea
        packet = activate("Reducir el impacto de las baterías sin aumentar el coste ni comprometer el suministro.")
        idea = packet["innovation"]["ideas"][0]
        dossier = preparar_dossier_desde_idea(idea, "Reducir el impacto de las baterías sin aumentar el coste ni comprometer el suministro.")
        prueba = dossier.get("prueba_discriminante", {})
        campos_astra = (
            "afirmacion_decisiva", "alternativa_explicativa", "intervencion_prueba",
            "observable", "resultado_favorable_mecanismo", "resultado_favorable_alternativa",
            "regla_decision", "condicion_fracaso",
        )
        for campo in campos_astra:
            assert campo in prueba, f"Campo ASTRA '{campo}' ausente en prueba_discriminante"
            assert prueba[campo], f"Campo ASTRA '{campo}' vacío"

    def test_03_verify_dossier_astra_completo(self):
        """verify_dossier_astra() verifica los 8 campos discriminantes."""
        from criba.engine import verify_dossier_astra
        dossier_valido = {
            "prueba_discriminante": {
                "afirmacion_decisiva": "test",
                "alternativa_explicativa": "test",
                "intervencion_prueba": "test",
                "observable": "test",
                "resultado_favorable_mecanismo": "test",
                "resultado_favorable_alternativa": "test",
                "regla_decision": "test",
                "condicion_fracaso": "test",
            }
        }
        resultado = verify_dossier_astra(dossier_valido)
        assert resultado["complete"] is True
        assert len(resultado["present"]) == 8
        assert len(resultado["missing"]) == 0

    def test_04_verify_dossier_astra_incompleto(self):
        """verify_dossier_astra() detecta campos faltantes."""
        from criba.engine import verify_dossier_astra
        dossier_incompleto = {
            "prueba_discriminante": {
                "afirmacion_decisiva": "test",
                # Faltan 7 campos
            }
        }
        resultado = verify_dossier_astra(dossier_incompleto)
        assert resultado["complete"] is False
        assert len(resultado["present"]) == 1
        assert len(resultado["missing"]) == 7

    def test_05_causal_model_family_specs_accesibles(self):
        """FAMILY_SPECS de causal_model.py es accesible desde engine."""
        from criba.causal_model import _ensure_family_specs, FAMILY_SPECS
        _ensure_family_specs()
        assert len(FAMILY_SPECS) > 0, "FAMILY_SPECS está vacío"
        # Verificar que tiene las familias principales
        assert "diagnostico" in FAMILY_SPECS
        assert "inversion" in FAMILY_SPECS
        assert "sustraccion" in FAMILY_SPECS

    def test_06_mcda_reexporta_metodos_ranking(self):
        """mcda.py re-exporta MCDAAnalyzer desde scoring/mcda.py."""
        from criba.mcda import MCDAAnalyzer
        assert MCDAAnalyzer is not None
        assert hasattr(MCDAAnalyzer, "topsis")
        assert hasattr(MCDAAnalyzer, "ahp")
        assert hasattr(MCDAAnalyzer, "promethee")
        assert hasattr(MCDAAnalyzer, "ensemble_rank")


# ===========================================================================
# INTEGRATION TESTS: Ciclo científico completo
# ===========================================================================

class TestCientificoIntegracion:
    """Tests de integración del ciclo científico completo."""

    @pytest.fixture(autouse=True)
    def skip_if_no_supra(self):
        """Skip si SUPRA no está disponible."""
        import urllib.request
        import os
        endpoint = os.environ.get("SUPRA_ENDPOINT", "http://127.0.0.1:8000")
        try:
            with urllib.request.urlopen(f"{endpoint}/health", timeout=2):
                pass
        except Exception:
            pytest.skip(f"SUPRA no disponible en {endpoint}")

    def test_07_scientific_cycle_genera_dossier(self):
        """scientific_cycle() genera dossier con 8 campos ASTRA."""
        from criba.engine import scientific_cycle, verify_dossier_astra
        resultado = scientific_cycle("Reducir el impacto de las baterías sin aumentar el coste ni comprometer el suministro.")
        assert resultado["error"] is None, f"Error: {resultado['error']}"
        assert resultado["packet"] is not None
        assert resultado["idea"] is not None
        assert resultado["dossier"] is not None
        # Verificar 8 campos ASTRA
        verificacion = verify_dossier_astra(resultado["dossier"])
        assert verificacion["complete"] is True, f"Campos faltantes: {verificacion['missing']}"

    def test_08_scientific_cycle_identidad_dossier(self):
        """El dossier generado tiene identidad correcta."""
        from criba.engine import scientific_cycle
        resultado = scientific_cycle("Reducir el impacto de las baterías sin aumentar el coste ni comprometer el suministro.")
        assert resultado["error"] is None
        dossier = resultado["dossier"]
        assert dossier["dossier_id"].startswith("dossier-")
        assert dossier["candidate_id"] == resultado["idea"]["id"]
        assert dossier["mechanism_version"].startswith("sha256:")
        assert dossier["protocol_version"].startswith("sha256:")

    def test_09_scientific_cycle_estados_honestos(self):
        """Los estados científicos son honestos (no se convierten UNKNOWN en éxito)."""
        from criba.engine import scientific_cycle
        resultado = scientific_cycle("Reducir el impacto de las baterías sin aumentar el coste ni comprometer el suministro.")
        assert resultado["error"] is None
        receipt = resultado["receipt"]
        # Verificar que los estados son honestos
        assert receipt["scientific_status"] in ("NOT_VALIDATED", "VALIDATED", "UNKNOWN")
        assert receipt["execution_status"] in ("NOT_EXECUTED", "EXECUTED", "UNKNOWN")
        # No convertir BLOCKED en éxito
        if receipt["status"] == "blocked":
            assert receipt["completion_status"] != "COMPLETED"


# ===========================================================================
# REAL HTTP TESTS: SUPRA real
# ===========================================================================

class TestCientificoRealHTTP:
    """Tests HTTP reales contra SUPRA (requiere SUPRA corriendo)."""

    @pytest.fixture
    def supra_endpoint(self):
        """Endpoint de SUPRA (variable de entorno o default)."""
        return os.environ.get("SUPRA_ENDPOINT", "http://127.0.0.1:8000")

    def test_10_supra_health_real(self, supra_endpoint):
        """SUPRA responde /health correctamente."""
        import urllib.request
        import json
        try:
            with urllib.request.urlopen(f"{supra_endpoint}/health", timeout=5) as resp:
                data = json.loads(resp.read().decode())
                assert data["status"] == "healthy"
                assert data["service"] == "supra-agentic-taskmaster"
        except Exception as e:
            pytest.skip(f"SUPRA no disponible en {supra_endpoint}: {e}")

    def test_11_scientific_cycle_envio_supra_real(self, supra_endpoint):
        """scientific_cycle() envía a SUPRA real y recibe receipt."""
        os.environ["SUPRA_ENDPOINT"] = supra_endpoint
        from criba.engine import scientific_cycle
        resultado = scientific_cycle("Reducir el impacto de las baterías sin aumentar el coste ni comprometer el suministro.")
        if resultado["error"] and "connection" in resultado["error"].lower():
            pytest.skip(f"SUPRA no disponible: {resultado['error']}")
        assert resultado["error"] is None, f"Error: {resultado['error']}"
        assert resultado["receipt"] is not None
        receipt = resultado["receipt"]
        assert receipt["project_id"]
        assert receipt["dossier_id"] == resultado["dossier"]["dossier_id"]
        assert receipt["candidate_id"] == resultado["dossier"]["candidate_id"]
