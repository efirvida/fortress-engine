# 12 — Análisis de Brechas: Motor de Grafo Semántico vs Fortaleza

**Autor**: Auditoría técnica del PRD v2.0  
**Fecha**: 2026-08-07  
**Fuentes analizadas**: PRD (`prd.md`) + 7 documentos de diseño de Fortaleza (rooms, walkthrough, puzzles, items, NPCs, mechanics, vocabulary, victory conditions)

---

## 1. Resumen Ejecutivo

**Veredicto**: PARCIAL — El motor PUEDE expresar la mayoría de las mecánicas de Fortaleza, pero tiene **3 brechas CRÍTICAS** y **5 brechas ALTAS** que requieren ajustes al PRD antes de la implementación.

El motor de grafo semántico con 5 operadores atómicos + Hiper-Aristas + Cliques de Participación es una arquitectura sólida para ficción interactiva. Sin embargo, el diseño actual **carece de ejecución condicional** dentro de las Hiper-Aristas, **no define un subsistema de combate** (aunque sea simple), y **no contempla episodios/multi-parte**. Estas brechas son subsanables con extensiones acotadas al PRD, no requieren rediseño arquitectónico completo.

La buena noticia: ~80% de las mecánicas de Fortaleza son expresables con el diseño actual. Las brechas son puntuales y tienen soluciones concretas.

---

## 2. Matriz de Cobertura

### 2.1 Navegación de Habitaciones

| Mecánica de Fortaleza | ¿Cubierta? | ¿Cómo? | Notas |
|------------------------|------------|--------|-------|
| Salidas simples (Norte/Sur/Este/Oeste/Arriba/Abajo/Entrar/Salir) | ✅ SÍ | Aristas Macro con `open: true` | Los nombres de direcciones son reemplazados por nombres de puertas ("Puerta verde", "Escalera") en el parser original |
| Puertas con contraseña (Linking) | ✅ SÍ | Arista Macro con `password: "..."` o `requires_flag: "knows_password"` | El motor debe validar el predicado antes de permitir el cruce |
| Puertas con acertijo (RiddleLink) | ✅ SÍ | Arista Macro con `answer: "treinta y nueve"`, `question: "..."` | Requiere que el parser distinga `RESPONDIENDO` de `DICIENDO` |
| DangerLink (necesita ítem) | ✅ SÍ | Arista Macro con `requires_item: "Talismán de aire"`; sin él → `FLAG(player_dead)` | El predicado `requires_item` chequea el inventario del jugador |
| DangerLink2 (NO llevar ítem) | ✅ SÍ | Arista Macro con `forbids_item: "Anillo de oro"`; si se lleva → `FLAG(player_dead)` | Lógica inversa: la presencia del ítem causa la muerte |
| Pasajes ocultos (PHidden) | ✅ SÍ | Hiper-Arista con COMBINE(herramienta, PHidden) → revela entidad oculta | El motor necesita modelar objetos PHidden como entidades con estado |
| Laberinto con múltiples nodos | ✅ SÍ | Grafo Macro estándar con 18 nodos y aristas etiquetadas | Las puertas 1, 2, 3 se modelan como aristas nombradas en cada nodo |

### 2.2 Inventario

| Mecánica de Fortaleza | ¿Cubierta? | ¿Cómo? | Notas |
|------------------------|------------|--------|-------|
| Tomar objetos (TRANSFER sala → inventario) | ✅ SÍ | Hiper-Arista "tomar_X": TRANSFER(X, room, player.inventory) | Requiere validación de que X está en la sala actual |
| Dejar objetos (TRANSFER inventario → sala) | ✅ SÍ | Hiper-Arista "dejar_X": TRANSFER(X, player.inventory, current_room) | El verbo `TODO` requiere iterar sobre el inventario |
| Límite de peso (40 unidades) | ⚠️ PARCIAL | El PRD menciona `weight` como componente pero **no define la validación de peso** en el motor | Ver Gap #4 |
| Objetos demasiado pesados (peso > LWeight) | ⚠️ PARCIAL | Ídem — no hay check de peso máximo individual vs LWeight | Ver Gap #4 |
| Item consumido al dar (give to Troll) | ✅ SÍ | TRANSFER(item, player.inventory, null) | El destino `null` significa destrucción/consumo |
| Talismán como protección/condena | ✅ SÍ | Manejo por predicados de aristas (DangerLink/DangerLink2) | No requiere lógica especial de inventario |

### 2.3 Combate

