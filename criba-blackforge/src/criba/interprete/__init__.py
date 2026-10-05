"""Interprete-serendipia: pipeline de interpretación epistemológica.

- PreFilter: prefiltrado causal top-N (Dh 0.45-0.85 + SOTA taboo + novelty band).
- Protocolo: 11 preguntas de expansión epistemológica (serendipia).
- Puerto único: propone y critica con modelo externo o runtime local admitido.
- InterpreteStore: historia transaccional, caché revalidada y pendientes reintentables.

Integración en engine.activate() como capa aditiva: el packet CRIBA base queda
intacto; el interprete añade el bloque innovation.interprete.
"""
