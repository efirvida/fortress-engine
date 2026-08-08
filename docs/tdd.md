# TDD — Documento de Diseño Técnico del Motor de Grafo Semántico

**Versión**: 1.0
**Tipo**: Technical Design Document
**Idioma**: Español
**Depende de**: PRD v2.0, GDD v1.0, Event System #13

---

## 1. Introducción

### 1.1 Propósito y Relación con Otros Documentos

Este documento define **cómo** se implementa el Motor de Grafo Semántico. Es el documento que un desarrollador lee para escribir código Python. Describe la estructura de clases, firmas de métodos, esquemas de base de datos, flujos de ejecución y estrategia de testing.

| Documento | Rol |
|-----------|-----|
| **PRD** (`prd.md`) | Qué construimos, por qué, para quién. Define la visión, alcance y arquitectura conceptual. |
| **GDD** (`gdd.md`) | Puente entre PRD y TDD. Describe el diseño con detalle para diseñadores y desarrolladores. Responde WHAT y WHY. |
| **TDD** (este documento) | **Cómo se implementa.** Estructura de clases Python, esquema SQLite, API de plugins, flujos de carga, testing. Responde HOW. |
| **Event System** (`13-event-system.md`) | Especificación del bus de eventos síncrono, taxonomía de eventos y contratos motor-UI. Referenciado por este TDD. |

### 1.2 Convenciones

- Los nombres de módulos, clases y archivos en este documento son **sugerencias**. El implementador puede ajustarlos siempre que se preserve la arquitectura en capas, las interfaces públicas (métodos y firmas) y la separación de responsabilidades.
- Todas las firmas de métodos usan type hints de Python (PEP 484).
- Las clases de datos del núcleo del motor usan `@dataclass` de stdlib. Pydantic se reserva exclusivamente para validación de archivos YAML durante la carga del mundo.
- Los ejemplos de código asumen Python 3.11+.
- El código del motor se escribe en inglés (nombres de clases, métodos, variables). Los datos del mundo (YAML) y el texto del juego están en español.

---

## 2. Estructura del Proyecto Python

```
fortress-engine/
├── pyproject.toml
├── README.md
├── src/
│   └── fortress_engine/
│       ├── __init__.py
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── orchestrator.py
│       │   ├── graph.py
│       │   ├── state.py
│       │   ├── operators.py
│       │   ├── goal_evaluator.py
│       │   └── episode_manager.py
│       ├── entities/
│       │   ├── __init__.py
│       │   ├── entity.py
│       │   ├── components.py
│       │   └── loader.py
│       ├── events/
│       │   ├── __init__.py
│       │   ├── event_bus.py
│       │   └── event_types.py
│       ├── persistence/
│       │   ├── __init__.py
│       │   ├── repository.py
│       │   ├── sqlite_repository.py
│       │   ├── event_log.py
│       │   └── models.py
│       ├── plugins/
│       │   ├── __init__.py
│       │   ├── parser_interface.py
│       │   ├── narrator_interface.py
│       │   ├── classic_parser.py
│       │   └── template_narrator.py
│       └── cli/
│           ├── __init__.py
│           └── main.py
├── tests/
│   ├── test_engine/
│   │   ├── test_orchestrator.py
│   │   ├── test_graph.py
│   │   ├── test_operators.py
│   │   └── test_goal_evaluator.py
│   ├── test_entities/
│   │   └── test_loader.py
│   ├── test_events/
│   │   └── test_event_bus.py
│   ├── test_persistence/
│   │   └── test_event_sourcing.py
│   └── test_integration/
│       └── test_walkthrough.py
├── worlds/
│   └── fortaleza/
│       ├── world.yaml
│       ├── episodes/
│       ├── shared/
│       ├── episode-01/
│       │   ├── rooms/
│       │   ├── items/
│       │   ├── npcs/
│       │   ├── actions/
│       │   └── macros/
│       ├── episode-02/
│       │   ├── rooms/
│       │   ├── items/
│       │   ├── npcs/
│       │   ├── actions/
│       │   └── macros/
│       └── narrator/
└── docs/                             # Documentación existente
```

### 2.1 Justificación de la Estructura

- **`src/fortress_engine/`** — layout `src/` para evitar importación accidental del código fuente sin instalar. Sigue PEP 517.
- **`engine/`** — núcleo del motor: grafo dual, operadores, estado, orquestador, episodios, goal evaluator. Ningún módulo aquí conoce detalles de UI ni de mundos concretos.
- **`entities/`** — modelo de entidad, validación de componentes, cargador YAML con Pydantic. Separado del motor porque el motor solo consume entidades ya validadas.
- **`events/`** — bus de eventos síncrono y tipos de evento. Implementación según `13-event-system.md`.
- **`persistence/`** — repositorio abstracto, implementación SQLAlchemy/SQLite, event sourcing log, ORM models. Acceso exclusivo a través de la interfaz `WorldStateRepository`.
- **`plugins/`** — interfaces ABC para parser y narrador, implementaciones V1 (clásico y plantillas). Plugins futuros (IA) se agregan aquí.
- **`cli/`** — punto de entrada para terminal. Lee stdin, escribe stdout.
- **`worlds/fortaleza/`** — datos del mundo de validación. Estructura multi-archivo por entidad según PRD 7.5 y GDD 3.1.

---

## 3. Modelo de Datos (Clases Python)

### 3.1 Entity

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Entity:
    entity_id: str
    type: str                      # "item" | "room" | "npc" | "player" | "container" | "door"
    name: str
    components: dict[str, Any]     # key-value component dictionary
    spatial_anchor: str | None     # entity_id of container, or None (null = destroyed/limbo)
```

**Notas de implementación**:
- `spatial_anchor == None` es el estado "destruido" o "en limbo" (ver patrón Limbo Room, PRD 4.3).
- No hay herencia de clases para tipos de entidad. El comportamiento se define por componentes y por Hiper-Aristas (ver PRD 4.1 y GDD 2.1).
- Los nombres de tipos están en inglés (`"item"`, `"room"`, `"npc"`, `"player"`, `"container"`, `"door"`) para consistencia con el código Python.

### 3.2 HyperEdge

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Clique:
    """Clique de Participación de una Hiper-Arista (PRD 4.3, GDD 2.3)."""
    subject: str | None           # entity_id del ejecutor; "player" = protagonista activo
    verb: str                     # verbo que dispara esta Hiper-Arista
    target: str | None            # entity_id del objetivo; "*" = any
    instrument: str | None        # entity_id del instrumento requerido; "*" = any; None = ninguno
    context: str | None           # entity_id contextual (ej: segundo protagonista)
    instrument_not: str | None    # el instrumento NO debe ser este entity_id
    instrument_any: bool = False  # True = cualquier ítem portable es válido como instrumento
    flag: str | None = None       # requiere bandera activa para formar clique
    flag_not: str | None = None   # requiere bandera inactiva para formar clique
    component: dict[str, str] | None = None  # {component_name: expected_value} — predicado de componente


@dataclass
class HyperEdge:
    """Hiper-Arista: acción reificada en el Grafo Micro (PRD 4.3, GDD 2.3)."""
    hyper_edge_id: str
    name: str                     # nombre descriptivo humano (debugging)
    priority: int                 # mayor = se evalúa primero
    clique: Clique                # Clique de Participación requerida
    operators: list[dict[str, Any]]  # secuencia de operadores atómicos (dicts, se castean a tipos concretos al ejecutar)
    output: str | None            # texto emitido como action_output al ejecutarse
```

**Notas de implementación**:
- `subject == "player"` es un valor especial: el motor lo resuelve al `active_protagonist_id` en tiempo de validación. Cualquier otro valor se interpreta como un `entity_id` literal.
- `target == "*"` e `instrument == "*"` son comodines: matchean cualquier entidad del tipo esperado en la room o inventario.
- La evaluación de prioridad es descendente (mayor primero). El PRD 4.3 establece que esto reemplaza la lógica `if/else` — basta con definir múltiples Hiper-Aristas con el mismo par `(verb, target)` y distintas prioridades.
- `operators` se almacena como `list[dict]` en el dataclass porque los datos vienen de YAML. El motor los convierte a los tipos concretos (`TransferOp`, `TransformOp`, etc.) al ejecutarlos.

### 3.3 MacroEdge

```python
from dataclasses import dataclass

@dataclass
class MacroEdge:
    """Arista del Grafo Macro: conexión entre anchors (PRD 4.2, GDD 2.2).

    Los predicados son GENÉRICOS y se evalúan de forma uniforme; NO existe
    connection_type. El creador del mundo decide la semántica según qué
    predicados defina. Una arista sin predicados siempre es transitable.
    """
    macro_edge_id: str
    from_anchor: str                 # entity_id del anchor origen
    to_anchor: str                   # entity_id del anchor destino
    direction: str                   # "bidirectional" | "unidirectional"
    passage_name: str                # nombre que el parser usa para matchear comandos de movimiento
    passage_description: str = ""    # texto mostrado al examinar el pasaje
    # Predicados genéricos — semántica decidida por el creador del mundo
    question: str | None = None      # texto de acertijo (narración, no se evalúa)
    requires_text: str | None = None # texto que el jugador debe decir para desbloquear (password/riddle)
    requires_item: str | None = None # ítem que debe estar en el inventario (danger)
    forbids_item: str | None = None  # ítem que NO debe estar en el inventario (danger_inverse)
    requires_flag: str | None = None # bandera que debe estar activa (conditional)
    forbids_flag: str | None = None  # bandera que debe estar inactiva/ausente (conditional)
    death_message: str | None = None # fatal si un predicado falla; si no → bloqueado
    open: bool = True                # estado actual del pasaje; False = cerrado (texto no resuelto)
```

**Notas de implementación**:
- Las aristas con `requires_text` arrancan con `open: False`. Se abren cuando el jugador dice el texto correcto (coincidencia insensible a mayúsculas y tildes).
- Una arista sin predicados tiene `open: True` siempre.
- El campo `open` es mutable — se modifica durante el juego (a diferencia del resto de campos que son inmutables después de la carga).
- `death_message` es el único discriminador entre fatal y bloqueado; el motor nunca interpreta nombres de tipos de conexión.

### 3.4 Operators

```python
from dataclasses import dataclass
from typing import Any, Union

@dataclass
class TransferOp:
    """TRANSFER: Mueve una entidad de un contenedor a otro (PRD 4.4, GDD 2.4)."""
    type: str = "TRANSFER"
    entity: str                              # entity_id a mover
    from_container: str | None = None        # contenedor origen (None = limbo/spawn)
    to_container: str | None = None          # contenedor destino (None = destruir)


@dataclass
class TransformOp:
    """TRANSFORM: Cambia un componente de una entidad (PRD 4.4, GDD 2.4)."""
    type: str = "TRANSFORM"
    entity: str                              # entity_id a transformar
    component: str                           # nombre del componente a modificar
    old_value: Any                           # valor esperado actual (validación previa)
    new_value: Any                           # nuevo valor a establecer


@dataclass
class CombineOp:
    """COMBINE: Destruye entradas y produce una entidad de salida (PRD 4.4, GDD 2.4)."""
    type: str = "COMBINE"
    input_entities: list[str]                # entity_ids de las entradas (se destruyen)
    output_entity: str                       # entity_id de la salida (debe existir, típicamente en _limbo)


@dataclass
class FlagOp:
    """FLAG: Establece o limpia una bandera global (PRD 4.4, GDD 2.4)."""
    type: str = "FLAG"
    flag: str                                # nombre de la bandera
    value: bool                              # valor a establecer


@dataclass
class TeleportOp:
    """TELEPORT: Cambia el anclaje espacial de una entidad (PRD 4.4, GDD 2.4)."""
    type: str = "TELEPORT"
    entity: str                              # entity_id a teletransportar
    from_anchor: str | None = None           # anchor de origen (para logging/validación; None si es desde limbo)
    to_anchor: str                           # anchor de destino


Operator = Union[TransferOp, TransformOp, CombineOp, FlagOp, TeleportOp]
```

**Notas de implementación**:
- Los operadores se construyen a partir de los `dicts` en `HyperEdge.operators`. El loader YAML produce dicts; el motor los convierte usando una factory function `operator_from_dict(data: dict) -> Operator`.
- La validación de peso en `TransferOp` se aplica solo cuando `to_container` es el `entity_id` del protagonista activo (ver PRD 4.4).
- `CombineOp.output_entity` debe ser una entidad que existe en el grafo, típicamente con `spatial_anchor: "_limbo"` (ver patrón Limbo Room, GDD 2.4).
- El orden de ejecución es secuencial y transaccional: si un operador falla, los anteriores no se revierten porque el grafo aún no mutó. Pero sí se detiene la secuencia — los operadores posteriores no se ejecutan.

