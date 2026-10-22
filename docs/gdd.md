# GDD — Motor de Grafo Semántico para Ficción Interactiva Generativa

**Versión**: 1.0
**Tipo**: Game Design Document
**Idioma**: Español
**Depende de**: PRD v2.0, Gap Analysis #12, Event System #13

**Última limpieza**: 2026-10-21 — contradicciones entre PRD/GDD/TDD resueltas contra el código. Decisiones de diseño abiertas: ver epic #99 (https://github.com/efirvida/fortress-engine/issues/99).

---

## 1. Introducción

Este documento define el diseño completo del Motor de Grafo Semántico —una máquina virtual para ficción interactiva— y su primer mundo de validación: **Fortaleza**, la aventura conversacional de Miguel Enrique Cepero (1995).

### Relación con otros documentos

| Documento | Rol |
|-----------|-----|
| **PRD** (`prd.md`) | Qué construimos, por qué, para quién. Define la visión y el alcance. |
| **GDD** (este documento) | **Puente entre el PRD y el TDD.** Describe el diseño con suficiente detalle para que un desarrollador lo implemente y un diseñador cree mundos. |
| **TDD** (`tdd.md`) | Cómo se implementa: estructura de clases Python, esquema SQLite, contratos de plugins. No existe ni está planificada una API REST. |

**El GDD responde WHAT y WHY, no HOW**. Los detalles de implementación (clases concretas, nombres de módulos, firmas de métodos) pertenecen al TDD.

### Audiencia

- **Desarrolladores** que implementarán el motor en Python.
- **Diseñadores narrativos** que crearán mundos nuevos editando archivos YAML.

### Principio rector

> El motor interpreta grafos. No sabe nada de Fortaleza, ni de ningún otro mundo. Cada decisión de diseño en este documento refuerza esa separación.

---

## 2. Diseño del Motor

### 2.1 Modelo de Entidades

El motor modela todos los elementos del mundo como **entidades**: una bolsa de componentes clave-valor con anclaje espacial. No hay herencia de clases para tipos de entidad — el comportamiento se define por los componentes presentes y por las Hiper-Aristas que los referencian.

#### Estructura canónica

```yaml
entity_id: "fortaleza-1-antorcha-01"
type: "item"          # cadena opaca definida por el creador del mundo (convención: item | room | npc | player | container | door)
name: "Antorcha"
components:
  description: |
    Una antorcha de madera resinosa. La llama titila débilmente,
    proyectando sombras danzantes en las paredes de piedra.
  weight: 5
  portable: true
  state: "encendida"
  light_source: true
spatial_anchor: "fortaleza-1-room-07"
```

**Campos obligatorios para toda entidad**:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `entity_id` | string | Identificador único global. Se recomienda la convención `<mundo>-<episodio>-<tipo>-<nombre>`. |
| `type` | string | Cadena opaca definida por el creador del mundo. El motor no la valida ni ramifica por ella; `item`, `room`, `npc`, `player`, `container` y `door` son solo convenciones. |
| `name` | string | Nombre que el parser usa para matchear comandos del jugador. En español, con tildes. |
| `components` | dict | Diccionario clave-valor con los atributos de la entidad. Las claves son strings; los valores pueden ser string, número, booleano, o lista. |
| `spatial_anchor` | string \| null | `entity_id` del contenedor donde está la entidad. `null` significa que no está en ninguna parte (destruida, en limbo). Para el jugador, es el `entity_id` de la room actual. |

#### Componentes reservados por el motor

Solo estos componentes son leídos por el código del motor. Todo lo demás es dato del mundo (se usa únicamente a través del mecanismo genérico de `{placeholders}` en `output`, o por predicados de las Hiper-Aristas).

| Componente | Quién lo lee | Semántica |
|------------|--------------|-----------|
| `weight` | Operadores (TRANSFER) | Peso de la entidad al calcular la carga de un contenedor. |
| `max_weight` | `inventory_capacity` (`entities/components.py`) | Capacidad máxima del contenedor. Ausente, `null` o `false`: ilimitada. `0` numérico: capacidad cero. Sin default numérico en el motor. |
| `portable` | Operadores (TRANSFER) | Si es `false`, el TRANSFER falla con el código `not_portable`. |

Los errores de peso se devuelven como códigos (`not_portable`, `too_heavy`); el texto vive en el narrador (`DEFAULT_SPANISH_MESSAGES` de `plugins/template_narrator.py`: «Usted no puede cargar con eso.» / «Sería demasiado peso.»).

> **Nota:** el CLI lee `is_dead` en el protagonista, y la bandera de derrota `player_dead` está fijada en el orquestador (ver 2.5). Ninguno es un componente o bandera configurable por el mundo.
>
> **Abierto:** componentes reservados, derrota como dato y rama por `type == "player"` en el CLI — ver #88.

Los componentes `dark`, `visited`, `synonyms`, `combat_pattern`, `mood`, `brain_type`, `hit_points`, `lethalweap`, `likeness`, `dialogue` y `player_controlled` que aparecen en las secciones siguientes son **convenciones del mundo Fortaleza que el motor no lee** (la oscuridad no está implementada, el motor no establece `visited`, el parser clásico solo compara `name`).

#### Tipos de entidad y sus componentes

Los «tipos» siguientes son convenciones de ejemplo: el motor es agnóstico al `type`.

##### Room

Una habitación, región o ubicación. Es un Nodo del Grafo Macro y también el contenedor espacial de otras entidades.

```yaml
entity_id: "fortaleza-1-room-01"
type: "room"
name: "Entrada de la Fortaleza"
components:
  description: |
    Te encuentras en el exterior de una imponente fortaleza de
    piedra negra. El viento ulula entre las almenas. Una pesada
    puerta de roble se alza ante ti. A tu alrededor, la maleza
    ha devorado lo que alguna vez fue un camino.
  visited: false
  dark: false
  episode: "episode-01"
spatial_anchor: null   # las rooms no tienen anclaje — son el anclaje
```

Componentes convencionales de Room:

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `description` | string (multilínea) | Texto que se muestra al entrar por primera vez, y al ejecutar `MIRAR` (vía `{placeholder}` en el `output` de la Hiper-Arista). |
| `visited` | boolean | Convención del mundo. **El motor no lo establece** (TELEPORT no lo modifica); un mundo que lo quiera debe marcarlo con TRANSFORM. |
| `dark` | boolean | Convención del mundo. **La oscuridad no está implementada**: el motor no consulta este componente. |

Componentes opcionales:

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `episode` | string | A qué episodio pertenece esta room. Útil para mundos multi-episodio. |
| `tags` | list | Etiquetas para agrupación (ej: `["interior", "peligrosa"]`). |

##### Item

Un objeto portable o fijo que existe en el mundo.

```yaml
entity_id: "fortaleza-1-item-maza"
type: "item"
name: "Maza"
components:
  description: "Una pesada maza de guerra. El mango está desgastado por el uso."
  weight: 39
  portable: true
  state: "idle"
  synonyms: ["martillo de guerra", "garrote"]
spatial_anchor: "fortaleza-1-room-01"
```

Componentes convencionales de Item (`weight` y `portable` son leídos por el motor; ver «Componentes reservados»):

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `description` | string | Texto mostrado al examinar el ítem (`EXAMINAR <item>`), vía `{placeholder}`. |
| `weight` | integer | Peso en unidades. Se compara con el `max_weight` del destino durante TRANSFER. |
| `portable` | boolean | Si es `false`, el ítem no puede transferirse al inventario (ej: una estatua fija, un mueble). |

Componentes opcionales:

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `state` | string | Estado actual del ítem: `"idle"`, `"encendida"`, `"volteado"`, `"roto"`. Se modifica con TRANSFORM. |
| `light_source` | boolean | Si es `true`, ilumina rooms oscuras. |
| `synonyms` | list | Convención del mundo; **el parser clásico no lo lee** (solo compara `name`). |
| `edible` | boolean | Si es `true`, puede consumirse (no usado en Fortaleza, pero disponible para otros mundos). |

##### NPC

Un personaje no jugador: enemigo, aliado, o criatura neutral.

```yaml
entity_id: "fortaleza-1-npc-ciclope"
type: "npc"
name: "Cíclope"
components:
  description: "Un cíclope enorme con un solo ojo inyectado en sangre."
  mood: "hostile"
  brain_type: "scripted"
  hit_points: 1
  lethalweap: "Maza"
  dialogue:
    HiData: |
      "¡Arrrggghhhh! ¡Me has matado! La contraseña de la
      Puerta gigante es... CIRCE."
    LowData: |
      "Todos sus esfuerzos son en vano. Probablemente no
      esté usando el objeto indicado."
spatial_anchor: "fortaleza-1-room-06"
```

Componentes convencionales de NPC (el motor no lee ninguno de ellos salvo el mecanismo genérico de placeholders):

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `description` | string | Texto mostrado al examinar el NPC. |
| `mood` | string | Estado emocional: `"hostile"`, `"neutral"`, `"happy"`, `"dead"`. Afecta qué Hiper-Aristas están disponibles. |
| `brain_type` | string | `"scripted"` (selecciona Hiper-Arista por prioridad, v1.1) o `"reactive"` (solo actúa cuando el jugador interactúa, v1.0). |
| `hit_points` | integer | Salud del NPC. En Fortaleza todos tienen 1 (mueren de un golpe con el arma correcta). |