| Mecánica de Fortaleza | ¿Cubierta? | ¿Cómo? | Notas |
|------------------------|------------|--------|-------|
| Atacar a un Guard con arma correcta → muere | ❌ NO | La Hiper-Arista definida en el PRD solo modela el caso CON arma correcta. Falta el caso CON arma incorrecta. | Ver Gap #1 (CRÍTICO) |
| Atacar a un Guard con arma incorrecta → se burla | ❌ NO | No hay operador condicional en los 5 operadores atómicos | Ver Gap #1 |
| Atacar a un Troll con cualquier arma → muere | ⚠️ PARCIAL | Se puede modelar con Hiper-Aristas por arma, pero son muchas combinaciones (~7 armas × ~30 trolls = 210 Hiper-Aristas) | Ver Gap #1, Recomendación A |
| Atacar a TDaugther con arma incorrecta → jugador muere | ❌ NO | Requiere lógica condicional: si arma ≠ lethalweap → matar jugador | Ver Gap #1 |
| Mensaje de confesión al morir (Guards) | ⚠️ PARCIAL | El texto de confesión debe ser parte del resultado de la Hiper-Arista | Ver Gap #2 |
| Enemigos sin contraataque (no es combate por turnos) | ✅ SÍ | Es una sola acción, no un loop. El diseño actual de acción única funciona. | Fortaleza no tiene combate multi-turno |
| Arma consumida al matar (no ocurre en Fortaleza) | N/A | No aplica — las armas no se rompen en el original | |

### 2.4 Puzles

| Puzle | ¿Cubierto? | ¿Cómo? | Notas |
|-------|------------|--------|-------|
| Los 4 Centros (Parte I) | ⚠️ PARCIAL | Requiere 4 Hiper-Aristas de combate + DangerLinks + Cliques con arma específica | Igual problema de condicional que todo el combate |
| Troll exchange (dar objeto → pista) | ✅ SÍ | Hiper-Arista "dar_X_a_Troll": TRANSFER(item, inventory, null), FLAG(troll_happy), output diálogo | Requiere Hiper-Arista separada para `interrogar_troll` con flag `troll_happy` como precondición |
| Ritual de 7 objetos (Parte II) | ✅ SÍ | 7 Hiper-Aristas "dejar_X_en_Y": TRANSFER(X, inventory, room_Y) | La condición de victoria consulta ubicación de entidades |
| Hija del Hechicero | ❌ NO | Requiere condicional: Aguja → mata, otra arma → jugador muere | Ver Gap #1 |
| Secuencias multi-paso (3+ pasos) | ✅ SÍ | FLAGs encadenados: Hiper-Arista A → FLAG X → Hiper-Arista B (requiere FLAG X) | El grafo de dependencias se modela naturalmente con banderas |
| PHidden anidado (Columna → Martillo → Puerta negra) | ✅ SÍ | Secuencia: COMBINE(Antorcha3, Columna) → revela Puerta madera, COMBINE(Martillo, Puerta madera) → revela Puerta negra | |
| La Prueba de los Anillos | ✅ SÍ | Secuencia de DangerLink2: `forbids_item: "Anillo de oro"`, `forbids_item: "Anillo de plata"`, `forbids_item: "Anillo de bronce"` + DangerLink con `requires_item: "Cinta de Moebius"` | |
| Acertijos (RiddleLink) | ✅ SÍ | Arista Macro con predicado `answer` | El parser debe enviar la respuesta como parte del comando `ABRIR ... RESPONDIENDO ...` |

### 2.5 Condiciones de Victoria

| Condición | ¿Cubierta? | ¿Cómo? | Notas |
|-----------|------------|--------|-------|
| 5 entidades nil en habitaciones (Parte I) | ✅ SÍ | Goal evaluator consulta ubicación de entidades: `entity.location != room_X` | El motor debe exponer un evaluador de Goal configurable en datos |
| 7 objetos en ubicaciones + 2 muertos (Parte II) | ✅ SÍ | Goal evaluator consulta ubicación y flags | Ídem |
| Efectos secundarios en Goal() (Pañuelo en Cocina → muerte) | ✅ SÍ | Se modela como un predicado de muerte en el evaluador de Goal | El evaluador debe soportar "side effects" al evaluar condiciones |
| Aparición del Cáliz al morir la Hija | ✅ SÍ | TELEPORT(Cáliz, limbo, room_46) como parte de la secuencia de operadores | El Cáliz se pre-define en una sala "limbo" y se teletransporta |

### 2.6 Comportamiento de NPCs

| Comportamiento | ¿Cubierto? | ¿Cómo? | Notas |
|----------------|------------|--------|-------|
| Troll espera pasivamente un ítem | ✅ SÍ | Entidad con estado `mood: hostile/neutral/happy`. Hiper-Aristas de interacción condicionadas por estado | No necesita "brain" autónomo |
| Guard bloquea/ataca al jugador | ✅ SÍ | Entidad en la sala. Hiper-Aristas de combate condicionadas por presencia del Guard | Ídem |
| NPC da pista al recibir ítem | ✅ SÍ | Texto de salida en la Hiper-Arista de "dar" | Requiere que la Hiper-Arista tenga output textual |
| NPC con diálogo (Hechicero) | ✅ SÍ | Hiper-Arista "interrogar_hechicero": output de texto | Sin cambio de estado |
| Cerebro scripteado (priority-based edge selection) | ⚠️ SOBREDISEÑADO | Fortaleza no tiene NPCs autónomos — todos son reactivos | El PRD asigna esto a Should Have (v1.1), lo cual es correcto |
| Cambio de estado del NPC (happy, dead) | ✅ SÍ | FLAG o TRANSFORM del componente `mood` | |

