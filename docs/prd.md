# PRD — Motor de Grafo Semántico para Ficción Interactiva Generativa

**Versión**: 2.0
**Tipo**: Product Requirements Document
**Idioma**: Español

---

## 1. Resumen Ejecutivo

**Qué**: Un motor de grafo semántico para ficción interactiva. No es un juego — es una máquina virtual para mundos interactivos. Los mundos se definen como datos (grafos en JSON/YAML); el motor los interpreta sin conocer su contenido.

**Por qué**: Separar la creación de mundos de la programación del motor. Un diseñador narrativo puede construir una aventura conversacional completa sin escribir una línea de código. La arquitectura de grafos con hiper-aristas convierte la validación de acciones en un problema de pathfinding, eliminando anidamientos de condicionales.

**Visión**: Construir una vez, ejecutar infinitos mundos. Fortaleza —la aventura conversacional en español de Miguel Enrique Cepero (1995)— es el mundo de prueba que demuestra que el motor puede replicar fielmente una obra compleja de 88 habitaciones, ~120 objetos, ~50 NPCs y 93 puzles, preservando cada palabra del texto original. El motor no sabe nada de Fortaleza; solo interpreta su grafo.

---

## 2. Identidad del Producto

### Esto ES

- Un **motor data-driven** que interpreta definiciones de mundo basadas en grafos
- Una **plataforma** para crear y ejecutar aventuras conversacionales
- Una **máquina virtual** donde la lógica del mundo vive en datos, no en código
- Un sistema con **interfaces enchufables** para parser y narrador
- Una arquitectura **AI-ready**: los LLMs se conectan como decoradores semánticos, no como cerebro del mundo

### Esto NO ES

- Un remake de La Fortaleza (Fortaleza es el primer mundo de ejemplo, no el producto)
- Un motor para un solo juego
- Un motor de aventuras gráficas
- Un sistema de generación procedural de mundos
- Un juego con lógica cableada en el código

---

## 3. Usuarios Objetivo

| Segmento | Rol | Necesidad |
|----------|-----|-----------|
| **Diseñadores narrativos** | Creadores de mundos | Definir mundos completos editando JSON/YAML, sin tocar el código del motor |
| **Desarrolladores** | Extensores del motor | Implementar plugins de parser y narrador contra interfaces estables |
| **Jugadores** | Usuarios finales | Experimentar mundos a través del runtime del motor |
| **Investigadores de IA** | Integradores de LLMs | Conectar modelos de lenguaje como parsers intencionales o narradores inmersivos |

---

## 4. Arquitectura Central

### 4.1 Modelo de Entidad Genérico

Cada elemento del mundo —jugador, NPC, puerta, habitación, contenedor, concepto abstracto— es una **Entidad** con:

- **UUID**: identificador único global
- **Componentes**: diccionarios clave-valor que definen estado (`state: "open"`, `durability: 10`, `mood: "hostile"`, `weight: 39`)
- **Anclaje Espacial**: referencia a la entidad contenedora ("la mesa está en la cocina", "el jugador está en el bosque")
- **Protagonistas**: el motor soporta **múltiples protagonistas** controlados por el jugador. Cualquier entidad con el componente `player_controlled: true` es un protagonista. No hay límite en la cantidad de entidades controlables simultáneamente.
  - El **protagonista activo** es la entidad `player_controlled` que actualmente tiene el foco de entrada del jugador.
  - **Cambiar de protagonista** es una acción de primera clase: el jugador transfiere el foco de una entidad controlable a otra con el comando `CAMBIAR A <nombre>`.
  - Cada protagonista mantiene su propio estado, inventario y posición en la escena que habita. Cambiar de protagonista no mueve entidades ni fusiona inventarios.

### 4.2 Topología de Grafo Dual (Macro y Micro)

Dos capas de grafo interconectadas separan el espacio de la interacción:

**Grafo Macro (Mapa Físico)**
- **Nodos Macro**: contenedores de escena (habitaciones, regiones, planetas)
- **Aristas Macro**: conexiones topológicas (pasillos, túneles, rutas de viaje). Cada arista tiene predicados de acceso (ej. `requires: "golden_key"`, `only_if_flag: "quest_complete"`)

**Grafo Micro (Mapa Semántico de Escena)**
- Dentro de cada Nodo Macro existe un subgrafo completo
- **Nodos Micro**: objetos, NPCs, elementos contextuales presentes en esa escena
- **Aristas Micro**: interacciones potenciales entre elementos (ej. "fósforo" se conecta con "leña")

### 4.3 Hiper-Aristas (Acciones Reificadas)

Las acciones NO son funciones — son nodos especiales en el Grafo Micro. Una **Hiper-Arista** (Nodo de Acción) requiere una **Clique de Participación** para activarse:

- Para que la acción "Encender" sea válida, el motor debe encontrar aristas activas que conecten Jugador + Fósforo + Leña + Chimenea con el nodo de acción
- Si falta un participante, o si la Leña está en el inventario pero la Chimenea está en otra habitación, la clique no se forma y la acción es imposible
- Esto elimina los `if/else` anidados — la validación se convierte en un problema de pathfinding en el grafo

Cada Hiper-Arista define:
- **Prioridad**: número entero que determina el orden de evaluación cuando existen múltiples Hiper-Aristas para el mismo verbo y objetivo. Mayor prioridad = se evalúa primero.
- **Clique de Participación**: conjunto de entidades requeridas y sus roles (`subject`, `target`, `instrument`, `context`). Los predicados de clique incluyen `instrument`, `instrument_not`, `instrument_any`, `flag`, `flag_not`, y `component`.
- **Secuencia de Operadores Atómicos**: los 5 operadores que se ejecutan si la clique es válida (puede ser una secuencia vacía `[]` si la acción solo produce texto)
- **Output**: texto que el narrador emite cuando la acción se ejecuta

**Comportamiento condicional sin operadores nuevos**: El motor no necesita un operador `if/then/else`. La ramificación se logra definiendo múltiples Hiper-Aristas para el mismo verbo + objetivo, cada una con distinta prioridad y diferentes predicados de clique. El motor evalúa en orden de prioridad descendente: la primera Hiper-Arista cuya Clique de Participación se forme es la que se ejecuta. Las de menor prioridad actúan como fallback.

Ejemplo — matar al Cíclope:
- `matar_ciclope_maza` (prioridad 10, `instrument: "Maza"`) → TRANSFER + FLAG + output de muerte
- `matar_ciclope_fallback` (prioridad 0, `instrument_any: true`) → secuencia vacía + output de burla