Componentes opcionales:

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `lethalweap` | string | Convención del mundo: nombre del arma que mata a este NPC. El motor no lo lee; la lógica real vive en las Hiper-Aristas (instrument + prioridad). |
| `likeness` | string | Nombre del ítem que el NPC acepta como regalo. Solo para Trolls. |
| `dialogue` | dict | Mapa de claves de estado (`HiData`, `LowData`) a texto de diálogo. |
| `combat_pattern` | string | Convención del mundo (`"guard"`, `"troll"`, `"tdaugther"`). El motor no lo lee ni infiere nada de `lethalweap`. |

##### Player

El protagonista controlado por el jugador. El motor soporta múltiples protagonistas simultáneos.

```yaml
entity_id: "fortaleza-1-player"
type: "player"
name: "Indy"
components:
  description: "Eres un aventurero en busca de la verdad."
  player_controlled: true
  max_weight: 40
  state: "alive"
spatial_anchor: "fortaleza-1-room-01"
```

Componentes convencionales de Player (el motor solo lee `max_weight`; el CLI lee `is_dead`; `player_controlled` no es leído por el motor):

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `player_controlled` | boolean | `true` para todos los protagonistas controlables. El motor trata esta colección como un conjunto, nunca como singleton. |
| `max_weight` | integer / null / false | Capacidad máxima de carga definida por el mundo. Ausente, `null` o booleano `false`: ilimitada. `0` numérico: capacidad cero. Sin default numérico en el motor. |
| `state` | string | Convención del mundo (`"alive"` / `"dead"`). El motor no lo lee: la derrota la decide la bandera `player_dead` (orquestador) y el CLI consulta `is_dead` — ver #88. |

Componentes opcionales:

| Componente | Tipo | Descripción |
|------------|------|-------------|
| `inventory` | list | Lista de `entity_id` de ítems que el protagonista lleva. Se gestiona con TRANSFER, no se edita manualmente. |
| `current_episode` | string | Episodio activo para este protagonista. |

##### Container

Una entidad que puede contener otras entidades (cofre, mesa, bolsa). No usado en Fortaleza pero disponible para mundos futuros.

```yaml
entity_id: "mundo-ejemplo-cofre"
type: "container"
name: "Cofre de roble"
components:
  description: "Un cofre polvoriento con herrajes de hierro."
  open: false
  locked: true
  key: "llave-oxidada"
spatial_anchor: "mundo-ejemplo-room-02"
```

##### Door

Una puerta es una **entidad del mundo** como cualquier otra: el motor no conoce el tipo
`door`. Los datos de la conexión (qué anchors conecta y bajo qué predicados) viven en el
**MacroEdge** (ver 2.2), no en los componentes de la entidad. La entidad door es opcional
y se usa para examinar la puerta, describirla, etc.

```yaml
entity_id: "fortaleza-1-door-puerta-principal"
type: "door"
name: "Puerta principal"
components:
  description: "Una pesada puerta de roble con refuerzos de hierro."
spatial_anchor: "fortaleza-1-room-01"
```

La conexión correspondiente se define como MacroEdge con sus predicados:

```yaml
macro_edge_id: "fortaleza-1-edge-puerta-principal"
from_anchor: "fortaleza-1-room-01"
to_anchor: "fortaleza-1-room-02"
direction: "bidirectional"
passage_name: "Puerta principal"
passage_description: "Una pesada puerta de roble con refuerzos de hierro."
requires_text: "ábrete sésamo"   # predicado genérico: se abre diciendo el texto
open: false
```

Los predicados de acceso son **genéricos** (ver 2.2): `requires_text`, `requires_item`, `forbids_item`, `requires_flag`, `forbids_flag`, y `death_message`. No existe `connection_type` — el motor nunca interpreta nombres de tipos de conexión.

### 2.2 Grafo Macro (Mapa Físico)

El Grafo Macro define la topología del mundo: qué rooms están conectadas y bajo qué condiciones se puede cruzar de una a otra. Es un grafo dirigido (o bidireccional, según la arista) donde los nodos son rooms y las aristas son puertas/pasajes.

#### Tipos de conexión

Cada arista del Grafo Macro es un conjunto de **predicados genéricos** que el motor evalúa de forma uniforme. No existe un `connection_type`: el creador del mundo decide la semántica según qué predicados defina. Una arista sin predicados siempre es transitable.

| Predicado | Significado | Comportamiento |
|-----------|-------------|----------------|
| *(ninguno)* | Arista abierta. | Siempre transitable. |
| `requires_text` | Texto que el jugador debe decir para desbloquear. | Con `open: false`, el cruce se permite al pronunciar el texto correcto (`ABRIR ... DICIENDO <texto>` / `RESPONDIENDO <texto>`); la coincidencia es insensible a mayúsculas y tildes y abre la arista. |
| `question` | Texto de acertijo mostrado por el narrador. | Datos de mundo para narración; el motor **no** la evalúa. |
| `requires_item` | Ítem que debe estar en el inventario. | Sin el ítem, el cruce se bloquea (o mata si hay `death_message`). |
| `forbids_item` | Ítem que NO debe estar en el inventario. | Con el ítem, el cruce se bloquea (o mata si hay `death_message`). |
| `requires_flag` | Bandera que debe estar activa. | Si no lo está, el cruce se bloquea. |
| `forbids_flag` | Bandera que debe estar inactiva/ausente. | Si está activa, el cruce se bloquea. |
| `death_message` | Consecuencia fatal de un predicado que falla. | Si un predicado falla Y `death_message` está definido → muerte; si no → cruce bloqueado. |

#### Formato YAML de una arista Macro

```yaml
# Conexión bidireccional simple (room-01 ↔ room-02) — sin predicados = abierta
macro_edge_id: "fortaleza-1-edge-01-02"
from_anchor: "fortaleza-1-room-01"
to_anchor: "fortaleza-1-room-02"
direction: "bidirectional"
passage_name: "Puerta principal"
passage_description: "Una pesada puerta de roble."

---
# Conexión con texto de desbloqueo (antes: password / riddle)
macro_edge_id: "fortaleza-1-edge-03-05"
from_anchor: "fortaleza-1-room-03"
to_anchor: "fortaleza-1-room-05"
direction: "bidirectional"
passage_name: "Escalera"
question: "¿Cuántos peldaños tiene la escalera?"   # narración, no se evalúa
requires_text: "treinta y nueve"
open: false
passage_description: "Una escalera de caracol que desciende en la oscuridad."

---
# Peligro: necesita ítem para no morir (antes: danger)
macro_edge_id: "fortaleza-1-edge-18-19"
from_anchor: "fortaleza-1-room-18"
to_anchor: "fortaleza-1-room-19"
direction: "bidirectional"
passage_name: "Tráquea"
requires_item: "Talismán de aire"
passage_description: "Un pasaje estrecho y palpitante."
death_message: "La Bestia te aplasta con sus pulmones. Has muerto."

---
# Peligro inverso: muere SI lleva el ítem (antes: danger_inverse)
macro_edge_id: "fortaleza-1-edge-27-28b"
from_anchor: "fortaleza-1-room-27"
to_anchor: "fortaleza-1-room-28"
direction: "unidirectional"
passage_name: "Puerta"
forbids_item: "Espada"
passage_description: "Una puerta de aspecto inofensivo."
death_message: "Una trampa mortal se activa. La Espada era el detonante."

---
# Acertijo con pregunta mostrada por el narrador (antes: riddle)
macro_edge_id: "fortaleza-1-edge-30-22"
from_anchor: "fortaleza-1-room-30"
to_anchor: "fortaleza-1-room-22"
direction: "unidirectional"
passage_name: "Puerta dorada"
question: "Invente un alfabeto con el que no pueda crearse a la Bestia"
requires_text: "cdfghjklmnopqruvwxyz"
open: false
passage_description: "Una puerta de oro macizo con inscripciones."

---
# Condicional: requiere bandera (antes: conditional)
macro_edge_id: "fortaleza-1-edge-07-10"
from_anchor: "fortaleza-1-room-07"
to_anchor: "fortaleza-1-room-10"
direction: "bidirectional"
passage_name: "Puerta prohibida"
requires_flag: "knows_lab_password"
passage_description: "Una puerta con la inscripción 'Prohibido el paso'."
```

#### Evaluación de predicados al cruzar

Cuando el jugador ejecuta un comando de movimiento (ej: `IR PUERTA PRINCIPAL`), el motor evalúa los predicados genéricos de la arista de forma uniforme, en este orden:

1. Busca en la room actual una arista Macro cuyo `passage_name` matchee el comando del jugador.
2. **Predicado de texto** (`requires_text`): si la arista está cerrada (`open: false`), el motor espera que el comando incluya el texto (`ABRIR PUERTA PRINCIPAL DICIENDO <texto>`). Si coincide (insensible a mayúsculas y tildes), abre la arista (`open: true`) y permite cruzar. Si no, el cruce se bloquea (o es fatal si hay `death_message`).

   > **Abierto:** el estado `open` vive en la arista del grafo (`MacroEdge.open`), no en `WorldState` ni en el log de eventos, así que se pierde al guardar/cargar; abrir una arista bidireccional abre también su espejo (`<id>_reverse`) — ver #79.
