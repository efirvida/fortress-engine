# 13 — Sistema de Eventos y Señales del Motor de Grafo Semántico

**Versión**: 1.0
**Tipo**: Documento de Diseño Técnico
**Idioma**: Español
**Depende de**: PRD v2.0 (secciones 4, 6, 7, 10), Gap Analysis (#12)

---

## 1. Principio de Diseño

> **La transición es señal, no presentación.**

El motor de grafo semántico es lógica pura — no sabe nada sobre cómo se presenta la información. La capa de UI es completamente independiente y se suscribe a los eventos que el motor emite. El motor dispara señales; la UI decide cómo renderizarlas.

Este principio es la base de la separación de concerns del PRD (sección 9: "Ninguna capa conoce los detalles de las otras") y es el habilitador de los tres targets de UI:

| UI | Cómo consume eventos | Cuándo |
|----|---------------------|--------|
| **Terminal (V1)** | Renderiza texto plano en consola | MVP |
| **Web (V2)** | Misma suscripción, renderiza HTML/CSS | Post-MVP |
| **Narrador IA (V1.2)** | Decora eventos con prosa generada por LLM | Could Have |

Las tres UIs funcionan con los mismos eventos del motor. Ninguna requiere cambios en el motor.

### 1.1 Qué es un Evento

Un evento es un registro inmutable de algo que ocurrió dentro del motor durante la resolución de un turno. No es una solicitud ni una promesa — es un hecho consumado. Cuando el motor emite `entity_teleported`, la entidad YA cambió de posición. El evento es la notificación, no la acción.

### 1.2 Qué NO es un Evento

- No es un comando del jugador (eso es input, que se recibe antes del ciclo)
- No es una consulta al estado (el estado se lee directamente del State Container)
- No es una promesa de UI ("vas a mostrar esto") — es una señal de motor ("esto ocurrió")
- No es asíncrono — todos los eventos se despachan sincrónicamente durante la resolución del turno

---

## 2. Taxonomía Completa de Eventos

Los eventos se agrupan en seis categorías. Cada evento tiene un propósito claro y un payload definido.

### 2.1 Eventos de Mundo

Señales que marcan hitos en la vida del mundo: carga, transiciones entre episodios, victoria y derrota.

| Evento | Cuándo se emite | Payload |
|--------|----------------|---------|
| `world_loaded` | Al cargar un mundo completo (todos los episodios, entidades, grafos) | `{ world_id, episode_count }` |
| `episode_started` | Al iniciar un episodio (inicial o por transición) | `{ episode_id, episode_name, start_room_id }` |
| `episode_completed` | Al cumplirse la condición de victoria del episodio | `{ episode_id, victory_text, carry_over: { inventory: [], flags: [] } }` |
| `episode_transition` | Durante la transición entre episodios (antes de cargar el nuevo grafo) | `{ from_episode_id, to_episode_id, carry_over_applied: { inventory: [], flags: [] } }` |
| `game_completed` | Al completar el último episodio del mundo | `{ world_id, total_turns }` |
| `game_over` | Al morir el protagonista activo o el jugador elegir salir | `{ reason: str, turn_number }` |

**Relación con el Gap #8 (Soporte Episódico)**: `episode_started`, `episode_completed` y `episode_transition` son las señales que permiten que la UI maneje la transición entre Partes I y II de Fortaleza sin que el motor conozca los detalles narrativos. La UI recibe `episode_transition` y decide si muestra una pantalla de "Fin de la Parte I", una animación, o simplemente carga el nuevo mapa.

**Flujo episódico**:

```
world_loaded("fortaleza", episode_count=2)
  └─ episode_started("episode-01", "La Fortaleza", "room-01")
       └─ [turnos de la Parte I...]
       └─ episode_completed("episode-01", victory_text, carry_over={})
       └─ episode_transition("episode-01", "episode-02", carry_over_applied={})
       └─ episode_started("episode-02", "La Fortaleza II", "room-01")
            └─ [turnos de la Parte II...]
            └─ episode_completed("episode-02", victory_text, carry_over={})
            └─ game_completed("fortaleza", total_turns=847)
```

### 2.2 Eventos de Turno

El ciclo de vida completo de un turno, desde que se inicia hasta que termina.

| Evento | Cuándo se emite | Payload |
|--------|----------------|---------|
| `turn_started` | Al inicio de cada ciclo de turno, antes de esperar input | `{ turn_number, active_protagonist_id }` |
| `input_received` | Cuando el parser recibe y valida el texto del jugador | `{ raw_text, protagonist_id }` |
| `action_attempted` | Cuando una Hiper-Arista es seleccionada para ejecución (antes de aplicar operadores) | `{ hyper_edge_id, clique: { subject, verb, target, instrument, context }, protagonist_id }` |
| `action_resolved` | Cuando una Hiper-Arista completa su ejecución (todos los operadores aplicados) | `{ hyper_edge_id, operators_executed: [str], has_effects: bool, protagonist_id }` |
| `npc_turn_started` | Al inicio del turno de NPCs (fase 3 del orquestador) | `{ turn_number }` |
| `npc_turn_ended` | Al finalizar el turno de todos los NPCs | `{ turn_number, npcs_acted: int }` |
| `turn_ended` | Al finalizar completamente el ciclo de turno | `{ turn_number, actions_resolved: int }` |

**Nota**: `action_attempted` y `action_resolved` son eventos separados porque una Hiper-Arista puede fallar durante la validación de la clique (después del parseo) o durante la ejecución de operadores (ej: peso excede capacidad). La UI puede usar `action_attempted` para feedback inmediato ("El jugador intenta atacar...") y `action_resolved` para el resultado final.

### 2.3 Eventos de Cambio de Estado

Cada uno de los cinco operadores atómicos emite un evento cuando se ejecuta exitosamente. Estos son los eventos más granulares — reflejan cambios reales en el State Container.

| Evento | Operador | Payload |
|--------|----------|---------|
| `entity_transferred` | TRANSFER | `{ entity_id, from_container_id, to_container_id }` |
| `entity_transformed` | TRANSFORM | `{ entity_id, component_key, old_value, new_value }` |
| `entity_combined` | COMBINE | `{ input_entity_ids: [str], output_entity_id }` |
| `flag_set` | FLAG | `{ flag_name, old_value, new_value }` |
| `entity_teleported` | TELEPORT | `{ entity_id, from_room_id, to_room_id }` |

**Estos eventos son producidos por el State Container, no por las Hiper-Aristas directamente**. Cuando una Hiper-Arista ejecuta `TRANSFER(Antorcha, room_03, player_inventory)`, el State Container aplica el cambio y emite `entity_transferred`. Esto garantiza que el event log refleje fielmente el estado real — si un TRANSFER falla (peso excedido, contenedor inválido), no se emite el evento.

### 2.4 Eventos de Narración

Estos eventos transportan texto que la UI debe mostrar al jugador. Son producidos por el narrador (V1: plantillas, V2: IA) o directamente por el motor para mensajes de sistema.

| Evento | Cuándo se emite | Payload |
|--------|----------------|---------|
| `room_entered` | Cuando el protagonista activo cambia de habitación (via TELEPORT o cruce de Arista Macro) | `{ room_id, room_name, description, protagonist_id }` |
| `room_described` | Cuando el jugador ejecuta un comando explícito de examinar la habitación (LOOK/MIRAR) | `{ room_id, description, protagonist_id }` |
| `item_examined` | Cuando el jugador examina un ítem (EXAMINE/EXAMINAR) | `{ item_id, item_name, description, protagonist_id }` |
| `inventory_listed` | Cuando el jugador consulta su inventario (INVENTORY/INVENTARIO) | `{ protagonist_id, items: [{ id, name, weight }], total_weight, capacity }` |
| `protagonists_listed` | Cuando el jugador usa el comando GRUPO | `{ protagonists: [{ id, name, location, status }] }` |
| `action_output` | Texto asociado a la ejecución de una Hiper-Arista (campo `output` en la definición YAML de la acción) | `{ hyper_edge_id, text, protagonist_id }` |
| `error_output` | Errores de parser, validación de clique, ejecución de operadores | `{ error_code, message, protagonist_id }` |
| `system_message` | Mensajes del motor que no pertenecen a una acción específica (ej: "La partida se ha guardado.") | `{ message }` |

**Relación con el Gap #2 (Salida de texto asociada a operadores)**: El campo `output` de las Hiper-Aristas se emite como `action_output`. El narrador por plantillas (V1) usa este texto directamente. El narrador IA (V2) puede usarlo como prompt base y decorarlo.

### 2.5 Eventos de NPC

Cuando un NPC ejecuta una acción autónoma (durante la fase 3 del orquestador de turnos), el motor emite estos eventos desde la perspectiva del protagonista activo.

| Evento | Cuándo se emite | Payload |
|--------|----------------|---------|
| `npc_acted` | Cuando un NPC completa una acción (Hiper-Arista ejecutada desde su cerebro) | `{ npc_id, npc_name, hyper_edge_id, operators_executed: [str], affects_protagonist: bool }` |
| `npc_dialogue` | Cuando un NPC produce texto (campo `output` de su Hiper-Arista) | `{ npc_id, npc_name, text }` |
| `npc_entered` | Cuando un NPC cambia de habitación (por TELEPORT o movimiento autónomo) | `{ npc_id, npc_name, from_room_id, to_room_id }` |
| `npc_died` | Cuando un NPC es transferido a `null` (destrucción/muerte) | `{ npc_id, npc_name, killed_by_id }` |

### 2.6 Eventos de Meta-Juego

Señales que no afectan la simulación pero son relevantes para la experiencia del jugador.

| Evento | Cuándo se emite | Payload |
|--------|----------------|---------|
| `game_saved` | Al completar una operación de guardado | `{ save_slot_id, turn_number, action_log_position }` |
| `game_loaded` | Al restaurar un estado desde guardado | `{ save_slot_id, turn_number }` |
| `protagonist_switched` | Cuando el jugador ejecuta `CAMBIAR A <nombre>` | `{ from_protagonist_id, to_protagonist_id }` |
| `save_replay_started` | Al iniciar la reproducción de un event log (load por event sourcing) | `{ save_slot_id, total_actions }` |
| `save_replay_ended` | Al finalizar la reproducción del event log | `{ save_slot_id, turn_number }` |

**Nota sobre `game_saved`**: El `action_log_position` es el índice en el event log donde se tomó el snapshot. Esto permite que el save/load por event sourcing sepa exactamente hasta qué punto re-ejecutar el log (ver sección 8).

---

## 3. Formato de Payload

### 3.1 Estructura Base

Todo evento comparte una estructura común:

```python
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

@dataclass(frozen=True)
class EngineEvent:
    event_id: UUID                # identificador único del evento
    type: str                     # tipo del evento (taxonomía anterior)
    turn_number: int              # turno actual (para ordenamiento/contexto)
    timestamp: float              # reloj monótono (time.monotonic()) para ordenamiento preciso
    payload: dict[str, Any]       # datos específicos del tipo de evento
    protagonist_id: str | None    # protagonista relacionado con este evento (None = global)
    episode_id: str | None        # episodio actual
```

**Decisiones de diseño**:

- `frozen=True`: los eventos son inmutables. Una vez emitidos, no se modifican. Esto es crítico para event sourcing y replay.
- `UUID` para `event_id`: garantiza unicidad global sin contador centralizado. Permite que eventos de distintas fuentes (motor, NPCs, plugins) coexistan sin colisiones.
- `time.monotonic()` para `timestamp`: no usa `time.time()` porque el reloj del sistema puede ajustarse (NTP, horario de verano). El reloj monótono solo avanza, lo que garantiza ordenamiento correcto durante replay.
- `payload` como `dict[str, Any]`: flexible pero con contratos implícitos por tipo de evento (documentados en la taxonomía).

### 3.2 Ejemplos de Payload por Tipo

```python
# Evento de Mundo
EngineEvent(
    event_id=UUID("a1b2c3d4-..."),
    type="world_loaded",
    turn_number=0,
    timestamp=0.001,
    payload={"world_id": "fortaleza", "episode_count": 2},
    protagonist_id=None,
    episode_id=None,
)

# Evento de Cambio de Estado
EngineEvent(
    event_id=UUID("e5f6g7h8-..."),
    type="entity_transferred",
    turn_number=42,
    timestamp=142.837,
    payload={
        "entity_id": "antorcha_01",
        "entity_name": "Antorcha",
        "from_container_id": "room_03",
        "to_container_id": "player_inventory",
        "hyper_edge_id": "tomar_antorcha",
    },
    protagonist_id="player_1",
    episode_id="episode-01",
)

# Evento de Narración
EngineEvent(
    event_id=UUID("i9j0k1l2-..."),
    type="action_output",
    turn_number=42,
    timestamp=142.841,
    payload={
        "hyper_edge_id": "tomar_antorcha",
        "text": "Tomas la antorcha de la pared. La llama titila débilmente.",
        "source": "template",  # "template" | "ai" | "system"
    },
    protagonist_id="player_1",
    episode_id="episode-01",
)
```

### 3.3 Serialización

Todos los eventos deben ser serializables a JSON para el event log de save/load:

```python
def event_to_dict(event: EngineEvent) -> dict:
    return {
        "event_id": str(event.event_id),
        "type": event.type,
        "turn_number": event.turn_number,
        "timestamp": event.timestamp,
        "payload": event.payload,
        "protagonist_id": event.protagonist_id,
        "episode_id": event.episode_id,
    }

def event_from_dict(data: dict) -> EngineEvent:
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

Los payloads deben contener solo tipos JSON primitivos (str, int, float, bool, None, list, dict). Nada de objetos Python, dataclasses anidadas ni referencias circulares.

---

## 4. Arquitectura del EventBus

### 4.1 Diseño

El EventBus es un observer pattern clásico implementado con componentes de stdlib. Sin dependencias externas.

```python
from collections import defaultdict
from typing import Callable

EventHandler = Callable[[EngineEvent], None]

class EventBus:
    """
    Bus de eventos síncrono con patrón Observer.

    Los suscriptores se registran por tipo de evento (string).
    Un suscriptor especial con event_type="*" recibe TODOS los eventos.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Registra un handler para un tipo de evento específico.

        Usa '*' para suscribirse a todos los eventos.
        """
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remueve un handler previamente registrado."""
        try:
            self._subscribers[event_type].remove(handler)
        except ValueError:
            pass  # handler no estaba registrado — no es error

    def emit(self, event: EngineEvent) -> None:
        """Despacha un evento a todos los suscriptores relevantes.

        El despacho es síncrono: todos los handlers se ejecutan antes de
        que emit() retorne. Los errores en handlers individuales no
        interrumpen a los demás handlers ni al motor.
        """
        handlers = self._subscribers.get(event.type, []) + self._subscribers.get("*", [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # El handler de UI falló — no detenemos el motor.
                # En debug mode, logueamos el error.
                if __debug__:
                    import sys
                    print(f"[EventBus] Error en handler {handler.__name__} "
                          f"para evento {event.type}: {e}", file=sys.stderr)
```

### 4.2 Suscriptores Estándar

El motor registra estos suscriptores por defecto al inicializarse. Cada uno es independiente y puede agregarse o removerse sin afectar a los demás.

```
┌──────────────────────────────────────────────────────────────────┐
│                         EVENTBUS                                  │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐              │
│  │  UI Layer   │  │ Save System │  │ Debug Console │              │
│  │             │  │             │  │              │              │
│  │ • room_     │  │ • *          │  │ • *          │              │
│  │   entered   │  │   (all      │  │   (all       │              │
│  │ • action_   │  │   events →  │  │   events →   │              │
│  │   output    │  │   append    │  │   pretty     │              │
│  │ • error_    │  │   to log)   │  │   print)     │              │
│  │   output    │  │             │  │              │              │
│  │ • game_over │  │             │  │              │              │
│  │ • input_    │  │             │  │              │              │
│  │   received  │  │             │  │              │              │
│  └─────────────┘  └─────────────┘  └──────────────┘              │
│                                                                   │
│  ┌─────────────┐  ┌─────────────────┐                            │
│  │ AI Narrator │  │ Test Harness    │                            │
│  │ (v1.2)      │  │                 │                            │
│  │             │  │ • input_        │                            │
│  │ • entity_*  │  │   received      │                            │
│  │ • flag_set  │  │ • action_       │                            │
│  │ • room_     │  │   resolved      │                            │
│  │   entered   │  │ • * (asserts)   │                            │
│  └─────────────┘  └─────────────────┘                            │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Propiedades del Despacho

| Propiedad | Valor | Justificación |
|-----------|-------|---------------|
| **Modo** | Síncrono | Single-player, sin concurrencia real. Simplifica el modelo mental y el debugging. |
| **Orden** | FIFO por tipo de evento | Los handlers se llaman en orden de registro. |
| **Errores** | Aislados por handler | Un handler que lanza excepción no afecta a los demás. |
| **Backpressure** | No existe | El motor no espera a que la UI termine de renderizar. Si la UI es lenta, pierde frames — el estado del motor siempre es consistente. |
| **Thread-safety** | No requerida | Todo corre en un solo hilo. Si en el futuro se agrega concurrencia (ej: AI narrator async), el EventBus se wrappea con un lock. |

### 4.4 Ciclo de Vida del EventBus

```
1. world_loaded → se crea el EventBus (uno por sesión de mundo)
2. Se registran suscriptores (UI, save system, debug console)
3. Durante cada turno, el motor emite eventos a través del EventBus
4. game_completed o game_over → el EventBus se destruye al cerrar el mundo
```

El EventBus **no es un singleton global**. Pertenece a la instancia del motor. Si en el futuro se ejecutan múltiples mundos en paralelo, cada uno tiene su propio EventBus.

---

## 5. Ciclo de Turno Anotado con Eventos

El siguiente es el flujo completo de un turno donde el jugador ataca a un Guard con el arma correcta. Cada paso está anotado con el evento que se emite y el componente del motor que lo produce.

```
TURNO #42 — Protagonista: "player_1" en room_15 ("Sala del Guard")

═══════════════════════════════════════════════════════════════════════
FASE 1: Turno del Protagonista Activo
═══════════════════════════════════════════════════════════════════════

01. TurnOrchestrator
    emit: turn_started({
        turn_number: 42,
        active_protagonist_id: "player_1",
    })

02. UI espera input del jugador...
    Jugador escribe: "atacar guardia con espada"

03. Parser
    texto → tupla: { subject: "player_1", verb: "atacar", target: "guard_01", instrument: "espada_01" }

04. TurnOrchestrator
    emit: input_received({
        raw_text: "atacar guardia con espada",
        protagonist_id: "player_1",
    })

05. GraphEngine — validación de Clique de Participación
    Busca Hiper-Aristas con verb="atacar", target="guard_01" en el Grafo Micro de room_15
    ┌─────────────────────────────────────────────────────────┐
    │ Hiper-Arista: "atacar_guard_con_espada"                  │
    │   priority: 10                                          │
    │   clique:                                               │
    │     subject: "player_1"         ✓ (está en room_15)     │
    │     verb: "atacar"              ✓ (matchea input)       │
    │     target: "guard_01"          ✓ (está en room_15)     │
    │     instrument: "espada_01"     ✓ (en inventario)       │
    │   clique formada → se ejecuta                           │
    └─────────────────────────────────────────────────────────┘

06. GraphEngine
    emit: action_attempted({
        hyper_edge_id: "atacar_guard_con_espada",
        clique: {
            subject: "player_1",
            verb: "atacar",
            target: "guard_01",
            instrument: "espada_01",
        },
        protagonist_id: "player_1",
    })

07. GraphEngine — Ejecuta secuencia de operadores de la Hiper-Arista:

    07a. StateContainer ejecuta: TRANSFER(guard_01, room_15, null)  // Guard muere
         emit: entity_transferred({
             entity_id: "guard_01",
             entity_name: "Guardia",
             from_container_id: "room_15",
             to_container_id: null,
             hyper_edge_id: "atacar_guard_con_espada",
         })
         emit: npc_died({
             npc_id: "guard_01",
             npc_name: "Guardia",
             killed_by_id: "player_1",
         })

    07b. StateContainer ejecuta: FLAG("guard_sala_15_muerto", true)
         emit: flag_set({
             flag_name: "guard_sala_15_muerto",
             old_value: false,
             new_value: true,
         })

08. Narrador — Hiper-Arista tiene campo output:
    emit: action_output({
        hyper_edge_id: "atacar_guard_con_espada",
        text: "El Guardia cae al suelo. Con su último aliento susurra: 'La contraseña de la Puerta Negra... es MARIPOSA...'",
        source: "template",
        protagonist_id: "player_1",
    })

09. GraphEngine
    emit: action_resolved({
        hyper_edge_id: "atacar_guard_con_espada",
        operators_executed: ["TRANSFER", "FLAG"],
        has_effects: true,
        protagonist_id: "player_1",
    })

═══════════════════════════════════════════════════════════════════════
FASE 2: Turno de Otros Protagonistas
═══════════════════════════════════════════════════════════════════════

    [En Fortaleza solo hay un protagonista — esta fase no produce eventos]

═══════════════════════════════════════════════════════════════════════
FASE 3: Turno de NPCs (Escena)
═══════════════════════════════════════════════════════════════════════

10. TurnOrchestrator
    emit: npc_turn_started({ turn_number: 42 })

11. [NPC "troll_03" en room_12 evalúa su cerebro]
    Hiper-Arista disponible: "troll_gritar" (sin precondiciones, siempre ejecutable)

12. GraphEngine
    emit: npc_acted({
        npc_id: "troll_03",
        npc_name: "Troll",
        hyper_edge_id: "troll_gritar",
        operators_executed: [],
        affects_protagonist: false,
    })
    emit: npc_dialogue({
        npc_id: "troll_03",
        npc_name: "Troll",
        text: "¡AAAAARRRGGGGG!",
    })

13. TurnOrchestrator
    emit: npc_turn_ended({
        turn_number: 42,
        npcs_acted: 1,
    })

═══════════════════════════════════════════════════════════════════════
FASE 4: Resolución y Cierre
═══════════════════════════════════════════════════════════════════════

14. GoalEvaluator — verifica condiciones de victoria
    [No se cumplen todavía — quedan 3 Guards más]

15. TurnOrchestrator
    emit: turn_ended({
        turn_number: 42,
        actions_resolved: 1,
    })

    [El motor espera el próximo input del jugador]
```

### 5.1 Caso: Acción que Falla (Peso Excedido)

```
TurnOrchestrator → action_attempted("tomar_bote", {...})
StateContainer → intenta TRANSFER(Bote, room_12, player_inventory)
StateContainer → calcula peso actual (35) + peso del Bote (39) = 74 > 40
StateContainer → LA TRANSFERENCIA FALLA — no se emite entity_transferred
TurnOrchestrator → action_resolved("tomar_bote", operators_executed=[], has_effects=false)
Narrador → error_output("tomar_bote", "Sería demasiado peso.")
```

**Principio clave**: solo los operadores que efectivamente modifican el estado emiten eventos. Si un TRANSFER falla por validación de peso, no hay `entity_transferred`. La UI recibe `action_resolved(has_effects=false)` y `error_output(...)` para informar al jugador.

---

## 6. Contrato de UI

El contrato define qué eventos debe manejar cada UI y cuáles son opcionales. Un UI que no maneja un evento simplemente lo ignora — el motor sigue funcionando.

### 6.1 Eventos Obligatorios (MUST handle)

Todo UI, sin importar su naturaleza (terminal, web, IA), DEBE suscribirse y responder a estos eventos:

| Evento | Qué debe hacer la UI |
|--------|---------------------|
| `room_entered` | Mostrar la descripción de la habitación al jugador |
| `action_output` | Mostrar el texto de salida de la acción |
| `error_output` | Mostrar el mensaje de error al jugador |
| `game_over` | Mostrar pantalla de muerte/derrota y opciones (reiniciar, cargar, salir) |
| `game_completed` | Mostrar pantalla de victoria final |
| `episode_completed` | Mostrar texto de victoria del episodio |
| `input_received` | Agregar el comando al historial de comandos del jugador |
| `system_message` | Mostrar mensaje del sistema |

### 6.2 Eventos Opcionales (MAY handle)

Estos eventos son decisiones de presentación. La UI decide si y cómo usarlos.

| Evento | Ejemplo de uso (Web UI) | Terminal UI |
|--------|------------------------|-------------|
| `entity_teleported` | Animar transición de habitación (fade out/in, slide) | Ignorar — `room_entered` ya muestra la nueva descripción |
| `entity_transferred` | Animar el ítem volando al inventario | Mostrar mensaje simple: "Tomaste la Antorcha." |
| `entity_transformed` | Partículas o efecto visual de transformación | Ignorar — el cambio se refleja en la descripción |
| `entity_combined` | Animación de fusión de ítems | Ignorar |
| `flag_set` | Mostrar notificación toast: "Nuevo conocimiento adquirido" | Ignorar — es información implícita |
| `npc_acted` | Animar al NPC realizando su acción | Opcional: mostrar en log de eventos |
| `npc_dialogue` | Mostrar globo de diálogo sobre el NPC | Mostrar texto: "El Troll grita: ¡AAAAARRRGGGGG!" |
| `npc_entered` | Animar al NPC entrando a la sala | Mostrar mensaje: "El Guardia entra en la sala." |
| `npc_died` | Animación de muerte del NPC | Mostrar texto ya incluido en `action_output` |
| `turn_started` / `turn_ended` | Actualizar UI chrome (número de turno, indicador de loading) | Ignorar |
| `action_attempted` / `action_resolved` | Progress indicator durante resolución | Ignorar |
| `protagonist_switched` | Actualizar HUD con el nuevo protagonista activo | Mostrar mensaje: "Ahora controlas a Faramir." |
| `protagonists_listed` | Mostrar panel de grupo con avatares | Mostrar lista de texto |
| `inventory_listed` | Mostrar panel de inventario con iconos | Mostrar lista de texto |
| `save_replay_started` / `save_replay_ended` | Mostrar barra de progreso de carga | Mostrar "Cargando..." |

### 6.3 Interfaz de UI

Cada UI implementa una interfaz común:

```python
from abc import ABC, abstractmethod

class UIInterface(ABC):
    """Interfaz que toda UI debe implementar."""

    @abstractmethod
    def initialize(self, event_bus: EventBus) -> None:
        """Registra los handlers de eventos en el EventBus."""
        ...

    @abstractmethod
    def wait_for_input(self, protagonist_id: str) -> str:
        """Bloquea hasta que el jugador ingrese un comando.
        Retorna el texto crudo del comando."""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Limpia recursos de la UI al cerrar el mundo."""
        ...
```

**Ejemplo: UI de Terminal (V1)**:

```python
class TerminalUI(UIInterface):
    def initialize(self, event_bus: EventBus) -> None:
        event_bus.subscribe("room_entered", self._on_room_entered)
        event_bus.subscribe("action_output", self._on_action_output)
        event_bus.subscribe("error_output", self._on_error_output)
        event_bus.subscribe("game_over", self._on_game_over)
        event_bus.subscribe("game_completed", self._on_game_completed)
        event_bus.subscribe("episode_completed", self._on_episode_completed)
        event_bus.subscribe("input_received", self._on_input_received)
        event_bus.subscribe("system_message", self._on_system_message)
        event_bus.subscribe("npc_dialogue", self._on_npc_dialogue)
        event_bus.subscribe("npc_entered", self._on_npc_entered)
        # No se suscribe a entity_teleported, flag_set, etc.
        # — la terminal no necesita animaciones.

    def _on_room_entered(self, event: EngineEvent) -> None:
        p = event.payload
        print(f"\n{p['room_name']}")
        print("-" * len(p['room_name']))
        print(p['description'])

    def _on_action_output(self, event: EngineEvent) -> None:
        print(event.payload["text"])

    def _on_error_output(self, event: EngineEvent) -> None:
        print(f"[ERROR] {event.payload['message']}")

    def _on_game_over(self, event: EngineEvent) -> None:
        print(f"\n=== FIN DEL JUEGO ===")
        print(f"Motivo: {event.payload['reason']}")

    # ... etc
```

### 6.4 Lo que la UI NUNCA debe hacer

- **No debe modificar el estado del motor.** La UI recibe eventos — no emite comandos de vuelta (el input del jugador va por otro canal: `wait_for_input()`).
- **No debe acceder directamente al State Container.** Si necesita consultar el estado (ej: para mostrar un mapa), usa la API pública del motor (`engine.get_world_state()`), no los eventos.
- **No debe asumir orden de eventos entre handlers.** Dos handlers del mismo tipo de evento no tienen orden garantizado entre sí (sí tienen orden FIFO de registro para el mismo tipo).
- **No debe bloquear el Event Loop.** Si un handler de UI hace una operación costosa (ej: llamada HTTP en Web UI), debe delegarla a un worker/secuencia asíncrona. El handler debe retornar rápido.

---

## 7. Integración con Narrador IA

El Narrador IA (v1.2, Could Have) es un suscriptor más del EventBus. No es parte del motor — es un plugin de la capa de interfaz.

### 7.1 Suscripciones del Narrador IA

El narrador IA se suscribe a eventos de cambio de estado y los decora con prosa generada por LLM:

```python
class AINarratorPlugin:
    def initialize(self, event_bus: EventBus, llm_client) -> None:
        self.llm = llm_client
        self.event_bus = event_bus

        # Se suscribe a eventos que disparan narración decorada
        event_bus.subscribe("entity_transferred", self._decorate_transfer)
        event_bus.subscribe("entity_transformed", self._decorate_transform)
        event_bus.subscribe("entity_combined", self._decorate_combine)
        event_bus.subscribe("room_entered", self._decorate_room)
        event_bus.subscribe("npc_acted", self._decorate_npc_action)
        event_bus.subscribe("flag_set", self._decorate_flag)

        # Se suscribe a action_output para reemplazar texto de plantilla
        event_bus.subscribe("action_output", self._decorate_output)
```

### 7.2 Flujo de Decoración

El narrador IA **reemplaza** el `action_output` generado por el narrador de plantillas, pero **no modifica** los eventos de cambio de estado. El motor emite ambos; la UI decide cuál mostrar:

```
Motor emite:
  entity_transferred(antorcha, room_03, player_inventory)  ← hecho inmutable
  action_output("Tomas la antorcha.")                       ← texto crudo (narrador V1)

Narrador IA intercepta action_output:
  1. Recibe el evento entity_transferred
  2. Consulta el estado actual de la escena (vía API pública del motor):
     - ¿Qué hay en la habitación?
     - ¿Qué banderas están activas?
     - ¿Cuál es el tono narrativo configurado?
  3. Construye un prompt para el LLM:
     """
     Acción: El jugador toma la Antorcha de la pared.
     Escena: Habitación oscura, húmeda, con olor a moho.
     Estilo: Gótico, atmosférico, primera persona.
     Texto base: "Tomas la antorcha."
     Genera una descripción inmersiva de 2-3 oraciones.
     """
  4. El LLM genera: "Tomas la antorcha de bronce frío de su soporte en
     la pared. La llama titila, proyectando sombras danzantes que revelan
     grietas en la piedra que antes no habías notado. El pasillo parece
     menos amenazante ahora — o quizás solo lo parece."
  5. Emite un NUEVO action_output con source="ai" y el texto generado

La UI (Terminal, Web) muestra el action_output con source="ai".
Si la UI prefiere el texto original, ignora los eventos con source="ai".
```

### 7.3 Coexistencia Narrador V1 + Narrador IA

Ambos narradores pueden coexistir. La UI elige cuál escuchar:

```python
class TerminalUI(UIInterface):
    def __init__(self, narrator_mode: str = "template"):
        self.narrator_mode = narrator_mode  # "template" o "ai"

    def _on_action_output(self, event: EngineEvent) -> None:
        source = event.payload.get("source", "template")
        if self.narrator_mode == "template" and source == "template":
            print(event.payload["text"])
        elif self.narrator_mode == "ai" and source == "ai":
            print(event.payload["text"])
        elif self.narrator_mode == "ai" and source == "template":
            pass  # Ignora el texto de plantilla cuando usa IA
```

### 7.4 Límites del Narrador IA

La IA decora la realidad — NO la crea. Los eventos de cambio de estado (`entity_transferred`, `flag_set`, etc.) SON la realidad. El narrador IA:

- ✅ PUEDE: embellecer `action_output` con prosa atmosférica
- ✅ PUEDE: generar descripciones de habitaciones más ricas (reemplazando `room_entered`)
- ✅ PUEDE: añadir flavor text a acciones de NPCs
- ❌ NO PUEDE: crear ítems, cambiar banderas, mover entidades
- ❌ NO PUEDE: modificar el payload de eventos del motor
- ❌ NO PUEDE: emitir eventos de cambio de estado (`entity_transferred`, `flag_set`, etc.)

Esto es lo que el PRD llama "Decorador Semántico" (sección 4.7).

---

## 8. Save/Load via Event Sourcing

El PRD define persistencia del Estado Global, pero el sistema de eventos permite un enfoque más potente: **event sourcing**. En lugar de guardar snapshots del estado completo, guardamos el log de eventos y reconstruimos el estado reproduciéndolo.

### 8.1 Dos Estrategias de Persistencia

| Estrategia | Qué guarda | Ventaja | Desventaja |
|-----------|-----------|---------|-----------|
| **Snapshot** | Estado Global completo (dict de entidades + flags) | Carga instantánea | Archivos grandes, sin historial de acciones |
| **Event Sourcing** | Log de eventos desde el inicio + snapshots periódicos | Historial completo, replay, debug | Carga más lenta (replay necesario) |

El motor implementa **ambas**. El event log es la fuente de verdad; los snapshots son cachés de rendimiento.

```
Save slot #1:
  ├── event_log.jsonl       ← Cada línea es un EngineEvent serializado
  └── snapshot_turn_42.json  ← Snapshot del estado en el turno 42
```

### 8.2 Save System como Suscriptor

El Save System se suscribe a `*` (todos los eventos) y los apende al event log:

```python
class EventSourcingSaveSystem:
    def initialize(self, event_bus: EventBus, log_path: str) -> None:
        self.event_bus = event_bus
        self.log_path = log_path
        self.action_count = 0

        # Se suscribe a todos los eventos
        event_bus.subscribe("*", self._append_to_log)

        # Se suscribe a game_saved para tomar snapshots
        event_bus.subscribe("game_saved", self._take_snapshot)

    def _append_to_log(self, event: EngineEvent) -> None:
        """Apende el evento al event log."""
        with open(self.log_path, "a") as f:
            f.write(json.dumps(event_to_dict(event)) + "\n")
        self.action_count += 1
```

### 8.3 Flujo de Guardado

```
1. Jugador ejecuta comando de guardado (ej: "GUARDAR 1")
2. Motor pausa el ciclo de turno
3. Motor emite:
   game_saved({
       save_slot_id: "slot_1",
       turn_number: 42,
       action_log_position: 847,  // línea actual del event log
   })
4. Save System recibe game_saved y toma un snapshot del State Container
5. Motor resume el ciclo de turno
```

### 8.4 Flujo de Carga

```
1. Jugador ejecuta comando de carga (ej: "CARGAR 1")
2. Motor pausa el ciclo de turno
3. Motor carga el snapshot más reciente del slot (si existe)
4. Motor reproduce el event log desde action_log_position + 1 hasta EOF
   - Durante el replay, los eventos se emiten normalmente
   - La UI puede suscribirse a save_replay_started/save_replay_ended
     para suprimir la renderización durante el replay
5. Motor emite:
   game_loaded({
       save_slot_id: "slot_1",
       turn_number: 42,
   })
6. Motor reanuda el ciclo de turno en el turno 43
```

### 8.5 Replay Silencioso

Durante el replay de carga, la UI puede elegir no renderizar:

```python
class TerminalUI(UIInterface):
    def __init__(self):
        self._replaying = False

    def initialize(self, event_bus: EventBus) -> None:
        event_bus.subscribe("save_replay_started", self._on_replay_started)
        event_bus.subscribe("save_replay_ended", self._on_replay_ended)
        # ... resto de suscripciones

    def _on_replay_started(self, event: EngineEvent) -> None:
        self._replaying = True

    def _on_replay_ended(self, event: EngineEvent) -> None:
        self._replaying = False

    def _on_action_output(self, event: EngineEvent) -> None:
        if self._replaying:
            return  # No mostrar nada durante el replay
        print(event.payload["text"])
```

### 8.6 Event Log como Herramienta de Debug

El event log en formato JSONL es directamente útil para debugging:

```bash
# Ver los últimos 20 eventos
$ tail -20 saves/slot_1/event_log.jsonl | jq '.type'

# Buscar todas las muertes del jugador
$ rg '"game_over"' saves/slot_1/event_log.jsonl

# Reconstruir la secuencia de comandos del jugador
$ rg '"input_received"' saves/slot_1/event_log.jsonl | jq '.payload.raw_text'
```

---

## 9. Ejemplos Concretos

### 9.1 Escenario A: Jugador se mueve a una nueva habitación

**Contexto**: El jugador está en `room_01` ("Entrada de la Fortaleza") y ejecuta `IR AL NORTE`. La Arista Macro `norte_entrada_a_pasillo` conecta `room_01` con `room_02` y no tiene condiciones (`open: true`).

```
Secuencia de eventos emitidos (en orden):

1. turn_started
   payload: { turn_number: 15, active_protagonist_id: "player_1" }

2. input_received
   payload: { raw_text: "ir al norte", protagonist_id: "player_1" }

3. action_attempted
   payload: {
     hyper_edge_id: "mover_norte_entrada_a_pasillo",
     clique: { subject: "player_1", verb: "ir", direction: "norte" },
     protagonist_id: "player_1",
   }

4. entity_teleported
   payload: {
     entity_id: "player_1",
     entity_name: "Jugador",
     from_room_id: "room_01",
     to_room_id: "room_02",
   }

5. room_entered
   payload: {
     room_id: "room_02",
     room_name: "Pasillo Oscuro",
     description: "Un pasillo oscuro y húmedo se extiende ante ti. "
                  "Las paredes de piedra están cubiertas de musgo. "
                  "Al fondo, una tenue luz parpadea.",
     protagonist_id: "player_1",
   }

6. action_resolved
   payload: {
     hyper_edge_id: "mover_norte_entrada_a_pasillo",
     operators_executed: ["TELEPORT"],
     has_effects: true,
     protagonist_id: "player_1",
   }

7. turn_ended
   payload: { turn_number: 15, actions_resolved: 1 }
```

**Qué ve el jugador (Terminal UI)**:

```
Pasillo Oscuro
--------------
Un pasillo oscuro y húmedo se extiende ante ti. Las paredes de piedra
están cubiertas de musgo. Al fondo, una tenue luz parpadea.
```

### 9.2 Escenario B: Jugador ataca a un Guard con el arma correcta

**Contexto**: El jugador está en `room_22` ("Torre del Guardia"). Tiene la Espada élfica en su inventario. El Guardia `guard_04` está en la misma habitación. La Hiper-Arista `atacar_guard_04_elfica` tiene prioridad 10 y requiere `instrument: "espada_elfica"`.

```
Secuencia de eventos emitidos (en orden):

1. turn_started
   payload: { turn_number: 87, active_protagonist_id: "player_1" }

2. input_received
   payload: { raw_text: "atacar guardia con espada elfica", protagonist_id: "player_1" }

3. action_attempted
   payload: {
     hyper_edge_id: "atacar_guard_04_elfica",
     clique: {
       subject: "player_1",
       verb: "atacar",
       target: "guard_04",
       instrument: "espada_elfica",
     },
     protagonist_id: "player_1",
   }

4. entity_transferred
   payload: {
     entity_id: "guard_04",
     entity_name: "Guardia de la Torre",
     from_container_id: "room_22",
     to_container_id: null,               // Guard muere → desaparece
     hyper_edge_id: "atacar_guard_04_elfica",
   }

5. npc_died
   payload: {
     npc_id: "guard_04",
     npc_name: "Guardia de la Torre",
     killed_by_id: "player_1",
   }

6. flag_set
   payload: {
     flag_name: "guard_04_muerto",
     old_value: false,
     new_value: true,
   }

7. flag_set
   payload: {
     flag_name: "enemigos_muertos",
     old_value: 2,
     new_value: 3,
   }

8. action_output
   payload: {
     hyper_edge_id: "atacar_guard_04_elfica",
     text: "Atraviesas al Guardia con tu espada. Él cae de rodillas y, "
           "con su último aliento, confiesa: 'El Centro del Cerebro... "
           "está protegido por un acertijo. La respuesta es... CUARENTA Y DOS.'",
     source: "template",
     protagonist_id: "player_1",
   }

9. action_resolved
   payload: {
     hyper_edge_id: "atacar_guard_04_elfica",
     operators_executed: ["TRANSFER", "FLAG", "FLAG"],
     has_effects: true,
     protagonist_id: "player_1",
   }

10. turn_ended
    payload: { turn_number: 87, actions_resolved: 1 }
```

### 9.3 Escenario C: Transición de Episodio (Parte I → Parte II)

**Contexto**: El jugador ha matado a los 5 enemigos de la Parte I. El GoalEvaluator detecta que se cumplió la condición de victoria del `episode-01`.

```
Secuencia de eventos emitidos (en orden):

1. episode_completed
   payload: {
     episode_id: "episode-01",
     episode_name: "La Fortaleza",
     victory_text: "Usted ha vencido a la Bestia.\n"
                   "Parece ser una persona persistente...\n\n"
                   "Veremos si en la próxima versión de La Fortaleza "
                   "tiene igual suerte.",
     carry_over: {
       inventory: [],
       flags: [],
     },
   }

2. action_output (texto de victoria del episodio)
   payload: {
     hyper_edge_id: null,
     text: "Usted ha vencido a la Bestia. Parece ser una persona persistente...\n\n"
           "Veremos si en la próxima versión de La Fortaleza tiene igual suerte.",
     source: "system",
     protagonist_id: "player_1",
   }

3. episode_transition
   payload: {
     from_episode_id: "episode-01",
     to_episode_id: "episode-02",
     carry_over_applied: {
       inventory: [],
       flags: [],
     },
   }

   [Motor internamente:]
   - Vacía el Grafo Macro de episode-01
   - Vacía los Grafos Micro de episode-01
   - Carga Grafo Macro de episode-02 (55 habitaciones)
   - Carga Grafos Micro de episode-02 (~53 ítems, ~23 NPCs)
   - No transfiere nada del inventario (carry_over vacío para Fortaleza)
   - No transfiere flags (carry_over vacío para Fortaleza)

4. episode_started
   payload: {
     episode_id: "episode-02",
     episode_name: "La Fortaleza II",
     start_room_id: "room_01",
   }

5. entity_teleported
   payload: {
     entity_id: "player_1",
     entity_name: "Jugador",
     from_room_id: null,            // No existía en el nuevo grafo todavía
     to_room_id: "room_01",         // Start room de episode-02
   }

6. room_entered
   payload: {
     room_id: "room_01",
     room_name: "Entrada de la Fortaleza",
     description: "Te encuentras nuevamente en la entrada de la Fortaleza. "
                  "Algo ha cambiado. El aire es más denso. Las sombras, más profundas. "
                  "Una nueva amenaza acecha en la oscuridad.",
     protagonist_id: "player_1",
   }

7. turn_ended (turno se reinicia a 1 para el nuevo episodio)
   payload: { turn_number: 1, actions_resolved: 0 }
```

### 9.4 Escenario D: Jugador muere (TDaugther, arma incorrecta)

**Contexto**: El jugador está en `room_46` ("Santuario de la Hija"). Intenta atacar a `hija_del_hechicero` con la Espada élfica. La Hiper-Arista `atacar_hija_incorrecto` (priority 5) es la que matchea porque la de arma correcta (Aguja, priority 10) no forma clique.

```
Secuencia de eventos emitidos (en orden):

1. turn_started
   payload: { turn_number: 312, active_protagonist_id: "player_1" }

2. input_received
   payload: { raw_text: "atacar hija con espada elfica", protagonist_id: "player_1" }

3. action_attempted
   payload: {
     hyper_edge_id: "atacar_hija_incorrecto",    // Catch-all: arma ≠ Aguja
     clique: {
       subject: "player_1",
       verb: "atacar",
       target: "hija_del_hechicero",
       instrument: "espada_elfica",
     },
     protagonist_id: "player_1",
   }

4. action_output
   payload: {
     hyper_edge_id: "atacar_hija_incorrecto",
     text: "La enorme serpiente se lanza sobre ti. Sus colmillos se hunden "
           "en tu carne antes de que puedas reaccionar. Todo se vuelve negro.",
     source: "template",
     protagonist_id: "player_1",
   }

5. flag_set
   payload: {
     flag_name: "player_dead",
     old_value: false,
     new_value: true,
   }

6. game_over
   payload: {
     reason: "killed_by_tdaugther",
     turn_number: 312,
   }

7. turn_ended
   payload: { turn_number: 312, actions_resolved: 1 }
```

---

## 10. Stack Técnico

### 10.1 Dependencias

**Cero dependencias externas.** Todo se implementa con la biblioteca estándar de Python.

| Componente | Implementación | Módulo |
|-----------|---------------|--------|
| `EngineEvent` | `dataclasses.dataclass(frozen=True)` | `dataclasses` (stdlib) |
| `EventBus` | `collections.defaultdict` para registro de handlers | `collections` (stdlib) |
| Serialización | `json.dumps` / `json.loads` | `json` (stdlib) |
| UUIDs | `uuid.uuid4()` | `uuid` (stdlib) |
| Timestamps | `time.monotonic()` | `time` (stdlib) |
| Tipado | Type hints con `typing` | `typing` (stdlib) |
| Interfaces | `abc.ABC`, `abc.abstractmethod` | `abc` (stdlib) |

**Justificación**: El motor es un intérprete de grafos — no necesita un message broker (RabbitMQ, Redis Pub/Sub) ni un event store externo. La simplicidad del observer pattern con stdlib es suficiente y mantiene el motor autocontenido.

### 10.2 Estructura de Archivos

```
src/
├── engine/
│   ├── events.py              # EngineEvent dataclass, event_to_dict, event_from_dict
│   ├── event_bus.py           # EventBus class
│   ├── state_container.py     # StateContainer (emite eventos de cambio de estado)
│   ├── graph_engine.py        # GraphEngine (emite eventos de acción)
│   ├── turn_orchestrator.py   # TurnOrchestrator (emite eventos de turno)
│   ├── world_loader.py        # WorldLoader (emite world_loaded)
│   ├── episode_manager.py     # EpisodeManager (emite eventos episódicos)
│   └── goal_evaluator.py      # GoalEvaluator (detecta victoria y emite episode_completed)
│
├── ui/
│   ├── ui_interface.py        # UIInterface (ABC)
│   ├── terminal_ui.py         # TerminalUI (V1)
│   └── web_ui.py              # WebUI (V2, futuro)
│
├── plugins/
│   ├── ai_narrator.py         # AINarratorPlugin (v1.2)
│   ├── ai_parser.py           # AIParserPlugin (v1.2)
│   └── command_logger.py      # CommandLogger (rastro, v1.1)
│
├── persistence/
│   ├── event_log.py           # EventSourcingSaveSystem
│   ├── snapshot.py            # Snapshot save/load
│   └── repository.py          # WorldStateRepository (ABC) + SQLite impl
│
└── tests/
    ├── test_events.py         # Tests de serialización de eventos
    ├── test_event_bus.py      # Tests del EventBus
    ├── test_turn_events.py    # Tests de integración: ciclo de turno completo
    └── test_event_sourcing.py # Tests de save/load por event sourcing
```

### 10.3 Testing

El EventBus es trivial de testear. Como es síncrono y sin estado compartido, los tests son deterministas:

```python
def test_event_bus_dispatches_to_subscriber():
    bus = EventBus()
    received = []

    def handler(event: EngineEvent) -> None:
        received.append(event)

    bus.subscribe("test_event", handler)
    event = EngineEvent(
        event_id=UUID("00000000-0000-0000-0000-000000000000"),
        type="test_event",
        turn_number=1,
        timestamp=0.0,
        payload={"key": "value"},
        protagonist_id=None,
        episode_id=None,
    )
    bus.emit(event)

    assert len(received) == 1
    assert received[0].type == "test_event"


def test_event_bus_wildcard_receives_all():
    bus = EventBus()
    received = []

    bus.subscribe("*", lambda e: received.append(e))
    bus.emit(make_event("a"))
    bus.emit(make_event("b"))
    bus.emit(make_event("c"))

    assert len(received) == 3


def test_event_bus_handler_error_does_not_block_others():
    bus = EventBus()
    second_called = False

    def failing_handler(event: EngineEvent) -> None:
        raise RuntimeError("UI crashed!")

    def normal_handler(event: EngineEvent) -> None:
        nonlocal second_called
        second_called = True

    bus.subscribe("test_event", failing_handler)
    bus.subscribe("test_event", normal_handler)
    bus.emit(make_event("test_event"))

    assert second_called  # El segundo handler sí se ejecutó


def test_event_bus_unsubscribe_removes_handler():
    bus = EventBus()
    received = []

    def handler(event: EngineEvent) -> None:
        received.append(event)

    bus.subscribe("test_event", handler)
    bus.unsubscribe("test_event", handler)
    bus.emit(make_event("test_event"))

    assert len(received) == 0
```

### 10.4 Rendimiento

Para un turno típico de Fortaleza (~5-15 eventos), el overhead del EventBus es insignificante:

- `emit()`: O(n) donde n = número de suscriptores del tipo de evento
- Con 3-5 suscriptores típicos (UI, save system, debug), cada `emit()` son 3-5 llamadas a función
- Un turno con 10 eventos = ~30-50 llamadas a función — microsegundos

Para event sourcing con mundos largos (1000+ turnos), el replay desde event log puede tardar. La estrategia de snapshots periódicos (cada N turnos) reduce el replay a O(turnos desde el último snapshot).

---

## Apéndice: Checklist de Implementación

- [ ] `EngineEvent` dataclass + serialización JSON
- [ ] `EventBus` class con subscribe/unsubscribe/emit
- [ ] `EventBus.emit()` con aislamiento de errores por handler
- [ ] `UIInterface` ABC con initialize/wait_for_input/shutdown
- [ ] `TerminalUI` implementando la interfaz
- [ ] StateContainer emite eventos de cambio de estado en cada operador atómico
- [ ] GraphEngine emite `action_attempted` y `action_resolved`
- [ ] TurnOrchestrator emite eventos de ciclo de turno
- [ ] EpisodeManager emite eventos episódicos
- [ ] GoalEvaluator emite `episode_completed`
- [ ] `EventSourcingSaveSystem` como suscriptor `*`
- [ ] Snapshot periódico integrado con `game_saved`
- [ ] Replay desde event log con supresión de renderizado
- [ ] Tests unitarios del EventBus
- [ ] Tests de integración del ciclo de turno completo
- [ ] Tests de event sourcing round-trip (save → load → estado idéntico)

---

*Documento de diseño preparado a partir del PRD v2.0 (secciones 4, 6, 9), el Gap Analysis (#12), y el principio arquitectónico "la transición es señal, no presentación".*