Esto requiere **cero operadores nuevos**. El motor solo necesita evaluar Hiper-Aristas en orden de prioridad para el mismo par (verbo, objetivo).

**Cliques multi-protagonista**: una Hiper-Arista puede exigir múltiples entidades `player_controlled` como participantes. Esto permite puzles cooperativos entre protagonistas de forma nativa en el grafo.

- Ejemplo: la acción `levantar_reja` requiere a `Protagonista_A` en la palanca (`subject`) Y a `Protagonista_B` en el portón (`context`).
- La clique no se forma hasta que ambas entidades `player_controlled` están en las posiciones requeridas.
- El motor trata a todos los protagonistas como entidades equivalentes en la validación de cliques — no hay distinción artificial entre "jugador principal" y "secundario".

### 4.3.1 Patrones de Combate

El combate no es un concepto del motor — es un **patrón de diseño de mundo** que los diseñadores siguen al definir Hiper-Aristas. Tres patrones cubren todos los enfrentamientos de Fortaleza:

**Patrón Guard**: enemigo que solo muere con su arma letal (`lethalweap`). Con cualquier otra arma, se burla sin cambio de estado.
- Hiper-Arista A (prioridad 10): `instrument: "<lethalweap>"` → TRANSFER(enemigo, sala, null) + FLAG(enemigo_muerto) + output de confesión
- Hiper-Arista B (prioridad 0): `instrument_any: true` → secuencia vacía + output de burla

**Patrón Troll**: enemigo que muere con cualquier arma.
- Hiper-Arista única: `instrument_any: true` → TRANSFER(enemigo, sala, null) + FLAG(enemigo_muerto) + output de muerte

**Patrón TDaugther**: enemigo que solo muere con un arma específica; cualquier otra arma causa la muerte del jugador.
- Hiper-Arista A (prioridad 10): `instrument: "Aguja"` → TRANSFER(enemigo, sala, null) + FLAG(enemigo_muerto) + TELEPORT(Cáliz, _limbo, sala_46)
- Hiper-Arista B (prioridad 0): `instrument_not: "Aguja"` → FLAG(player_dead) + output de muerte del jugador

Estos patrones son **convenciones YAML**, no conceptos del motor. Cualquier diseñador de mundo puede definir sus propios patrones de combate o interacción usando múltiples Hiper-Aristas con prioridad.

**Dónde se define `lethalweap`**: Es un **componente de la entidad NPC**, no un concepto del motor. Se define en el archivo YAML del NPC:

```yaml
# npcs/ciclope.yaml
entity_id: "ciclope-01"
type: "npc"
name: "Cíclope"
components:
  mood: "hostile"
  lethalweap: "Maza"
  description: "Un cíclope enorme bloquea el paso..."
```

Las Hiper-Aristas de combate consultan este componente mediante el predicado `instrument: "<valor>"`. El motor solo compara el instrumento usado por el jugador con el valor del componente `lethalweap` — no tiene lógica de combate cableada.

### 4.4 Cinco Operadores Atómicos Universales

El motor solo implementa 5 operadores transaccionales. Cada Hiper-Arista ejecuta una secuencia de estos:

| # | Operador | Descripción | Ejemplo |
|---|----------|-------------|---------|
| 1 | **TRANSFER** | Mueve una entidad de un contenedor a otro | mesa → inventario |
| 2 | **TRANSFORM** | Cambia el componente de estado de una entidad | madera → cenizas; cerradura → rota |
| 3 | **COMBINE** | Toma múltiples entidades de entrada y genera una nueva entidad de salida | harina + agua = masa |
| 4 | **FLAG** | Establece o limpia una bandera global en el Estado del Mundo | `boss_defeated: true` |
| 5 | **TELEPORT** | Cambia el Anclaje Espacial de una entidad | mover al jugador a otro Nodo Macro |

**Validación de peso en TRANSFER**: La validación de peso se aplica **únicamente** cuando `destination == player.inventory`. Las transferencias entre otros contenedores (sala → cofre, cofre → sala, NPC → sala) no tienen restricción de peso. Esto permite que cofres y salas contengan cualquier cantidad de objetos sin límite artificial.

Cuando el destino de una operación TRANSFER es `player.inventory`, el motor ejecuta dos validaciones antes de aplicar la transferencia:

1. **Peso máximo individual**: si `entity.weight > player.max_weight`, la acción se rechaza con output `"Usted no puede cargar con eso."`.
2. **Capacidad del inventario**: si `sum(inventory_items.weight) + entity.weight > player.max_weight`, la acción se rechaza con output `"Sería demasiado peso."`.

El valor `player.max_weight` se configura en `world.yaml` (por defecto 40). Cada entidad portable define su `weight` como componente (ej: `weight: 39` para el Bote y la Maza, objetos al borde del límite).

### 4.5 Estado Global y Persistencia

Un único contenedor de estado mutable:

- **Diccionario de Entidades**: todos los nodos del grafo con sus componentes actualizados
- **Libro de Banderas**: variables globales que actúan como "memoria del mundo" — cualquier condición de acceso en una arista puede consultar este libro
- **100% serializable** a JSON/BSON. Aunque el estado completo es 100% serializable, la estrategia de persistencia canónica es **Event Sourcing**: se almacena un log de Hiper-Aristas ejecutadas (ver sección 10). El motor puede regenerar cualquier estado reproduciendo el log desde el estado inicial. Opcionalmente, para acelerar la carga, el motor puede mantener un snapshot caché del último estado guardado, pero la fuente de verdad es el log de eventos.

### 4.6 Orquestador de Turnos

No es un simple bucle entrada→salida. Es un **Sistema de Turnos Sincrónico** que orquesta múltiples protagonistas y NPCs.

**Principio arquitectónico**: El Orquestador de Turnos siempre itera sobre `player_controlled_entities` como una colección (lista o conjunto), nunca asume un singleton. Incluso cuando el mundo define un solo protagonista, el código del motor trata `player_controlled_entities` como una colección de N elementos. Esto garantiza que el soporte multi-protagonista no requiera refactorización futura.

Para cada **ciclo de turno**:

1. **Turno del Protagonista Activo**:
   - Recibe la entrada de texto del jugador para el protagonista que tiene el foco.
   - El parser resuelve la intención en la escena actual de ESE protagonista.
   - Las acciones se ejecutan en el contexto de ese protagonista (su inventario, su posición, sus componentes).