3. **Predicados de ítem** (`requires_item` / `forbids_item`): verifica el inventario del protagonista activo. Si fallan, el cruce se bloquea (o es fatal si hay `death_message`).
4. **Predicados de bandera** (`requires_flag` / `forbids_flag`): verifica el libro de banderas. Si fallan, el cruce se bloquea (o es fatal si hay `death_message`).
5. `death_message` es el único discriminador entre **fatal** y **bloqueado**: el motor nunca interpreta nombres de tipos de conexión.
6. Si todos los predicados pasan, ejecuta `TELEPORT(protagonista, room_actual, room_destino)`.
7. Emite `entity_entered` con la descripción de la nueva room.

### 2.3 Grafo Micro (Interacciones de Escena)

Dentro de cada room, el Grafo Micro contiene Hiper-Aristas que definen qué acciones son posibles en esa escena. Cada Hiper-Arista es un nodo de acción que requiere una **Clique de Participación** para activarse.

> **Abierto:** en la práctica las aristas funcionan como un índice global: el cargador copia las registradas en `start_anchor` a cada anchor que no tiene ninguna, y el filtrado por escena ocurre solo al validar la clique (presencia de los miembros en la anchor del sujeto) — ver #83.

#### Estructura completa de una Hiper-Arista

```yaml
hyper_edge_id: "fortaleza-1-action-matar-ciclope-maza"
name: "Matar al Cíclope con Maza"
priority: 10
clique:
  subject: "player"              # quien ejecuta la acción
  verb: "matar"                  # verbo que dispara esta Hiper-Arista
  target: "fortaleza-1-npc-ciclope"   # sobre quién/qué se ejecuta
  instrument: "fortaleza-1-item-maza" # con qué (arma, herramienta)
  context: null                  # ubicación o entidad contextual
  instrument_not: null           # el instrumento NO debe ser este
  instrument_any: false          # cualquier instrumento es válido
  flag: null                     # requiere bandera activa
  flag_not: null                 # requiere bandera inactiva
operators:
  - type: "TRANSFER"
    entity: "fortaleza-1-npc-ciclope"
    from_container: "fortaleza-1-room-06"
    to_container: null
  - type: "FLAG"
    flag: "ciclope_muerto"
    value: true
  - type: "FLAG"
    flag: "knows_puerta_gigante_password"
    value: true
output: |
  Atraviesas al Cíclope con tu Maza. El gigante se tambalea
  y cae al suelo con un estruendo que hace temblar los estantes.

  Con su último aliento, susurra:
  "La contraseña de la Puerta gigante es... CIRCE."

  Sus ojos se cierran para siempre.
```

#### Sistema de prioridades

Cuando existen múltiples Hiper-Aristas con el mismo `verb` y `target`, el motor las evalúa en orden descendente de `priority`. La primera cuya Clique de Participación se forme es la que se ejecuta. Las demás se ignoran.

**Regla**: mayor prioridad = se evalúa primero. Esto permite modelar casos especiales (arma correcta, prioridad 10) y fallbacks (cualquier otra arma, prioridad 0) sin operadores condicionales.

#### Clique de Participación

Una Hiper-Arista solo se ejecuta si todos los miembros requeridos de la Clique están presentes y satisfacen los predicados:

| Miembro | Descripción | Validación |
|---------|-------------|------------|
| `subject` | Quién ejecuta la acción. Normalmente el protagonista activo. | Debe estar en la misma anchor que `target`. |
| `verb` | El verbo parseado del comando del jugador. | Debe coincidir exactamente. |
| `target` | La entidad sobre la que se actúa. | Debe estar en la misma anchor que `subject`, o en el inventario de `subject`. |
| `instrument` | La herramienta o arma usada. | Si se especifica, debe estar en el inventario de `subject` o en la anchor. |
| `context` | Entidad contextual (ej: una segunda entidad `player_controlled` para puzles cooperativos). | Debe satisfacer la misma regla de presencia que `target`. |

> **Abierto:** los predicados conviven hoy en tres dialectos (campos de la clique como `flag`/`flag_not`, predicados de las aristas Macro como `requires_flag`, y condiciones de goal) — ver #84.

#### Comodín `"*"` para instrument

El valor especial `"*"` en `instrument` significa "cualquier ítem es válido como instrumento". Útil para Hiper-Aristas catch-all.

```yaml
# Fallback: atacar al Cíclope con cualquier arma que no sea la Maza
hyper_edge_id: "fortaleza-1-action-matar-ciclope-fallback"
name: "Atacar al Cíclope (arma incorrecta)"
priority: 0
clique:
  subject: "player"
  verb: "matar"
  target: "fortaleza-1-npc-ciclope"
  instrument: "*"
  instrument_any: true
operators: []    # secuencia vacía: sin cambio de estado
output: |
  Atacas al Cíclope con todas tus fuerzas, pero
  tu arma apenas le hace cosquillas.

  El Cíclope se ríe con desprecio:
  "Todos sus esfuerzos son en vano. Probablemente
  no esté usando el objeto indicado."
```

En este caso, el motor primero evalúa la Hiper-Arista de prioridad 10 (requiere `instrument: "Maza"`). Si el jugador no tiene la Maza, la clique no se forma. Luego evalúa la de prioridad 0 (`instrument_any: true`), que siempre se forma si el jugador tiene al menos un ítem portable en el inventario.

#### Campo `output`

El texto en `output` se emite como evento `action_output` después de ejecutar todos los operadores. Es el texto que el jugador lee. En el narrador V1 (plantillas), este texto se muestra directamente. En V2 (IA), el LLM lo usa como base para generar prosa más rica.

Si la Hiper-Arista tiene `operators: []` (secuencia vacía), solo se emite el `output` — útil para acciones que solo producen texto (interrogar, examinar, fallbacks de combate).

### 2.4 Operadores Atómicos

El motor implementa exactamente 5 operadores. Una Hiper-Arista define una secuencia de operadores que se ejecutan en orden. **Comportamiento actual:** la secuencia se detiene en el primer fallo; las mutaciones anteriores se conservan, junto con los eventos de cambio de estado ya emitidos (no hay rollback).

> **Abierto:** los operadores no son atómicos — ver #80.

#### TRANSFER

Mueve una entidad de un contenedor a otro.

```yaml
- type: "TRANSFER"
  entity: "fortaleza-1-item-antorcha"
  from_container: "fortaleza-1-room-07"   # contenedor origen (room, inventory, null)
  to_container: "fortaleza-1-player"       # contenedor destino (room, inventory, null)
```

Las claves son `from_container` / `to_container`: el cargador rechaza las claves desconocidas (`from` / `to` provocan `ValueError`). Además de ids literales, `@anchor` se resuelve al anchor del protagonista.

**Precondiciones**:
- `entity` existe en `from_container`.
- Si `to_container` es un inventario (`player_controlled`), se valida el peso:
- Si hay un límite numérico y `entity.weight > player.max_weight`: la acción falla. Se emite `error_output` con `error_code="not_portable"` + `data`; el texto español vive en el narrador (`DEFAULT_SPANISH_MESSAGES["error_output.not_portable"]`).
- Si hay un límite numérico y `sum(inventory_items.weight) + entity.weight > player.max_weight`: la acción falla. Se emite `error_output` con `error_code="too_heavy"` + `data`; el texto español vive en el narrador (`DEFAULT_SPANISH_MESSAGES["error_output.too_heavy"]`).
- Si `entity.portable == false` y `to_container` es un inventario: la acción falla.

**Postcondiciones**:
- `entity.spatial_anchor` cambia a `to_container`.
- Si `to_container` es `null`, la entidad se marca como destruida (no aparece en ninguna room ni inventario).
- Se emite `entity_transferred`.

**Casos especiales**:
- `to_container: null` = destruir/consumir la entidad (ej: dar un ítem a un Troll lo consume).
- `from_container: null` = la entidad no estaba en ninguna parte (solo útil para spawn desde limbo — ver TELEPORT).

#### TRANSFORM

Modifica un componente de una entidad sin cambiar su identidad.

```yaml
- type: "TRANSFORM"
  entity: "fortaleza-2-item-reloj-arena"
  component: "state"
  old_value: "idle"
  new_value: "volteado"
```

**Precondiciones**:
- `entity` existe.
- El componente `component` existe y tiene el valor `old_value`. Si el valor actual no coincide con `old_value`, la acción falla (protege contra transformaciones duplicadas).

**Postcondiciones**:
- `entity.components[component]` cambia a `new_value`.
- La entidad mantiene su `entity_id`, `type` y `spatial_anchor`.
- Se emite `entity_transformed`.

**Casos de uso típicos**:
- Cambiar el estado de un ítem: `Reloj de arena` con `state: "volteado"`.
- Cambiar el mood de un NPC: `mood: "hostile"` → `mood: "happy"`.
- Marcar una puerta como abierta: `open: false` → `open: true`.

Si el diseñador necesita un cambio de identidad (ej: "madera" → "cenizas"), debe usar COMBINE en lugar de TRANSFORM.