### 3.5 WorldState

```python
from dataclasses import dataclass, field

@dataclass
class WorldState:
    """Estado global del mundo en un instante dado (PRD 4.5, GDD 2.5)."""
    entities: dict[str, 'Entity']                         # entity_id → Entity
    flag_book: dict[str, bool]                            # flag_name → value
    player_controlled_entities: list[str]                 # entity_ids controlables por el jugador
    active_protagonist_id: str                            # protagonista con foco de entrada actual
    current_episode_id: str                               # episodio activo
    turn_number: int = 0                                  # turno actual

    def get_entity(self, entity_id: str) -> 'Entity':
        """Retorna la entidad por ID. Lanza KeyError si no existe."""
        return self.entities[entity_id]

    def set_flag(self, flag: str, value: bool) -> None:
        """Establece una bandera global."""
        self.flag_book[flag] = value

    def get_flag(self, flag: str) -> bool:
        """Retorna el valor de una bandera. False si no existe."""
        return self.flag_book.get(flag, False)

    def to_dict(self) -> dict:
        """Serializa el estado completo a un diccionario JSON-compatible."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> 'WorldState':
        """Deserializa un diccionario a un WorldState."""
        ...
```

**Notas de implementación**:
- `to_dict()` y `from_dict()` son necesarios para snapshots de estado (persistencia) y para exponer el estado a plugins. Ver PRD 4.5.
- `player_controlled_entities` es siempre una lista, incluso con un solo protagonista. El motor itera sobre esta colección sin asumir singleton (restricción #8 del PRD).
- Las entidades se almacenan en un diccionario plano por `entity_id`. No hay jerarquía de contenedores — el anclaje espacial es un campo de la entidad.

### 3.6 EngineEvent

```python
from dataclasses import dataclass
from uuid import UUID
from typing import Any

@dataclass(frozen=True)
class EngineEvent:
    """Evento inmutable emitido por el motor (Event System 3.1)."""
    event_id: UUID                    # identificador único
    type: str                         # tipo del evento (taxonomía en Event System 2)
    turn_number: int                  # turno en que se emitió
    timestamp: float                  # time.monotonic() para ordenamiento
    payload: dict[str, Any]           # datos específicos del tipo de evento
    protagonist_id: str | None = None # protagonista relacionado (None = global)
    episode_id: str | None = None     # episodio actual
```

**Notas de implementación**:
- `frozen=True`: los eventos son inmutables una vez creados. Crítico para event sourcing.
- `timestamp` usa `time.monotonic()`, no `time.time()`. Ver justificación en Event System 3.1.
- `payload` usa `dict[str, Any]` con contratos implícitos por tipo de evento documentados en Event System 2.

### 3.7 ParsedCommand

```python
from dataclasses import dataclass

@dataclass
class ParsedCommand:
    """Resultado estructurado del parser (PRD 5, GDD 2.5)."""
    subject: str | None             # entity_id del sujeto (normalmente el protagonista activo)
    verb: str                       # verbo en minúsculas y normalizado
    target: str | None              # entity_id del objetivo
    context: str | None = None      # entity_id contextual
    instrument: str | None = None   # entity_id del instrumento
    text: str | None = None         # texto hablado (DICIENDO/RESPONDIENDO)
```

### 3.8 Episode y GoalConditions

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class GoalCondition:
    """Una condición atómica de victoria (PRD 4.9, GDD 2.7)."""
    type: str                       # "entity_in_room" | "entity_not_in_room" | "entity_dead"
                                    # | "flag_is_set" | "flag_is_not_set" | "entity_has_component"
    params: dict[str, Any]          # parámetros según el tipo (entity, room, flag, component, value)


@dataclass
class GoalConditions:
    """Árbol de condiciones de victoria con composición and/or (PRD 4.9)."""
    conditions: list[GoalCondition | dict[str, Any]]  # puede contener {"and": [...]} o {"or": [...]}
    output: str                                          # texto de victoria
    side_effects: list[dict] = field(default_factory=list)  # efectos adicionales al cumplir el goal


@dataclass
class CarryOver:
    """Reglas de continuidad entre episodios (PRD 4.9, GDD 2.7)."""
    inventory: list[str] = field(default_factory=list)  # ["*"] = todo, ["item_x"] = específicos, [] = nada
    flags: list[str] = field(default_factory=list)      # ["*"] = todas, ["flag_a"] = específicas, [] = nada


@dataclass
class Episode:
    """Definición de un episodio del mundo (PRD 4.9, GDD 2.7)."""
    id: str                          # identificador único (ej: "episode-01")
    name: str                        # nombre descriptivo
    order: int                       # orden secuencial
    description: str | None          # texto de introducción
    requires: list[str]              # IDs de episodios que deben completarse antes. [] = independiente.
    start_anchor: str                # entity_id de la anchor inicial
    goal: GoalConditions             # condiciones de victoria
    carry_over: CarryOver            # reglas de continuidad
```

---

## 4. Diseño de Módulos

### 4.1 `engine/orchestrator.py` — Orquestador de Turnos

**Responsabilidad**: Bucle principal del motor. Coordina input del jugador → parseo → validación de Hiper-Aristas → ejecución de operadores → evaluación de goal → emisión de eventos. Es el punto de entrada del runtime del motor.

**Clases principales**:

- `TurnOrchestrator` — bucle de juego. Lee input, orquesta las fases, mantiene la referencia al estado.

**Dependencias**:
- `engine/graph.py` — `DualGraphEngine` (para buscar y validar Hiper-Aristas)
- `engine/state.py` — `WorldState` (para leer y mutar estado)
- `engine/operators.py` — funciones de operadores atómicos
- `engine/goal_evaluator.py` — `GoalEvaluator`
- `engine/episode_manager.py` — `EpisodeManager`
- `events/event_bus.py` — `EventBus`
- `plugins/parser_interface.py` — `ParserInterface`
- `plugins/narrator_interface.py` — `NarratorInterface`

**Interfaz pública**:

```python
class TurnOrchestrator:
    def __init__(
        self,
        state: WorldState,
        graph: DualGraphEngine,
        event_bus: EventBus,
        parser: ParserInterface,
        narrator: NarratorInterface,
        goal_evaluator: GoalEvaluator,
        episode_manager: EpisodeManager,
        repository: WorldStateRepository | None = None,
        save_system: EventSourcingSaveSystem | None = None,
        vocabulary: 'Vocabulary | None' = None,
    ) -> None:
        """Inicializa el orquestador con todas sus dependencias inyectadas."""
        ...

    def execute_turn(self, raw_text: str) -> None:
        """
        Ejecuta un ciclo completo de turno (PRD 4.6, GDD 2.5).
        Flujo:
          1. emit turn_started
          2. parser.parse(raw_text, world_state) → ParsedCommand
          3. Comandos de sistema: guardar, cargar, terminar, cambiar protagonista
          4. emit input_received
          5. graph.get_hyper_edges_for_verb(room, verb) → candidates (ordenados por prioridad)
          6. Para cada candidate: _validate_clique() → si OK, break
          7. Si ninguna clique: emit error_output, retornar
          8. emit action_attempted
          9. _execute_operators(selected.operators) → cada op exitoso emite su evento de cambio
          10. emit action_output (si selected.output no vacío)
          11. emit action_resolved
          12. _evaluate_goal() → si goal cumplido: transición de episodio o game_completed
          13. Verificar player_dead → game_over
          14. emit turn_ended
        """
        ...

    # Private methods
    def _validate_clique(
        self, hyper_edge: HyperEdge, parsed: ParsedCommand, state: WorldState
    ) -> bool:
        """Valida si la Clique de Participación de la Hiper-Arista se forma (PRD 4.3)."""
        ...

    def _execute_operators(
        self, operators: list[dict], state: WorldState
    ) -> list[str]:
        """
        Ejecuta la secuencia de operadores atómicos transaccionalmente.
        Retorna la lista de tipos de operadores ejecutados exitosamente.
        Si un operador falla, detiene la secuencia y emite error_output.
        """
        ...

    def _evaluate_goal(self) -> bool:
        """Evalúa condiciones de victoria del episodio. Retorna True si se cumplen."""
        ...
```

**Manejo de comandos de sistema** (PRD 4.6):

El orquestador intercepta los siguientes comandos antes del parseo normal. Las palabras de reconocimiento vienen del `Vocabulary` del mundo (`system_commands` en `shared/vocabulary.yaml`); las palabras listadas aquí son los defaults en código (`DEFAULT_SYSTEM_COMMANDS`) cuando el mundo no las declara. Lo mismo aplica a los verbos de movimiento (`movement_verbs`, default `{"ir", "abrir"}`):
- `"GUARDAR <slot>"` → el orquestador emite `game_saved({ save_slot })`. La persistencia del snapshot la hace `EventSourcingSaveSystem._on_game_saved` vía su `state_provider`.
- `"CARGAR <slot>"` → delega en `repository.load_latest_snapshot()` + replay de event log + emite `game_loaded`.
- `"TERMINAR"` → emite `game_over({ reason: "player_quit" })`.
- `"CAMBIAR A <nombre>"` → busca entidad `player_controlled` con ese nombre, actualiza `active_protagonist_id`, emite `protagonist_switched` (comando prefijo — se recorta la surface).
- `"ESPERAR"` → no-op (pasa el turno).
- `"GRUPO"` → emite `protagonists_listed`.

### 4.2 `engine/graph.py` — Motor de Grafo Dual

**Responsabilidad**: Construye y consulta el Grafo Dual (Macro y Micro). Almacena las estructuras de grafo en memoria y provee métodos para búsqueda de aristas, validación de cliques y pathfinding.

**Clases principales**:

- `DualGraphEngine` — contiene el Grafo Macro (rooms + macro edges) y los Grafos Micro por room (Hiper-Aristas indexadas por verbo).

**Dependencias**:
- `entities/entity.py` — `Entity`
- `engine/state.py` — `WorldState`

**Interfaz pública**:

```python
class DualGraphEngine:
    def __init__(self) -> None:
        self._anchors: dict[str, Entity] = {}                  # anchor_id → Entity
        self._macro_edges: dict[str, list[MacroEdge]] = {}     # from_anchor_id → [MacroEdge]
        self._hyper_edges: dict[str, dict[str, list[HyperEdge]]] = {}  # anchor_id → { verb: [HyperEdge] }

    def add_anchor(self, anchor: Entity) -> None:
        """Registra una anchor como Nodo del Grafo Macro."""
        ...

    def add_macro_edge(self, edge: MacroEdge) -> None:
        """Registra una arista del Grafo Macro."""
        ...

    def add_hyper_edge(self, anchor_id: str, hyper_edge: HyperEdge) -> None:
        """Registra una Hiper-Arista en el Grafo Micro de una anchor."""
        ...

    def build_macro_graph(
        self, anchors: list[Entity], macro_edges: list[MacroEdge]
    ) -> None:
        """Construye el grafo completo desde listas de anchors y aristas macro."""
        ...

    def get_edges_from_anchor(self, anchor_id: str) -> list[MacroEdge]:
        """Retorna las aristas Macro que salen de una anchor."""
        return self._macro_edges.get(anchor_id, [])

    def get_macro_edge_by_passage_name(
        self, anchor_id: str, passage_name: str
    ) -> MacroEdge | None:
        """Busca una arista Macro por nombre de pasaje en una anchor."""
        ...

    def get_hyper_edges_for_verb(
        self, anchor_id: str, verb: str
    ) -> list[HyperEdge]:
        """
        Retorna Hiper-Aristas del Grafo Micro de la anchor que matchean el verbo,
        ordenadas por prioridad descendente.
        """
        ...

    def validate_clique(
        self, hyper_edge: HyperEdge, parsed: ParsedCommand, state: WorldState
    ) -> bool:
        """
        Verifica si la Clique de Participación de la Hiper-Arista se satisface
        con el estado actual del mundo (PRD 4.3, GDD 2.3).

        Reglas de validación (GDD 2.3):
        - subject: debe ser el protagonista activo o estar en la misma anchor que target.
        - verb: debe coincidir exactamente.
        - target: debe estar en la misma anchor que subject, o en el inventario de subject.
          "*" = any entity in anchor or inventory.
        - instrument: si se especifica, debe estar en inventario de subject o en la anchor.
          "*" = cualquier ítem portable.
        - context: misma regla que target.
        - instrument_not: el instrumento NO debe ser este. Si lo es, clique no se forma.
        - instrument_any: True = cualquier ítem portable en inventario satisface instrument.
        - flag: la bandera debe estar activa (True).
        - flag_not: la bandera debe estar inactiva (False o inexistente).
        - component: {key: value} → entity.components[key] == value.
        """
        ...

    def validate_macro_edge(
        self, edge: MacroEdge, state: WorldState
    ) -> 'MacroGateResult':
        """
        Evalúa los predicados de una arista Macro (GDD 2.2).
        Retorna un `MacroGateResult` (dataclass congelada):
        - is_valid: True si todas las gates pasaron.
        - is_fatal: True si alguna gate falló Y `edge.death_message` está presente.
        - gate_code: uno de los 5 códigos planos cuando es inválido
          (`text_closed`, `requires_item`, `forbids_item`, `requires_flag`,
          `forbids_flag`); cadena vacía si es válido.
        - data: siempre incluye `passage_name` + el predicado que falló.
        El orquestador enruta muerte-vs-bloqueo vía `is_fatal` (sin comparación
        de strings).
        """
        ...

    def resolve_special_values(
        self, clique_value: str | None, state: WorldState
    ) -> str | None:
        """
        Resuelve valores especiales en la clique:
        - "player" → active_protagonist_id
        - "*" → se mantiene como "*" (el validador de clique lo maneja)
        - Otro valor → se retorna tal cual (entity_id literal)
        """
        ...
```

**Notas de implementación**:
- Las Hiper-Aristas se indexan por `(anchor_id, verb)` para búsqueda O(1).
- El ordenamiento por prioridad descendente ocurre al insertar o al consultar. Si se hace al insertar, se usa `bisect` para mantener la lista ordenada.
- El motor valida que no existan dos Hiper-Aristas con el mismo `(verb, target, priority)` en la misma anchor. Si las hay, emite una advertencia (PRD 4.8).

### 4.3 `engine/operators.py` — Operadores Atómicos

**Responsabilidad**: Implementación de los 5 operadores atómicos. Cada operador es una función pura que toma `(WorldState, op_data)` y retorna `(OperatorResult)`. Las funciones no emiten eventos — el orquestador es responsable de emitir eventos según el resultado.

**Dependencias**:
- `engine/state.py` — `WorldState`
- `entities/entity.py` — `Entity`

**Interfaz pública**:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperatorResult:
    success: bool
    code: str | None = None                            # código plano de falla (None en éxito)
    data: dict[str, Any] = field(default_factory=dict)  # datos estructurados para el narrador
    events_payload: dict[str, Any] | None = None  # datos para que el orquestador emita eventos


def execute_transfer(
    state: WorldState, op: TransferOp, protagonist_id: str
) -> OperatorResult:
    """
    TRANSFER: Mueve entity de from_container a to_container (PRD 4.4, GDD 2.4).

    Validaciones:
    - Si to_container es el protagonista activo:
      1. Si entity.weight > player.max_weight → error_code: "not_portable" + data.
      2. Si sum(inventory_items.weight) + entity.weight > player.max_weight → error_code: "too_heavy" + data.
      3. Si entity.portable == false → error: entidad no portable.
    - entity debe existir en from_container.

    Postcondiciones:
    - entity.spatial_anchor = to_container
    - Si to_container es None, la entidad se marca como destruida.
    """
    ...


def execute_transform(
    state: WorldState, op: TransformOp
) -> OperatorResult:
    """
    TRANSFORM: Cambia un componente de una entidad (PRD 4.4, GDD 2.4).

    Validaciones:
    - entity existe.
    - entity.components[component] == old_value (protege transformaciones duplicadas).

    Postcondiciones:
    - entity.components[component] = new_value.
    """
    ...


def execute_combine(
    state: WorldState, op: CombineOp, anchor_id: str
) -> OperatorResult:
    """
    COMBINE: Destruye inputs y produce output (PRD 4.4, GDD 2.4).

    Validaciones:
    - Todas las input_entities existen.
    - output_entity existe en el grafo.

    Postcondiciones:
    - input_entities: TRANSFER a null (destruidas).
    - output_entity: TELEPORT desde su ubicación actual a anchor_id.
    """
    ...


def execute_flag(
    state: WorldState, op: FlagOp
) -> OperatorResult:
    """
    FLAG: Establece una bandera global (PRD 4.4, GDD 2.4).

    Sin validaciones previas. Siempre exitoso.

    Postcondiciones:
    - state.flag_book[flag] = value.
    """
    ...


def execute_teleport(
    state: WorldState, op: TeleportOp
) -> OperatorResult:
    """
    TELEPORT: Cambia el anclaje espacial de una entidad (PRD 4.4, GDD 2.4).

    Validaciones:
    - entity existe.
    - to_anchor existe en el grafo (las anchors del grafo se pasan como parámetro o se consultan del state).

    Postcondiciones:
    - entity.spatial_anchor = to_anchor.
    - Si la entidad es una room (no aplica para TELEPORT, pero por completitud):
      - Marca room.visited = True.
    """
    ...


def execute_operator(
    state: WorldState, op_data: dict, protagonist_id: str, graph: 'DualGraphEngine'
) -> OperatorResult:
    """
    Factory: despacha al operador concreto según op_data["type"].
    Convierte el dict al dataclass correspondiente y llama a la función.
    """
    ...
```

**Notas de implementación**:
- Los operadores son funciones puras sin efectos secundarios fuera de `WorldState`. No conocen al EventBus.
- El orquestador recibe el `OperatorResult` y emite los eventos correspondientes (`entity_transferred`, `entity_transformed`, etc.).
- Las validaciones de peso (`not_portable`, `too_heavy`), `portable == false` y las precondiciones de transform/combine/teleport pueden fallar: `OperatorResult` transporta `code` + `data` planos y el narrador renderiza el texto (`DEFAULT_SPANISH_MESSAGES`). `error_message` fue removido (spec de operadores atómicos).

### 4.4 `engine/state.py` — Contenedor de Estado

**Responsabilidad**: `WorldState` es el contenedor mutable del estado global. Provee métodos de acceso y mutación para entidades y banderas. También incluye serialización/deserialización para snapshots.

**Dependencias**:
- `entities/entity.py` — `Entity`

**Interfaz pública**:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldState:
    entities: dict[str, Entity] = field(default_factory=dict)
    flag_book: dict[str, bool] = field(default_factory=dict)
    player_controlled_entities: list[str] = field(default_factory=list)
    active_protagonist_id: str = ""
    current_episode_id: str = ""
    turn_number: int = 0

    def get_entity(self, entity_id: str) -> Entity:
        """Retorna la entidad por ID. Lanza KeyError si no existe."""
        if entity_id not in self.entities:
            raise KeyError(f"Entity '{entity_id}' not found")
        return self.entities[entity_id]

    def entity_exists(self, entity_id: str) -> bool:
        """Retorna True si la entidad existe."""
        return entity_id in self.entities

    def set_flag(self, flag: str, value: bool) -> None:
        """Establece una bandera global."""
        self.flag_book[flag] = value

    def get_flag(self, flag: str) -> bool:
        """Retorna el valor de una bandera. False si no existe."""
        return self.flag_book.get(flag, False)

    def get_entities_in_container(self, container_id: str) -> list[Entity]:
        """Retorna todas las entidades cuyo spatial_anchor == container_id."""
        return [
            e for e in self.entities.values()
            if e.spatial_anchor == container_id
        ]

    def get_player_inventory(self, protagonist_id: str) -> list[Entity]:
        """Retorna las entidades en el inventario de un protagonista."""
        return self.get_entities_in_container(protagonist_id)

    def get_inventory_weight(self, protagonist_id: str) -> int:
        """Retorna la suma de pesos de todos los ítems en el inventario del protagonista."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serializa el estado completo a un diccionario JSON-compatible."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'WorldState':
        """Deserializa un diccionario a un WorldState. Lanza ValueError si los datos son inválidos."""
        ...
```

### 4.5 `engine/goal_evaluator.py` — Evaluador de Condiciones de Victoria

**Responsabilidad**: Evalúa el árbol de condiciones de victoria de un episodio contra el `WorldState` actual. Soporta los 6 tipos de condiciones atómicas + composición `and`/`or` anidada (PRD 4.9, GDD 2.7).

**Dependencias**:
- `engine/state.py` — `WorldState`

**Interfaz pública**:

```python
class GoalEvaluator:
    def __init__(self, conditions: GoalConditions) -> None:
        """Inicializa el evaluador con las condiciones de victoria del episodio."""
        self._conditions = conditions

    def check(self, state: WorldState) -> bool:
        """
        Evalúa si se cumplen las condiciones de victoria.
        Soporta las condiciones definidas en PRD 4.9 y su composición and/or.

        Tipos de condición:
        - entity_in_room: entity.spatial_anchor == room
        - entity_not_in_room: entity.spatial_anchor != room (incluye entity destruida)
        - entity_dead: entity.spatial_anchor is None (TRANSFER a null)
        - flag_is_set: state.get_flag(flag) == True
        - flag_is_not_set: state.get_flag(flag) == False
        - entity_has_component: entity.components[component] == value

        Composición:
        - {"and": [cond1, cond2, ...]} → todas deben cumplirse
        - {"or": [cond1, cond2, ...]} → al menos una debe cumplirse
        """
        ...

    def _evaluate_condition(self, condition: GoalCondition, state: WorldState) -> bool:
        """Evalúa una condición atómica."""
        ...

    def _evaluate_composite(self, node: dict[str, Any], state: WorldState) -> bool:
        """Evalúa un nodo compuesto (and/or) recursivamente."""
        ...

    @property
    def output(self) -> str:
        """Texto de victoria."""
        return self._conditions.output

    @property
    def side_effects(self) -> list[dict]:
        """Efectos adicionales al cumplir el goal."""
        return self._conditions.side_effects
```

### 4.6 `engine/episode_manager.py` — Gestor de Episodios

**Responsabilidad**: Carga y gestiona la transición entre episodios. Controla qué episodios están disponibles, aplica carry_over, y coordina la carga/descarga de grafos por episodio (PRD 4.9, GDD 2.7).

**Dependencias**:
- `engine/state.py` — `WorldState`
- `engine/graph.py` — `DualGraphEngine`
- `entities/loader.py` — `EntityLoader`
- `events/event_bus.py` — `EventBus`

**Interfaz pública**:

```python
class EpisodeManager:
    def __init__(
        self,
        episodes: list[Episode],
        world_path: str,
        event_bus: EventBus,
    ) -> None:
        """
        Inicializa el gestor con la lista de episodios del mundo.
        Marca como 'available' aquellos cuyo requires == [].
        """
        ...

    def start_episode(self, episode_id: str, state: WorldState) -> DualGraphEngine:
        """
        Carga el grafo del episodio desde archivos YAML.
        - Carga rooms, items, npcs, actions, macros del directorio del episodio.
        - TELEPORT del protagonista a start_anchor.
        - Emite episode_started.
        - Retorna el DualGraphEngine construido.
        """
        ...

    def transition_to_next(
        self, current_episode_id: str, state: WorldState, current_graph: DualGraphEngine
    ) -> DualGraphEngine | None:
        """
        Transiciona al próximo episodio (PRD 4.9, GDD 2.7).
        - Aplica carry_over (inventario y flags).
        - Descarga el grafo actual.
        - Carga el grafo del próximo episodio.
        - Emite episode_transition, episode_started.
        - Retorna el nuevo DualGraphEngine, o None si no hay próximo episodio.
        """
        ...

    def apply_carry_over(self, carry_over: CarryOver, state: WorldState) -> None:
        """
        Aplica reglas de carry_over al estado actual:
        - inventory: ["*"] transfiere todos los ítems del inventario.
                     ["item_x", ...] transfiere ítems específicos.
                     [] no transfiere nada.
        - flags: ["*"] transfiere todas las banderas.
                 ["flag_a", ...] transfiere banderas específicas.
                 [] no transfiere nada.
        """
        ...

    def get_available_episodes(self) -> list[Episode]:
        """Retorna los episodios disponibles para iniciar."""
        ...

    def unload_graph(self, graph: DualGraphEngine) -> None:
        """Libera la memoria del grafo actual."""
        ...
```

**Notas de implementación**:
- La gestión de memoria es explícita: el grafo del episodio completado se descarta completamente antes de cargar el siguiente. Esto evita conflictos de `entity_id` entre episodios (PRD 4.9).
- El `carry_over` de Fortaleza es `{inventory: [], flags: []}` — no se transfiere nada entre Parte I y Parte II. El motor soporta transferencia total (`"*"`) o selectiva para mundos futuros.
- La carga de archivos YAML por episodio se delega en `EntityLoader`.

### 4.7 `events/event_bus.py` — Bus de Eventos Síncrono

**Responsabilidad**: Implementación del patrón Observer para desacoplar el motor de la UI y otros suscriptores. Diseño síncrono, en proceso, sin backpressure. Según especificación completa en `13-event-system.md` sección 4.

**Clases principales**:

- `EventBus` — registro y despacho de handlers por tipo de evento.

**Dependencias**: Solo stdlib (`collections.defaultdict`, `typing`).

**Interfaz pública**:

```python
from collections import defaultdict
from typing import Callable
from fortress_engine.events.event_types import EngineEvent

EventHandler = Callable[[EngineEvent], None]


class EventBus:
    """Bus de eventos síncrono con patrón Observer (Event System 4.1)."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Registra un handler para un tipo de evento específico.
        Usa '*' para suscribirse a todos los eventos.
        """
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Remueve un handler previamente registrado.
        No lanza error si el handler no estaba registrado.
        """
        try:
            self._subscribers[event_type].remove(handler)
        except ValueError:
            pass

    def emit(self, event: EngineEvent) -> None:
        """
        Despacha un evento a todos los suscriptores relevantes.
        El despacho es síncrono. Errores en handlers individuales no
        interrumpen a los demás handlers ni al motor.
        """
        handlers = (
            self._subscribers.get(event.type, []) +
            self._subscribers.get("*", [])
        )
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                if __debug__:
                    import sys
                    print(
                        f"[EventBus] Error in handler {handler.__name__} "
                        f"for event {event.type}: {e}",
                        file=sys.stderr,
                    )
```

**Suscriptores estándar** (Event System 4.2):
- **UI Layer**: se suscribe a `entity_entered`, `action_output`, `error_output`, `game_over`, `input_received`.
- **Save System**: se suscribe a `*` (todos los eventos → event log).
- **Debug Console**: se suscribe a `*` (todos los eventos → pretty print, solo en modo debug).

**Propiedades del despacho** (Event System 4.3):
- **Modo**: Síncrono. Todos los handlers se ejecutan antes de que `emit()` retorne.
- **Orden**: FIFO por tipo de evento (orden de registro).
- **Errores**: Aislados. Un handler que lanza no afecta a los demás.
- **Backpressure**: No existe. Si la UI es lenta, pierde frames.
- **Thread-safety**: No requerida en v1.0. Todo corre en un solo hilo.

### 4.8 `events/event_types.py` — Tipos de Evento

**Responsabilidad**: Define el dataclass `EngineEvent` inmutable y las funciones de serialización/deserialización a JSON para el event log.

**Implementación según Event System sección 3**:

```python
from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Any
import time
import json


@dataclass(frozen=True)
class EngineEvent:
    event_id: UUID
    type: str
    turn_number: int
    timestamp: float
    payload: dict[str, Any]
    protagonist_id: str | None = None
    episode_id: str | None = None

    @classmethod
    def create(
        cls,
        event_type: str,
        turn_number: int,
        payload: dict[str, Any],
        protagonist_id: str | None = None,
        episode_id: str | None = None,
    ) -> 'EngineEvent':
        """Factory method: genera UUID y timestamp automáticamente."""
        return cls(
            event_id=uuid4(),
            type=event_type,
            turn_number=turn_number,
            timestamp=time.monotonic(),
            payload=payload,
            protagonist_id=protagonist_id,
            episode_id=episode_id,
        )


def event_to_dict(event: EngineEvent) -> dict[str, Any]:
    """Serializa un EngineEvent a un diccionario JSON-compatible."""
    return {
        "event_id": str(event.event_id),
        "type": event.type,
        "turn_number": event.turn_number,
        "timestamp": event.timestamp,
        "payload": event.payload,
        "protagonist_id": event.protagonist_id,
        "episode_id": event.episode_id,
    }


def event_from_dict(data: dict[str, Any]) -> EngineEvent:
    """Deserializa un diccionario a un EngineEvent."""
    return EngineEvent(
        event_id=UUID(data["event_id"]),
        type=data["type"],
        turn_number=data["turn_number"],
        timestamp=data["timestamp"],
        payload=data["payload"],
        protagonist_id=data.get("protagonist_id"),
        episode_id=data.get("episode_id"),
    )
```

### 4.9 `persistence/repository.py` — Interfaz de Persistencia

**Responsabilidad**: Clase base abstracta que define el contrato de persistencia. Todo acceso a almacenamiento en el motor debe pasar por esta interfaz (restricción #7 del PRD).

**Interfaz pública**:

```python
from abc import ABC, abstractmethod
from fortress_engine.events.event_types import EngineEvent
from fortress_engine.engine.state import WorldState


class WorldStateRepository(ABC):
    """Interfaz de persistencia para el motor (PRD 10, GDD 2.6)."""

    @abstractmethod
    def append_event(self, event: EngineEvent) -> None:
        """Apende un evento al log inmutable de eventos (event sourcing)."""
        ...

    @abstractmethod
    def get_event_log(self, since_turn: int = 0) -> list[EngineEvent]:
        """Retorna eventos desde un turno específico. since_turn=0 retorna todos."""
        ...

    @abstractmethod
    def get_latest_turn(self) -> int:
        """Retorna el número de turno más alto registrado. 0 si el log está vacío."""
        ...

    @abstractmethod
    def save_snapshot(self, state: WorldState, turn: int, save_slot: str) -> None:
        """Guarda un snapshot del estado completo como caché opcional."""
        ...

    @abstractmethod
    def load_latest_snapshot(self, save_slot: str) -> tuple[WorldState, int] | None:
        """
        Carga el snapshot más reciente del slot.
        Retorna (WorldState, turn_number) o None si no hay snapshot.
        """
        ...
```

### 4.10 `persistence/sqlite_repository.py` — Implementación SQLite

**Responsabilidad**: Implementación concreta de `WorldStateRepository` usando SQLAlchemy sobre SQLite. Gestiona tanto el event log como los snapshots.

**Clases principales**:

- `SQLiteWorldStateRepository` — implementa todos los métodos del ABC usando SQLAlchemy.

**Dependencias**:
- `persistence/repository.py` — `WorldStateRepository`
- `persistence/models.py` — `EventLog`, `SaveSnapshot` (ORM models)
- `sqlalchemy` — ORM y engine

**Interfaz pública**:

```python
class SQLiteWorldStateRepository(WorldStateRepository):
    def __init__(self, db_path: str) -> None:
        """
        Inicializa la conexión a SQLite.
        Crea las tablas si no existen (create_all).
        db_path: ruta al archivo .db (ej: "saves/slot_1/fortaleza.db").
        """
        ...

    def append_event(self, event: EngineEvent) -> None:
        """Inserta una fila en event_log."""
        ...

    def get_event_log(self, since_turn: int = 0) -> list[EngineEvent]:
        """Consulta event_log WHERE turn_number > since_turn ORDER BY turn_number, id."""
        ...

    def get_latest_turn(self) -> int:
        """SELECT MAX(turn_number) FROM event_log."""
        ...

    def save_snapshot(self, state: WorldState, turn: int, save_slot: str) -> None:
        """Inserta (o actualiza) una fila en save_snapshots."""
        ...

    def load_latest_snapshot(self, save_slot: str) -> tuple[WorldState, int] | None:
        """SELECT * FROM save_snapshots WHERE save_slot = ? ORDER BY turn_number DESC LIMIT 1."""
        ...
```

### 4.11 `persistence/event_log.py` — Log de Eventos (Event Sourcing)

**Responsabilidad**: Suscriptor del EventBus que persiste todos los eventos en el log. Implementa el patrón Event Sourcing descrito en GDD 2.6 y Event System 8.

**Clases principales**:

- `EventSourcingSaveSystem` — suscriptor `*` del EventBus que apende eventos al repositorio.

**Interfaz pública**:

```python
class EventSourcingSaveSystem:
    def __init__(self, event_bus: EventBus, repository: WorldStateRepository) -> None:
        """
        Se suscribe a '*' en el EventBus.
        Cada evento emitido se apende automáticamente al repository.
        """
        ...

    def _append_to_log(self, event: EngineEvent) -> None:
        """Handler que apende el evento al repositorio."""
        ...

    def replay_state(
        self,
        initial_state: WorldState,
        graph: 'DualGraphEngine',
        since_turn: int = 0,
    ) -> tuple[WorldState, int]:
        """
        Reconstruye el estado reproduciendo el event log desde since_turn.
        Retorna (estado_final, último_turno).

        Durante el replay:
        - Se emiten save_replay_started/save_replay_ended para que la UI suprima renderización.
        - Solo se reproducen eventos de tipo action_resolved (los que modifican estado).
        """
        ...
```

**Notas de implementación**:
- Solo se persisten eventos que modifican estado (`action_resolved` con `has_effects: true`). Eventos de narración (`action_output`, `entity_entered`) no se persisten porque son derivables del estado.
- El replay carga el snapshot más reciente y reproduce solo los eventos posteriores a ese snapshot. Si no hay snapshot, reproduce todo el log desde el estado inicial.

### 4.12 `entities/loader.py` — Cargador YAML de Entidades

**Responsabilidad**: Escanea directorios de archivos YAML, los valida con Pydantic, y construye los objetos `Entity`, `HyperEdge`, `MacroEdge` y `Episode` que el motor consume.

**Dependencias**:
- `entities/entity.py` — `Entity`
- `pyyaml` — parsing YAML
- `pydantic` — validación de esquemas

**Interfaz pública**:

```python
class EntityLoader:
    def __init__(self, world_path: str) -> None:
        """
        world_path: ruta al directorio del mundo (ej: "worlds/fortaleza/").
        """
        ...

    def load_world_config(self) -> dict[str, Any]:
        """Carga y valida world.yaml. Retorna el diccionario de configuración."""
        ...

    def load_episodes(self) -> list['Episode']:
        """Carga todos los episodios desde episodes/*.yaml."""
        ...

    def load_shared_entities(self, episode_id: str) -> list[Entity]:
        """Carga entidades compartidas (player, vocabulario) desde shared/."""
        ...

    def load_vocabulary(self, world_path: str | None = None) -> 'Vocabulary' | None:
        """
        Carga el vocabulario del mundo desde `<world>/shared/vocabulary.yaml`.
        Retorna None si el archivo no existe (el parser usa su cascada de
        defaults). El `Vocabulary` resultante contiene: verbs, stopwords,
        prepositions, speech_markers, speech_verbs, messages (texto del
        narrador por error_code/system code), movement_verbs y
        system_commands.
        """
        ...

    def load_rooms(self, episode_id: str) -> list[Entity]:
        """Carga todas las rooms desde episode-XX/rooms/*.yaml."""
        ...

    def load_items(self, episode_id: str) -> list[Entity]:
        """Carga todos los ítems desde episode-XX/items/*.yaml."""
        ...

    def load_npcs(self, episode_id: str) -> list[Entity]:
        """Carga todos los NPCs desde episode-XX/npcs/*.yaml."""
        ...

    def load_macro_edges(self, episode_id: str) -> list['MacroEdge']:
        """Carga todas las aristas Macro desde episode-XX/macros/*.yaml."""
        ...

    def load_hyper_edges(self, episode_id: str) -> list['HyperEdge']:
        """Carga todas las Hiper-Aristas desde episode-XX/actions/*.yaml."""
        ...

    def load_episode_data(
        self, episode_id: str, episode: 'Episode'
    ) -> dict[str, Any]:
        """
        Carga todos los datos de un episodio:
        {
            'rooms': [...],
            'items': [...],
            'npcs': [...],
            'macro_edges': [...],
            'hyper_edges': [...],
        }
        """
        ...

    def validate_world(self) -> list[str]:
        """
        Valida la integridad del mundo:
        - Sin referencias colgantes (toda entidad referenciada existe).
        - Sin prioridades duplicadas para (verb, target) en la misma anchor.
        - Todas las banderas en predicados flag/flag_not declaradas.
        - Todas las start_anchor existen.
        - carry_over: ítems y banderas existen en el episodio origen.
        - Todas las rooms alcanzables desde start_anchor.

        Retorna una lista de mensajes de error. Lista vacía = mundo válido.
        """
        ...
```

**Validación con Pydantic**:

Cada tipo de archivo YAML tiene un modelo Pydantic que valida su estructura antes de convertirlo a dataclass:

```python
from dataclasses import dataclass, field
from pydantic import BaseModel


@dataclass
class Vocabulary:
    """Vocabulario del mundo cargado desde shared/vocabulary.yaml."""
    language: str
    verbs: dict[str, list[str]]
    stopwords: list[str]
    prepositions: dict[str, list[str]]
    speech_markers: list[str]
    speech_verbs: list[str]
    messages: dict[str, str] = field(default_factory=dict)
    movement_verbs: list[str] = field(default_factory=list)
    system_commands: dict[str, list[str]] = field(default_factory=dict)


class PluginConfigYAML(BaseModel):
    plugin: str
    options: dict[str, Any] = {}


class WorldYAML(BaseModel):
    """Modelo Pydantic de world.yaml (PRD 4.8, GDD 3.1)."""
    world_id: str
    name: str
    language: str = "es"                                     # default "es"
    parser: str | PluginConfigYAML = PluginConfigYAML(plugin="classic")
    narrator: str | PluginConfigYAML = PluginConfigYAML(plugin="template")


class EntityYAML(BaseModel):
    entity_id: str
    type: str
    name: str
    components: dict[str, Any] = {}
    spatial_anchor: str | None = None


class HyperEdgeYAML(BaseModel):
    hyper_edge_id: str
    name: str
    priority: int
    clique: CliqueYAML
    operators: list[dict[str, Any]] = []
    output: str | None = None


class CliqueYAML(BaseModel):
    subject: str | None = None
    verb: str
    target: str | None = None
    instrument: str | None = None
    context: str | None = None
    instrument_not: str | None = None
    instrument_any: bool = False
    flag: str | None = None
    flag_not: str | None = None
    component: dict[str, str] | None = None
```

### 4.13 `plugins/parser_interface.py` — Interfaz de Parser

**Responsabilidad**: Define el contrato que todo parser debe implementar (PRD 5). Es una clase abstracta con un único método.

**Interfaz pública**:

```python
from abc import ABC, abstractmethod


class ParserInterface(ABC):
    """Interfaz que todo parser debe implementar (PRD 5, GDD 2.5)."""

    @abstractmethod
    def parse(self, raw_text: str, world_state: 'WorldState') -> 'ParsedCommand':
        """
        Parsea texto crudo del jugador en una tupla estructurada.

        Args:
            raw_text: texto ingresado por el jugador.
            world_state: estado actual del mundo (entidades, flags, protagonista activo).

        Returns:
            ParsedCommand con subject, verb, target, context, instrument resueltos.
        """
        ...
```

### 4.14 `plugins/narrator_interface.py` — Interfaz de Narrador

**Responsabilidad**: Define el contrato que todo narrador debe implementar (PRD 6). El narrador se suscribe al EventBus y produce texto para el jugador.

**Interfaz pública**:

```python
from abc import ABC, abstractmethod


class NarratorInterface(ABC):
    """Interfaz que todo narrador debe implementar (PRD 6, GDD 2.5)."""

    @abstractmethod
    def initialize(self, event_bus: 'EventBus') -> None:
        """
        Se suscribe a los eventos relevantes del EventBus.
        El narrador es responsable de registrar sus propios handlers.
        """
        ...

    @abstractmethod
    def handle_event(self, event: 'EngineEvent', world_state: 'WorldState') -> str | None:
        """
        Maneja un evento del motor y retorna texto para mostrar al jugador.
        Retorna None si el evento no produce salida de texto.

        Eventos que típicamente producen texto:
        - entity_entered → descripción de la habitación
        - action_output → texto del campo output de la Hiper-Arista
        - error_output → mensaje de error
        - episode_completed → texto de victoria
        - game_over → texto de derrota
        - system_message → mensaje del sistema
        """
        ...
```

### 4.15 `plugins/classic_parser.py` — Parser Clásico V1

**Responsabilidad**: Implementación del parser clásico que replica el comportamiento del parser original de Fortaleza (Turbo Pascal 7). Reconoce 37 verbos (canónicos + grupos de sinónimos, según `docs/07-vocabulary.md`), ~180 sustantivos, con matching parcial, normalización de tildes y filtrado de stopwords V2.

**Dependencias**:
- `plugins/parser_interface.py` — `ParserInterface`

**Interfaz pública**:

```python
class ClassicParser(ParserInterface):
    """
    Parser V1: réplica del parser original de Fortaleza (PRD 5, GDD 2.5).

    Características:
    - 37 verbos reconocidos: inventario ORIGINAL de Fortaleza según
      docs/07-vocabulary.md (autoritativo), con verbos canónicos + grupos de
      sinónimos — NO es una lista genérica de aventura textual.
    - ~180 sustantivos (nombres de entidades + sinónimos).
    - Matching parcial de nombres ("Puerta Principal" coincide con "Puerta").
    - Normalización de tildes: áéíóúüñ → aeiouun.
    - Stopwords V2: LA, EL, LOS, LAS, UN, UNA, AL, DEL, POR.
    - Sintaxis: VERBO [SUSTANTIVO] [PREPOSICIÓN SUSTANTIVO].
    """

    # Stopwords V2 (PRD 5). Desviación documentada del V1 sugerido en
    # docs/12-engine-gap-analysis.md P7: V2 = {LA, EL, POR, AL} + {UN, UNA, DEL,
    # LOS, LAS}. Es la lista que ya usa MinimalParser, V1 ⊂ V2 y mejora la UX.
    STOPWORDS: set[str] = {"LA", "EL", "LOS", "LAS", "UN", "UNA", "AL", "DEL", "POR"}

    # Verbos del parser clásico (PRD 7.1, docs/07-vocabulary.md).
    # Grupos de sinónimos (todos se resuelven al verbo canónico):
    #   ATRAVESAR/IR/CRUZAR/PASAR → ir      OBSERVAR/MIRAR → mirar
    #   TOMAR/COGER → tomar                 LEER/VER/EXAMINAR → examinar
    #   SOLTAR/DEJAR → dejar                ROMPER/FORZAR/DESTROZAR → romper
    #   PREGUNTAR/INTERROGAR → interrogar   REGALAR/DAR → dar
    #   MATAR/ASESINAR → matar              ABANDONAR/TERMINAR → terminar
    #   MIAR/ORINAR → orinar
    # Formas manejadas sin grupo: INVENTARIO, ABRIR, PESAR, SALVAR, EJECUTAR,
    # TODO, PORCIENTO, CLS, CON, A, DICIENDO, RESPONDIENDO, ESPERAR.
    VERBS: set[str] = {
        "IR", "ATRAVESAR", "CRUZAR", "PASAR",
        "TOMAR", "COGER",
        "SOLTAR", "DEJAR",
        "ABRIR",
        "MATAR", "ASESINAR",
        "OBSERVAR", "MIRAR",
        "LEER", "VER", "EXAMINAR",
        "ROMPER", "FORZAR", "DESTROZAR",
        "PREGUNTAR", "INTERROGAR",
        "INVENTARIO",
        "REGALAR", "DAR",
        "CON", "A",
        "ABANDONAR", "TERMINAR",
        "RESPONDIENDO", "DICIENDO",
        "EJECUTAR", "SALVAR",
        "PORCIENTO", "TODO", "PESAR",
        "MIAR", "ORINAR",
        "CLS",
    }

    # Vocabulario por defecto en código: {canónico: [sinónimos]} + stopwords V2.
    # Fallback del parser cuando no se recibe `vocabulary` y tampoco existe
    # worlds/<nombre>/shared/vocabulary.yaml (ver GDD 3.1).
    DEFAULT_SPANISH_VOCABULARY: dict[str, list[str]] = {
        "IR": ["ATRAVESAR", "CRUZAR", "PASAR"],
        "TOMAR": ["COGER"],
        "DEJAR": ["SOLTAR"],
        "MIRAR": ["OBSERVAR"],
        "EXAMINAR": ["LEER", "VER"],
        "ROMPER": ["FORZAR", "DESTROZAR"],
        "INTERROGAR": ["PREGUNTAR"],
        "DAR": ["REGALAR"],
        "MATAR": ["ASESINAR"],
        "TERMINAR": ["ABANDONAR"],
        "ORINAR": ["MIAR"],
    }

    def __init__(self, vocabulary: dict[str, list[str]] | None = None) -> None:
        """
        vocabulary: diccionario de sinónimos {canónico: [sinónimos]}.
        Resolución de vocabulario en cascada:
        1. El dict `vocabulary` recibido (si no es None).
        2. worlds/<nombre>/shared/vocabulary.yaml del mundo (si el archivo existe).
        3. DEFAULT_SPANISH_VOCABULARY (constante en código, mismo inventario de
           37 verbos + stopwords V2).
        """
        ...

    def parse(self, raw_text: str, world_state: 'WorldState') -> 'ParsedCommand':
        """
        Algoritmo de parseo:
        1. Normalizar: mayúsculas → minúsculas, tildes → ASCII.
        2. Tokenizar por espacios.
        3. Filtrar stopwords.
        4. Identificar verbo (primer token que matchea VERBS).
        5. Identificar target: buscar tokens restantes contra nombres de entidades
           en la room actual o inventario del protagonista, con matching parcial.
        6. Identificar instrument: tokens después de preposición "CON".
        7. Retornar ParsedCommand con entity_ids resueltos.
        """
        ...

    def _normalize(self, text: str) -> str:
        """Normaliza texto: minúsculas, tildes a ASCII."""
        ...

    def _match_entity(
        self, name: str, candidates: list['Entity']
    ) -> 'Entity' | None:
        """
        Busca una entidad por nombre con matching parcial.
        "Puerta Principal" matchea con entity.name == "Puerta principal".
        Retorna la entidad o None.
        """
        ...
```

### 4.16 `plugins/template_narrator.py` — Narrador por Plantillas V1

**Responsabilidad**: Narrador que emite texto directamente desde los datos del mundo (campo `output` de Hiper-Aristas, `description` de rooms, mensajes de sistema). Sin generación de texto — es el texto exacto definido por el diseñador.

**Dependencias**:
- `plugins/narrator_interface.py` — `NarratorInterface`
- `events/event_bus.py` — `EventBus`

**Interfaz pública**:

```python
class TemplateNarrator(NarratorInterface):
    """
    Narrador V1: texto directo desde datos del mundo (PRD 6, GDD 2.5).

    Responsable de TODO el texto que ve el jugador:
    - Descripciones de habitaciones (entity_entered → room.components.description)
    - Output de acciones (action_output → texto del campo output de Hiper-Arista)
    - Mensajes de error (error_output → mensaje)
    - Mensajes de sistema (system_message → mensaje)
    - Textos de victoria/derrota (episode_completed, game_over)
    """

    def __init__(self, templates: dict[str, str] | None = None) -> None:
        """
        templates: diccionario con textos de sistema (guardado, carga, etc.).
        Si es None, usa templates por defecto.
        """
        ...

    def initialize(self, event_bus: 'EventBus') -> None:
        """Se suscribe a eventos que producen texto para el jugador."""
        event_bus.subscribe("entity_entered", self._on_entity_entered)
        event_bus.subscribe("action_output", self._on_action_output)
        event_bus.subscribe("error_output", self._on_error_output)
        event_bus.subscribe("episode_completed", self._on_episode_completed)
        event_bus.subscribe("game_over", self._on_game_over)
        event_bus.subscribe("system_message", self._on_system_message)
        event_bus.subscribe("entity_described", self._on_entity_described)
        event_bus.subscribe("entity_examined", self._on_entity_examined)
        event_bus.subscribe("inventory_listed", self._on_inventory_listed)

    def handle_event(
        self, event: 'EngineEvent', world_state: 'WorldState'
    ) -> str | None:
        """Despacha el evento al handler correspondiente. Retorna el texto o None."""
        ...

    def _on_entity_entered(self, event: 'EngineEvent') -> str | None:
        """Retorna la descripción de la room desde el payload del evento."""
        ...

    def _on_action_output(self, event: 'EngineEvent') -> str | None:
        """Retorna el texto del campo output de la Hiper-Arista."""
        ...

    def _on_error_output(self, event: 'EngineEvent') -> str | None:
        """Retorna el mensaje de error."""
        ...
```

**Nota (Epic #3 — plugin factory)**: `TemplateNarrator` expone además la propiedad `language` (default `"es"`). La factory de plugins (`create_narrator`) la inyecta desde el `world.yaml` del mundo para que los mensajes de sistema y las plantillas sigan el idioma del mundo (ver §9.2).

### 4.17 `cli/main.py` — Punto de Entrada CLI

**Responsabilidad**: Interfaz de línea de comandos para ejecutar el motor, validar mundos y correr walkthroughs. Usa `argparse` de stdlib.

**Interfaz pública**:

```python
def main() -> None:
    """
    Punto de entrada CLI.

    Comandos:
      fortress-engine run <world_path> [--save SLOT]
          Inicia el juego. Lee comandos de stdin, escribe salida a stdout.

      fortress-engine validate <world_path>
          Valida la integridad de los datos del mundo. Retorna 0 si es válido.

      fortress-engine test <world_path> --walkthrough <file>
          Ejecuta un walkthrough (archivo de comandos, uno por línea) y verifica
          que el goal del episodio se cumple al final.
    """
    ...
```

**Protocolo stdin/stdout**:
- El motor lee una línea de stdin por turno (comando del jugador).
- La salida del narrador se escribe a stdout.
- Los eventos del motor son consumidos internamente por los suscriptores (narrador, save system). La UI de terminal simplemente imprime el texto producido por el narrador.
- El código de salida es 0 si el juego terminó normalmente, 1 si hubo error.

---

## 5. Esquema SQLite (SQLAlchemy)

### 5.1 Modelos ORM

Definidos en `persistence/models.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Index
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class EventLog(Base):
    """Tabla inmutable de eventos ejecutados (event sourcing)."""
    __tablename__ = "event_log"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    event_id: str = Column(String(36), nullable=False, unique=True)     # UUID4
    event_type: str = Column(String(50), nullable=False)                # "action_resolved"
    turn_number: int = Column(Integer, nullable=False)
    timestamp: float = Column(Float, nullable=False)                    # time.monotonic()
    payload: str = Column(Text, nullable=False)                        # JSON string
    protagonist_id: str | None = Column(String(100), nullable=True)
    episode_id: str | None = Column(String(50), nullable=True)
    save_slot: str = Column(String(20), nullable=False, default="auto") # "auto", "slot_1", "slot_2", "slot_3"
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)


