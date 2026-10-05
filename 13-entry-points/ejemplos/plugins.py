"""Descubrimiento de entry points con ``importlib.metadata``.

Un entry point tiene tres partes (especificación de PyPA):

- **grupo**: qué tipo de objeto ofrece (``console_scripts``,
  ``act9_pipeline.modelos``, ...);
- **nombre**: cómo se llama dentro del grupo (``act9-entrenar``, ``svc``, ...);
- **referencia**: dónde está el objeto, con la forma ``modulo:objeto``.

Al instalar un paquete, el instalador (pip, uv, Poetry, conda) escribe sus
entry points en ``<paquete>.dist-info/entry_points.txt``. Este módulo lee esos
archivos de **todos** los paquetes instalados, así que encuentra tanto las
familias de modelos que trae ``act9_pipeline`` como las que agregue cualquier
otro paquete que se registre en el mismo grupo.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from importlib.metadata import EntryPoint, entry_points

#: Grupo en el que se registran las familias de modelos. La especificación
#: recomienda que empiece con el nombre del paquete que lo consume, para que
#: no choque con los grupos de otros proyectos.
GRUPO_MODELOS = "act9_pipeline.modelos"

#: Prefijo de las referencias de los comandos de este paquete.
_MODULO = "act9_pipeline"


@dataclass
class Familia:
    """Una familia de modelos cargada desde su entry point."""

    nombre: str
    referencia: str
    distribucion: str
    estimador: object = field(repr=False)
    espacio: dict = field(repr=False)
    descripcion: str = ""


def _origen(ep: EntryPoint) -> str:
    """Paquete (distribución) que declaró el entry point, con su versión."""
    dist = getattr(ep, "dist", None)
    if dist is None:
        return "?"
    return f"{dist.metadata['Name']} {dist.version}"


def _validar(spec: object) -> None:
    if not isinstance(spec, dict):
        raise TypeError("debe devolver un diccionario")
    faltan = {"estimador", "espacio"} - set(spec)
    if faltan:
        raise KeyError(f"faltan las llaves {sorted(faltan)}")
    validos = set(spec["estimador"].get_params())
    desconocidos = set(spec["espacio"]) - validos
    if desconocidos:
        raise ValueError(
            f"{type(spec['estimador']).__name__} no tiene los hiperparametros "
            f"{sorted(desconocidos)}"
        )


def descubrir_modelos() -> dict[str, Familia]:
    """Carga todas las familias registradas en ``act9_pipeline.modelos``.

    Se ordenan por nombre para que el espacio de búsqueda (y por lo tanto el
    resultado de la calibración) no dependa del orden en que el sistema de
    archivos devuelva los paquetes instalados.

    Un plugin roto **no** tumba el pipeline: se avisa y se omite. En
    producción eso evita que un paquete mal instalado detenga el entrenamiento
    de los demás modelos.
    """
    familias: dict[str, Familia] = {}
    for ep in sorted(entry_points(group=GRUPO_MODELOS), key=lambda e: e.name):
        if ep.name in familias:
            warnings.warn(
                f"El modelo '{ep.name}' esta registrado dos veces; se usa el de "
                f"{familias[ep.name].distribucion} y se ignora el de {_origen(ep)}.",
                stacklevel=2,
            )
            continue
        try:
            spec = ep.load()()
            _validar(spec)
        except Exception as exc:  # cualquier fallo del plugin se reporta igual
            warnings.warn(
                f"Se omite el plugin '{ep.name}' ({ep.value}): {exc}", stacklevel=2
            )
            continue
        familias[ep.name] = Familia(
            nombre=ep.name,
            referencia=ep.value,
            distribucion=_origen(ep),
            estimador=spec["estimador"],
            espacio=spec["espacio"],
            descripcion=spec.get("descripcion", ""),
        )
    return familias


def comandos_del_paquete() -> list[EntryPoint]:
    """Los ``console_scripts`` que instaló este paquete, ordenados por nombre."""
    return sorted(
        (
            ep
            for ep in entry_points(group="console_scripts")
            if ep.value.split(":")[0].split(".")[0] == _MODULO
        ),
        key=lambda e: e.name,
    )