#### COMBINE

Toma múltiples entidades de entrada y produce una entidad de salida. Las entradas se destruyen.

```yaml
- type: "COMBINE"
  input_entities:
    - "fortaleza-1-item-maza"
    - "fortaleza-1-item-monolito"
  output_entity: "fortaleza-1-item-trebol"
```

**Precondiciones**:
- Todas las `input_entities` existen y están en la room actual (o en el inventario del sujeto).
- `output_entity` existe en el grafo (pre-definida, posiblemente en `_limbo`).

**Postcondiciones**:
- Las `input_entities` se destruyen (`TRANSFER` a `null`).
- `output_entity` se mueve desde su ubicación actual a la room del sujeto (`TELEPORT` a la room actual).
- Se emite `entity_combined` y `entity_transferred` para cada input.

**Casos de uso**:
- Romper un PHidden: COMBINE(Maza, Monolito) → Trebol.
- Fusionar ítems: COMBINE(Harina, Agua) → Masa.
- Revelar objetos ocultos: COMBINE(Cuadro, Estatua de Satanás) → Puerta oculta.

#### FLAG

Establece o limpia una bandera global en el Libro de Banderas.

```yaml
- type: "FLAG"
  flag: "ciclope_muerto"
  value: true
```

**Precondiciones**:
- Ninguna. FLAG siempre se ejecuta.

**Postcondiciones**:
- `flag_book[flag]` se establece a `value`.
- Se emite `flag_set`.

**Casos de uso**:
- Registrar la muerte de un enemigo: `FLAG("ciclope_muerto", true)`.
- Desbloquear una puerta condicional: `FLAG("knows_lab_password", true)`.
- Marcar progreso en una secuencia de puzles: `FLAG("columna_rota", true)`.

Las banderas son el mecanismo principal para modelar estado global y secuencias de puzles. Una Hiper-Arista A establece una bandera; una Hiper-Arista B posterior requiere esa bandera en su clique (`flag: "columna_rota"`).

#### TELEPORT

Cambia el anclaje espacial de una entidad, moviéndola a otra room.

```yaml
- type: "TELEPORT"
  entity: "fortaleza-2-item-caliz"
  from_anchor: "_limbo"
  to_anchor: "fortaleza-2-room-46"
```

**Precondiciones**:
- `entity` existe.
- `to_anchor` existe en el Grafo Macro.

**Postcondiciones**:
- `entity.spatial_anchor` cambia a `to_anchor`.
- Si la entidad es un protagonista, se emite `entity_entered` con la descripción de la nueva room.
- Se emite `entity_teleported`.

> **Nota:** TELEPORT no establece `visited` (no implementado). Si un mundo quiere ese dato, es una convención del mundo que debe mantener con TRANSFORM.

**Casos de uso**:
- Mover al jugador a otra room (cruce de arista Macro, transición de episodio).
- Hacer aparecer un ítem cuando un enemigo muere (desde `_limbo`).
- Mover un NPC de una room a otra.

**Patrón "Limbo Room"**: para modelar entidades que "aparecen" (spawnean), se pre-definen en una room especial `_limbo` que no es accesible al jugador. Un TELEPORT desde `_limbo` a una room visible simula un spawn sin necesidad de un operador CREATE. Esto es lo que resuelve el Gap #6 (entidades que aparecen, como el Cáliz al morir la Hija del Hechicero).

### 2.5 Orquestador de Turnos

El Orquestador de Turnos es el bucle principal del motor. Coordina el input del jugador, la validación de Hiper-Aristas, la ejecución de operadores, y la emisión de eventos.

#### Flujo completo del ciclo de turno

**Carga del mundo**: Antes de que el ciclo de turnos comience, el motor carga el mundo escaneando recursivamente todos los subdirectorios de datos. La validación de carga incluye:
- Sin referencias colgantes (toda entidad referenciada existe)
- Sin prioridades duplicadas para el mismo par (verbo, objetivo) — si dos Hiper-Aristas comparten verbo, objetivo y prioridad, el motor emite una advertencia
- Todas las banderas referenciadas en predicados están declaradas
- Validación de carry_over: los ítems y banderas existen en el episodio origen

```
TURNO N — Protagonista activo: player_1

PASO 1: INICIO DE TURNO
  turn_number += 1
  EMITIR turn_started({ turn_number, active_protagonist_id })

PASO 2: ENTRADA DEL JUGADOR
  raw_text = UI.wait_for_input(active_protagonist_id)

  SI raw_text es comando de sistema:
    "GUARDAR <slot>"  → ejecutar save
    "CARGAR <slot>"   → ejecutar load
    "TERMINAR"        → EMITIR game_over({ reason: "player_quit" })
    RETORNAR (no se considera un turno de juego)

  SI raw_text es "CAMBIAR A <nombre>":
    Buscar entidad player_controlled con name == <nombre>
    SI existe:
      EMITIR protagonist_switched({ from, to })
      active_protagonist = nuevo protagonista
      RETORNAR

  // Los comandos de sistema y los verbos de movimiento NO están hardcodeados
  // en el orquestador: provienen del Vocabulary del mundo (secciones
  // `movement_verbs` y `system_commands` de `shared/vocabulary.yaml`). Los
  // defaults en código (`DEFAULT_MOVEMENT_VERBS={"ir","abrir"}`,
  // `DEFAULT_SYSTEM_COMMANDS`) solo aplican cuando el mundo no los declara.

PASO 3: PARSEO
  parsed = parser.parse(raw_text, world_state)
  // parsed = { subject, verb, target, context, instrument }
  // world_state incluye:
  //   - active_protagonist_id: el protagonista que tiene el foco actual
  //   - entities: diccionario completo de entidades con sus componentes
  //   - flags: libro de banderas globales
  //   - current_episode: identificador del episodio activo

  EMITIR input_received({ raw_text, protagonist_id })

PASO 4: BÚSQUEDA DE HIPER-ARISTAS
  // Obtener la room actual del protagonista activo
  current_room = active_protagonist.spatial_anchor

  // Filtrar Hiper-Aristas del Grafo Micro de current_room
  // que matcheen parsed.verb
  candidates = graph.get_hyper_edges(
    room: current_room,
    verb: parsed.verb
  )

  SI candidates está vacío:
    EMITIR error_output({ error_code: "no_action", data: { verb, protagonist_id } })
    IR A PASO 10

  // Ordenar por prioridad descendente
  candidates.sort_by_priority_desc()

PASO 5: VALIDACIÓN DE CLIQUES
  PARA CADA candidate EN candidates:
    clique_formada = validar_clique(candidate, parsed, world_state)

    SI clique_formada:
      selected = candidate
      EMITIR action_attempted({
        hyper_edge_id: selected.id,
        clique: { subject, verb, target, instrument, context },
        protagonist_id
      })
      ROMPER

  SI ninguna clique se formó:
    EMITIR error_output({ error_code: "no_action", data: { verb, protagonist_id } })
    IR A PASO 10

PASO 6: EJECUCIÓN DE OPERADORES
  operators_executed = []

  PARA CADA op EN selected.operators:
    resultado = ejecutar_operador(op, world_state)
    SI resultado.es_exitoso:
      operators_executed.append(op.type)
      // StateContainer emite el evento correspondiente:
      //   entity_transferred, entity_transformed,
      //   entity_combined, flag_set, entity_teleported
    SINO:
      // El operador falló (ej: peso excedido)
      // NO se emite evento de cambio de estado
      EMITIR error_output({ error_code: resultado.code, data: resultado.data })
      ROMPER  // no ejecutar más operadores de esta Hiper-Arista

PASO 7: EMITIR OUTPUT DE LA HIPER-ARISTA
  SI selected.output NO está vacío:
    EMITIR action_output({
      hyper_edge_id: selected.id,
      text: selected.output,
      source: "template"
    })

PASO 8: REGISTRAR ACCIÓN COMPLETADA
  EMITIR action_resolved({
    hyper_edge_id: selected.id,
    operators_executed,
    has_effects: len(operators_executed) > 0,
    protagonist_id
  })

  // Guardar en event log (event sourcing)
  log_action(selected.id, operators_executed, turn_number)

PASO 9: TURNO DE OTROS PROTAGONISTAS (v1.1)
  // En v1.0, si hay un solo protagonista, este paso es no-op.
  // En mundos multi-protagonista:
  PARA CADA p EN player_controlled_entities DONDE p != active_protagonist:
    SI p tiene acciones en cola:
      ejecutar_accion_en_cola(p)
    // (cerebro autónomo de otros protagonistas es v1.1)

PASO 10: TURNO DE NPCs (v1.1)
  // En v1.0, los NPCs son reactivos — no tienen turno propio.
  // En v1.1:
  EMITIR npc_turn_started({ turn_number })
  PARA CADA npc CON brain_type == "scripted":
    acciones_disponibles = graph.get_hyper_edges_for_npc(npc)
    SI acciones_disponibles NO está vacío:
      accion = seleccionar_por_prioridad(acciones_disponibles)
      ejecutar_operadores_de_npc(accion, npc)
      EMITIR npc_acted({ npc_id, action_id })
  EMITIR npc_turn_ended({ npcs_acted: N })

PASO 11: EVALUAR CONDICIONES DE VICTORIA/DERROTA
  episode = world.current_episode

  // Verificar victoria del episodio
  SI goal_evaluator.check(episode.goal, world_state):
    EMITIR episode_completed({
      episode_id: episode.id,
      victory_text: episode.victory.output,   // emitido vía narrador, no directamente por el motor
      carry_over: episode.carry_over
    })

    next_episode = world.next_episode()

    SI next_episode existe:
      EMITIR episode_transition({
        from_episode_id: episode.id,
        to_episode_id: next_episode.id,
        carry_over_applied: transferir_carry_over(episode.carry_over)
      })
      descargar_grafo_actual()
      cargar_grafo(next_episode)
      TELEPORT(jugador, _limbo, next_episode.start_anchor)
      EMITIR episode_started({ episode_id: next_episode.id, ... })
    SINO:
      EMITIR game_completed({ world_id, total_turns: turn_number })
      RETORNAR

  // Verificar derrota
  // (la bandera "player_dead" está fijada en el orquestador; no es configurable por el mundo — ver #88)
  SI flag_book["player_dead"] == true:
    EMITIR game_over({
      reason: "player_died",
      turn_number
    })
    RETORNAR

PASO 12: FIN DE TURNO
  EMITIR turn_ended({ turn_number, actions_resolved: 1 })

  // El motor espera el próximo input del jugador
  // (vuelve al PASO 1 en el próximo ciclo)
```