2. **Turno de Otros Protagonistas**:
   - Las demás entidades `player_controlled` pueden ejecutar acciones en cola o autónomas (si tienen un componente `brain` configurado en modo autónomo).
   - Cada una permanece en su escena actual con su propio estado e inventario, sin interferir con las demás.
   - **En el MVP**: si el mundo define un solo protagonista (`len(player_controlled_entities) == 1`), este paso es un no-op. Si el mundo define múltiples protagonistas pero ninguno tiene `brain` configurado en modo autónomo ni acciones en cola, simplemente pasan su turno. La capacidad de encolar acciones y los cerebros autónomos se implementan en v1.1.

3. **Turno de NPCs (Escena)**:
   - Cada entidad con componente `brain` —sin importar en qué escena está— consulta su subgrafo de acciones disponibles según el estado actual y las banderas globales.
     - **Cerebro scripteado**: elige la arista de mayor prioridad.
     - **Cerebro generativo (IA)**: un LLM recibe las aristas disponibles en lenguaje natural y selecciona una.

4. **Resolución**:
   - Todas las acciones de todas las escenas se validan y ejecutan, aplicando los operadores atómicos.
   - El narrador produce salida desde la perspectiva del **protagonista activo**.
   - Opcionalmente, el narrador puede incluir resúmenes breves de eventos relevantes que ocurrieron a otros protagonistas (depende de la implementación del narrador — el motor expone los datos, el narrador decide cómo presentarlos).

**Comandos especiales para múltiples protagonistas**:

| Comando | Efecto |
|---------|--------|
| `CAMBIAR A <nombre>` | Transfiere el foco de entrada al protagonista indicado. El protagonista anterior pasa a estado inactivo (pero sigue existiendo en su escena). |
| `ESPERAR` | El protagonista activo pasa su turno sin actuar. Los demás protagonistas y NPCs ejecutan sus turnos normalmente. |
| `GRUPO` | Lista todos los protagonistas con su nombre, ubicación actual y estado resumido ("en combate", "herido", "descansando"). |

**Nota sobre MVP vs v1.1**: La arquitectura del motor trata `player_controlled_entities` como una colección desde el día uno, y el loop de turnos itera sobre ella incluso cuando la lista tiene 1 elemento. Sin embargo:
- **MVP**: El loop de turnos funciona pero solo existe 1 protagonista. Los otros protagonistas pasan su turno silenciosamente (no-op).
- **v1.1**: Comandos de usuario (`CAMBIAR A`, `GRUPO`, `ESPERAR`), cliques cooperativas, y cerebros autónomos para otros protagonistas.

### 4.7 Puente de IA (El "Decorador Semántico")

La IA (LLM) NO participa en la lógica del mundo — solo en la interfaz humano-máquina. Esto previene alucinaciones de puzles:

- **Parser Intencional**: toma entrada en texto libre del jugador ("toma el farol viejo de la mesa") y la traduce a una tupla estructurada: `{subject: "player", verb: "take", target: "lantern", context: "table"}`. El motor encuentra este verbo en el Grafo Micro de la escena actual.

- **Narrador Inmersivo**: después de que el motor ejecuta una transacción y obtiene un resultado crudo ("Objeto transferido al inventario"), se invoca al LLM con el estado actual y el resultado. El LLM genera prosa atmosférica y rica ("Tomas el farol de bronce frío; el polvo centellea en la tenue luz que se filtra por la ventana"). **La IA decora la realidad; no la crea.**

### 4.8 Carga del Mundo desde Archivos YAML

El motor carga los datos del mundo escaneando directorios de archivos YAML. El proceso de carga es:

1. Escanea el directorio `worlds/<nombre-del-mundo>/`
2. Carga `world.yaml` primero (configuración global, banderas iniciales)
3. Carga todos los `rooms/*.yaml` → construye los Nodos del Grafo Macro
4. Carga todos los `items/*.yaml` y `npcs/*.yaml` → los ubica en sus habitaciones iniciales (anclaje espacial)
5. Carga todos los `actions/*.yaml` → construye las Hiper-Aristas

   El motor escanea **recursivamente** todos los subdirectorios de `actions/` (y cualquier otro directorio de datos). El orden de precedencia entre archivos no importa porque las Hiper-Aristas se ordenan por prioridad en tiempo de ejecución, no por orden de archivo.

6. Valida el grafo completo:
   - Sin referencias colgantes (toda entidad referenciada en cliques, predicados y operadores existe)
   - Sin prioridades duplicadas para el mismo par (verbo, objetivo) — si dos Hiper-Aristas comparten verbo, objetivo y prioridad, el motor emite una advertencia
   - Todas las banderas referenciadas en predicados `flag`/`flag_not` están declaradas en `world.yaml` o en algún episodio
   - Todas las habitaciones referenciadas como `start_anchor` existen en los datos de rooms
   - Validación de carry_over: los ítems y banderas referenciados existen en el episodio origen
7. Construye la estructura de grafo en memoria

### 4.9 Soporte Multi-Episodio

Un mundo puede dividirse en múltiples episodios, cada uno con su propio grafo, condiciones de victoria y reglas de continuidad.

**Definición de episodios** (`world.yaml` → `episodes: []`):

```yaml
episodes:
  - id: "ep-1"
    name: "La Fortaleza — Parte I"
    requires: []
    start_anchor: room-01
    goal:
      conditions:
        - type: entity_not_in_room
          entity: Centro_del_cerebro
          room: room-22
        # ... más condiciones
    carry_over:
      inventory: []
      flags: []
  - id: "ep-2"
    name: "La Fortaleza — Parte II"
    requires: [ep-1]
    start_anchor: room-01
    goal:
      conditions:
        - type: entity_in_room
          entity: Antorcha
          room: room-03
        # ... 7 objetos en ubicaciones + 2 enemigos muertos
    carry_over:
      inventory: []
      flags: []
```

**Campos de cada episodio**:
- `id`: identificador único del episodio
- `name`: nombre descriptivo
- `requires: []`: lista de episodios que deben completarse antes. `[]` = independiente (puede iniciarse directamente). `[ep-1]` = secuencial.
- `start_anchor`: habitación donde aparece el jugador al iniciar el episodio
- `goal`: condiciones de victoria evaluadas por el motor al final de cada turno
- `carry_over`: qué se transfiere al próximo episodio

**Campos de `carry_over`**:
- `inventory`: `["*"]` (todo el inventario), `["item_x"]` (ítems específicos), o `[]` (nada)
- `flags`: `["*"]` (todas las banderas), `["flag_a"]` (banderas específicas), o `[]` (nada)