### 2.7 Salida de Texto

| Texto | ¿Cubierto? | ¿Cómo? | Notas |
|-------|------------|--------|-------|
| Descripción de habitación al entrar | ✅ SÍ | Componente `description` en la entidad de la habitación. El narrador lo emite al cambiar de ubicación | |
| Descripción de ítem al examinar | ✅ SÍ | Componente `description` en la entidad del ítem | |
| Mensajes de combate (confesión, burla) | ⚠️ PARCIAL | Deben ser output de la Hiper-Arista, pero el PRD no define cómo se asocia texto a operadores | Ver Gap #2 |
| Mensajes de muerte | ✅ SÍ | FLAG `player_dead` + narrador emite texto de muerte | |
| Texto de ~22,000 palabras preservado | ✅ SÍ | Vive en componentes `description` de entidades y en outputs de Hiper-Aristas | El contrato de compatibilidad requiere preservación exacta |
| Rastro (save/replay de comandos) | ❌ NO | El PRD menciona serialización JSON del estado, pero NO el sistema de replay de comandos | Ver Gap #7 |

### 2.8 Casos Borde

| Caso | ¿Cubierto? | ¿Cómo? | Notas |
|------|------------|--------|-------|
| DangerLink2 inverso (talismán = muerte) | ✅ SÍ | Predicado `forbids_item` en arista Macro | |
| Comandos con distinto efecto según sala | ✅ SÍ | Hiper-Aristas scoped por sala. Cada sala tiene su propio Grafo Micro con acciones diferentes | |
| Objetos con distinto efecto en distintas salas | ✅ SÍ | Hiper-Aristas independientes por sala | |
| "Rastro" (scent trail) | ❌ NO | No modelado en el PRD | Ver Gap #7 |
| Item con doble uso (Antorcha: ilumina + derrite columna de hielo) | ✅ SÍ | Hiper-Aristas independientes en salas diferentes | |
| NPC que cambia de tipo (Monstruo: Troll que también debe ser matable para Goal) | ✅ SÍ | Dos Hiper-Aristas: una para dar, otra para matar. Goal consulta si `Monstruo = nil` | |
| Reloj de arena debe VOLTEARSE antes de dar | ⚠️ PARCIAL | Requiere una Hiper-Arista "voltear_reloj": TRANSFORM(Reloj, state, "volteado") + precondición en dar | Ver Gap #5 |

---

## 3. Brechas Encontradas

### Gap #1: EJECUCIÓN CONDICIONAL EN HIPER-ARISTAS — CRÍTICO

**Severidad**: CRÍTICO  
**Afecta a**: Todo el sistema de combate, Hija del Hechicero, Guards

**Problema**: Los 5 operadores atómicos (TRANSFER, TRANSFORM, COMBINE, FLAG, TELEPORT) se ejecutan **incondicionalmente** una vez que la Clique de Participación es válida. Pero Fortaleza requiere lógica condicional:

```
SI arma == lethalweap → TRANSFER(enemigo, sala, null), FLAG(enemigo_muerto), output confesión
SINO → output burla, sin cambio de estado
```

Y para TDaugther:
```
SI arma == Aguja → TRANSFER(Hija, sala, null), FLAG(hija_muerta), TELEPORT(Cáliz, limbo, sala_46)
SINO → FLAG(player_dead), output "La serpiente te devora"
```

**Evidencia**: El ejemplo del PRD para "matar_ciclope" solo modela el caso con arma correcta. No define qué ocurre si el jugador usa un arma incorrecta. En el original, si atacas al Cíclope con algo que no sea la Maza, el Cíclope se ríe y no muere. Esto pasa para **todos** los Guards (8 en Parte I, 4 en Parte II) y la TDaugther.

**Impacto**: Sin ejecución condicional, el motor no puede implementar:
- Combate con arma correcta vs incorrecta (~12 enemigos × 2 casos = 24 escenarios)
- Hija del Hechicero con arma incorrecta = muerte del jugador
- Cualquier puzle con ramificación binaria

### Gap #2: SALIDA DE TEXTO ASOCIADA A OPERADORES — ALTO

**Severidad**: ALTO  
**Afecta a**: Confesiones, burlas, diálogos de NPCs, descripciones de eventos

**Problema**: El PRD no define cómo se asocia texto a la ejecución de una Hiper-Arista. Los 5 operadores producen cambios de estado, pero el jugador necesita leer mensajes. La interfaz del Narrador (`narrate(result, worldState) → string`) es demasiado genérica.

