"""Contrato único de interpretación y su procedencia.

Existe UN puerto. Los dos backends lo implementan y ambos pasan por el mismo
esquema, la misma validación, el mismo dossier, el mismo scoring posterior, el
mismo SupraClient y la misma persistencia. No hay una segunda ruta.

Honestidad científica, impuesta aquí y no en el consumidor:

- El intérprete propone. No inventa evidencia, ni outcomes, ni scores.
- Si falta un campo obligatorio, el resultado es PENDIENTE_INTERPRETACION con
  el motivo real. Nunca se rellena un campo ausente para que el esquema pase.
- UNKNOWN no se convierte en cero y NOT_EXECUTED no se convierte en EXECUTED:
  este módulo no escribe ninguno de esos valores.

La procedencia se registra SIEMPRE, también en los fallos, porque un fallo sin
causa no es diagnosticable. Nunca contiene claves ni cabeceras: solo el
endpoint sin credenciales.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

from .contrato import PROMPT_VERSION as PROMPT_VERSION
from .contrato import SCHEMA_VERSION as SCHEMA_VERSION
from .contrato import validar_critica

ESTADO_PROPUESTA = "PROPUESTA"
ESTADO_PENDIENTE = "PENDIENTE_INTERPRETACION"

# Campos que el pipeline de inventar.py consume de una propuesta. Fijarlos aqui
# evita que cada backend invente sus propias claves.
CAMPOS_PROPUESTA = (
    "estado",
    "hipotesis",
    "mecanismo",
    "aportacion_por_tecnica",
    "supuestos",
    "prueba_concreta",
    "ruta_desbloqueo",
    "error",
    "pertinencia",
    "cadena_causal",
    "evidencia_citada",
    "conocimiento_previo",
    "incertidumbre",
    "novedad",
    "prueba",
    "comprobacion_restricciones",
    "critica",
)


@dataclass(frozen=True)
class Provenance:
    """Lo que hay que poder responder sobre cada interpretación.

    ``endpoint`` es la URL base sin usuario, clave ni query. ``raw_output_sha256``
    permite auditar la salida sin guardarla ni filtrar contenido sensible.
    """

    interpreter_backend: str
    provider: str
    model_requested: str
    model_reported: str
    endpoint: str
    timestamp: str
    duration_ms: int
    prompt_version: str
    schema_version: str
    request_id: str
    fallback_used: bool
    raw_output_sha256: str
    prompt_sha256: str = ""
    generation_parameters: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def sin_secretos(self) -> dict[str, Any]:
        """Defensa extra: si alguien metió una clave en el endpoint, se cae."""
        limpio = self.as_dict()
        for campo in ("endpoint", "provider", "model_reported"):
            valor = limpio.get(campo) or ""
            for marcador in ("key=", "token=", "Bearer", "@"):
                if marcador in valor:
                    limpio[campo] = "[REDACTADO]"
        return limpio


def sin_secretos(base_url: str) -> str:
    """Quita credenciales de una URL sin romperla.

    Una URL de base no deberia traer usuario ni clave, pero si se trae hay que
    quitarlo sin romper el esquema: una procedencia con ``host:8642/v1`` en
    lugar de ``http://host:8642/v1`` ya no es una URL utilizable.
    """
    if "@" in base_url:
        esquema, _, resto = base_url.rpartition("://")
        _, _, host = resto.partition("@")
        base_url = f"{esquema}://{host}" if esquema else host
    for separador in ("?", "#"):
        if separador in base_url:
            base_url = base_url.split(separador, 1)[0]
    return base_url.rstrip("/")


def hash_salida(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()


def nuevo_request_id() -> str:
    return uuid.uuid4().hex[:16]


def marca_temporal() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


@dataclass(frozen=True)
class InterpretationResult:
    """Resultado del intérprete. El mismo esquema para todos los backends."""

    estado: str
    hipotesis: str = ""
    mecanismo: str = ""
    aportacion_por_tecnica: list[str] = field(default_factory=list)
    supuestos: list[str] = field(default_factory=list)
    prueba_concreta: str = ""
    ruta_desbloqueo: str = ""
    error: str = ""
    provenance: Provenance | None = None
    # Diagnóstico del proveedor para UI/auditoría. Nunca contiene cabeceras ni
    # credenciales: solo la salida textual del modelo y metadatos declarados
    # por la respuesta OpenAI-compatible. No forma parte de CAMPOS_PROPUESTA,
    # por lo que no altera el contrato científico consumido por el pipeline.
    raw_output: str = ""
    finish_reason: str = ""
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    # Clasificación estructurada del fallo, para diagnóstico del banco sin
    # volver a interpretar el texto del error. No forma parte de
    # CAMPOS_PROPUESTA: no altera el contrato científico.
    error_kind: str = ""
    pertinencia: str = ""
    cadena_causal: list[str] = field(default_factory=list)
    evidencia_citada: list[int] = field(default_factory=list)
    conocimiento_previo: list[str] = field(default_factory=list)
    incertidumbre: str = ""
    novedad: str = ""
    prueba: dict[str, Any] = field(default_factory=dict)
    comprobacion_restricciones: list[dict[str, Any]] = field(default_factory=list)
    critica: dict[str, Any] = field(default_factory=dict)
    model_requests: int = 0

    @property
    def es_propuesta(self) -> bool:
        """Una etiqueta declarada no sustituye el mecanismo ni la crítica completa."""
        respuesta = self.critica.get("respuesta")
        return (
            self.estado == ESTADO_PROPUESTA
            and isinstance(self.mecanismo, str)
            and bool(self.mecanismo.strip())
            and not self.error
            and self.critica.get("evaluation_status") == "CRITIQUED"
            and isinstance(respuesta, dict)
            and not validar_critica(respuesta)
        )

    def motivo_real(self) -> str:
        if self.error:
            return self.error
        if self.estado == ESTADO_PROPUESTA and (
            not isinstance(self.mecanismo, str) or not self.mecanismo.strip()
        ):
            return "PROPUESTA sin mecanismo"
        if self.estado == ESTADO_PROPUESTA and not self.es_propuesta:
            return "PROPUESTA sin crítica completa y aprobatoria"
        return self.error or ""

    def to_campos(self) -> dict[str, Any]:
        """La forma que inventar.py ya consume. Sin campos de mas."""
        estado = self.estado if self.es_propuesta else ESTADO_PENDIENTE
        return {
            "estado": estado,
            "hipotesis": self.hipotesis,
            "mecanismo": self.mecanismo if self.es_propuesta else "",
            "aportacion_por_tecnica": list(self.aportacion_por_tecnica)
            if self.es_propuesta
            else [],
            "supuestos": list(self.supuestos) if self.es_propuesta else [],
            "prueba_concreta": self.prueba_concreta if self.es_propuesta else "",
            "ruta_desbloqueo": self.ruta_desbloqueo if self.es_propuesta else "",
            "error": "" if self.es_propuesta else self.motivo_real(),
            "pertinencia": self.pertinencia,
            "cadena_causal": list(self.cadena_causal),
            "evidencia_citada": list(self.evidencia_citada),
            "conocimiento_previo": list(self.conocimiento_previo),
            "incertidumbre": self.incertidumbre,
            "novedad": self.novedad,
            "prueba": dict(self.prueba),
            "comprobacion_restricciones": list(self.comprobacion_restricciones),
            "critica": dict(self.critica),
        }


@runtime_checkable
class InterpreterPort(Protocol):
    """Lo unico que el pipeline necesita saber de un interprete."""

    backend: str
    provider: str

    def operativo(self) -> tuple[bool, str]:
        """(Listo para interpretar?, motivo real si no lo esta)."""
        ...

    def proponer(
        self,
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> InterpretationResult: ...


def pendiente(motivo: str, provenance: Provenance) -> InterpretationResult:
    """Construye un PENDIENTE honesto, con su motivo y su procedencia."""
    return InterpretationResult(estado=ESTADO_PENDIENTE, error=motivo, provenance=provenance)