**Flujo de transición entre episodios**:
1. El evaluador de goal detecta que se cumplieron las condiciones de victoria del episodio actual
2. El motor emite los eventos de victoria (texto de cierre, eventos del mundo)
3. Si existe un próximo episodio (definido por `requires` o secuencia), el motor aplica `carry_over`: transfiere inventario y banderas según lo especificado
4. Descarga el grafo del episodio actual y carga el grafo del próximo episodio desde `episodes/<id>.yaml` y sus directorios asociados
5. Ejecuta TELEPORT del jugador a `start_anchor` del nuevo episodio
6. Emite evento de inicio de episodio (texto de introducción, descripción de la habitación inicial)

Si no hay próximo episodio, el motor emite el evento de victoria final del mundo.

**Estructura de archivos con episodios**: ver sección 7.5.

**Nota sobre Fortaleza**: En el original, Parte I y II son programas separados sin estado compartido. La implementación los modela como dos episodios dentro de `worlds/fortaleza/` con `carry_over: {inventory: [], flags: []}` — preservando la separación total. El motor soporta carry_over para permitir mundos futuros con continuidad narrativa entre episodios.

**Gramática de condiciones de victoria**:

El evaluador de `goal` soporta los siguientes tipos de condición:

| Tipo | Parámetros | Descripción |
|------|-----------|-------------|
| `entity_in_room` | `entity`, `room` | La entidad está en la habitación especificada |
| `entity_not_in_room` | `entity`, `room` | La entidad NO está en la habitación especificada |
| `entity_dead` | `entity` | La entidad fue destruida (TRANSFER a null) |
| `flag_is_set` | `flag` | La bandera global tiene valor `true` |
| `flag_is_not_set` | `flag` | La bandera global tiene valor `false` o no existe |
| `entity_has_component` | `entity`, `component`, `value` | La entidad tiene el componente con el valor especificado |

Las condiciones pueden combinarse con `and` y `or`:

```yaml
goal:
  conditions:
    and:
      - type: entity_not_in_room
        entity: Centro_del_cerebro
        room: room-22
      - type: entity_not_in_room
        entity: Centro_del_corazon
        room: room-21
      - or:
          - type: flag_is_set
            flag: ruta_alternativa
          - type: entity_dead
            entity: Guardian_del_puente
      - type: entity_not_in_room
        entity: Troll
        room: room-12
```

El evaluador se ejecuta al final de cada turno. Si todas las condiciones se cumplen, el episodio se considera completado.

**Gestión de memoria**: El motor solo mantiene en memoria el grafo del episodio activo. Durante una transición, el grafo del episodio completado se descarga completamente antes de cargar el grafo del episodio siguiente. Esto:
- Minimiza el uso de memoria (solo ~88 nodos Macro en el peor caso para Fortaleza)
- Evita conflictos de identificadores entre episodios (dos episodios pueden tener room-01 sin colisión)
- Simplifica el modelo mental: el motor siempre opera sobre un solo grafo de mundo en cada momento

---

## 5. Sistema de Parser (Enchufable)

El parser es una **interfaz de plugin**. El motor nunca sabe qué parser está ejecutándose — solo recibe una tupla estructurada y la procesa.

### Interfaz del Parser

Todos los parsers implementan la misma interfaz:

```
Input:  (raw_text: string, world_state: WorldState)
        Donde world_state incluye:
        - active_protagonist_id: el protagonista que tiene el foco actual
        - entities: diccionario completo de entidades con sus componentes
        - flags: libro de banderas globales
        - current_episode: identificador del episodio activo
Output: { subject: EntityID, verb: string, target: EntityID, context: EntityID?, instrument: EntityID? }
```

El motor recibe esta tupla y busca el verbo en el Grafo Micro de la escena actual para formar la Clique de Participación.

### V1: Parser Clásico (MVP)

Réplica exacta del parser original de Fortaleza:
- **37 verbos** reconocidos (IR, TOMAR, MATAR, DAR, ABRIR, ROMPER, INTERROGAR, etc.)
- **~180 sustantivos** entre objetos, puertas, NPCs y ubicaciones
- Matching parcial de nombres (`"Puerta Principal"` coincide con `"Puerta"`)
- Normalización de tildes (`áéíóúüñ → aeiounN`)
- Ignora artículos (`LA`, `EL`) y la preposición `POR`
- Ignora la preposición `AL`
- Sintaxis completa documentada en `docs/07-vocabulary.md`

### V2: Parser Clásico Expandido

Expande las stopwords del parser original para mejorar la experiencia de usuario:
- Agrega a las stopwords de V1: `UN`, `UNA`, `DEL`, `LOS`, `LAS`
- Misma lógica de matching parcial y normalización que V1
- Compatible hacia atrás: todos los comandos que funcionan en V1 funcionan en V2

### V3: Parser Intencional (IA)

Reemplaza el parser clásico por un LLM:
- Recibe texto libre en lenguaje natural + el estado del mundo
- Traduce a la misma tupla estructurada `{subject, verb, target, context, instrument}`
- El motor no sabe qué parser está usando — la interfaz es idéntica

### Extensibilidad

Nuevos parsers (para otros idiomas, para entrada por voz, para interfaces gráficas) se pueden agregar sin tocar el código del motor. Solo deben implementar la interfaz de parser.

---

## 6. Sistema de Narrador (Enchufable)

El narrador convierte el resultado crudo del motor en texto que el jugador lee.

### Interfaz del Narrador

```
Input:  resultado estructurado de la transacción + estado actual del mundo
Output: texto para el jugador (string)
```

### V1: Narrador por Plantillas (MVP)

- El texto de salida se obtiene directamente de los datos del mundo
- Las descripciones de habitaciones, diálogos de NPCs, mensajes de sistema están en los archivos de datos
- Sin generación — el texto es exactamente el definido por el diseñador del mundo

El narrador V1 es responsable de TODO el texto que ve el jugador:
- **Descripciones de habitaciones**: después de cada TELEPORT del protagonista, el motor notifica al narrador con `entity_entered`, y el narrador emite la descripción de la habitación desde el componente `description` de la entidad room.
- **Output de acciones**: el texto del campo `output` de cada Hiper-Arista ejecutada.
- **Mensajes del sistema**: errores del parser, mensajes de peso excedido, notificaciones de guardado.
- **Eventos narrativos**: introducción de episodios, textos de victoria y derrota.

El motor produce eventos (`entity_entered`, `action_output`, `error_output`, etc.) y el narrador los convierte en texto. Ver `docs/13-event-system.md` para la taxonomía completa de eventos.

### V2: Narrador Inmersivo (IA)