En Fortaleza, cada acción tiene texto específico:
- Matar al Cíclope con Maza → "¡Arrrggghhhh! ¡Me has matado!" + texto codificado
- Matar al Cíclope con otra cosa → "Todos sus esfuerzos son en vano. Probablemente no esté usando el objeto indicado."
- Dar Escoba a la Bruja → "Tráeme mi escoba y te daré un consejo." → diálogo de recompensa
- Interrogar Bruja sin dar Escoba → "Tráeme mi escoba y te daré un consejo."

**Evidencia**: El PRD menciona un directorio `text/` con descripciones, pero no define el formato de output para Hiper-Aristas. La sección 4.3 define la secuencia de operadores pero no asocia texto.

### Gap #3: SISTEMA DE COMBATE COMO CONCEPTO EXPLÍCITO — ALTO

**Severidad**: ALTO  
**Afecta a**: Claridad del diseño, implementación de Guards y TDaugther

**Problema**: El PRD trata el combate implícitamente como "una Hiper-Arista más", pero el combate en Fortaleza tiene patrones específicos que merecen un tratamiento explícito:

1. **Guards**: Solo mueren con `lethalweap`, se burlan con cualquier otra arma
2. **Trolls**: Mueren con cualquier arma, gritan "AAAAARRRGGGGG!!!"
3. **TDaugther**: Arma incorrecta = muerte del jugador
4. **NPCs sin arma**: Si atacas sin especificar arma, se intenta con manos desnudas (`weapon = ''`)

**Evidencia**: El código original (`CASTLES.PAS:586-609`, `964-974`, `1329-1344`) muestra que `Kill` es un comando de primera clase con dispatch por tipo de entidad (`Troll.Die`, `Guard.Die`, `TDaugther.Die`).

El motor podría implementar esto sin cambiar la arquitectura, pero el PRD debería:
- Reconocer `combat` como una acción con dispatch condicional
- Definir el patrón para Guards (lethalweap match → kill, else → mock)
- Definir el patrón para Trolls (any weapon → kill)
- Definir el patrón para TDaugther (wrong weapon → kill player)

### Gap #4: SISTEMA DE PESO Y CAPACIDAD DE INVENTARIO — ALTO

**Severidad**: ALTO  
**Afecta a**: Jugabilidad, economía de inventario, puzles de acarreo

**Problema**: El PRD menciona `weight` como un componente de entidad, pero **no define**:
1. La capacidad máxima del inventario (LWeight = 40)
2. El check de peso antes de TRANSFER al inventario
3. El mensaje de error ("Sería demasiado peso.")
4. El check de peso individual ("Usted no puede cargar con eso.")
5. Cómo se calcula `bag^.Heaviness` (suma de pesos de todos los ítems)

**Evidencia**: `CASTLES.PAS:11` define `LWeight = 40`. La constante es usada en `CASTLES.PAS:66-71` (`Suitcase`) para validar cada inserción. El Bote pesa 39, la Maza pesa 39 — objetos al borde del límite.

**Impacto**: Sin sistema de peso, el jugador puede cargar todos los ítems simultáneamente, rompiendo la economía de inventario y trivializando decisiones de qué llevar.

### Gap #5: TRANSFORMACIÓN DE ÍTEMS (CAMBIOS DE ESTADO) — MEDIO

**Severidad**: MEDIO  
**Afecta a**: Reloj de arena (voltear), ítems con estado

**Problema**: El operador TRANSFORM "cambia el componente de estado de una entidad" (ejemplo: madera → cenizas). Pero en Fortaleza hay casos donde un ítem cambia de estado sin cambiar de identidad:

- **Reloj de arena**: Caronte dice "víralo antes de entregármelo". El jugador debe voltearlo — cambia su estado pero sigue siendo el mismo ítem. Esto es TRANSFORM(Reloj, state, "volteado").
- **Ítems con dos estados**: No hay muchos en Fortaleza, pero el PRD debería definir cómo se manejan.

Este gap es de severidad MEDIA porque TRANSFORM técnicamente puede manejarlo, pero el PRD no da ejemplos de transformaciones de estado que no cambien la identidad del objeto. El ejemplo "madera → cenizas" sugiere un cambio de entidad, no de estado.

### Gap #6: ENTIDADES QUE APARECEN/SPAWNEAN — MEDIO

**Severidad**: MEDIO  
**Afecta a**: Aparición del Cáliz, revelación de objetos ocultos

**Problema**: Cuando la Hija del Hechicero muere, aparece un Cáliz en la habitación. El código original: `PRoom(At(45))^.Insert(new(PThing, Init('Cáliz', '...', 3)))`. Esto es un **spawn** — crear una entidad nueva.

Los 5 operadores no incluyen SPAWN/CREATE. Workaround: pre-definir el Cáliz en una sala "limbo" y usar TELEPORT. Esto funciona pero es una solución indirecta.