class SaveSnapshot(Base):
    """Snapshots periódicos del estado global (caché de rendimiento)."""
    __tablename__ = "save_snapshots"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    save_slot: str = Column(String(20), nullable=False)                 # "slot_1", "slot_2", "slot_3"
    turn_number: int = Column(Integer, nullable=False)
    world_state_json: str = Column(Text, nullable=False)                # WorldState.to_dict() → JSON
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
```

### 5.2 Índices

```python
# Búsqueda por turno (replay incremental)
Index("idx_event_log_turn", EventLog.turn_number)

# Búsqueda por tipo de evento (debugging)
Index("idx_event_log_type", EventLog.event_type)

# Búsqueda por save slot (múltiples slots de guardado)
Index("idx_event_log_slot", EventLog.save_slot)

# Búsqueda de snapshot más reciente por slot
Index("idx_snapshot_slot_turn", SaveSnapshot.save_slot, SaveSnapshot.turn_number.desc())
```

### 5.3 Estrategia de Migraciones

Se recomienda **Alembic** para gestionar migraciones de esquema:

```
fortress-engine/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── alembic.ini
```

El comando `alembic upgrade head` se ejecuta automáticamente al inicializar el repositorio (`SQLiteWorldStateRepository.__init__`). Si la base de datos no existe, se crea con el esquema actual. Si existe, se aplican las migraciones pendientes.

**Alternativa para MVP**: `Base.metadata.create_all(engine)` al iniciar. Simple y suficiente para v1.0. Alembic se agrega en v1.1 cuando el esquema evolucione.

---

## 6. Flujo de Carga de Mundo

Este flujo describe lo que ocurre cuando el motor carga un mundo (PRD 4.8, GDD 2.5). Es la secuencia exacta de pasos que ejecuta `TurnOrchestrator.run()`.

### Paso a paso

1. **Leer `world.yaml`**
   - Cargar configuración global: `world_id`, `name`, `language`, `player_defaults`, lista de episodios.
   - Validar con Pydantic.

2. **Crear entidad del jugador**
   - Leer `shared/player.yaml`.
   - Crear `Entity(type="player", ...)`.
   - Validar componente `player_controlled: true`.

3. **Determinar episodio activo**
   - Si es una partida nueva: el primer episodio con `requires: []`.
   - Si es carga desde save slot: restaurar `current_episode_id` desde snapshot.

4. **Cargar datos del episodio** desde `episodes/<id>.yaml`:
   - `goal`, `carry_over`, `start_anchor`.
   - Validar con Pydantic.

5. **Cargar rooms** desde `episode-XX/rooms/*.yaml`:
   - Cada archivo → una `Entity(type="room")`.
   - Validar componentes `description`, `visited`, `dark`.

6. **Cargar ítems** desde `episode-XX/items/*.yaml`:
   - Cada archivo → una `Entity(type="item")`.
   - Asignar `spatial_anchor` según el campo YAML (room donde aparece inicialmente).

7. **Cargar NPCs** desde `episode-XX/npcs/*.yaml`:
   - Cada archivo → una `Entity(type="npc")`.
   - Validar componentes `mood`, `brain_type`, `hit_points`.

8. **Cargar aristas Macro** desde `episode-XX/macros/*.yaml`:
   - Cada archivo → un `MacroEdge`.
   - Validar que no contengan campos legados (`connection_type`, `password`, `answer`): `MacroEdgeYAML` usa `extra="forbid"` y falla ruidosamente ante ellos.

9. **Cargar Hiper-Aristas** desde `episode-XX/actions/*.yaml`:
   - Cada archivo → un `HyperEdge`.
   - Validar estructura de `clique` y `operators`.

10. **Construir el Grafo Dual**:
    - `DualGraphEngine.add_anchor()` para cada room.
    - `DualGraphEngine.add_macro_edge()` para cada arista Macro.
    - `DualGraphEngine.add_hyper_edge()` para cada Hiper-Arista (indexada por anchor y verbo).

11. **Validar integridad del grafo**:
    - Sin referencias colgantes: toda entidad referenciada en cliques, predicados y operadores existe en `entities`.
    - Sin prioridades duplicadas: si dos Hiper-Aristas en la misma room comparten `(verb, target, priority)`, emitir advertencia (no bloquear).
    - Todas las banderas en predicados `flag`/`flag_not` están declaradas en `world.yaml` o en el episodio.
    - `start_anchor` existe en las rooms cargadas.
    - Validación de `carry_over`: los ítems y banderas referenciados existen.
    - (Futuro v1.1) Rooms alcanzables desde `start_anchor`.

12. **Inicializar WorldState**:
    - `entities`: todas las entidades cargadas.
    - `flag_book`: banderas iniciales desde `world.yaml` (típicamente vacío).
    - `player_controlled_entities`: [player_id].
    - `active_protagonist_id`: player_id.
    - `current_episode_id`: episode.id.
    - `turn_number`: 0.

13. **Inicializar orquestador**:
    - Crear `EventBus`.
    - Registrar suscriptores estándar (narrador, save system, debug).
    - Inyectar dependencias en `TurnOrchestrator`.

14. **Emitir eventos de inicio**:
    - `turn_started({ turn_number: 1, active_protagonist_id })`.
    - `episode_started({ episode_id, episode_name, start_anchor_id })`.
    - `entity_entered` con la descripción de `start_anchor`.
    - El narrador produce la salida inicial que el jugador ve.

15. **Entrar en el bucle de turnos**:
    - Esperar input del jugador.
    - Ejecutar `execute_turn(raw_text)`.
    - Repetir hasta `game_over` o `game_completed`.

---

## 7. Estrategia de Testing

### 7.1 Tests Unitarios

#### `tests/test_engine/test_operators.py`

Cada operador atómico se prueba en aislamiento con un `WorldState` mínimo:

```python
def test_transfer_item_to_inventory_success():
    """TRANSFER: mover ítem de room a inventario del protagonista."""
    ...

def test_transfer_item_exceeds_max_weight():
    """TRANSFER: ítem con weight > player.max_weight → error 'Usted no puede cargar con eso.'"""
    ...

def test_transfer_inventory_full():
    """TRANSFER: inventario lleno → error 'Sería demasiado peso.'"""
    ...

def test_transfer_item_not_portable():
    """TRANSFER: ítem con portable=false → error."""
    ...

def test_transfer_to_null_destroys_entity():
    """TRANSFER a null → entidad destruida (spatial_anchor = None)."""
    ...

def test_transform_changes_component():
    """TRANSFORM: cambia state de una entidad."""
    ...

def test_transform_fails_if_old_value_mismatch():
    """TRANSFORM: old_value no coincide → error, no se modifica."""
    ...

def test_combine_destroys_inputs_and_creates_output():
    """COMBINE: inputs → null, output → room actual."""
    ...

def test_combine_fails_if_input_missing():
    """COMBINE: input_entity no existe → error."""
    ...

def test_flag_sets_value():
    """FLAG: establece bandera a true/false."""
    ...

def test_teleport_moves_entity():
    """TELEPORT: cambia spatial_anchor de una entidad."""
    ...

def test_teleport_fails_if_room_not_found():
    """TELEPORT: to_anchor no existe → error."""
    ...
```

#### `tests/test_engine/test_goal_evaluator.py`

```python
def test_all_condition_types():
    """Evalúa cada uno de los 6 tipos de condición atómica."""
    ...

def test_and_composition():
    """Composición and: todas deben cumplirse."""
    ...

def test_or_composition():
    """Composición or: al menos una debe cumplirse."""
    ...

def test_nested_and_or():
    """Composición anidada: and(or(...), ...)."""
    ...
```

#### `tests/test_engine/test_graph.py`

```python
def test_clique_validation_subject_verb_target():
    """Clique con subject, verb, target → se forma si todos están en la room."""
    ...

def test_clique_validation_instrument_required():
    """Clique con instrument específico → solo se forma si el ítem está en inventario."""
    ...

def test_clique_validation_instrument_not():
    """Clique con instrument_not → no se forma si el jugador tiene ese ítem."""
    ...

def test_clique_validation_instrument_any():
    """Clique con instrument_any → se forma con cualquier ítem portable."""
    ...

def test_clique_validation_flag_required():
    """Clique con flag → solo se forma si la bandera es True."""
    ...

def test_clique_validation_flag_not():
    """Clique con flag_not → solo se forma si la bandera es False."""
    ...

def test_clique_validation_component_predicate():
    """Clique con component → verifica entity.components[key] == value."""
    ...

def test_hyper_edges_ordered_by_priority():
    """get_hyper_edges_for_verb retorna Hiper-Aristas en orden de prioridad descendente."""
    ...

def test_macro_edge_open_always_valid():
    """Arista sin predicados → siempre transitable."""
    ...

def test_macro_edge_requires_text_unlocks_with_correct_text():
    """Arista con requires_text → se abre con el texto correcto."""
    ...

def test_macro_edge_requires_item_blocks_or_kills():
    """Arista con requires_item → sin ítem se bloquea (o muere si hay death_message)."""
    ...

def test_macro_edge_forbids_item_blocks_or_kills():
    """Arista con forbids_item → con ítem se bloquea (o muere si hay death_message)."""
    ...

def test_macro_edge_requires_flag_blocks():
    """Arista con requires_flag → sin la bandera se bloquea."""
    ...
```

#### `tests/test_events/test_event_bus.py`

Según Event System 10.3 (tests ya definidos en ese documento):
- `test_event_bus_dispatches_to_subscriber`
- `test_event_bus_wildcard_receives_all`
- `test_event_bus_handler_error_does_not_block_others`
- `test_event_bus_unsubscribe_removes_handler`

#### `tests/test_entities/test_loader.py`

```python
def test_load_room_from_yaml():
    """Carga una room desde YAML y valida con Pydantic."""
    ...

def test_load_item_from_yaml():
    """Carga un ítem desde YAML."""
    ...

def test_load_hyper_edge_from_yaml():
    """Carga una Hiper-Arista con operadores."""
    ...

def test_yaml_validation_rejects_invalid_entity():
    """YAML sin entity_id → error de validación Pydantic."""
    ...

def test_validate_world_detects_dangling_references():
    """Validador detecta referencias a entidades inexistentes."""
    ...

def test_validate_world_detects_duplicate_priorities():
    """Validador detecta prioridades duplicadas para (verb, target)."""
    ...
```

### 7.2 Tests de Integración

#### `tests/test_persistence/test_event_sourcing.py`

```python
def test_event_sourcing_round_trip():
    """
    Event sourcing round-trip:
    1. Crear WorldState inicial con 2 rooms, 1 ítem.
    2. Ejecutar 3 acciones (tomar ítem, mover a otra room, soltar ítem).
    3. Guardar snapshot + event log.
    4. Cargar desde snapshot → verificar estado == estado guardado.
    """
    ...

def test_replay_from_empty_log():
    """
    Replay desde log vacío → estado inicial sin cambios.
    """
    ...

def test_replay_reconstructs_state():
    """
    Replay de 50 acciones → estado reconstruido es idéntico al original.
    """
    ...
```

#### `tests/test_integration/` (adicionales)

```python
def test_full_turn_cycle():
    """
    Ciclo completo de turno:
    1. Input "TOMAR ANTORCHA" → parse → validar clique → TRANSFER → emitir eventos.
    2. Verificar que la entidad cambió de spatial_anchor.
    3. Verificar que se emitieron los eventos correctos (action_attempted, entity_transferred, action_output, action_resolved).
    """
    ...

def test_episode_transition():
    """
    Transición de episodio:
    1. Completar goal de episode-01.
    2. Verificar carry_over aplicado.
    3. Verificar que episode-02 cargó correctamente.
    4. Verificar que el jugador está en start_anchor de episode-02.
    """
    ...
```

### 7.3 Test de Aceptación — Fortaleza Walkthrough

#### `tests/test_integration/test_walkthrough.py`

```python
def test_fortaleza_walkthrough_part1():
    """
    Test de aceptación definitivo (PRD 11, GDD 3.4):

    1. Cargar worlds/fortaleza/.
    2. Iniciar episode-01.
    3. Leer docs/09-walkthrough.md, extraer todos los comandos de la Parte I.
    4. Ejecutar cada comando secuencialmente con execute_turn().
    5. Después del último comando, verificar:
       - goal_evaluator.check() retorna True.
       - No se emitieron game_over events.
    """
    ...

def test_fortaleza_walkthrough_part2():
    """
    Igual que test_fortaleza_walkthrough_part1 pero para Parte II.
    Verifica la transición automática y la victoria final.
    """
    ...
```

**Nota sobre el walkthrough**: El test no verifica el texto de salida palabra por palabra — eso es responsabilidad de los datos YAML (que deben contener el texto exacto del original). El test verifica que la secuencia de comandos produce el resultado esperado en términos de estado (posiciones de entidades, flags, y finalmente goal cumplido).

### 7.4 Fixtures de Test

**Fixture: Mundo mínimo (`worlds/_test_minimal/`)**

Un mundo de 2 rooms, 1 ítem, 1 NPC, 1 puzle, usado por todos los tests unitarios y de integración:

```yaml
# world.yaml
world_id: "test-minimal"
name: "Test Minimal World"
player_defaults:
  max_weight: 40

episodes:
  - id: "ep-1"
    name: "Test Episode"
    requires: []
    start_anchor: "test-room-01"
    goal:
      conditions:
        - type: flag_is_set
          flag: "puzzle_solved"
      output: "Victoria!"
    carry_over:
      inventory: []
      flags: []
```

**Fixture: WorldState pre-construido**

```python
import pytest

@pytest.fixture
def world_state_with_item_in_room():
    """WorldState con 2 rooms, 1 ítem en room-01, jugador en room-01."""
    ...

@pytest.fixture
def world_state_with_enemy():
    """WorldState con 1 room, 1 NPC hostil, jugador con arma en inventario."""
    ...
```

**Fixture: Event log pre-construido**

```python
@pytest.fixture
def event_log_with_10_actions():
    """Lista de 10 EngineEvent de tipo action_resolved para tests de replay."""
    ...
```

---

## 8. Dependencias Python (`pyproject.toml`)

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "fortress-engine"
version = "0.1.0"
description = "Motor de Grafo Semántico para Ficción Interactiva Generativa"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Fortaleza Engine Contributors"}
]

dependencies = [
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "sqlalchemy>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "alembic>=1.13",
]

[project.scripts]
fortress-engine = "fortress_engine.cli.main:main"

[project.entry-points."fortress_engine.parsers"]
classic = "fortress_engine.plugins.classic_parser:ClassicParser"

[project.entry-points."fortress_engine.narrators"]
template = "fortress_engine.plugins.template_narrator:TemplateNarrator"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
python_files = "test_*.py"
```

**Justificación de dependencias**:
- **PyYAML**: parsing de archivos YAML del mundo. Sin dependencias externas, estable.
- **Pydantic ≥2.0**: validación de esquemas YAML al cargar. Solo se usa en la capa de carga (`entities/loader.py`). Las entidades en runtime son dataclasses simples.
- **SQLAlchemy ≥2.0**: ORM para persistencia. Abstrae el backend de base de datos. SQLite en v1.0, migrable a PostgreSQL en el futuro.
- **pytest ≥8.0**: framework de testing estándar.
- **pytest-cov**: cobertura de código.
- **Alembic**: migraciones de esquema de base de datos (v1.1+, opcional en MVP).

---

## 9. API de Plugins

### 9.1 Contratos

Los plugins son componentes intercambiables que implementan interfaces ABC. El motor nunca conoce la implementación concreta — solo la interfaz (PRD 5, PRD 6).

```python
from abc import ABC, abstractmethod
from fortress_engine.events.event_types import EngineEvent
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity


class ParserInterface(ABC):
    """Contrato para parsers (PRD 5)."""

    @abstractmethod
    def parse(self, raw_text: str, world_state: WorldState) -> 'ParsedCommand':
        """
        Traduce texto crudo a comando estructurado.

        Args:
            raw_text: texto ingresado por el jugador.
            world_state: estado actual del mundo (entidades, flags, protagonista activo).

        Returns:
            ParsedCommand con entity_ids resueltos.
        """
        ...


class NarratorInterface(ABC):
    """Contrato para narradores (PRD 6)."""

    @abstractmethod
    def initialize(self, event_bus: 'EventBus') -> None:
        """Se suscribe a eventos del motor que producen texto para el jugador."""
        ...

    @abstractmethod
    def handle_event(
        self, event: EngineEvent, world_state: WorldState
    ) -> str | None:
        """
        Procesa un evento del motor y produce texto para el jugador.
        Retorna None si el evento no produce texto visible.
        """
        ...
```

### 9.2 Carga de Plugins

> **SUPERSEDED (Epic #3)** — las funciones de carga `load_parser`/`load_narrator`
> que aparecen abajo quedan **reemplazadas** por la **plugin factory**
> (`plugins/factory.py`):
>
> ```python
> def create_parser(plugin_config: PluginConfig, world_language: str) -> ParserInterface
> def create_narrator(plugin_config: PluginConfig, world_language: str) -> NarratorInterface
> ```
>
> `PluginConfig` es un dataclass congelado con `name: str` y
> `options: dict[str, Any]`. La factory es el **único** código que toca los
> entry points (arch constant #7 preservada); el resto del motor habla con las
> interfaces. La factory inyecta `language=world_language` al construir la
> instancia. El Orquestador recibe las instancias ya construidas por **inyección
> de constructor**. El bloque de código siguiente es HISTÓRICO — se conserva
> como referencia pero no debe usarse en implementación nueva.

El motor descubre plugins mediante **Python entry points** definidos en `pyproject.toml`:

```toml
[project.entry-points."fortress_engine.parsers"]
classic = "fortress_engine.plugins.classic_parser:ClassicParser"

[project.entry-points."fortress_engine.narrators"]
template = "fortress_engine.plugins.template_narrator:TemplateNarrator"
```

Mecanismo de carga en el motor (HISTÓRICO — pre-factory, conservado solo como referencia):

```python
from importlib.metadata import entry_points

def load_parser(name: str) -> ParserInterface:
    """Carga un parser por nombre desde los entry points. SUPERSEDED: usar create_parser()."""
    eps = entry_points(group="fortress_engine.parsers")
    for ep in eps:
        if ep.name == name:
            cls = ep.load()
            return cls()
    raise ValueError(f"Parser '{name}' not found. Available: {[ep.name for ep in eps]}")

def load_narrator(name: str) -> NarratorInterface:
    """Carga un narrador por nombre desde los entry points. SUPERSEDED: usar create_narrator()."""
    eps = entry_points(group="fortress_engine.narrators")
    for ep in eps:
        if ep.name == name:
            cls = ep.load()
            return cls()
    raise ValueError(f"Narrator '{name}' not found. Available: {[ep.name for ep in eps]}")
```

El `world.yaml` especifica el idioma y qué parser/narrador usar. Se acepta la forma de objeto (`plugin:` + `options: {}`) y la forma legacy de string (`parser: "classic"`), ambas se normalizan a un `PluginConfigYAML`:

```yaml
# world.yaml
world_id: "fortaleza"
language: "es"
parser:
  plugin: "classic"
  options: {}
narrator:
  plugin: "template"
  options: {}
```

> Forma legacy equivalente (aún aceptada y normalizada): `parser: "classic"`,
> `narrator: "template"`.

### 9.3 Aislamiento de Errores

Los plugins son código externo desde la perspectiva del motor. Si un plugin lanza una excepción:
- El motor captura la excepción, emite `error_output` con `error_code="parser_error"` y `data={}`, y continúa.
- El plugin no puede tumbar el motor.
- En modo debug, el traceback completo se imprime en stderr.
- El texto del mensaje vive en el narrador (`error_output.parser_error` en `DEFAULT_SPANISH_MESSAGES`) — el motor no construye strings.

```python
def execute_turn(self, raw_text: str) -> None:
    try:
        parsed = self._parser.parse(raw_text, self._state)
    except Exception as e:
        self._event_bus.emit(EngineEvent.create(
            event_type="error_output",
            turn_number=self._state.turn_number,
            payload={
                "error_code": "parser_error",
                "data": {},
            },
            protagonist_id=self._state.active_protagonist_id,
        ))
        if __debug__:
            import traceback
            traceback.print_exc()
        return
    # ... resto del ciclo de turno
```

---

## 10. CLI (Interfaz de Línea de Comandos)

### 10.1 Comandos

```
fortress-engine run <world_path> [--save SLOT] [--parser NAME] [--narrator NAME]
    Inicia el juego interactivo.
    - world_path: ruta al directorio del mundo (ej: "worlds/fortaleza/")
    - --save SLOT: carga desde un slot de guardado (1, 2, 3, o "auto")
    - --parser NAME: parser a usar (default: "classic")
    - --narrator NAME: narrador a usar (default: "template")

fortress-engine validate <world_path>
    Valida la integridad de los datos del mundo.
    - Retorna 0 y "World is valid." si no hay errores.
    - Retorna 1 y lista de errores si los hay.
    - Opciones: --verbose (muestra warnings también)

fortress-engine test <world_path> --walkthrough <file> [--episode ID]
    Ejecuta un walkthrough en modo no interactivo.
    - Lee comandos del archivo (uno por línea).
    - Ejecuta cada comando secuencialmente.
    - Al finalizar, verifica que el goal del episodio se cumple.
    - Retorna 0 si el walkthrough completa exitosamente.
    - Retorna 1 si el walkthrough falla.
    - --episode ID: episodio a ejecutar (default: primer episodio disponible)
```

### 10.2 Implementación del comando `run`

```python
import argparse
import sys

def cmd_run(args: argparse.Namespace) -> int:
    """Ejecuta el juego en modo interactivo."""

    # 1. Cargar mundo
    loader = EntityLoader(args.world_path)
    world_config = loader.load_world_config()
    episodes = loader.load_episodes()

    # 2. Determinar parser, narrador y vocabulario (via plugin factory)
    vocabulary = loader.load_vocabulary()  # worlds/<name>/shared/vocabulary.yaml o None
    parser_cfg = world_config.get("parser", {"plugin": "classic", "options": {}})
    narrator_cfg = world_config.get("narrator", {"plugin": "template", "options": {}})
    if isinstance(parser_cfg, str):
        parser_cfg = {"plugin": parser_cfg, "options": {}}
    if isinstance(narrator_cfg, str):
        narrator_cfg = {"plugin": narrator_cfg, "options": {}}
    language = world_config.get("language", "es")
    parser = create_parser(PluginConfig(**parser_cfg), language)
    narrator = create_narrator(PluginConfig(**narrator_cfg), language)

    # 3. Inicializar estado, grafo, event bus
    state = WorldState()
    event_bus = EventBus()
    narrator.initialize(event_bus)

    # 4. Inicializar persistencia (si --save)
    repository = None
    if args.save:
        db_path = f"saves/slot_{args.save}/fortaleza.db"
        repository = SQLiteWorldStateRepository(db_path)
        save_system = EventSourcingSaveSystem(event_bus, repository, state_provider=lambda: state)
        event_bus.subscribe("game_saved", save_system._on_game_saved)

    # 5. Cargar episodio inicial
    episode_manager = EpisodeManager(episodes, args.world_path, event_bus)
    active_episode = episode_manager.get_available_episodes()[0]
    episode_data = loader.load_episode_data(active_episode.id, active_episode)

    # 6. Construir grafo
    graph = DualGraphEngine()
    graph.build_macro_graph(episode_data["rooms"], episode_data["macro_edges"])
    for he in episode_data["hyper_edges"]:
        # Determinar anchor: buscar target/spatial_anchor
        graph.add_hyper_edge(anchor_id, he)

    # 7. Inicializar WorldState
    for entity in episode_data["rooms"] + episode_data["items"] + episode_data["npcs"]:
        state.entities[entity.entity_id] = entity
    player = loader.load_shared_entities(active_episode.id)[0]
    state.entities[player.entity_id] = player
    state.player_controlled_entities = [player.entity_id]
    state.active_protagonist_id = player.entity_id
    state.current_episode_id = active_episode.id

    # TELEPORT a start_anchor
    state.get_entity(player.entity_id).spatial_anchor = active_episode.start_anchor

    # 8. Inicializar orquestador
    goal_evaluator = GoalEvaluator(active_episode.goal)
    orchestrator = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=event_bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_evaluator,
        episode_manager=episode_manager,
        repository=repository,
        save_system=save_system if args.save else None,
        vocabulary=vocabulary,
    )

    # 9. Emitir eventos de inicio
    event_bus.emit(EngineEvent.create(
        event_type="world_loaded",
        turn_number=0,
        payload={"world_id": world_config["world_id"], "episode_count": len(episodes)},
    ))
    event_bus.emit(EngineEvent.create(
        event_type="episode_started",
        turn_number=0,
        payload={
            "episode_id": active_episode.id,
            "episode_name": active_episode.name,
            "start_anchor_id": active_episode.start_anchor,
        },
    ))

    # 10. Bucle principal
    running = True
    while running:
        try:
            raw_text = input("> ")
        except (EOFError, KeyboardInterrupt):
            event_bus.emit(EngineEvent.create(
                event_type="game_over",
                turn_number=state.turn_number,
                payload={"reason": "player_quit"},
            ))
            break

        if not raw_text.strip():
            continue

        orchestrator.execute_turn(raw_text.strip())

        # Verificar si el juego terminó
        if state.get_flag("player_dead"):
            running = False
        # (game_completed también detiene — manejado dentro de execute_turn)

    return 0
```

### 10.3 Protocolo stdin/stdout

- El motor lee **una línea por turno** de stdin.
- La salida se escribe a stdout **a través del narrador**, que es un suscriptor del EventBus.
- El narrador V1 escribe directamente con `print()`. El narrador V2 (IA) podría escribir a stdout o a un callback.
- Los errores del motor (no del juego) se escriben a stderr.
- El código de salida: 0 = juego terminado normalmente, 1 = error de carga/validación.

---

## 11. Decisiones de Arquitectura

### 11.1 Dataclasses sobre Pydantic para Entidades en Runtime

**Decisión**: Las entidades (`Entity`, `HyperEdge`, `MacroEdge`, etc.) usan `@dataclass` de stdlib. Pydantic se usa exclusivamente para validar archivos YAML durante la carga del mundo.

**Razón**: Las dataclasses son más ligeras (sin overhead de validación en cada acceso). En runtime, las entidades ya fueron validadas durante la carga. Pydantic agregaría ~30% de overhead en cada operación de lectura/escritura de componentes, lo cual es innecesario porque el motor confía en los datos ya validados.

**Dónde se usa Pydantic**: `EntityYAML`, `HyperEdgeYAML`, `CliqueYAML`, etc., en `entities/loader.py`. Estos modelos validan la estructura al cargar desde YAML y luego se convierten a dataclasses.

### 11.2 Síncrono por Defecto

**Decisión**: El motor v1.0 es completamente síncrono y single-threaded. No hay `async/await` en el bucle principal. Los eventos se despachan sincrónicamente en el mismo hilo.

**Razón**: El motor es single-player y por turnos. La concurrencia agregaría complejidad sin beneficio. El AI Narrator (v1.2) correrá en un thread/process separado y se comunicará con el motor vía el EventBus (que se wrappeará con un lock cuando sea necesario). Ver Event System 4.3.

### 11.3 Event Log como Fuente de Verdad

**Decisión**: La persistencia usa Event Sourcing (GDD 2.6). El event log en SQLite es la fuente de verdad. Los snapshots son cachés de rendimiento, no la fuente autoritativa.

**Razón**:
- El log de eventos es inmutable y auditable.
- Permite debugging determinístico (replay para reproducir bugs).
- Compatible con el sistema de "rastro" del Fortaleza original.
- Facilita la integración con IA: el log es contexto estructurado sin ambigüedad.
- Si hay conflicto entre snapshot y event log, el event log gana.

### 11.4 Datos del Mundo Inmutables Después de la Carga

**Decisión**: Las entidades se cargan desde YAML a `WorldState`. Ningún archivo YAML se modifica en runtime. Todas las mutaciones ocurren en memoria.

**Razón**:
- Los archivos YAML son la definición estática del mundo (source of truth para diseñadores).
- El estado mutable vive en `WorldState` y se persiste vía Event Sourcing.
- Separación clara entre "diseño del mundo" (YAML) y "estado de la partida" (event log + snapshots).
- Permite que múltiples jugadores compartan los mismos archivos YAML con distintos save slots.

### 11.5 Sin ORM para Datos del Mundo

**Decisión**: SQLAlchemy se usa SOLO para la persistencia del estado de partida (event log, snapshots). Los datos del mundo (rooms, ítems, NPCs, Hiper-Aristas) viven en archivos YAML y se cargan en memoria como objetos Python.

**Razón**:
- Los datos del mundo son estáticos durante una partida. No necesitan queries complejas ni joins.
- YAML es el formato que los diseñadores editan. Ponerlos en SQLite requeriría herramientas de import/export.
- La carga en memoria desde YAML es instantánea para mundos de ~500 entidades.
- Separación de concerns: YAML = definición del mundo, SQLite = estado de la partida.

### 11.6 Colección, no Singleton para Protagonistas

**Decisión**: `WorldState.player_controlled_entities` es siempre una `list[str]`, incluso cuando el mundo define un solo protagonista. El código del motor itera sobre esta colección sin asumir `len() == 1`.

**Razón**: Restricción #8 del PRD. Si el motor asume singleton, agregar multi-protagonista en v1.1 requeriría refactorización masiva. Tratar `player_controlled_entities` como colección desde el día uno garantiza que la arquitectura está lista para múltiples protagonistas sin cambios en el núcleo.

### 11.7 Interfaces como ABCs para Plugins

**Decisión**: Parser y Narrador se definen como clases base abstractas (`ABC`). El motor depende de la interfaz, no de la implementación concreta.

**Razón**:
- Permite cambiar de parser/narrador sin modificar el motor (restricción #2 del PRD).
- Facilita testing: se puede inyectar un mock parser que retorna comandos predefinidos.
- Habilita la integración futura con IA (Parser Intencional V3, Narrador Inmersivo V2) como plugins que implementan la misma interfaz.
- Descubrimiento vía entry points: no hay importaciones hardcodeadas de implementaciones concretas.

---

## 12. Plan de Implementación (Roadmap)

Orden de implementación alineado con las prioridades MoSCoW del PRD sección 8.

### Fase 1 — Núcleo del Motor (MVP — Must Have)

| # | Tarea | Módulo(s) | Depende de |
|---|-------|-----------|------------|
| 1 | Project scaffolding | `pyproject.toml`, estructura de directorios | — |
| 2 | `Entity` dataclass + `components.py` | `entities/entity.py`, `entities/components.py` | 1 |
| 3 | Modelos Pydantic para validación YAML | `entities/loader.py` (modelos YAML) | 2 |
| 4 | `EntityLoader` — carga de archivos YAML | `entities/loader.py` | 3 |
| 5 | `WorldState` container + `FlagBook` | `engine/state.py` | 2 |
| 6 | 5 operadores atómicos | `engine/operators.py` | 5 |
| 7 | `MacroEdge` + `HyperEdge` + `Clique` dataclasses | `engine/graph.py` (modelos), o archivo separado | 2 |
| 8 | `DualGraphEngine` — construcción y consulta | `engine/graph.py` | 7, 5 |
| 9 | `EngineEvent` + `EventBus` | `events/event_types.py`, `events/event_bus.py` | — |
| 10 | `GoalEvaluator` — 6 tipos de condición + and/or | `engine/goal_evaluator.py` | 5 |
| 11 | Modelos ORM + `SQLiteWorldStateRepository` | `persistence/models.py`, `persistence/sqlite_repository.py` | 9 |
| 12 | `EventSourcingSaveSystem` | `persistence/event_log.py` | 11, 9 |
| 13 | `ParserInterface` ABC + `ClassicParser` V1 | `plugins/parser_interface.py`, `plugins/classic_parser.py` | 2, 5 |
| 14 | `NarratorInterface` ABC + `TemplateNarrator` V1 | `plugins/narrator_interface.py`, `plugins/template_narrator.py` | 9 |
| 15 | `Episode` + `EpisodeManager` | `engine/episode_manager.py` | 3, 8 |
| 16 | `TurnOrchestrator` (bucle principal) | `engine/orchestrator.py` | 6, 8, 9, 10, 13, 14, 15 |
| 17 | CLI — comando `run` | `cli/main.py` | 16, 4, 11 |
| 18 | Datos del mundo Fortaleza en YAML | `worlds/fortaleza/` (88 rooms, ~120 ítems, ~50 NPCs, ~450 Hiper-Aristas, ~100 aristas Macro) | 3 |

### Fase 2 — Validación (MVP — Must Have)

| # | Tarea | Módulo(s) | Depende de |
|---|-------|-----------|------------|
| 19 | Tests unitarios de operadores | `tests/test_engine/test_operators.py` | 6 |
| 20 | Tests unitarios de `GoalEvaluator` | `tests/test_engine/test_goal_evaluator.py` | 10 |
| 21 | Tests unitarios de `DualGraphEngine` (clique + macro edges) | `tests/test_engine/test_graph.py` | 8 |
| 22 | Tests unitarios de `EventBus` | `tests/test_events/test_event_bus.py` | 9 |
| 23 | Tests unitarios de `EntityLoader` (carga + validación) | `tests/test_entities/test_loader.py` | 4 |
| 24 | Tests unitarios de `ClassicParser` con comandos de Fortaleza | `tests/` (nuevo archivo) | 13 |
| 25 | Tests de integración: event sourcing round-trip | `tests/test_persistence/test_event_sourcing.py` | 12 |
| 26 | Tests de integración: ciclo completo de turno | `tests/test_integration/` (nuevo archivo) | 16 |
| 27 | Tests de integración: transición de episodio | `tests/test_integration/` (nuevo archivo) | 15, 16 |
| 28 | Fortaleza walkthrough como test de aceptación | `tests/test_integration/test_walkthrough.py` | 18, 16 |
| 29 | CLI — comando `validate` | `cli/main.py` | 4 |
| 30 | CLI — comando `test --walkthrough` | `cli/main.py` | 28 |

### Fase 3 — v1.1 (Should Have)

| # | Tarea |
|---|-------|
| 31 | Herramienta de edición de mundos (CLI o visual) |
| 32 | Validador de mundos mejorado (rooms inalcanzables, puzles sin solución) |
| 33 | Cerebro scripteado de NPCs (selección por prioridad) |
| 34 | Comandos multi-protagonista: `CAMBIAR A`, `GRUPO`, `ESPERAR` |
| 35 | Cliques multi-protagonista (Hiper-Aristas con múltiples `player_controlled`) |
| 36 | Cerebros autónomos para otros protagonistas |
| 37 | Sistema de pistas (tres niveles: sutil, medio, explícito) |
| 38 | Múltiples slots de guardado (mínimo 3) |

### Fase 4 — v1.2 (Could Have)

| # | Tarea |
|---|-------|
| 39 | Parser Intencional con IA (V3) — LLM traduce texto libre a tupla |
| 40 | Narrador Inmersivo con IA (V2) — LLM decora resultados con prosa |
| 41 | Cerebro generativo de NPCs — LLM selecciona acciones |
| 42 | Mundos de ejemplo adicionales (tutorial 5 rooms + demo) |
| 43 | Visualización de grafos (herramienta de debugging) |

---

## Referencias

| Documento | Descripción |
|-----------|-------------|
| `prd.md` | Product Requirements Document v2.0 |
| `gdd.md` | Game Design Document v1.0 |
| `docs/13-event-system.md` | Diseño del sistema de eventos |
| `docs/12-engine-gap-analysis.md` | Gap analysis entre PRD y Fortaleza |
| `docs/06-mechanics.md` | Mecánicas del juego original |
| `docs/08-room-graph.md` | Grafo de conexiones entre habitaciones |
| `docs/09-walkthrough.md` | Walkthrough comando por comando |
| `docs/04-puzzles.md` | Los 93 puzles con mecánicas |
| `docs/10-puzzle-dependencies.md` | Grafo de dependencias entre puzles |
| `docs/07-vocabulary.md` | 37 verbos y ~180 sustantivos del parser |

---

*Documento preparado a partir del PRD v2.0, GDD v1.0, y el Event System #13. Define el HOW del motor: estructura de clases, firmas de métodos, esquemas de base de datos, flujos de ejecución y estrategia de testing.*