- El motor produce el resultado estructurado crudo
- Un LLM recibe el estado actual de la escena y el resultado
- Genera prosa atmosférica y rica que envuelve el resultado crudo
- Ejemplo: resultado crudo `{action: "TRANSFER", entity: "old_lantern", from: "table", to: "inventory"}` → "Tomas el farol de bronce frío de la mesa; el polvo centellea en la tenue luz que se filtra por la ventana."

### Extensibilidad

Nuevos narradores (otros idiomas, diferentes estilos literarios, narración por voz) se agregan sin modificar el motor.

---

## 7. Primer Mundo de Ejemplo: Fortaleza

Fortaleza es el proof-of-concept que valida la arquitectura del motor. No es el producto — es el primer mundo que demuestra que el motor puede replicar una obra compleja preservando cada detalle.

**Nota sobre múltiples protagonistas**: Fortaleza Parte I y II son juegos de un solo protagonista. Sus datos de mundo definen `player_controlled: true` en exactamente una entidad. El soporte multi-protagonista es una capacidad del **motor**, no una característica de este mundo. Mundos futuros —como un ejemplo de aventura cooperativa— demostrarán la funcionalidad completa con múltiples protagonistas, comandos `CAMBIAR A`, puzles cooperativos con cliques multi-protagonista y turnos orquestados entre varios personajes controlables.

### 7.1 Especificación como Datos de Grafo

| Elemento | Cantidad | Tipo en el Grafo |
|----------|----------|------------------|
| **Habitaciones** | 88 (33 Parte I + 55 Parte II) | Nodos Macro |
| **Conexiones entre habitaciones** | ~200 (Linking, OpenLink, DangerLink, DangerLink2, RiddleLink) | Aristas Macro con predicados |
| **Objetos** | ~120 (~70 Parte I + ~53 Parte II) | Nodos Micro con componentes |
| **NPCs** | ~50 (14 Trolls + 8 Guards Parte I, 18 Trolls + 5 Guards + 1 TDaugther Parte II) | Nodos Micro con componente `brain` |
| **Puzles** | 93 (43 Parte I + 50 Parte II) | Hiper-Aristas con Cliques de Participación |
| **Acertijos** | 7 (4 Parte I + 3 Parte II) | Aristas RiddleLink con `question` + `requires_text` |
| **Verbos del parser** | 37 | Vocabulario del parser clásico V1 |
| **Sustantivos** | ~180 | Nombres de entidades en el grafo |
| **Texto en español** | ~22,000 palabras | Componentes `description` en entidades |

### 7.2 Tipos de Conexión como Aristas Macro

Cada tipo de conexión del original se modela como una arista del Grafo Macro con predicados específicos:

| Tipo Original | Modelo en el Grafo | Predicados |
|---------------|-------------------|------------|
| **Linking** | Arista Macro con predicado `requires_text` | `{ requires_text: "...", open: false }` — si no, siempre abierta |
| **OpenLink** | Arista Macro sin condiciones | *(sin predicados)* |
| **DangerLink** | Arista Macro con predicado `requires_item` | `{ requires_item: "Talismán de aire", death_message: "..." }` — sin él, muerte |
| **DangerLink2** | Arista Macro con predicado `forbids_item` | `{ forbids_item: "Anillo de oro", death_message: "..." }` — si se lleva, muerte |
| **RiddleLink** | Arista Macro con `question` + `requires_text` | `{ question: "...", requires_text: "treinta y nueve", open: false }` |
| **Hidden** | Arista Micro con operador COMBINE | `{ breaker: "Maza", reveals: "Trebol" }` — COMBINE(Maza, Monolito) → Trebol |

Los predicados de arista son **genéricos** — no existe `connection_type`. El motor evalúa los predicados de forma uniforme y `death_message` distingue cruce fatal de cruce bloqueado.

### 7.3 Puzles como Hiper-Aristas

Cada puzle del original se modela como una Hiper-Arista con su Clique de Participación:

**Ejemplo: Matar al Cíclope (Puzzle 10, Parte I)**

```
Hiper-Arista: "matar_ciclope"
  Clique de Participación:
    - subject: Player
    - verb: "matar"
    - target: Cíclope (entidad en Biblioteca, room 6)
    - instrument: Maza (debe estar en inventario del jugador)
  
  Secuencia de Operadores:
    1. TRANSFER(Cíclope, Biblioteca, null)     // el Cíclope muere → desaparece
    2. FLAG("ciclope_muerto", true)             // desbloquea la contraseña de la Puerta gigante
    3. TRANSFER(Confesión_Cíclope, null, Player) // el jugador recibe la confesión como texto
```

**Ejemplo: Ritual Final (Parte II)**

```
Hiper-Arista: "ritual_final"
  Clique de Participación:
    - 7 entidades target en ubicaciones específicas:
      - Antorcha en habitación 1
      - Péndulo en habitación 3
      - Espejo en habitación 4
      - Bote en habitación 12
      - Rosa diamante en habitación 31
      - Escudo de Aquiles en habitación 40
      - Cinta de Moebius en habitación 43
    - 2 entidades ausentes:
      - Monstruo NOT IN habitación 9
      - Hija del Hechicero NOT IN habitación 46
    - Pañuelo NOT IN habitación 7
  
  Secuencia de Operadores:
    1. FLAG("fortaleza_abierta", true)
    2. TELEPORT(Player, habitación_victoria)
```

### 7.4 Contrato de Compatibilidad

- La guía de juego documentada en `docs/09-walkthrough.md` debe funcionar comando por comando en el motor
- El texto original es sagrado — se reproduce exactamente, pero ahora vive en archivos de datos, no en código compilado
- Las soluciones de puzles, contraseñas, respuestas a acertijos, armas letales, objetos de regalo y secuencias de acciones permanecen idénticas
- Las condiciones de victoria son exactas: 5 enemigos muertos (Parte I), 7 objetos colocados + 2 enemigos muertos (Parte II)

### 7.5 Estructura de Archivos de Datos de Fortaleza