**Impacto**: Para Fortaleza, el workaround de "limbo room" es suficiente (hay pocos spawns). Para otros mundos, podría ser una limitación. Recomendación: documentar el patrón `TELEPORT desde limbo` como la forma canónica de modelar apariciones.

### Gap #7: SISTEMA DE RASTRO (SAVE/REPLAY DE COMANDOS) — BAJO

**Severidad**: BAJO  
**Afecta a**: Fidelidad con el original, modo "replay"

**Problema**: El sistema original de "rastro" (`CASTLES.PAS:1171-1236`) guarda comandos "relevantes" (los que cambian estado) en un archivo de texto y permite reproducirlos. Es diferente al save/load tradicional porque:
- El archivo es texto editable (soporta comentarios `{ }`)
- Solo guarda comandos que modifican estado (no guarda MIRAR, INVENTARIO, INTERROGAR)
- Permite ejecución silenciosa (`VerboseExec`)
- Se puede usar para debug y testing

**Evidencia**: `CASTLES.PAS:1196-1215` — `SaveTrack` y `ExecTrack` implementan esta funcionalidad.

**Impacto**: El PRD menciona "Guardado/Carga" como serialización JSON del estado (sección 8.1), que es suficiente para MVP. El rastro es una reliquia encantadora del original pero no es crítico para que el motor sea funcional. Puede agregarse post-MVP.

### Gap #8: SOPORTE MULTI-PARTE / EPISÓDICO — CRÍTICO

**Severidad**: CRÍTICO  
**Afecta a**: Organización del mundo Fortaleza como Partes I y II, cualquier mundo con episodios

**Problema**: El PRD actual define UN mundo con 88 habitaciones, asumiendo que Fortaleza Parte I y II son un solo grafo continuo. Pero:
- Parte I y Parte II tienen **mapas completamente diferentes** (33 vs 55 habitaciones, ambos empiezan en room 1)
- No hay paso directo de una parte a la otra (son ejecutables separados)
- No comparten inventario, flags ni estado
- Tienen diferentes condiciones de victoria y narrativas
- El orden es secuencial: completar Parte I → empezar Parte II

**Evidencia**: `FORT1.PAS` y `FORT2.PAS` son programas independientes. `FORT1.PAS` termina con "Veremos si en la próxima versión de La Fortaleza tiene igual suerte." — confirmando que el autor las concibió como entregas separadas.

**Impacto**: Si el usuario quiere que Fortaleza 1 y 2 sean episodios del mismo juego, el PRD necesita un concepto de "mundo multi-episodio" que no existe actualmente.

---

## 4. Recomendaciones

### Recomendación A: Agregar Operador COND (Condicional) — Resuelve Gap #1

Agregar un **6º operador** o extender las Hiper-Aristas para soportar ramas condicionales:

```yaml
# Nueva estructura de Hiper-Arista con condicional
hiper_arista: "matar_ciclope"
  clique:
    subject: Player
    verb: matar
    target: Cíclope
    instrument: "*"  # cualquier arma
  branches:
    - condition:
        entity: Cíclope.component.lethalweap
        equals: "$instrument"
      operators:
        - TRANSFER(Cíclope, Biblioteca, null)
        - FLAG(ciclope_muerto, true)
      output: "¡Arrrggghhhh! ¡Me has matado!"
    - default: true
      output: "Todos sus esfuerzos son en vano."
```

Alternativa más simple: mantener solo 5 operadores pero permitir **múltiples Hiper-Aristas con la misma acción y cliques mutuamente excluyentes**:

```yaml
# Hiper-Arista 1: arma correcta
hiper_arista: "matar_ciclope_correcto"
  clique:
    subject: Player
    verb: matar
    target: Cíclope
    instrument: "Maza"  # solo Maza
  operators:
    - TRANSFER(Cíclope, Biblioteca, null)
    - FLAG(ciclope_muerto)
  output: "¡Arrrggghhhh! ¡Me has matado!"
  priority: 10

# Hiper-Arista 2: arma incorrecta (catch-all)
hiper_arista: "matar_ciclope_incorrecto"
  clique:
    subject: Player
    verb: matar
    target: Cíclope
    instrument: "*"  # cualquier otra arma
  operators: []  # sin cambio de estado
  output: "Todos sus esfuerzos son en vano."
  priority: 5
```

**Recomendación**: La opción de múltiples Hiper-Aristas con prioridad es más limpia porque no agrega operadores. El motor evalúa primero la de mayor prioridad; si la clique se forma (tienes la Maza), la ejecuta. Si no, evalúa la de menor prioridad (catch-all).

Para **TDaugther**, la Hiper-Arista catch-all ejecutaría `FLAG(player_dead)`:

```yaml
hiper_arista: "matar_hija_incorrecto"
  clique:
    subject: Player
    verb: matar
    target: Hija_del_Hechicero
    instrument_not: "Aguja"  # nuevo predicado
  operators:
    - FLAG(player_dead)
  output: "La enorme serpiente se lanza sobre usted y lo devora."
  priority: 5
```