**Nota sobre el narrador**: El motor no emite texto directamente. Todos los mensajes que el jugador lee son producidos por el narrador, que se suscribe a los eventos del motor:

- `entity_entered` → el narrador emite la descripción de la habitación (`room.components.description`)
- `action_output` → el narrador emite el texto del campo `output` de la Hiper-Arista
- `error_output` → el narrador emite mensajes de error (parser, peso excedido, comandos inválidos)
- `episode_started`, `episode_completed`, `game_over` → el narrador emite textos narrativos de transición

El narrador V1 (plantillas) simplemente emite el texto tal cual está definido en los datos. El narrador V2 (IA) podrá decorarlo. Ver `docs/13-event-system.md` para la taxonomía completa.

### 2.6 Sistema de Guardado/Carga (Event Sourcing)

El motor implementa persistencia mediante event sourcing: cada cambio de estado se registra como un evento en un log, y el estado del mundo se reconstruye reproduciendo ese log. Los snapshots son solo una caché de rendimiento, nunca la fuente de verdad.

#### Principio

```
Estado(t) = reproducir(eventos_de_cambio_de_estado[snapshot..t], snapshot)
```

Donde `snapshot` es el último snapshot del slot (o el estado inicial del mundo recién cargado si el slot no tiene ninguno).

#### Almacenamiento

La persistencia pasa por el `WorldStateRepository` (`persistence/repository.py`), implementado con SQLAlchemy sobre SQLite (`persistence/sqlite_repository.py`). No hay archivos JSONL ni `snapshot_turn_N.json`. Tablas:

- `event_log`: eventos persistidos, con número de turno y slot.
- `save_snapshots`: snapshots completos del estado por slot y turno.