```
worlds/fortaleza/
├── world.yaml              # Metadatos del mundo (nombre, versión, idioma, max_weight)
├── episodes/
│   ├── parte-1.yaml        # Episodio 1: goal, carry_over, configuración
│   └── parte-2.yaml        # Episodio 2: goal, carry_over, configuración
├── rooms/
│   ├── room-01.yaml        # "Entrada de la Fortaleza"
│   ├── room-02.yaml        # "Pasillo Oscuro"
│   └── ...                 # 88 archivos de habitaciones, una por archivo
├── items/
│   ├── antorcha.yaml
│   ├── maza.yaml
│   └── ...                 # ~120 archivos de objetos
├── npcs/
│   ├── ciclope.yaml
│   ├── troll-01.yaml
│   └── ...                 # ~50 archivos de NPCs
├── actions/
│   ├── matar-ciclope-maza.yaml
│   ├── matar-ciclope-fallback.yaml
│   └── ...                 # ~400-450 Hiper-Aristas (una por archivo)
├── macros/
│   ├── vocabulary.yaml     # Definiciones de verbos y sinónimos
│   └── parser-rules.yaml   # Reglas del parser clásico
└── narrator/
    └── templates.yaml      # Strings del narrador basado en plantillas
```

---

## 8. Features (MoSCoW)

### 8.1 Must Have (MVP — Motor v1.0 + Mundo Fortaleza)

| Feature | Detalle |
|---------|---------|
| **Sistema de Entidades** | UUIDs, componentes clave-valor, anclajes espaciales |
| **Motor de Grafo Dual** | Grafo Macro + Grafos Micro por escena |
| **Hiper-Aristas** | Sistema de acciones con validación por Clique de Participación |
| **Cinco Operadores Atómicos** | TRANSFER, TRANSFORM, COMBINE, FLAG, TELEPORT implementados |
| **Parser Clásico V1** | 37 verbos, ~180 sustantivos, matching parcial, normalización de tildes |
| **Narrador por Plantillas V1** | Salida de texto directa desde datos del mundo |
| **Sistema de Turnos con arquitectura multi-protagonista** | La colección `player_controlled_entities` es siempre una lista, incluso con 1 elemento; el loop itera sobre ella |
| **Formato de Mundo YAML** | Esquema de definición de mundos con validación |
| **Guardado/Carga vía Event Sourcing** | Log de Hiper-Aristas ejecutadas, con snapshot caché opcional |
| **Mundo Fortaleza** | Datos de grafo completos para ambas partes (88 habitaciones, ~120 objetos, ~50 NPCs, 93 puzles) |
| **Mundo Fortaleza jugable** | El walkthrough documentado funciona comando por comando |
| **Texto en español preservado** | Las ~22,000 palabras del original reproducidas exactamente |

### 8.2 Should Have (v1.1)

| Feature | Detalle |
|---------|---------|
| **Herramienta de edición de mundos** | CLI o visual para crear/modificar grafos sin editar YAML manualmente |
| **Validador de mundos** | Detecta habitaciones inalcanzables, objetos huérfanos, puzles sin solución |
| **Cerebro scripteado de NPCs** | Selección de acciones por prioridad en el Grafo Micro |
| **Soporte multi-protagonista** | Comandos de usuario `CAMBIAR A`, `GRUPO`, `ESPERAR`; cliques cooperativas; cerebros autónomos para otros protagonistas; mundos de ejemplo con múltiples personajes controlables |
| **Comando de cambio de protagonista** | `CAMBIAR A <nombre>` transfiere el foco de entrada entre protagonistas |
| **Cliques multi-protagonista** | Hiper-Aristas que requieren múltiples entidades `player_controlled` en posiciones específicas para formar la clique |
| **Sistema de pistas** | Integración de pistas contextuales (tres niveles: sutil, medio, explícito) |
| **Múltiples slots de guardado** | Mínimo 3 slots con persistencia completa |

### 8.3 Could Have (v1.2)

| Feature | Detalle |
|---------|---------|
| **Parser Intencional con IA (V3)** | LLM traduce texto libre a tupla estructurada |
| **Narrador Inmersivo con IA (V2)** | LLM decora resultados crudos con prosa atmosférica |
| **Cerebro generativo de NPCs** | LLM selecciona acciones entre las aristas disponibles |
| **Mundos de ejemplo adicionales** | Un mundo tutorial de 5 habitaciones + un demo pequeño |
| **Visualización de grafos** | Herramienta de debugging para explorar el grafo en tiempo real |

### 8.4 Won't Have (v1)

| Exclusión | Razón |
|-----------|-------|
| **Gameplay en tiempo real** | El motor es por turnos; cambiar esto requiere rediseño arquitectónico |
| **Renderizado gráfico** | La salida es texto; el narrador puede ser IA pero no genera imágenes |
| **Multijugador** | Fuera del alcance de la arquitectura de turno único |
| **Entrada/Salida por voz** | Puede agregarse como plugin futuro de parser/narrador |
| **Generación procedural de mundos** | Los mundos se diseñan, no se generan |
| **Lógica específica de Fortaleza en el código del motor** | El motor no conoce nombres de habitaciones, objetos ni puzles |

---