Esto requiere un nuevo predicado de clique: `instrument_not` (o generalizar a `component_not_equals`).

### Recomendación B: Definir Campo `output` en Hiper-Aristas — Resuelve Gap #2

Agregar un campo `output` a la definición de Hiper-Arista que especifica el texto a mostrar cuando la acción se ejecuta:

```yaml
hiper_arista: "dar_escoba_a_bruja"
  clique:
    subject: Player
    verb: dar
    target: Bruja
    instrument: Escoba
  operators:
    - TRANSFER(Escoba, player.inventory, null)
    - FLAG(bruja_happy)
  output: "La bruja toma la escoba y sonríe. 'Gracias, querido. Escucha mi consejo: ...'"
```

El narrador por plantillas usa este campo directamente. El narrador IA futuro puede usarlo como base para generar prosa más rica.

### Recomendación C: Formalizar el Subsistema de Peso — Resuelve Gap #4

Definir explícitamente en el PRD:

1. **Componente `weight`**: cada entidad portable tiene un `weight: número`
2. **Capacidad del jugador**: definida en `world.yaml` como `player_carry_capacity: 40`
3. **Validación antes de TRANSFER al inventario**: el motor calcula `sum(weight of inventory items) + item.weight`. Si > capacidad, la acción falla con mensaje "Sería demasiado peso."
4. **Validación de peso individual**: si `item.weight > player_carry_capacity`, falla con "Usted no puede cargar con eso."

Esto no requiere nuevos operadores — es una regla de validación del motor al ejecutar TRANSFER con destino `player.inventory`.

### Recomendación D: Documentar Patrones de TRANSFORM — Resuelve Gap #5

Agregar al PRD ejemplos de TRANSFORM que NO cambian la identidad de la entidad:

```yaml
# Transformación de estado
TRANSFORM(Reloj_de_arena, state, "volteado")

# Transformación que cambia la entidad (como en el PRD)
TRANSFORM(Madera, type, "Cenizas")  # o COMBINE
```

Aclarar que TRANSFORM modifica componentes; si el componente modificado es `type` o `name`, efectivamente cambia la identidad percibida de la entidad (madera → cenizas). Si es `state` o `mood`, la entidad mantiene su identidad.

### Recomendación E: Documentar Patrón "Limbo Room" — Resuelve Gap #6

Agregar al PRD una sección "Entity Lifecycle" que documente:
- Las entidades pueden pre-definirse en una sala especial `_limbo` (no accesible al jugador)
- TELEPORT desde `_limbo` a una sala visible = "spawn"
- TRANSFER a `null` = "destroy/consume"
- Esto evita la necesidad de un operador CREATE/DESTROY

### Recomendación F: Agregar Predicados de Clique Adicionales — Resuelve Gap #1 (Complemento)

Para soportar lógica condicional con múltiples Hiper-Aristas, las cliques necesitan predicados adicionales:

| Predicado | Significado | Ejemplo |
|-----------|-------------|---------|
| `instrument: "value"` | El instrumento debe ser exactamente X | `instrument: "Maza"` |
| `instrument_not: "value"` | El instrumento NO debe ser X | `instrument_not: "Aguja"` |
| `instrument_any: true` | Cualquier instrumento es válido | `instrument_any: true` |
| `flag: "name"` | Requiere que la bandera esté activa | `flag: bruja_happy` |
| `flag_not: "name"` | Requiere que la bandera NO esté activa | `flag_not: ciclope_muerto` |
| `component: {entity, key, value}` | Requiere que la entidad tenga cierto componente | `component: {Bruja, mood, happy}` |

### Recomendación G: Sistema de Rastro como Plugin Opcional — Resuelve Gap #7

Mover el sistema de rastro a un plugin de "Command Logger" que:
- Se activa/desactiva con configuración
- Guarda comandos que produjeron cambios de estado (TRANSFER/TRANSFORM/COMBINE/FLAG/TELEPORT exitosos)
- Permite reproducir secuencias de comandos
- Soporta comentarios `{ }` para compatibilidad con el formato original

Esto va en Should Have (v1.1) o Could Have (v1.2).

---

## 5. Soporte Episódico: Diseño Concreto

### 5.1 Diagnóstico Actual

El PRD v2.0 **no soporta episodios**. Define un mundo como un grafo monolítico: un conjunto de habitaciones, un conjunto de ítems, un conjunto de NPCs, un conjunto de Hiper-Aristas. La transición entre Partes I y II de Fortaleza no está modelada.

### 5.2 Propuesta de Diseño

#### Estructura de archivos para mundos multi-episodio