El esquema exacto (columnas, índices, migraciones) está en el TDD §5; este documento no lo duplica. Alembic no está inicializado: el MVP usa `Base.metadata.create_all` (#22).

> **Abierto:** formato de serialización de los eventos y versionado de los saves — ver #81. Decisión JSON vs SQLite — ver #97.

#### Qué eventos se persisten

Solo se persisten eventos con efectos sobre el estado:

- Los cinco eventos de cambio de estado: `entity_transferred`, `entity_transformed`, `entity_combined`, `flag_set`, `entity_teleported`.
- `action_resolved`, únicamente cuando la Hiper-Arista tiene `has_effects` (solo con fines de auditoría; el replay lo ignora).

Los eventos narrativos (`action_output`, `entity_entered`, `error_output`, …) y las acciones de solo lectura (MIRAR, INVENTARIO, Hiper-Aristas con `operators: []`) **no** se registran: son derivables del estado.

#### Flujo de guardado

> **Estado actual:** la capa de persistencia (repositorio, `EventSourcingSaveSystem`, replay) está implementada y probada de forma aislada, pero el CLI **no la conecta**: `fortress-engine run --save` solo imprime «persistence deferred» y no se crea ningún sistema de guardado (`cli/main.py:287`). El flujo siguiente describe el diseño que se activará al conectarla.

1. El jugador ejecuta `GUARDAR <slot>` (no hay autoguardado: `game_saved` solo se emite desde ese comando).
2. Se emite `game_saved`.
3. `EventSourcingSaveSystem` (`persistence/event_log.py`), suscrito al `EventBus`, toma un snapshot del estado vía `state_provider` y lo guarda con `save_snapshot(state, turn, save_slot)`.

Los eventos de cambio de estado se van añadiendo al log (`append_event`) a medida que ocurren durante la partida.

> **Abierto:** los errores de guardado dentro de los handlers del bus se tragan (`events/event_bus.py`), por lo que un fallo de persistencia no interrumpe el turno ni se notifica al jugador — ver #82.

#### Algoritmo de replay (carga)

`EventSourcingSaveSystem.replay_state(state, save_slot, graph=None)`:

1. Emite `save_replay_started`.
2. Carga el snapshot más reciente del slot (`load_latest_snapshot`) y lo aplica al estado.
3. Lee los eventos posteriores al snapshot (`get_event_log(since_turn=...)`) y aplica cada evento de cambio de estado **directamente** sobre el estado, sin re-emitirlo por el bus.
4. Omite `action_resolved`; ante un tipo de evento desconocido lanza `CorruptEventError`.
5. Emite `save_replay_ended`; el motor reanuda el ciclo de turnos.

> **Abierto:** el estado `open` de las aristas Macro no forma parte del `WorldState` ni del log, por lo que no se restaura al cargar — ver #79.

**Ventajas del event sourcing para IA**: El log estructurado de acciones es el contexto perfecto para un LLM. Cada acción ejecutada es un dato inequívoco — no hay ambigüedad sobre qué hizo el jugador, en qué orden, con qué resultado. Un futuro narrador IA puede consumir este log para generar resúmenes de sesión, pistas contextuales, o narración adaptativa.

### 2.7 Sistema de Episodios

Un mundo puede dividirse en episodios secuenciales o independientes. Cada episodio tiene su propio grafo (rooms, ítems, NPCs, Hiper-Aristas), condiciones de victoria, y reglas de continuidad.

#### Definición de episodio en YAML

```yaml
# episode-01.yaml
id: "episode-01"
name: "La Fortaleza"
order: 1
description: |
  Primera parte de la aventura. Derrota a la Bestia
  eliminando sus cinco Centros vitales.
requires: []              # [] = independiente; ["ep-1"] = secuencial
start_anchor: "fortaleza-1-room-01"
goal:
  conditions:
    - type: entity_not_in_room
      entity: "fortaleza-1-npc-centro-cerebro"
      room: "fortaleza-1-room-22"
    - type: entity_not_in_room
      entity: "fortaleza-1-npc-centro-corazon"
      room: "fortaleza-1-room-21"
    - type: entity_not_in_room
      entity: "fortaleza-1-npc-centro-estomago"
      room: "fortaleza-1-room-20"
    - type: entity_not_in_room
      entity: "fortaleza-1-npc-centro-pulmones"
      room: "fortaleza-1-room-19"
    - type: entity_not_in_room
      entity: "fortaleza-1-npc-troll-12"
      room: "fortaleza-1-room-12"
  output: |
    Has vencido a la Bestia. Sus cinco Centros vitales
    han sido destruidos y el Troll de los Baños yace muerto.

    Parece ser una persona persistente...
    Veremos si en la próxima versión de La Fortaleza
    tiene igual suerte.
  side_effects: []       # efectos adicionales al cumplir el goal

carry_over:
  inventory: []           # [] = nada; ["*"] = todo; ["item_x"] = específicos
  flags: []               # [] = nada; ["*"] = todas; ["flag_a"] = específicas
```

#### Condiciones de goal disponibles

| Tipo | Parámetros | Descripción |
|------|-----------|-------------|
| `entity_in_room` | `entity`, `room` | La entidad está en la habitación especificada |
| `entity_not_in_room` | `entity`, `room` | La entidad NO está en la habitación especificada |
| `entity_dead` | `entity` | La entidad fue destruida (TRANSFER a null) |
| `flag_is_set` | `flag` | La bandera global tiene valor `true` |
| `flag_is_not_set` | `flag` | La bandera global tiene valor `false` o no existe |
| `entity_has_component` | `entity`, `component`, `value` | La entidad tiene el componente con el valor especificado |

Las condiciones pueden combinarse con `and` y `or` anidados (ver PRD sección 4.9 para la gramática completa).

#### Flujo de transición entre episodios

```
episodio_actual.completado
  │
  ├─ carry_over.inventory  → ¿qué ítems se transfieren?
  ├─ carry_over.flags      → ¿qué banderas se transfieren?
  │
  ├─ descargar grafo del episodio actual
  │   (rooms, ítems, NPCs, Hiper-Aristas se liberan de memoria)
  │
  ├─ cargar grafo del próximo episodio
  │   (nuevas rooms, ítems, NPCs, Hiper-Aristas desde archivos YAML)
  │
  └─ TELEPORT(jugador, null, start_anchor del nuevo episodio)
      → emitir episode_started
      → emitir entity_entered con descripción de la nueva room inicial
```

#### Episodios independientes vs secuenciales

- **`requires: []`**: el episodio puede iniciarse directamente. Útil para mundos con selección de capítulo.
- **`requires: ["episode-01"]`**: el episodio solo está disponible después de completar el episodio listado. Es el caso de Fortaleza: Parte II requiere Parte I.

#### Cómo el motor determina qué episodios están disponibles

Al cargar un mundo:
1. Carga todos los episodios desde `episodes/*.yaml` (un archivo por episodio; `world.yaml` no contiene la lista de episodios).
2. Marca como `available` aquellos cuyo `requires` está vacío.
3. Cuando un episodio se completa, marca como `available` aquellos cuyo `requires` contiene el episodio recién completado.
4. El jugador puede elegir entre los episodios disponibles (si hay más de uno).

Para Fortaleza: solo `episode-01` está disponible al inicio. Al completarlo, `episode-02` se desbloquea y la transición es automática (porque la lista de `episodes` tiene orden secuencial).

**Gestión de memoria**: El motor solo mantiene en memoria el grafo del episodio activo. Durante una transición, el grafo del episodio completado se descarga completamente antes de cargar el grafo del episodio siguiente. Esto:
- Minimiza el uso de memoria (solo ~55 nodos Macro en el peor caso para Fortaleza)
- Evita conflictos de identificadores entre episodios (room-01 puede existir en ambos episodios sin colisión)
- Simplifica el modelo mental: el motor siempre opera sobre un solo grafo de mundo en cada momento

---

## 3. Diseño del Mundo Fortaleza

Fortaleza es el primer mundo que valida el motor. No es el producto — es la prueba de que la arquitectura funciona. Cada habitación, objeto, NPC y puzle del original de 1995 debe ser expresable en el formato de datos del motor.

### 3.1 Estructura de Archivos

```
worlds/fortaleza/
├── world.yaml                    # Metadatos globales, idioma, configuración de plugins, lista de episodios
├── episodes/
│   ├── episode-01.yaml           # Parte I: goal, carry_over, configuración
│   └── episode-02.yaml           # Parte II: goal, carry_over, configuración
├── shared/
│   ├── player.yaml               # Definición del protagonista (compartido)
│   └── vocabulary.yaml           # Vocabulario del mundo: verbos y sinónimos, stopwords, preposiciones y marcadores de habla del parser; opcionalmente: messages (texto del narrador por error_code), movement_verbs y system_commands
├── episode-01/
│   ├── rooms/                    # 50 archivos, uno por room (alcoba_de_la_bruja.yaml, almacenes.yaml, …)
│   ├── items/                    # 57 archivos (antorcha_1.yaml, maza.yaml, …)
│   ├── npcs/                     # 24 archivos (arana.yaml, arpia.yaml, ciclope.yaml, …)
│   ├── actions/                  # 8 archivos, uno por verbo, cada uno con una lista de Hiper-Aristas
│   │   ├── he_dar.yaml           #   (he_matar.yaml, he_tomar.yaml, he_dejar.yaml, …)
│   │   └── ...
│   └── macros/                   # 124 archivos, una arista Macro por archivo (me_almacenes_jardin.yaml, …)
├── episode-02/
│   ├── rooms/                    # 55 archivos
│   ├── items/                    # 67 archivos
│   ├── npcs/                     # 23 archivos
│   ├── actions/                  # 9 archivos (he_dar_ep2.yaml, he_matar_ep2.yaml, …)
│   └── macros/                   # 61 archivos
└── narrator/                     # Existe pero está vacío: el narrador V1 usa DEFAULT_SPANISH_MESSAGES
                                  # (plugins/template_narrator.py) y los `messages` de shared/vocabulary.yaml
```

Las acciones se agrupan por verbo en listas YAML (el cargador acepta una lista por archivo); entre los dos episodios hay 17 archivos de acciones y 248 Hiper-Aristas.

### 3.2 Mapeo: Original → Motor

Cada concepto del código original (Turbo Pascal 7, `CASTLES.PAS`) se traduce a un concepto del motor:

| Concepto Original | Archivo/Función | Concepto en el Motor | Formato |
|-------------------|-----------------|---------------------|---------|
| `Room` | `CASTLES.PAS` | Entidad tipo `"room"` en Grafo Macro | `rooms/*.yaml` |
| `Thing` | `CASTLES.PAS` | Entidad tipo `"item"` | `items/*.yaml` |
| `Troll` / `Guard` / `TDaugther` | `CASTLES.PAS` | Entidad tipo `"npc"` con `combat_pattern` | `npcs/*.yaml` |
| `PMan` (jugador) | `CASTLES.PAS` | Entidad tipo `"player"` | `shared/player.yaml` |
| `PLinking` | `CASTLES.PAS` | Arista Macro con `requires_text` y `open: false`, o sin predicados | `macros/*.yaml` |
| `POpenLink` | `CASTLES.PAS` | Arista Macro sin predicados (siempre abierta) | `macros/*.yaml` |
| `PDangerLink` | `CASTLES.PAS` | Arista Macro con `requires_item` (+ `death_message`) | `macros/*.yaml` |
| `PDangerLink2` | `CASTLES.PAS` | Arista Macro con `forbids_item` (+ `death_message`) | `macros/*.yaml` |
| `PRiddleLink` | `CASTLES.PAS` | Arista Macro con `question` + `requires_text` + `open: false` | `macros/*.yaml` |
| `PHidden` | `CASTLES.PAS` | Hiper-Arista con operador COMBINE(herramienta, PHidden) | `actions/*.yaml` |
| `Castle.Go()` | `CASTLES.PAS:723` | Orquestador de Turnos: validación de arista Macro + TELEPORT | Motor |
| `Castle.Kill()` | `CASTLES.PAS:586` | Hiper-Aristas de combate con sistema de prioridades | `actions/*.yaml` |
| `Castle.Give()` | `CASTLES.PAS:678` | Hiper-Arista "dar_X_a_Y" con TRANSFER(item, inventory, null) | `actions/*.yaml` |
| `Castle.Break()` | `CASTLES.PAS:437` | Hiper-Arista con COMBINE(herramienta, PHidden) | `actions/*.yaml` |
| `Castle.Ask()` | `CASTLES.PAS:522` | Hiper-Arista "interrogar_X" con output de diálogo | `actions/*.yaml` |
| `Troll.Die()` | `CASTLES.PAS` | Patrón Troll en Hiper-Aristas de combate | `actions/*.yaml` |
| `Guard.Die()` | `CASTLES.PAS` | Patrón Guard en Hiper-Aristas de combate | `actions/*.yaml` |
| `TDaugther.Die()` | `CASTLES.PAS` | Patrón TDaugther en Hiper-Aristas de combate | `actions/*.yaml` |
| `Suitcase` / `Heaviness` | `CASTLES.PAS:66` | Validación de peso en TRANSFER al inventario | Motor |
| `Goal()` | `FORT1.PAS` / `FORT2.PAS` | Evaluador de goal del episodio | `episodes/*.yaml` |
| `SaveTrack()` / `ExecTrack()` | `CASTLES.PAS:1171` | Event Sourcing (event log + snapshot) | Motor |
| Banderas globales | Variables globales en Pascal | Libro de Banderas (diccionario clave-valor) | Motor (State Container) |
| `SetData()` | `FORT1.PAS` / `FORT2.PAS` | Carga de archivos YAML por directorio | Motor (World Loader) |

### 3.3 Ejemplos Concretos

Los siguientes 5 ejemplos muestran cómo elementos específicos de Fortaleza se traducen al formato YAML del motor. Se eligieron para cubrir los patrones más representativos.

> **Nota:** los ejemplos son ilustrativos. En el mundo real los ids de Fortaleza son cortos (`he_matar_ciclope`, `ciclope`, `maza`) y los textos deben provenir del original (ver #98: test automatizado de fidelidad de texto). Las claves de TRANSFER son `from_container` / `to_container`.

#### Ejemplo 1: Sala inicial (room-01, Parte I)

```yaml
# episode-01/rooms/room-01.yaml
entity_id: "fortaleza-1-room-01"
type: "room"
name: "el exterior de la fortaleza"
components:
  description: |
    Te encuentras en el exterior de una imponente fortaleza de
    piedra negra. Las torres se alzan hacia un cielo plomizo y
    el viento arrastra hojas secas a tus pies. Frente a ti, una
    pesada puerta de roble domina la muralla. Hay un Roble, una
    Maza, un Pastel de cerezas, un Llamador de bronce. La Puerta
    principal te bloquea el paso. También ves un Túnel y una
    Pared solitaria.
  visited: false
  dark: false
  episode: "episode-01"
spatial_anchor: null
```

#### Ejemplo 2: Conexión simple (room-01 → room-02)

```yaml
# episode-01/macros/edges-room-01.yaml
macro_edge_id: "fortaleza-1-edge-01-02-puerta-principal"
from_anchor: "fortaleza-1-room-01"
to_anchor: "fortaleza-1-room-02"
direction: "bidirectional"
passage_name: "Puerta principal"
passage_description: "Una pesada puerta de roble con refuerzos de hierro. Tiene un llamador de bronce."
requires_text: "ábrete sésamo"
open: false

---
macro_edge_id: "fortaleza-1-edge-01-04-tunel"
from_anchor: "fortaleza-1-room-01"
to_anchor: "fortaleza-1-room-04"
direction: "bidirectional"
passage_name: "Túnel"
passage_description: "Un túnel oscuro que se interna en la montaña."
```

#### Ejemplo 3: Guard con arma letal (Cíclope + Maza)

**Hiper-Arista de prioridad 10 (arma correcta)**:

```yaml
# episode-01/actions/matar-ciclope-maza.yaml
hyper_edge_id: "fortaleza-1-action-matar-ciclope-maza"
name: "Matar al Cíclope con la Maza"
priority: 10
clique:
  subject: "player"
  verb: "matar"
  target: "fortaleza-1-npc-ciclope"
  instrument: "fortaleza-1-item-maza"
  instrument_any: false
operators:
  - type: "TRANSFER"
    entity: "fortaleza-1-npc-ciclope"
    from_container: "fortaleza-1-room-06"
    to_container: null
  - type: "FLAG"
    flag: "ciclope_muerto"
    value: true
  - type: "FLAG"
    flag: "knows_password_puerta_gigante"
    value: true
output: |
  Blandes la Maza con todas tus fuerzas y golpeas al Cíclope
  en su único ojo. El gigante se tambalea y cae al suelo con
  un estruendo que hace temblar los estantes de la Biblioteca.

  Con su último aliento, el Cíclope susurra:
  "La contraseña de la Puerta gigante es... CIRCE."
```

**Hiper-Arista de prioridad 0 (catch-all, arma incorrecta)**:

```yaml
# episode-01/actions/matar-ciclope-fallback.yaml
hyper_edge_id: "fortaleza-1-action-matar-ciclope-fallback"
name: "Atacar al Cíclope con arma incorrecta"
priority: 0
clique:
  subject: "player"
  verb: "matar"
  target: "fortaleza-1-npc-ciclope"
  instrument: "*"
  instrument_any: true
operators: []
output: |
  Atacas al Cíclope con todas tus fuerzas, pero tu arma
  apenas logra arañar su gruesa piel.

  El Cíclope se ríe con desprecio:
  "Todos sus esfuerzos son en vano. Probablemente no esté
  usando el objeto indicado."
```

#### Ejemplo 4: DangerLink (pasaje que requiere Talismán)

```yaml
# episode-01/macros/edges-room-18.yaml
macro_edge_id: "fortaleza-1-edge-18-19-traquea"
from_anchor: "fortaleza-1-room-18"
to_anchor: "fortaleza-1-room-19"
direction: "bidirectional"
passage_name: "Tráquea"
requires_item: "fortaleza-1-item-talisman-aire"
passage_description: "Un conducto palpitante y resbaladizo. Las paredes se contraen rítmicamente."
death_message: |
  Intentas cruzar la Tráquea sin la protección adecuada.
  Las paredes se contraen y te aplastan como a un insecto.

  Lamento informarle que usted está muerto.
```

#### Ejemplo 5: Puzzle multi-paso (Columna de hielo → Martillo → Puerta negra)

Este es un ejemplo de cadena de Hiper-Aristas encadenadas por FLAGs. El puzzle original requiere romper una Columna de Cristal con la Antorcha 3, luego romper una Puerta de madera con un Martillo, y finalmente cruzar una Puerta negra.

**Paso 1: Romper la Columna de Cristal (revela Puerta de madera)**:

```yaml
# episode-01/actions/romper-columna-cristal.yaml
hyper_edge_id: "fortaleza-1-action-romper-columna-cristal"
name: "Romper la Columna de Cristal con Antorcha 3"
priority: 10
clique:
  subject: "player"
  verb: "romper"
  target: "fortaleza-1-item-columna-cristal"
  instrument: "fortaleza-1-item-antorcha-3"
operators:
  - type: "COMBINE"
    input_entities:
      - "fortaleza-1-item-antorcha-3"
      - "fortaleza-1-item-columna-cristal"
    output_entity: "fortaleza-1-item-puerta-madera-phidden"
  - type: "FLAG"
    flag: "columna_cristal_rota"
    value: true
output: |
  Acercas la Antorcha 3 a la Columna de Cristal.
  El hielo comienza a derretirse lentamente, revelando
  una Puerta de madera oculta tras la columna.
```

**Paso 2: Romper la Puerta de madera (revela Puerta negra)**:

```yaml
# episode-01/actions/romper-puerta-madera.yaml
hyper_edge_id: "fortaleza-1-action-romper-puerta-madera"
name: "Romper la Puerta de madera con el Martillo"
priority: 10
clique:
  subject: "player"
  verb: "romper"
  target: "fortaleza-1-item-puerta-madera-phidden"
  instrument: "fortaleza-1-item-martillo"
  flag: "columna_cristal_rota"
operators:
  - type: "COMBINE"
    input_entities:
      - "fortaleza-1-item-martillo"
      - "fortaleza-1-item-puerta-madera-phidden"
    output_entity: "fortaleza-1-item-puerta-negra-phidden"
  - type: "FLAG"
    flag: "puerta_madera_rota"
    value: true
output: |
  Golpeas la Puerta de madera con el Martillo.
  La madera se astilla y cede, revelando una Puerta negra
  que se abre a un pasadizo oscuro.
```

**Paso 3: Cruzar la Puerta negra**:

```yaml
# episode-01/macros/edges-room-28.yaml
macro_edge_id: "fortaleza-1-edge-28-50-puerta-negra"
from_anchor: "fortaleza-1-room-28"
to_anchor: "fortaleza-1-room-50"
direction: "unidirectional"
passage_name: "Puerta negra"
requires_flag: "puerta_madera_rota"
passage_description: "Una puerta negra que antes no estaba allí."
```

Nótese cómo la secuencia es: `columna_cristal_rota` → `puerta_madera_rota` → la arista Macro se desbloquea. Las banderas actúan como "llaves" que cada paso entrega al siguiente.

### 3.4 Contrato de Compatibilidad

El motor debe cumplir tres contratos con la obra original:

#### 1. El walkthrough debe ser ejecutable

Cada comando documentado en `docs/09-walkthrough.md` debe producir el mismo resultado en el motor que en el original. Esto incluye:

- Moverse entre las 88 habitaciones usando las mismas puertas y contraseñas.
- Resolver los 93 puzles con las mismas secuencias de acciones.
- Experimentar las mismas condiciones de victoria y derrota.
- Recibir los mismos mensajes de error ante comandos inválidos.

#### 2. Cada puzzle debe ser resoluble

Cada puzzle documentado en `docs/04-puzzles.md` debe ser resoluble con las mismas acciones que en el original. Las dependencias entre puzles (documentadas en `docs/10-puzzle-dependencies.md`) deben preservarse.

#### 3. Las ~22,000 palabras de texto deben preservarse exactamente

Cada palabra del texto original —descripciones de habitaciones, diálogos de NPCs, mensajes de sistema, confesiones de Guards, pistas de Trolls— debe estar presente en los archivos YAML del mundo, en los campos `description` y `output`. Con tildes, puntuación y mayúsculas exactamente como en el original.

### 3.5 Estadísticas del Mundo

| Elemento | Parte I | Parte II | Total |
|----------|---------|----------|-------|
| **Rooms** | 33 (1-33 + laberinto) | 55 (1-55) | 88 |
| **Ítems** | ~70 | ~53 | ~123 |
| **NPCs** | 14 Trolls + 8 Guards | 18 Trolls + 5 Guards + 1 TDaugther | ~46 |
| **Hiper-Aristas** | estimado ~200 | estimado ~250 | estimado ~450; **real: 248** en 17 archivos |
| **Aristas Macro** | ~40 | ~60 | ~100 |
| **Acertijos (RiddleLink)** | 4 | 3 | 7 |
| **Palabras de texto** | ~11,000 | ~11,000 | ~22,000 |
| **Episodios** | 1 (episode-01) | 1 (episode-02, secuencial) | 2 |

Nota sobre la estimación de Hiper-Aristas: cada puzzle se descompone en múltiples acciones (dar, interrogar con/sin regalo, matar con/sin arma correcta, romper, tomar, dejar). La estimación original era ~450; el mundo actual tiene 248 (las acciones genéricas con comodín, `target: "*"` y `@anchor`, reducen el número; la cobertura completa de los 93 puzles la verifica el walkthrough, #41).

---

## 4. Flujo de Creación de un Mundo Nuevo

Esta sección es una guía para diseñadores narrativos que quieren crear un mundo desde cero. No requiere conocimientos de programación — solo editar archivos YAML.

### Paso 1: Crear la estructura base

```bash
mkdir -p worlds/<nombre>/episodes
mkdir -p worlds/<nombre>/shared
mkdir -p worlds/<nombre>/episode-01/{rooms,items,npcs,actions,macros}
```

### Paso 2: Definir `world.yaml`

```yaml
# worlds/<nombre>/world.yaml
world_id: "mi-aventura"
name: "Mi Aventura"
version: "1.0"
language: "es"
author: "Tu Nombre"
description: "Una breve descripción de tu mundo."

parser:
  plugin: "classic"
  options: {}
narrator:
  plugin: "template"
  options: {}
```

> El cargador (`WorldYAML`) solo lee `world_id`, `name`, `language`, `parser` y
> `narrator`; las demás claves (`version`, `author`, `description`) son
> informativas y se ignoran. Los episodios **no** van en `world.yaml`: cada uno
> vive en `episodes/<id>.yaml` (ver Paso 9). `max_weight` se define en el
> protagonista (`shared/player.yaml`, Paso 3), no en `world.yaml`.

> La forma de objeto (`parser: {plugin: "classic", options: {}}`) y la forma
> legacy de string (`parser: "classic"`, `narrator: "template"`) son aceptadas;
> ambas se normalizan a un `PluginConfigYAML`. `language` (default `"es"`) se
> inyecta en el parser y el narrador al construirlos vía la plugin factory.

### Paso 3: Definir el protagonista

```yaml
# shared/player.yaml
entity_id: "mi-aventura-1-player"
type: "player"
name: "Aventurero"
components:
  player_controlled: true
  max_weight: 40
  state: "alive"
spatial_anchor: "mi-aventura-1-room-01"
```

### Paso 4: Crear rooms

Una room por archivo YAML. Incluir `description` (lo que el jugador lee al entrar). `visited` y `dark` son convenciones del mundo que el motor no lee (ver 2.1).

```yaml
# episode-01/rooms/room-01.yaml
entity_id: "mi-aventura-1-room-01"
type: "room"
name: "La entrada de la cueva"
components:
  description: |
    Estás frente a la entrada de una cueva oscura.
    El viento sopla desde el interior, trayendo un olor a humedad.
    Ves una Antorcha en el suelo y una Puerta de piedra.
  visited: false
  dark: false
spatial_anchor: null
```

### Paso 5: Crear ítems

Un ítem por archivo YAML. Definir `weight`, `portable`, y `spatial_anchor` (dónde aparece inicialmente).

```yaml
# episode-01/items/antorcha.yaml
entity_id: "mi-aventura-1-item-antorcha"
type: "item"
name: "Antorcha"
components:
  description: "Una antorcha de madera resinosa, lista para ser encendida."
  weight: 5
  portable: true
  state: "apagada"
  light_source: true
spatial_anchor: "mi-aventura-1-room-01"
```

### Paso 6: Crear NPCs

Definir `description` y los componentes que el mundo necesite (`mood`, `brain_type`, `lethalweap`, `likeness`… son convenciones que el motor no lee; la lógica real vive en las Hiper-Aristas).

```yaml
# episode-01/npcs/dragon.yaml
entity_id: "mi-aventura-1-npc-dragon"
type: "npc"
name: "Dragón"
components:
  description: "Un dragón escupefuego que bloquea el paso."
  mood: "hostile"
  brain_type: "reactive"
  hit_points: 1
  lethalweap: "Espada de cristal"
  combat_pattern: "guard"
  dialogue:
    HiData: "El dragón se desploma. 'La llave... está en el cofre...'"
    LowData: "¡Tus ataques no pueden atravesar sus escamas!"
spatial_anchor: "mi-aventura-1-room-03"
```

### Paso 7: Definir conexiones entre rooms (Aristas Macro)

```yaml
# episode-01/macros/edges-room-01.yaml
macro_edge_id: "mi-aventura-1-edge-01-02"
from_anchor: "mi-aventura-1-room-01"
to_anchor: "mi-aventura-1-room-02"
direction: "bidirectional"
passage_name: "Puerta de piedra"
passage_description: "Una puerta de piedra que se desliza hacia un lado."
```

### Paso 8: Definir Hiper-Aristas para interacciones

Aquí es donde se define la jugabilidad. Cada interacción (tomar, matar, dar, romper, interrogar) es una Hiper-Arista.

```yaml
# episode-01/actions/matar-dragon-espada.yaml
hyper_edge_id: "mi-aventura-1-action-matar-dragon-espada"
name: "Matar al Dragón con la Espada de cristal"
priority: 10
clique:
  subject: "player"
  verb: "matar"
  target: "mi-aventura-1-npc-dragon"
  instrument: "mi-aventura-1-item-espada-cristal"
operators:
  - type: "TRANSFER"
    entity: "mi-aventura-1-npc-dragon"
    from_container: "mi-aventura-1-room-03"
    to_container: null
  - type: "FLAG"
    flag: "dragon_muerto"
    value: true
output: "Atraviesas el corazón del dragón con la Espada de cristal. Cae muerto."

---
# episode-01/actions/matar-dragon-fallback.yaml
hyper_edge_id: "mi-aventura-1-action-matar-dragon-fallback"
name: "Atacar al Dragón con arma incorrecta"
priority: 0
clique:
  subject: "player"
  verb: "matar"
  target: "mi-aventura-1-npc-dragon"
  instrument: "*"
  instrument_any: true
operators: []
output: "¡Tus ataques no pueden atravesar sus escamas!"
```

### Paso 9: Definir condiciones de victoria

En `episodes/episode-01.yaml`, el campo `goal` define qué debe cumplirse para ganar:

```yaml
# worlds/<nombre>/episodes/episode-01.yaml
id: "episode-01"
name: "Capítulo 1"
order: 1
requires: []
start_anchor: "mi-aventura-1-room-01"
goal:
  conditions:
    - type: entity_dead
      entity: "mi-aventura-1-npc-dragon"   # o anidado: params: {entity: ...}
  output: "¡Has derrotado al dragón!"
carry_over:
  inventory: []
  flags: []
```

Las condiciones aceptan parámetros planos (`entity:`, `room:`) o anidados en `params:`.

### Paso 10: Validar el mundo

El CLI `fortress-engine` ya incluye tres herramientas de verificación:

```bash
fortress-engine validate worlds/mi-aventura/ [--verbose]      # integridad del mundo (referencias colgantes, etc.)
fortress-engine audit-graph worlds/mi-aventura/ [--episode ID] [--json] [--include-info]   # auditoría estática del grafo Macro
fortress-engine solve worlds/mi-aventura/ [--episode ID] [--answers FILE] [--json] [--max-turns N]   # completabilidad por exploración ciega
```

- `validate` carga el mundo y devuelve los problemas de integridad (código de salida distinto de 0 si hay alguno).
- `audit-graph` audita la integridad del grafo Macro de un episodio.
- `solve` verifica que el episodio sea completable explorando a ciegas dentro de un presupuesto de turnos.

> **Abierto:** el alcance del validador (más allá de lo anterior) — ver #46.

### Paso 11: Probar con el walkthrough

Escribir un archivo `walkthrough.txt` con la secuencia de comandos para completar el mundo y ejecutarlo contra el motor:

```bash
fortress-engine test worlds/mi-aventura/ --walkthrough walkthrough.txt [--episode episode-01]
```

Esto ejecuta cada comando y comprueba si se cumple el goal del episodio.

---

## 5. Decisiones de Diseño Pendientes (para TDD)

El TDD ya existe (`tdd.md`) y resolvió la mayoría de las decisiones que este GDD dejaba abiertas. Estado actual:

| Tema | Estado |
|------|--------|
| Estructura de clases Python | Resuelto — TDD §3–4 |
| Esquema SQLite | Resuelto — TDD §5 (migraciones: Alembic sin inicializar, #22) |
| API REST | No planificada |
| Serialización y versionado de eventos | Abierto — #81 (decisión JSON vs SQLite: #97) |
| Parser V1 | Resuelto — TDD §4.15 |
| Parser NLP | Abierto — #91 (el parser clásico se mantiene como réplica fiel del original) |
| Narrador V1 (plantillas) | Resuelto — TDD §4.16 |
| Plugins | Resuelto — TDD §9 |
| Concurrencia | Resuelto — TDD §11.2 (single-threaded, síncrono) |
| Testing | Resuelto — TDD §7 |
| Fidelidad de texto | Abierto — #98 |

---

## Referencias

| Documento | Descripción |
|-----------|-------------|
| `prd.md` | Product Requirements Document v2.0 |
| `docs/12-engine-gap-analysis.md` | Análisis de brechas entre PRD y Fortaleza; resolvió los gaps CRÍTICOS |
| `docs/13-event-system.md` | Diseño del sistema de eventos: bus síncrono, taxonomía, contratos |
| `docs/06-mechanics.md` | Mecánicas del juego original (inventario, combate, movimiento, guardado) |
| `docs/08-room-graph.md` | Grafo completo de conexiones entre las 88 habitaciones |
| `docs/09-walkthrough.md` | Walkthrough completo comando por comando (ambas partes) |
| `docs/04-puzzles.md` | Los 93 puzles con mecánicas y soluciones |
| `docs/10-puzzle-dependencies.md` | Grafo de dependencias entre puzles |

---

*Documento preparado a partir del PRD v2.0, el Gap Analysis #12, el Event System #13, y los 7 documentos de diseño de Fortaleza. Define el WHAT y WHY del motor y su primer mundo, dejando el HOW para el TDD.*