## 9. Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CAPA DE DATOS                                │
│                                                                     │
│  worlds/fortaleza/                    worlds/demo/                  │
│  ├── macro-graph.json                 ├── macro-graph.json          │
│  ├── micro-graphs/*.json              ├── micro-graphs/*.json       │
│  ├── entities.json                    ├── entities.json             │
│  ├── hyper-edges.json                 ├── hyper-edges.json          │
│  └── vocabulary.json                  └── vocabulary.json           │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ carga
                                   ▼
┌─────────────────────────────────────────────────────────────────-────┐
│                        CAPA DE MOTOR                                 │
│                                                                      │
│  ┌───────────────-──┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Entity Manager  │  │   Graph Engine   │  │  State Container   │  │
│  │                  │  │                  │  │                    │  │
│  │  • UUID registry │  │  • Macro Graph   │  │  • Entity Dict     │  │
│  │  • Components    │  │  • Micro Graphs  │  │  • Flag Book       │  │
│  │  • Spatial       │  │  • Hyper-Edges   │  │  • Serialization   │  │
│  │    Anchors       │  │  • Pathfinding   │  │    (JSON/BSON)     │  │
│  └────────┬───────-─┘  └────────┬─────────┘  └─────────┬──────────┘  │
│           │                     │                      │             │
│           └────────-────────────┼──────────────────────┘             │
│                                 ▼                                    │
│                    ┌───────────────────────┐                         │
│                    │   Turn Orchestrator   │                         │
│                    │                       │                         │
│                    │  1. Player Turn       │                         │
│                    │  2. Scene Turn (NPCs) │                         │
│                    │  3. Resolution        │                         │
│                    │     (5 Atomic Ops)    │                         │
│                    └───────────┬───────────┘                         │
└────────────────────────────────┼─-───────────────────────────────────┘
                                 │ interfaces estables
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CAPA DE INTERFAZ                               │
│                                                                     │
│  ┌────────────────────────┐    ┌───────────────────────────┐        │
│  │   PARSER PLUGIN        │    │   NARRATOR PLUGIN         │        │
│  │                        │    │                           │        │
│  │  V1: Classical         │    │  V1: Template-based       │        │
│  │    text → {subject,    │    │    structured result      │        │
│  │    verb, target, ctx}  │    │    → player-facing text   │        │
│  │                        │    │                           │        │
│  │  V2: AI Intentional    │    │  V2: AI Immersive         │        │
│  │    LLM translates      │    │    LLM decorates raw      │        │
│  │    free text → tuple   │    │    result with prose      │        │
│  └────────────┬───────────┘    └─────────────┬─────────────┘        │
│               │                              │                      │
│               └──────────────┬───────────────┘                      │
│                              ▼                                      │
│                    ┌───────────────────┐                            │
│                    │    PLAYER UI      │                            │
│                    │  (terminal/web)   │                            │
│                    └───────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Principio fundamental**: La CAPA DE DATOS define el mundo. La CAPA DE MOTOR interpreta grafos. La CAPA DE INTERFAZ traduce entrada/salida. Ninguna capa conoce los detalles de las otras.

---

## 10. Stack Tecnológico

### Lenguaje

**Python** — elegido por su legibilidad, prototipado rápido, ecosistema rico y soporte robusto de bibliotecas de IA/LLM (crítico para las fases futuras de parser y narrador con IA).

### Persistencia

**SQLAlchemy** como ORM para abstracción de base de datos. Permite migrar de SQLite a PostgreSQL/MySQL sin cambiar el código del motor. SQLite se elige como backend inicial por:

- Almacenamiento local sin configuración (zero-config)
- Base de datos en un solo archivo (fácil de respaldar, versionar o migrar)
- Suficiente para persistencia de estado single-player
- Lecturas rápidas para consultas de entidades y banderas durante la resolución de turnos

### Sistema de Guardado/Carga: Event Sourcing

El guardado no almacena snapshots del estado — almacena **logs de Hiper-Aristas ejecutadas**. Cada acción exitosa (TRANSFER, TRANSFORM, COMBINE, FLAG, TELEPORT) se registra como un evento en el log. Reconstruir cualquier estado del juego es replay el log desde el estado inicial.

- El log se persiste en SQLite vía SQLAlchemy
- Ventajas: historial completo de acciones, debugging determinístico, posibilidad de "deshacer" rebobinando el log, tamaño de archivo mínimo
- Compatible con el sistema de "rastro" original de Fortaleza (que guardaba comandos relevantes en texto)

### Interfaz de Persistencia (Repository)

Una interfaz limpia `WorldStateRepository` (clase base abstracta) que encapsula todas las operaciones de estado:

```
WorldStateRepository (ABC)
├── append_event(event: HyperEdgeEvent) → void
├── get_event_log(since_turn: int) → list[HyperEdgeEvent]
├── get_latest_turn() → int
├── save_snapshot(state: WorldState, turn: int) → void   # caché opcional
└── load_latest_snapshot() → (WorldState, int) | None     # caché opcional
```

La interfaz incluye métodos de snapshot como caché opcional para acelerar la carga. La fuente de verdad es siempre el log de eventos.

Esta interfaz permite intercambiar SQLite por PostgreSQL, Redis o DynamoDB en el futuro sin tocar el código del motor. Implementación inicial: **SQLite** (módulo `sqlite3` de stdlib). Futuro: backend web-capable.

### Formato de Datos del Mundo

**YAML** (no JSON). Razones:

- Legible por humanos, soporta comentarios (crítico para que los diseñadores documenten puzles e intenciones)
- Mejor soporte de strings multilínea para descripciones de habitaciones y diálogos
- Menos ruido sintáctico que JSON
- Estándar en la industria de videojuegos para datos (usado por Godot, Unity YAML, etc.)

### Bibliotecas Python

- **PyYAML** para parsing de archivos YAML
- **Pydantic** para validación de datos y cumplimiento de esquemas en archivos YAML
- **SQLAlchemy** para abstracción de base de datos (backend inicial: SQLite)
- **pytest** para testing

### Estructura Multi-Archivo del Mundo

Cada tipo de entidad tiene su propio directorio de archivos YAML, NO un archivo monolítico:

```
worlds/fortaleza/
├── world.yaml           # Metadatos del mundo, banderas globales, estado inicial
├── episodes/
│   ├── parte-1.yaml     # Episodio 1: configuración, goal, carry_over
│   └── parte-2.yaml     # Episodio 2: configuración, goal, carry_over
├── rooms/
│   ├── room-01.yaml     # "Entrada de la Fortaleza"
│   ├── room-02.yaml     # "Pasillo Oscuro"
│   └── ...              # 88 archivos de habitaciones en total
├── items/
│   ├── antorcha.yaml
│   ├── espada.yaml
│   └── ...              # ~120 archivos de objetos
├── npcs/
│   ├── troll-01.yaml
│   ├── guardia-01.yaml
│   └── ...              # ~50 archivos de NPCs
├── actions/
│   ├── encender-fuego.yaml
│   ├── abrir-puerta.yaml
│   └── ...              # Definiciones de acciones / hiper-aristas
├── macros/
│   ├── vocabulary.yaml  # Definiciones de verbos y sinónimos
│   └── parser-rules.yaml # Reglas del parser clásico
└── narrator/
    └── templates.yaml   # Strings del narrador basado en plantillas
```

Cada archivo define UNA entidad. El motor carga el directorio al iniciar, descubre todos los archivos y construye el grafo en memoria. Esto permite:

- Diffs de control de versiones a nivel de entidad (no buscar en un archivo de 5000 líneas)
- Diseñadores de mundo trabajando en diferentes habitaciones/NPCs en paralelo
- Agregar o quitar entidades sin tocar otros archivos
- Usar anclas y alias de YAML entre archivos para definiciones compartidas
- Futuro: un editor de mundos puede generar estos archivos automáticamente

### Sistema de Eventos

El motor se comunica con la UI exclusivamente a través de eventos (diseño detallado en `docs/13-event-system.md`). La arquitectura de eventos garantiza el desacoplamiento total entre el motor y cualquier interfaz de usuario.

- **Bus de eventos síncrono, en proceso, sin backpressure** — los eventos se emiten y procesan en el mismo ciclo del motor
- El motor emite eventos tipados; la UI se suscribe y renderiza
- Categorías de eventos: **World** (carga, inicio, victoria), **Turn** (inicio/fin de turno), **State Change** (TRANSFER, TRANSFORM, COMBINE, FLAG, TELEPORT), **Narration** (output de texto), **NPC** (acción de NPC), **Meta** (guardado, carga, cambio de parser)

### Sistema de Plugins

- **Interfaces** como contratos estables:
  - `ParserInterface`: `parse(raw_text: string, world_state: WorldState) → { subject, verb, target, context, instrument }`
  - `NarratorInterface`: `narrate(result, worldState) → string`
- Comunicación vía **stdin/stdout** o **llamadas a biblioteca dinámica** — el motor no necesita saber qué hay del otro lado
- Los plugins pueden escribirse en cualquier lenguaje que implemente la interfaz

---

## 11. Métricas de Éxito

| Métrica | Criterio de Aceptación |
|---------|----------------------|
| **Fortaleza jugable** | El walkthrough documentado en `docs/09-walkthrough.md` se completa comando por comando sin desviaciones |
| **Motor agnóstico** | Un nuevo mundo de 5 habitaciones se crea sin modificar una sola línea del código del motor |
| **Serialización** | El Estado Global se serializa y deserializa en un ciclo completo sin pérdida de datos (round-trip fidelity) |
| **Parser V1** | Resuelve correctamente el 100% de los comandos documentados de Fortaleza (37 verbos × sintaxis) |
| **Independencia de plugins** | Cambiar de Parser V1 a Parser V2 no requiere modificar el motor |
| **Preservación de texto** | Las ~22,000 palabras del texto original de Fortaleza se reproducen con exactitud (tildes, puntuación, mayúsculas) |

---

## 12. Restricciones

1. **El motor NUNCA debe contener lógica específica de un mundo.** Nada de nombres de habitaciones cableados, objetos hardcodeados, ni soluciones de puzles en el código del motor.
2. **Parser y Narrador son interfaces enchufables.** Cambiar uno no debe afectar al motor ni al otro.
3. **El formato de datos de mundo debe ser legible por humanos y versionable.** JSON/YAML, no binario. Un diseñador debe poder editar un archivo y ver el cambio al recargar.
4. **El texto en español de Fortaleza debe preservarse exactamente.** Es el contrato de compatibilidad con la obra original y su comunidad.
5. **La arquitectura debe soportar integración futura con IA sin rediseño.** Los puntos de conexión (parser intencional, narrador inmersivo, cerebro generativo) están definidos desde el día uno.
6. **Cada habitación, objeto, NPC y acción DEBE definirse en su propio archivo YAML dentro del subdirectorio correspondiente.** No se permite agrupar múltiples entidades en un solo archivo.
7. **La capa de persistencia DEBE accederse a través de la interfaz Repository.** No se permiten llamadas directas a SQLite en el código del motor.
8. **El motor no debe asumir un solo protagonista.** Toda la lógica de turnos, consultas al grafo y resolución de acciones debe tratar `player_controlled` como un conjunto, nunca como un singleton. Los datos del mundo definen qué entidades son controlables; el motor no hardcodea esta decisión.

---

## 13. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **Validación por grafos más lenta que lógica cableada** | Media | Medio | El pathfinding en grafos de ~100 nodos es trivial. Para mundos masivos, caching de cliques precalculadas |
| **88 habitaciones + 93 puzles generan archivos YAML numerosos** | Alta | Medio | Herramienta de edición (Should Have) para no editar YAML manualmente. Formato con referencias por UUID en vez de datos duplicados |
| **Parser clásico para español es complejo** | Alta | Alto | El parser V1 replica exactamente el original (37 verbos, ~180 sustantivos). La complejidad ya está resuelta en el código original y documentada |
| **Parser de IA podría malinterpretar la intención del jugador** | Media | Alto | El parser de IA es Could Have (v1.2). El parser clásico V1 es determinista y cubre el MVP |
| **Sobre-ingeniería: motor genérico para un solo mundo** | Alta | Medio | El motor se valida con Fortaleza pero se diseña para múltiples mundos. El mundo demo de 5 habitaciones (Could Have) prueba la genericidad |

---

## 14. Fuera de Alcance (Explícito)

- Lógica específica de Fortaleza en el código del motor
- Soluciones de puzles cableadas en código
- Características de aventura gráfica (sprites, animaciones, point-and-click)
- Funcionalidades online o multijugador
- Generación procedural de mundos (la edición está en alcance, la generación no)
- Traducción del texto de Fortaleza a otros idiomas
- Contenido nuevo para Fortaleza (habitaciones, objetos, puzles, historia adicionales)
- Motor de física o combate en tiempo real

---

## 15. Referencias

### Documentación del Mundo Fortaleza
- `docs/01-story.md` — Narrativa completa, ambientación, trama, personajes
- `docs/02-rooms.md` — 88 habitaciones con descripciones, conexiones y contenidos
- `docs/03-items.md` — ~120 objetos con pesos, ubicaciones y usos
- `docs/04-puzzles.md` — 93 puzles con mecánicas y soluciones
- `docs/05-npcs.md` — ~50 NPCs y enemigos con diálogos y comportamientos
- `docs/06-mechanics.md` — Motor original: inventario, movimiento, combate, guardado
- `docs/07-vocabulary.md` — 37 verbos y ~180 sustantivos del parser
- `docs/08-room-graph.md` — Grafo completo de conexiones entre habitaciones
- `docs/09-walkthrough.md` — Guía completa comando por comando
- `docs/10-puzzle-dependencies.md` — Grafo de dependencias entre puzles
- `docs/11-victory-conditions.md` — Condiciones exactas de victoria y derrota
- `docs/12-engine-gap-analysis.md` — Análisis de brechas entre el PRD v2.0 y las mecánicas de Fortaleza; documento que identificó y resolvió los gaps de diseño (ejecución condicional, combate, peso, episodios)
- `docs/13-event-system.md` — Diseño del sistema de eventos: bus síncrono, categorías de eventos, contrato motor-UI

### Código Original
- `FORT1.PAS`, `FORT2.PAS` — Entry points (Turbo Pascal 7)
- `CASTLES.PAS` — Motor de aventura conversacional (1346 líneas)
- `LEXIC.PAS`, `VOCABL.PAS` — Lexicográfico y vocabulario del parser
- Issue de build original: https://github.com/merchise/fortaleza/issues/2

---

*Documento preparado a partir del análisis completo del código fuente original y la documentación extraída de 11 archivos de diseño que cubren la totalidad de la narrativa, mecánicas, puzles, objetos, NPCs y condiciones de victoria de ambas partes del juego.*