```
worlds/fortaleza/
├── world.yaml                    # Metadatos globales, banderas compartidas
├── episodes/
│   ├── episode-01.yaml           # "La Fortaleza" — Parte I
│   ├── episode-02.yaml           # "La Fortaleza II" — Parte II
├── shared/                       # Entidades compartidas entre episodios (ej: jugador)
│   ├── player.yaml
│   └── shared-flags.yaml
├── episode-01/                   # Datos específicos de Parte I
│   ├── rooms/
│   ├── items/
│   ├── npcs/
│   └── actions/
├── episode-02/                   # Datos específicos de Parte II
│   ├── rooms/
│   ├── items/
│   ├── npcs/
│   └── actions/
└── narrator/
```

#### Definición de Episodio (`episode-01.yaml`)

```yaml
id: "episode-01"
name: "La Fortaleza"
order: 1
start_anchor: "room-01"
description: "Primera parte: derrota a la Bestia"

victory:
  conditions:
    - type: entity_not_in_room
      entity: Centro_del_cerebro
      room: room-22
    - type: entity_not_in_room
      entity: Centro_del_corazon
      room: room-21
    - type: entity_not_in_room
      entity: Centro_del_estomago
      room: room-20
    - type: entity_not_in_room
      entity: Centro_de_los_pulmones
      room: room-19
    - type: entity_not_in_room
      entity: Troll
      room: room-12
  output: |
    Usted ha vencido a la Bestia.
    Parece ser una persona persistente...

carry_over:                       # Qué se transfiere al próximo episodio
  inventory: []                    # Nada en este caso
  flags: []                        # Nada en este caso
```

#### Transición entre episodios

En el bucle principal del motor:

```
while not world.game_over:
    episode = world.current_episode
    
    while not (episode.goal_met or world.game_over):
        execute_turn()
    
    if episode.goal_met:
        next = world.next_episode()
        if next:
            world.transition_to(next)
            # world.transition_to():
            #   1. Mostrar texto de victoria del episodio actual
            #   2. Vaciar grafo de habitaciones
            #   3. Cargar grafo del próximo episodio
            #   4. Transferir carry_over (inventario, flags) del jugador
            #   5. TELEPORT(jugador, start_anchor del nuevo episodio)
            #   6. Mostrar introducción del nuevo episodio
        else:
            world.win_game()
```

#### Estado compartido entre episodios

El campo `carry_over` define qué persiste:
- `inventory: ["*"]` — todo el inventario se transfiere
- `inventory: ["item_x", "item_y"]` — solo ítems específicos
- `flags: ["*"]` — todas las banderas
- `flags: ["flag_a"]` — banderas específicas
- `player_components: ["health"]` — componentes del jugador que persisten

#### Consideraciones específicas de Fortaleza

En Fortaleza original, **nada** se transfiere entre partes (inventario vacío, sin banderas compartidas). Pero si el usuario quiere que sean episodios conectados, podría decidir, por ejemplo:

- Transferir la Espada como recompensa por vencer a la Bestia
- Transferir el conocimiento de contraseñas como flags ("saw_roble_message")
- O mantener la separación total como en el original

### 5.3 ¿Qué del PRD actual se reutiliza?

- **Arquitectura de Grafo Dual**: cada episodio tiene su propio Grafo Macro + Micro
- **Hiper-Aristas**: definidas por episodio, en archivos YAML separados
- **5 operadores atómicos**: sin cambios
- **Sistema de Turnos**: sin cambios (solo hay un protagonista en Fortaleza)
- **Parser/Narrador**: sin cambios
- **Serialización**: el estado global ahora incluye `current_episode`

### 5.4 ¿Qué hay que agregar al PRD?

1. **Sección nueva**: "Soporte Multi-Episodio" en la Arquitectura Central
2. **Estructura de archivos**: revisar sección 4.8 y 10 para incluir directorio `episodes/`
3. **Transición de episodios**: nuevo proceso en el Orquestador de Turnos
4. **Evaluador de Goal por episodio**: cada episodio define su propia condición de victoria
5. **Estado carry_over**: definición de qué persiste entre episodios

---

## 6. Preguntas para el Usuario

Las siguientes decisiones de diseño requieren input humano. Están formuladas en español y ordenadas por prioridad:

### 6.1 Sobre el combate

**P1**: ¿Preferís la opción de **múltiples Hiper-Aristas con prioridad** (más limpia, sin nuevos operadores, pero requiere 2 Hiper-Aristas por enemigo) o un **nuevo operador COND** (más compacto, una sola Hiper-Arista por enemigo, pero introduce branching en la secuencia de operadores)?

**P2**: La Hija del Hechicero tiene una mecánica única: si la atacás sin la Aguja, **vos** morís. Esto es distinto a todos los demás enemigos. ¿Querés que el motor tenga un concepto explícito de "enemigo que contraataca letalmente" (tipo `TDaugther`) o lo resolvemos con la misma mecánica de Hiper-Aristas catch-all que proponemos para los Guards?

### 6.2 Sobre los episodios

