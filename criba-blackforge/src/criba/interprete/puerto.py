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

PROMPT_VERSION = "proponer-v1"
SCHEMA_VERSION = "propuesta-1"

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

    @property
    def es_propuesta(self) -> bool:
        """PROPUESTA solo si además trae mecanismo: el mecanismo es obligatorio.

        Un PROPUESTA sin mecanismo no describe nada accionable, asi que se
        degrada a pendiente con el motivo, en vez de emitir una propuesta vacia.
        """
        return self.estado == ESTADO_PROPUESTA and bool(self.mecanismo.strip())

    def motivo_real(self) -> str:
        if self.error:
            return self.error
        if self.estado == ESTADO_PROPUESTA and not self.mecanismo.strip():
            return "PROPUESTA sin mecanismo"
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