**P3**: En el original, Fortaleza 1 y 2 son programas separados. No comparten nada. ¿Querés que en tu implementación **compartan algún estado** (inventario, conocimiento de contraseñas, alguna bandera narrativa) o preferís mantener la separación total?

**P4**: Al terminar la Parte I con el mensaje "Veremos si en la próxima versión de La Fortaleza tiene igual suerte", ¿querés una transición **directa** a la Parte II (el jugador sigue jugando, se carga el nuevo mapa) o una pausa con pantalla de "Fin de la Parte I — Presioná ENTER para continuar"?

**P5**: ¿Las 88 habitaciones van en un solo mundo (`worlds/fortaleza/`) con dos episodios, o preferís dos mundos separados (`worlds/fortaleza-1/` y `worlds/fortaleza-2/`) que el motor pueda encadenar?

### 6.3 Sobre la fidelidad con el original

**P6**: El sistema de "rastro" (save/replay de comandos en texto editable) es una reliquia del original. ¿Querés que lo implementemos **exactamente igual** (archivos de texto con comandos, soporte de comentarios `{ }`, ejecución silenciosa) o preferís un sistema de save/load moderno (JSON del estado completo) y dejamos el rastro como easter egg futuro?

**P7 — Resuelto**: se adopta la lista V2 expandida (añade `UN`, `UNA`, `DEL`, `LOS`, `LAS` a `LA`, `EL`, `POR`, `AL`) para el parser V1 — consistente con MinimalParser y mejor UX. La lista V1 original queda como subconjunto estricto.

**P8**: La función de matching parcial de nombres (`Equals` en `EQSTRING.PAS`) busca que todas las palabras del input estén en el nombre del objeto. Esto hace que `"Puerta"` coincida con `"Puerta Principal"`. ¿Mantenemos este comportamiento exacto o lo hacemos más estricto (ej: matching por prefijo)?

### 6.4 Sobre el motor

**P9**: El PRD define soporte multi-protagonista (varios `player_controlled`). Esto agrega complejidad al Orquestador de Turnos y a las Cliques. ¿Es **necesario para el MVP** o podemos moverlo a v1.1? (Fortaleza solo usa un protagonista.)

**P10**: El PRD menciona SQLite como capa de persistencia. Para el MVP de un motor de ficción interactiva single-player, ¿es suficiente con serialización a JSON en archivo (sin base de datos) o necesitás SQLite desde el día uno?

---

## Apéndice A: Resumen de Predicados de Arista Necesarios

Para cubrir todas las conexiones de Fortaleza, las Aristas Macro necesitan los siguientes predicados:

| Predicado | Tipo | Usado en |
|-----------|------|----------|
| `open: true` | Boolean | OpenLink (~50% de conexiones) |
| `password: "string"` | String | Linking con contraseña (~15 puertas) |
| `answer: "string"` | String | RiddleLink (~7 acertijos) |
| `requires_item: "string"` | EntityRef | DangerLink (~15 pasajes) |
| `forbids_item: "string"` | EntityRef | DangerLink2 (~8 pasajes) |
| `requires_flag: "string"` | FlagRef | Puertas condicionadas por estado |
| `forbids_flag: "string"` | FlagRef | Puertas bloqueadas por estado |

Los predicados `requires_item` y `forbids_item` ya están en el PRD. Los demás se infieren de los tipos de conexión documentados.

## Apéndice B: Cantidad de Hiper-Aristas Estimadas para Fortaleza

| Categoría | Cantidad estimada | Notas |
|-----------|-------------------|-------|
| Combate (Guards, arma correcta) | 12 | 8 Parte I + 4 Parte II |
| Combate (catch-all, arma incorrecta) | 12 | Una por cada Guard |
| Combate (Trolls) | ~30 | Todos aceptan cualquier arma |
| Combate (TDaugther, arma correcta) | 1 | Solo Aguja |
| Combate (TDaugther, catch-all) | 1 | Cualquier otra arma → muerte jugador |
| Dar ítem a Troll | ~30 | 14 Parte I + 16 Parte II |
| Interrogar Troll (feliz) | ~30 | Una por cada Troll que aceptó regalo |
| Interrogar Troll (infeliz) | ~30 | Catch-all para Trolls sin regalo |
| Romper PHidden | ~15 | Incluyendo PHidden anidados |
| Tomar ítem | ~120 | Una por cada objeto portable |
| Dejar ítem | ~120 | Una por cada objeto portable |
| Ritual (dejar ítems rituales) | 7 | Específicos de victoria Parte II |
| **Total aproximado** | **~400-450** | |

Nota: Los ~93 puzles del PRD resultan en ~400+ Hiper-Aristas porque cada puzle se descompone en múltiples acciones (dar, interrogar, matar con/sin arma correcta, romper, tomar, dejar).

---

*Documento generado a partir del análisis cruzado del PRD v2.0 del Motor de Grafo Semántico y la documentación completa de Fortaleza Partes I y II.*
