# Grafo de Conexiones de Habitaciones — Fortaleza Partes I y II

Este documento describe **todas** las conexiones entre habitaciones para ambas partes del juego,
extraídas directamente del código fuente (`FORT1.PAS`, `FORT2.PAS`, `CASTLES.PAS`).

Las conexiones se implementan insertando objetos `PLinking`, `POpenLink`, `PDangerLink`,
`PDangerLink2`, y `PRiddleLink` dentro de cada habitación. La función `Links` no existe como tal;
las conexiones se establecen en `SetData()` mediante estos objetos.

---

## TIPOS DE CONEXIÓN (CASTLES.PAS)

| Tipo | Descripción | Uso |
|------|-------------|-----|
| `PLinking` | Puerta estándar con llave opcional | `key = ''` → siempre abierta; `key <> ''` → necesita contraseña |
| `POpenLink` | Puerta siempre abierta | `opn := TRUE` siempre |
| `PDangerLink` | Pasaje peligroso que requiere talismán | Si no tienes el talismán, **mueres** al cruzar |
| `PDangerLink2` | Pasaje peligroso INVERTIDO | Si llevas el talismán, **mueres** al cruzar |
| `PRiddleLink` | Puerta con acertijo | Debes resolver el acertijo para abrirla |
| `PHidden` | Objeto oculto que esconde otro | Se rompe con un objeto específico |

### Cómo leer las conexiones

```
Habitación A ──[Puerta X (condición)]──→ Habitación B
```

La flecha indica la dirección. Si es bidireccional, cada habitación tiene su propio `PLinking`/`POpenLink` hacia la otra.

---

## PARTE I: LA FORTALEZA (33 habitaciones)

### Mapa ASCII de Conexiones (Zona Principal)

```
                              ┌──────────────┐
                              │  27. Puente  │
                              │ (acceso desde │
                              │  exterior vía │
                              │  pared secreta)│
                              └──────┬───────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                 │
              [Puerta]        [Puerta oculta]   [Puerta secreta
              → 28            (Cuadro→Estatua    → exterior
                               Satanás)          (necesita Antorcha)
```

```
                          ┌─────────────┐
                          │ 1. Exterior │
                          └──┬──────┬──┘
                    [Pta princ]    [Túnel]
                   (needs password)  │
                         │           │
              ┌──────────▼───┐       │
              │ 2. Salón     │       │
              │  Recepciones │       │
              └──┬───┬───────┘       │
        [Pta princ] [Pta negra]      │
        → 1         → 3              │
                                     │
         ┌───────────────────────────┘
         ▼
  ┌──────────────┐      ┌──────────────┐
  │ 3. Sala de   │◄────►│ 4. Patio     │
  │    juegos    │[P.Azul│   interior  │
  └──┬───────┬───┘      └──┬───────┬───┘
     │       │              │       │
 [Escalera] [Pta negra] [Pta azul] [Pta verde]
 (acertijo)  → 2        → 3        → 6
  → 5
     │
     ▼
┌──────────────┐
│ 5. Cuarto de │
│    espejos   │
└──┬───────┬───┘
   │       │
[Escalera] [Espejo opaco]
→ 3       → Puerta oculta → 14
```

```
  ┌──────────────┐      ┌──────────────────────────────────────┐
  │ 6. Biblioteca│◄────►│ 7. Pasillo                           │
  └──┬───┬───┬───┘      └──┬────┬────┬────┬────┬──────────────┘
     │   │   │              │    │    │    │    │
[Pta verde]│[Libro]    [Puerta]│[Pta │[Pta │[Pta │[Pta gris]
→ 4    │   → 13        → 6    │vieja│roja │proh.│→ 15
       │                       │→ 8 │→ 9 │→ 10 │
  [Puerta gigante]             │    │    │     │
  (needs password)             ▼    ▼    ▼     │
  → 7                     ┌────┐┌───┐┌────┐   │
                          │ 8  ││ 9 ││ 10 │   │
                          │Bru.││Gue.││Lab.│   │
                          └──┬─┘└─┬─┘└──┬─┘   │
                             │     │     │      │
                         [Escap.] [Cama] [Pta]   │
                         →14     →11   →7      │
                         (Candel) (Hacha)        │
                                                ▼
                                           ┌──────────┐
                                           │ 15. Sala │
                                           │ infusion.│
                                           └────┬─────┘
                                                │
                                    ┌───────────┼───────────┐
                                    │           │           │
                                [Pta gris]  [Pta amarilla]  │
                                → 7         → 13           │
```

```
                              ┌─────────────────┐
                              │ 13. Jardín      │
                              └┬──┬──┬──┬──┬──┬─┘
                               │  │  │  │  │  │
                    ┌──────────┘  │  │  │  │  └──────────┐
                    ▼             │  │  │  │              ▼
              ┌──────────┐        │  │  │  │     ┌──────────────┐
              │ 12. Baños│◄───────┘  │  │  └────►│ 23. Almacén  │
              │   Bestia │[Pta verde]│  │ [Pta   └──────┬───────┘
              └──────────┘           │  │ madera]       │
                                     │  │          [Pta verde] → 24
                              ┌──────┘  │
                              ▼         ▼
                    ┌──────────────┐ ┌──────────────┐
                    │ 14. Alcoba   │ │ 16. Calabozos│
                    │   doncella   │ └──────┬───────┘
                    └──┬───┬───┬───┘   [Pta hierro] → 13
                       │   │   │
          ┌────────────┘   │   └────────────┐
          ▼                ▼                ▼
   [Pta azul]→13    [Pta oculta]→5    [Escaparate]→8
```

```
                              ┌────────────────┐
                              │ 24. Páramo     │
                              └┬───┬───┬───┬───┘
                               │   │   │   │
                    ┌──────────┘   │   │   └──────────┐
                    ▼              │   │              ▼
             [Pta verde]→23  [Pozo]→1 │     [Túnel] (DangerLink)
                               │      │     → 24 (loop, sin protección: muerte)
                               │      │
                               ▼      ▼
                        [Pta cristal] [Lobo (Guard, lethalweap: Látigo)]
                        → 25
                               │
                               ▼
                     ┌─────────────────────┐
                     │ 25. Salón de cristal│
                     └──┬──────────────┬───┘
                        │              │
                  [Pta cristal]→24  [Pta tela]→26
                        │
                  [Pta triangular]
                  (acertijo: nombre del duende)
                  → 17
```

```
              ┌──────────────────────────────────────────┐
              │ 17. Boca de la Bestia                     │
              └──┬───────────────────────┬────────────────┘
                 │                       │
           [Pta triangular]→25    [Garganta] (OpenLink)
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │ 18. Interior Bestia │
                              └──┬──────┬──────┬────┘
                                 │      │      │
                     [Garganta]→17      │      │
                                 │      │      │
                          [Tráquea]    [Esófago] [Arteria princ.]
                          (DangerLink) (DangerLink) (DangerLink)
                          talismán:?   talismán:? talismán:Corazón
                              │           │       unicornio
                              ▼           ▼           ▼
                        ┌──────────┐ ┌──────────┐ ┌──────────┐
                        │19.Pulmones│ │20.Estómago│ │21.Corazón│
                        │Guard:Centro│ │Guard:Centro│ │Guard:Ctro│
                        │pulmones   │ │estómago   │ │corazón   │
                        └──────────┘ └──────────┘ └──────────┘
                        [Tráquea]→18  [Esófago]→18  [Arteria]→18
```

```
  ┌─────────────────────────────┐
  │ 27. Puente de mármol        │
  └──┬──────┬──────┬──────┬─────┘
     │      │      │      │
     │      │      │      └─[Puerta] (PDangerLink2, necesita Espada) → 28
     │      │      │
     │      │      └─[Puerta secreta] (PDangerLink, necesita Antorcha) → 1
     │      │
     │      └─[Estatua de Satanás] (PHidden) → romper con Cuadro
     │         → Puerta oculta → 28
     │
     └─[Araña] (Troll, quiere Hilo de Ariadna)
        → pista: "Busca al Minotauro y mátalo con la espada"
```

### El Laberinto (habitaciones 28-49)

```
                              ┌──────────────────────────┐
                              │ 28. Antesala Laberinto    │
                              └──┬───┬───┬───┬───┬───────┘
                                 │   │   │   │   │
                    ┌────────────┘   │   │   │   └──────────┐
                    ▼                │   │   │              ▼
              [Puerta]→27      [Columna Cristal]│    [Puerta verde]
                               (PHidden →        │    (OpenLink) → 31
                                Antorcha 3 →      │
                                PHidden →         │
                                Martillo →        │
                                Puerta negra      │
                                → 50)             │
                                                  │
                                        [Crunch] (Troll, quiere Pastel cerezas)
                                        → pista: "El 12 te guiará"
                                                  │
                                        [Dédalo] (Troll, quiere Vendajes)
                                        → pista: "Solo el hierro te protegerá"
```

**Navegación del Laberinto (POpenLinks con Puerta 1, Puerta 2, Puerta 3):**

```
Nodo 31 (entrada desde 28):
  1→32  2→28  3→38

Nodo 32:
  1→31  2→33  3→44

Nodo 33:
  1→26(celda)  2→32  3→34

Nodo 34:
  1→35  2→41  3→33

Nodo 35:
  1→34  2→36  3→46

Nodo 36:
  1→49  2→35  3→37

Nodo 37:
  1→29(Minotauro!)  2→31  3→36

Nodo 38:
  1→26(celda)  2→39  3→31

Nodo 39:
  1→31  2→38  3→40

Nodo 40:
  1→31  2→26(celda)  3→39

Nodo 41:
  1→33  2→34  3→42

Nodo 42:
  1→32  2→43  3→41

Nodo 43:
  1→26(celda)  2→42  3→44

Nodo 44:
  1→45  2→32  3→31

Nodo 45:
  1→44  2→32  3→31

Nodo 46:
  1→47  2→33  3→35

Nodo 47:
  1→46  2→34  3→48

Nodo 48:
  1→31  2→49  3→47

Nodo 49:
  [Salida] → 28 (Antesala)
```

**Ruta del laberinto ("El 12 te guiará"):**

Crunch dice que "el 12 te guiará en el Laberinto. Luego solo debes dar un paso." Esto significa que debes tomar la puerta correspondiente al número 12 en cada nodo. Como hay 3 puertas (1, 2, 3), contar hasta 12 en módulo 3 da: 12 mod 3 = 0, pero como las puertas son 1-3, sería 3. Sin embargo, la pista probablemente significa que tomes secuencialmente puertas que sumen o indiquen la ruta.

**Interpretación alternativa:** "12" podría ser la secuencia de puertas: puerta 1, puerta 2 = la ruta. O más probablemente: en cada bifurcación tomas la puerta 1, luego la 2, y así. La ruta correcta desde la entrada (31):

Entrada → 1 (32) → 2 (33) → 1 (26/celda) — ¡trampa!

Otra interpretación: "el 12" se refiere a la puerta 1 en el segundo nodo y la puerta 2 en el tercer nodo, etc.

La ruta que lleva desde 31 hasta la salida en 49 (pasando por el Minotauro en 29):
- 31 → 1 (32) → 2 (33) → 3 (34) → 1 (35) → 3 (46) → 1 (47) → 3 (48) → 2 (49) → Salida → 28

O directamente desde 37 (que contiene al Minotauro): 37 → 2 (31) → 2 (28)...

La ruta al Minotauro (29):
- 31 → 1 (32) → 2 (33) → 3 (34) → 1 (35) → 2 (36) → 3 (37) → 1 (29)

Y desde el Minotauro de vuelta:
- 29 → [Puerta] (OpenLink) → 47

---

### Tabla Completa de Habitaciones — Parte I

| # | Nombre | Exits (dirección → destino) | Condiciones | Items | NPCs/Enemigos |
|---|--------|----------------------------|-------------|-------|---------------|
| 1 | el exterior de la fortaleza | Puerta principal → 2 | Necesita contraseña (del Roble) | Roble, Maza (peso 39), Pastel de cerezas | Llamador de bronce (Troll, quiere Cigarro) |
| | | Túnel → 4 | Siempre abierto (OpenLink) | | |
| | | Pared solitaria → Puerta secreta → 27 | Romper Pared (PHidden), luego DangerLink necesita Antorcha | | |
| 2 | el Salón de recepciones | Puerta principal → 1 | Necesita contraseña | Retrato | Monolito de mármol (PHidden) → contiene Trebol (Troll, quiere Vaso de agua) |
| | | Puerta negra → 3 | Siempre abierta | | |
| 3 | la Sala de juegos | Puerta negra → 2 | Siempre abierta | Escoba, Inscripción, Hilo de Ariadna | |
| | | Puerta azul → 4 | Siempre abierta | | |
| | | Escalera → 5 | Acertijo: "¿Cuántos peldaños tiene la escalera?" → "treinta y nueve" | | |
| 4 | el Patio interior | Puerta azul → 3 | Siempre abierta | Balanza | Estatua de Atenea (Troll, quiere Lanza), Estatua de Hermes (Troll, quiere Paraguas) |
| | | Puerta verde → 6 | Siempre abierta | | |
| 5 | el Cuarto de espejos | Escalera → 3 | Necesita contraseña "treinta y nueve" | Hueso de gato | Espejo opaco (PHidden) → contiene Puerta oculta → 14 |
| | | Puerta oculta → 14 | Siempre abierta (tras romper espejo) | | |
| 6 | la Biblioteca | Puerta verde → 4 | Siempre abierta | Vaso de agua, Candelabro | Cíclope (Guard, lethalweap: ¿Maza?) |
| | | Libro → 13 | Siempre abierto (PLinking sin key) | | |
| | | Puerta (gigante) → 7 | Necesita contraseña | | |
| 7 | Pasillo | Puerta → 6 | Necesita contraseña | Antorcha | |
| | | Puerta vieja → 8 | Siempre abierta | | |
| | | Puerta roja → 9 | Siempre abierta | | |
| | | Puerta prohibida → 10 | Necesita contraseña | | |
| | | Puerta gris → 15 | Siempre abierta | | |
| 8 | la Alcoba de la bruja | Puerta vieja → 7 | Siempre abierta | Polvo mágico, Poción para crecer | Bruja (Troll, quiere Escoba) |
| | | Escaparate → 14 | DangerLink, necesita Candelabro | | |
| 9 | el Cuarto del guerrero | Puerta roja → 7 | Siempre abierta | Vendajes, Grabado | Cama (PHidden → romper con Hacha → Puerta → 11) |
| 10 | el Laboratorio de la Bestia | Puerta prohibida → 7 | Necesita contraseña | Piedra filosofal, Máquina del tiempo | Homúnculo (Troll, quiere Poción para crecer) |
| 11 | la Sala de armas | Puerta → 9 | Siempre abierta | Espada, Lanza, Arco, Daga, Ariete, Látigo | |
| 12 | los Baños de la Bestia | Puerta verde → 13 | Siempre abierta | Rosa, Inscripción, Espejo | Troll (Troll, quiere Polvo mágico) |
| 13 | el Jardín | Puerta verde → 12 | Siempre abierta | Inscripción, Cedro | |
| | | Puerta azul → 14 | Siempre abierta | | |
| | | Puerta amarilla → 15 | Siempre abierta | | |
| | | Puerta de hierro → 16 | Siempre abierta | | |
| | | Puerta de madera → 23 | Siempre abierta | | |
| 14 | la Alcoba de la doncella | Puerta azul → 13 | Siempre abierta | Cuadro, Corazón de unicornio | Doncella (Troll, quiere Rosa) |
| | | Puerta oculta → 5 | Siempre abierta | | |
| | | Escaparate → 8 | Siempre abierto | | |
| 15 | la Sala de infusiones | Puerta gris → 7 | Siempre abierta | Taza de café, Cigarro | Arpía (Guard) |
| | | Puerta amarilla → 13 | Siempre abierta | | |
| 16 | los Calabozos | Puerta de hierro → 13 | Siempre abierta | Paraguas, Talismán de aire | Esqueleto (Troll, quiere Taza de café) |
| 17 | Boca de la Bestia | Puerta triangular → 25 | Siempre abierta | | |
| | | Garganta → 18 | Siempre abierta (OpenLink) | | |
| 18 | Interior de la Bestia | Garganta → 17 | OpenDoor (abierta) | Inscripción | |
| | | Tráquea → 19 | DangerLink (necesita talismán: ¿Talismán de aire?) | | |
| | | Esófago → 20 | DangerLink (necesita talismán: ¿Paraguas?) | | |
| | | Arteria principal → 21 | DangerLink (necesita Corazón de unicornio) | | |
| 19 | Pulmones de la Bestia | Tráquea → 18 | OpenDoor | | Centro de los pulmones (Guard, lethalweap: ¿Maza?) |
| 20 | el Estómago de la Bestia | Esófago → 18 | OpenDoor | | Centro del estomago (Guard, lethalweap: ¿Lanza?) |
| 21 | el Corazón de la Bestia | Arteria principal → 18 | OpenDoor | | Centro del corazón (Guard, lethalweap: ¿Arco?) |
| 22 | el Cerebro de la Bestia | (acceso desde 30 vía Puerta dorada) | | Inscripción | Centro del cerebro (Guard, lethalweap: Antorcha) |
| 23 | los Almacenes de la Fortaleza | Puerta de madera → 13 | Siempre abierta | Hacha | Ratón (Troll, quiere Piedra filosofal) |
| | | Puerta verde → 24 | Siempre abierta | | |
| 24 | un extenso páramo | Puerta verde → 23 | Siempre abierta | | Lobo (Guard, lethalweap: Látigo) |
| | | Pozo → 1 | Siempre abierto (OpenLink) | | |
| | | Puerta de cristal → 25 | Necesita contraseña | | |
| | | Túnel → 24 (loop) | DangerLink (necesita talismán) | | |
| 25 | Salón de cristal | Puerta de cristal → 24 | Necesita contraseña | | Bailarina (Troll, quiere Máquina del tiempo) |
| | | Puerta de tela → 26 | Siempre abierta | | |
| | | Puerta triangular → 17 | Acertijo: "¿Cuál es el nombre del duende?" → "Crunch" | | |
| 26 | celda pequeña | (sin salida propia) | | Inscripción | |
| 27 | un puente de mármol | Puerta secreta → 1 | DangerLink, necesita Antorcha | Martillo | Araña (Troll, quiere Hilo de Ariadna) |
| | | Estatua de Satanás → Puerta oculta → 28 | PHidden (romper con Cuadro) | | |
| | | Puerta → 28 | DangerLink2, necesita NO tener Espada → ¡MUERTE! | | |
| 28 | la Antesala del Laberinto | Puerta → 27 | Siempre abierta | | Crunch (Troll, quiere Pastel de cerezas), Dédalo (Troll, quiere Vendajes) |
| | | Columna de Cristal → Puerta de madera → Puerta negra → 50 | PHidden anidado (Antorcha 3 → Martillo) | | |
| | | Puerta verde → 31 | OpenLink, siempre abierta | | |
| 29 | la cueva del Minotauro | Puerta → 47 | OpenLink, siempre abierta | Antorcha 1-7 (6 apagada) | Minotauro (Guard, lethalweap: Espada) |
| 30 | el Salón de los elegidos | Puerta dorada → 22 | Acertijo: "Invente un alfabeto con el que no pueda crearse a la Bestia" → "cdfghjklmnopqruvwxyz" (sin A,B,E,I,S,T) | | |
| 31-48 | pasillos del Laberinto | Puerta 1/2/3 → varios | POpenLinks (siempre abiertos) | | |
| 49 | pasillo del Laberinto | Salida → 28 | OpenLink | | |
| 50 | el Jardín (falso) | Puerta negra → 26 (celda) | OpenLink | Inscripción, Cedro | |
| | | Puerta verde/azul/amarilla/madera → 26 (todas a la celda) | OpenLinks (¡trampa!) | | |
| | | Puerta de hierro → 30 | Acertijo: "¿Cuántas antorchas iluminan al Minotauro?" → "Seis" | | |

---

## PARTE II: LA FORTALEZA (55 habitaciones)

### Mapa ASCII de Conexiones (Zona Inicial)

```
┌──────────────────┐
│ 1. Hab. Huéspedes│
└────────┬─────────┘
    [Puerta] → 2
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Pasillo                                                 │
└──┬──────┬──────┬──────┬──────┬──────┬──────────────────────┘
   │      │      │      │      │      │
[Puerta] │      │      │      │  [Puerta de oro]→8
→ 1      │      │      │      │
         │      │      │      │
   [Pta espinos] │      │  [Pta Negra]
   → 6          │      │  → 3
                │      │
          [Pta metal]  [Pta Azul]
          (DangerLink) (acertijo: nombre hija)
          necesita     → 4
          Pañuelo
          → 7
                │
          [Grifo] (Guard)
          lethalweap: Daga
```

```
┌─────────────────┐     ┌─────────────────┐
│ 3. Salón de Fumar│     │ 4. Cuarto Hija  │
└──┬──────────────┘     │    del Hechicero │
   │                    └──┬──────┬───────┘
[Pta Negra]→2              │      │
                      [Pta Azul]→2  [Agujero]
                                    (OpenLink)→5
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │ 5. Casa      │
                                    │    muñecas   │
                                    └──┬───┬───┬───┘
                                       │   │   │
                                  [Agujero]│[Pta baúl]
                                  →4       │(MIAU)→10
                                           │
                                     [Ventana]
                                     (PHidden, romper con
                                      Corta-cristales)
                                     → Pasadizo → 13
```

```
┌─────────────────┐     ┌─────────────────┐
│ 6. Cuarto       │     │ 7. Cocina       │
│    Leñador      │     └──┬──────────────┘
└──┬──────────────┘        │
   │                 [Pta metal]→2
[Pta espinos]→2            │
                      (DangerLink, necesita Pañuelo)
```

```
┌──────────────────┐
│ 8. Terrazas      │
└──┬───────┬───────┘
   │       │
[Pta oro]→2 │
   │   [Escalera caracol]
   │   (OpenLink)→11
   │       │
   │       ▼
   │  ┌─────────────┐
   │  │ 11. Orilla 1 │
   │  │   Río Negro  │
   │  └──┬──────┬───┘
   │     │      │
   │ [Escalera] [Río Negro]
   │ →9      (OpenLink)→12
   │     │
   │     ▼
   │  ┌──────────────────┐
   │  │ 9. Calabozo       │
   │  │    Monstruo       │
   │  └──────────────────┘
   │     │
   │ [Escalera]→8
   │
   └──────────────────────────────┐
                                  │
┌─────────────────────────────────┘
│
▼
┌──────────────────┐
│ 12. Orilla 2     │
│    Río Negro     │
└──┬───────────────┘
   │
[Río Negro]→11
   │
[Arbol de marfil] (PHidden, Hacha → Maza)
   │
[Muralla] (PHidden, Maza → Avenida de hierro → 13)
```

```
┌──────────────────────────────────────────────────────┐
│ 13. Jardines del Hechicero                           │
└──┬──────┬──────┬──────┬──────┬──────┬────────────────┘
   │      │      │      │      │      │
[Avenida]│      │      │      │      │
→ 12     │      │      │      │      │
         │      │      │      │      │
   [Pta madera] [Pta amarilla] │  [Pta tela] [Pta verde]
   → 14        → 17            │  → 15       → 16
                   (password:   │
                   Omicuos      │
                   Ihanti)      │
                          [Pta roja]→18
                                │
                          [Jardinero] (Troll, quiere Hacha)
```

```
┌──────────────────┐     ┌───────────────────┐
│ 14. Comedor      │     │ 15. Sastrería     │
└──┬───────────────┘     └──┬────────────────┘
   │                        │
[Pta madera]→13        [Pta tela]→13
   │
[Túnel] (DangerLink, necesita Arco)→49
   │
[Huevo] (PHidden, Piedra → Dinosaurio)
        (Troll, quiere Sonajero)
```

```
┌──────────────────┐
│ 18. Salón Velas  │
└──┬───────┬───────┘
   │       │
[Pta roja]→13  [Pta blanca]→20
   │       │
[Escalera]→19  │
   │       │
[Dragón] (Troll, quiere Daga)
   → pista: "Omicuos Ihanti"
```

```
┌──────────────────┐     ┌──────────────────┐
│ 19. Cuarto        │     │ 20. Cuarto       │
│     Inmortal      │     │     Juguetes     │
└──┬───────────────┘     └──┬───────┬───────┘
   │                        │       │
[Escalera]→18          [Pta blanca]→18 │
   │                        │   [Pta piedra]→21
[Inmortal] (Guard,            │
lethalweap: Arco)             │
```

```
┌──────────────────────────────────────────────┐
│ 21. Ruinas                                   │
└──┬───────┬───────┬───────────────────────────┘
   │       │       │
[Pta piedra]→20 [Escalera] [Desierto]
   │       │  → 27       → 34
[Pta hierro]→22  │
                │
                ▼
┌──────────────────┐
│ 22. Salón Recepc.│
└──┬───────────────┘
   │
[Pta hierro]→21
   │
[Pta gris]→24
```

```
┌──────────────────────────────────────────────┐
│ 24. Patio Interior                           │
└──┬───────┬───────┬───────────────────────────┘
   │       │       │
[Pta gris]→22 [Pta azul]→23 [Pta verde]→25
   │       │       │
[Pta negra]→26    │
                  │
                  ▼
┌──────────────────┐
│ 23. Cuarto Pintor│
└──┬───────────────┘
[Pta azul]→24
```

```
┌──────────────────┐     ┌──────────────────┐
│ 25. Juglar       │     │ 26. Ogro         │
└──┬───────────────┘     └──┬───────────────┘
   │                        │
[Pta verde]→24         [Pta negra]→24
   │                        │
[Escalera] (DangerLink,     [Ogro] (Guard, lethalweap:
necesita Escudo de Aquiles)  Cubo de agua)
→ 28
   │
[Juglar] (Troll, quiere Arpa)
→ pista: "Lleva algo de la fragua de Vulcano"
```

```
                              ┌─────────────────┐
                              │ 27. Subterráneos│
                              └──┬──────┬───────┘
                                 │      │
                           [Escalera]→21 │
                                 │  [Túnel] (DangerLink,
                                 │  necesita Escudo Aquiles)
                                 │  → 28
                                 │      │
                                 ▼      ▼
                          ┌──────────────────┐
                          │ 28. Catacumbas   │
                          └──┬───────┬───────┘
                             │       │
                    [Túnel]→27  [Escalera]→25
                    (DangerLink, (DangerLink,
                     Escudo)      Escudo)
                             │
                       [Pasadizo]→29
                             │
                             ▼
                    ┌──────────────────┐
                    │ 29. Cataratas    │
                    └──┬───────────────┘
                       │
                 [Pasadizo]→28
                       │
                 [Catarata] (OpenLink)→31
```

```
┌──────────────────────────────────────────────────┐
│ 31. Fondo del Lago                               │
└──┬───────┬───────┬───────────────────────────────┘
   │       │       │
[Grieta]   │  [Sendero dorado]
(DangerLink,│  (DangerLink2,
Talismán    │  necesita NO tener
Nieve)      │  Marmidosa)
→ 32        │  → 33
            │
      [Reja] (PHidden, Tenazas → Escalera)
      → 35
            │
      [Doncella del Lago] (Troll, quiere Talismán de Nieve)
```

```
┌──────────────────┐     ┌──────────────────┐
│ 32. Cueva Cristal │     │ 33. Orilla Lago  │
└──┬───────────────┘     └──┬───────────────┘
   │                        │
[Grieta]→31           [Sendero dorado]→31
   │                   (DangerLink2, sin Marmidosa)
[Marmidosa] (ítem)         │
                      [Camino]→36
```

```
┌──────────────────┐     ┌──────────────────┐
│ 34. Oasis        │     │ 35. Catedral     │
└──┬───────┬───────┘     └──┬───────┬───────┘
   │       │                │       │
[Desierto]→21 [Ruta camellos]→35 [Ruta]→34 [Puerta]→36
   │                        │
[Pordiosero] (Troll,         [Obispo] (Troll, quiere Silla)
quiere Bolsa)
```

```
┌──────────────────┐
│ 36. Desierto     │
└──┬───────┬───────┘
   │       │
[Camino]       [Puerta]→35
(DangerLink2,
sin Talismán Nieve)
→ 33
   │
[Muralla] (PHidden, Piedra verde → Avenida flores)
→ 37
   │
[Escudo de Aquiles] (ítem)
```

```
┌──────────────────┐     ┌──────────────────┐
│ 37. Valle        │     │ 38. Pico Negro   │
└──┬───────┬───────┘     └──┬───────┬───────┘
   │       │                │       │
[Avenida]→36 [Montañas]→38 [Montañas]→37 [Precipicio]
   │                        │       │  (DangerLink,
[Camello] (Troll,            │       │   necesita Saltador)
quiere Botella de vino)      │       │  → 40
                             │       │
                       [Pta Madera]→39 [Ladera]→42
                             │
                             ▼
                       ┌──────────────────┐
                       │ 39. Choza Monje  │
                       └──┬───────────────┘
                          │
                    [Pta Madera]→38
                          │
                    [Monje] (Troll, quiere Rosario)
```

```
┌──────────────────┐     ┌──────────────────┐
│ 40. Ciudad Aband.│     │ 41. Choza Sabio  │
└──┬───────┬───────┘     └──┬───────────────┘
   │       │                │
[Túnel]→21 [Escalera]→37 [Pta Hierro]→40
   │       │                │
[Pta Hierro]→41 [Sabio] (Troll, quiere
   │            Esqueleto Murciélago)
[Estatua Cristal]          │
(PHidden, Corta-Cristales → [Cinta de Moebius] (ítem)
Horante, Troll, quiere      [Péndulo] (ítem)
Muñeco diabólico)
```

```
┌──────────────────┐     ┌──────────────────┐
│ 42. Campo        │     │ 43. Torre Cristal│
│    cultivado     │     │    (exterior)    │
└──┬───────┬───────┘     └──┬───────┬───────┘
   │       │                │       │
[Ladera]→38 [Río]          [Río]→42 [Escalera]
   │       │  (DangerLink,    │  (DangerLink, caracol→44
[Tenazas]   │   Cuerda)→43    │   Cuerda)    │
   │       │                [Pta Hierro]→47 │
[Labrador] (Troll,                          │
quiere Bolsa semillas)                      ▼
                                      ┌──────────────────┐
                                      │ 44. Torre arriba │
                                      └──┬───────┬───────┘
                                         │       │
                                   [Escalera]→43 │
                                         │  [Pta Cristal]
                                   [Esfera]      (acertijo: nombre
                                   (PHidden,     completo hija →
                                   Marmidosa →   "Aura Srka")
                                   Tablilla)     → 45
```

```
┌──────────────────┐     ┌──────────────────┐
│ 45. Alcoba Aura  │     │ 46. Alcoba Secreta│
└──┬───────┬───────┘     └──┬───────────────┘
   │       │                │
[Pta Cristal]→44 [Pta Secreta]→45
   │       │  (DangerLink,
[Carta]       │   necesita Lienzo)
(PHidden →    │
Pta Secreta)  │
   │       [Hija del Hechicero]
[Espejo] (ítem) (TDaugther, lethalweap: Aguja)
```

```
┌──────────────────┐     ┌──────────────────┐
│ 47. Calabozos    │     │ 48. Celda        │
└──┬───────┬───────┘     └──┬───────────────┘
   │       │                │
[Pta Hierro]→43        [Reja]→47
   │       │           (password: Grifo)
[Reja]→48  │                │
(password:  │          [Encapuchado] (Troll,
Grifo)      │           quiere Receta)
   │       │
[Pta Gris]→49
   │
[Carcelero] (Guard,
lethalweap: Marmidosa)
```

```
┌──────────────────────────────────────────┐
│ 49. Antesala de la Prueba                │
└──┬───────┬───────┬───────────────────────┘
   │       │       │
[Pta Gris]→47 [Túnel]→14 [Pta Verde]
   │       │  (DangerLink, (DangerLink2,
[Arco] (ítem) Arco)       sin Anillo oro)
            │              → 50
            │              │
            │              ▼
            │       ┌──────────────────┐
            │       │ 50. Salón Verde  │
            │       └──┬───────────────┘
            │          │
            │    [Pta Verde]→49
            │    (DangerLink2, sin Anillo oro)
            │          │
            │    [Pta Azul]→51
            │    (DangerLink2, sin Anillo plata)
            │          │
            │          ▼
            │    ┌──────────────────┐
            │    │ 51. Salón Azul   │
            │    └──┬───────────────┘
            │       │
            │ [Pta Azul]→50
            │ (DangerLink2, sin Anillo plata)
            │       │
            │ [Pta Blanca]→52
            │ (DangerLink2, sin Anillo bronce)
            │       │
            │       ▼
            │ ┌──────────────────┐
            │ │ 52. Salón Blanco │
            │ └──┬───────────────┘
            │    │
            │ [Pta Blanca]→51
            │ (DangerLink2, sin Anillo bronce)
            │    │
            │ [Pta triangular]→53
            │ (DangerLink, necesita Cinta Moebius)
            │    │
            │    ▼
            │ ┌──────────────────────┐
            │ │ 53. Límites Fortaleza│
            │ └──┬──────────┬────────┘
            │    │          │
            │ [Pta triang]→52 [Puente]
            │ (DangerLink,    (DangerLink,
            │  Cinta Moebius)  necesita Grabado)
            │    │          → 54
            │ [Muralla] (PHidden, NADA)
            │ [Guardián] (Troll, quiere Sombrero)
            │    │
            │    ▼
            │ ┌──────────────────────┐
            │ │ 54. Pirámide         │
            │ └──┬───────────────────┘
            │    │
            │ [Puente]→53
            │ (DangerLink, Grabado)
            │    │
            │ [Columna Hielo] (PHidden, Antorcha →
            │  Puerta Roble, acertijo: "¿Quién invirtió
            │  el reloj de Caronte?" → "Yo")
            │  → 55
            │    │
            │    ▼
            │ ┌──────────────────────────┐
            │ │ 55. Habitaciones         │
            │ │     Hechicero            │
            │ └──┬───────────────────────┘
            │    │
            │ [Pta Roble]→54
            │    │
            │ [Hechicero] (Troll, quiere Marmidosa)
```

---

### Tabla Completa de Habitaciones — Parte II

| # | Nombre | Exits | Condiciones | Items | NPCs/Enemigos |
|---|--------|-------|-------------|-------|---------------|
| 1 | una habitación para huéspedes | Puerta → 2 | Siempre abierta | — | — |
| 2 | el pasillo | Puerta → 1 | Siempre abierta | — | Grifo (Guard, lethalweap: Daga) |
| | | Puerta de espinos → 6 | Siempre abierta | | |
| | | Puerta de metal → 7 | DangerLink, necesita Pañuelo | | |
| | | Puerta Negra → 3 | Siempre abierta | | |
| | | Puerta Azul → 4 | Acertijo: "¿Cuál es el nombre de la hija del Hechicero?" → "Aura" | | |
| | | Puerta de oro → 8 | Siempre abierta | | |
| 3 | el Salón de Fumar | Puerta Negra → 2 | Siempre abierta | Balanza, Inscripción, Piedra de Roseta | — |
| 4 | el cuarto de la hija del Hechicero | Puerta Azul → 2 | Siempre abierta | Pañuelo, Carta | — |
| | | Agujero → 5 | OpenLink | | |
| 5 | la casa de muñecas | Agujero → 4 | OpenLink | — | Ventana (PHidden, Corta-cristales → Pasadizo → 13) |
| | | Puerta del baúl → 10 | Password: "MIAU" | | |
| 6 | el cuarto del Leñador | Puerta de espinos → 2 | Siempre abierta | Daga, Botella de vino, Hacha | — |
| 7 | la Cocina | Puerta de metal → 2 | DangerLink, necesita Pañuelo | Receta, Muslo de carnero, Pescado | — |
| 8 | las Terrazas | Puerta de oro → 2 | Siempre abierta | Inscripción, Reloj de arena, Silla | — |
| | | Escalera de caracol → 11 | OpenLink | | |
| 9 | el calabozo del Monstruo | Escalera de caracol → 8 | OpenLink | Inscripción | Monstruo (Troll, quiere Muslo de carnero) |
| 10 | el interior del baúl | Puerta del baúl → 5 | Password: "MIAU" | Piedra verde | Gato (Troll, quiere Pescado) |
| 11 | una orilla del Río Negro | Escalera de caracol → 9 | OpenLink | Bote | Caronte (Troll, quiere Reloj de arena) |
| | | Río Negro → 12 | OpenLink | | |
| 12 | una orillas del Río Negro | Río Negro → 11 | OpenLink | Maza (en PHidden Árbol) | — |
| | | Avenida de hierro → 13 | PHidden Muralla (Maza → OpenLink) | | |
| 13 | los Jardines del Hechicero | Avenida hierro → 12 | OpenLink | Piedra | Jardinero (Troll, quiere Hacha) |
| | | Puerta de madera → 14 | Siempre abierta | | |
| | | Puerta amarilla → 17 | Password: "Omicuos Ihanti" | | |
| | | Puerta de tela → 15 | Siempre abierta | | |
| | | Puerta verde → 16 | Siempre abierta | | |
| | | Puerta roja → 18 | Siempre abierta | | |
| 14 | el Comedor | Puerta de Madera → 13 | Siempre abierta | — | Huevo (PHidden, Piedra → Dinosaurio, Troll, quiere Sonajero) |
| | | Túnel → 49 | DangerLink, necesita Arco | | |
| 15 | la Sastrería | Puerta de Tela → 13 | Siempre abierta | Muñeco diabólico, Aguja | — |
| 16 | el cuarto del jardinero | Puerta verde → 13 | Siempre abierta | Corta-cristales, Sombrero | — |
| 17 | la habitación de los tesoros | Puerta amarilla → 13 | Siempre abierta | Rosa diamante, Anillo de oro, Arpa, Bolsa | — |
| 18 | el salón de las velas | Puerta roja → 13 | Siempre abierta | — | Dragón (Troll, quiere Daga) |
| | | Puerta blanca → 20 | Siempre abierta | | |
| | | Escalera → 19 | OpenLink | | |
| 19 | el cuarto del Inmortal | Escalera → 18 | OpenLink | Inscripción | Inmortal (Guard, lethalweap: Arco) |
| 20 | el cuarto de juguetes | Puerta blanca → 18 | Siempre abierta | Saltador, Sonajero, Talismán de Nieve | — |
| | | Puerta de piedra → 21 | Siempre abierta | | |
| 21 | las Ruinas | Puerta de piedra → 20 | Siempre abierta | — | — |
| | | Puerta de hierro → 22 | Siempre abierta | | |
| | | Escalera → 27 | OpenLink | | |
| | | Desierto → 34 | OpenLink | | |
| 22 | el Salón de Recepciones | Puerta de hierro → 21 | Siempre abierta | Anillo de bronce | — |
| | | Puerta gris → 24 | Siempre abierta | | |
| 23 | el cuarto de un pintor | Puerta azul → 24 | Siempre abierta | Lienzo, Grabado | — |
| 24 | el Patio Interior | Puerta gris → 22 | Siempre abierta | — | — |
| | | Puerta azul → 23 | Siempre abierta | | |
| | | Puerta verde → 25 | Siempre abierta | | |
| | | Puerta negra → 26 | Siempre abierta | | |
| 25 | las habitaciones del Juglar | Puerta verde → 24 | Siempre abierta | Cuerda | Juglar (Troll, quiere Arpa) |
| | | Escalera → 28 | DangerLink, necesita Escudo de Aquiles | | |
| 26 | la alcoba del Ogro | Puerta negra → 24 | Siempre abierta | Inscripción | Ogro (Guard, lethalweap: Cubo de agua) |
| 27 | los Subterráneos | Escalera → 21 | OpenLink | Antorcha | — |
| | | Túnel → 28 | DangerLink, necesita Escudo de Aquiles | | |
| 28 | las Catacumbas | Túnel → 27 | DangerLink, Escudo Aquiles | Esqueleto de Murciélago | — |
| | | Escalera → 25 | DangerLink, Escudo Aquiles | | |
| | | Pasadizo → 29 | OpenLink | | |
| 29 | el punto donde comienzan unas enormes cataratas | Pasadizo → 28 | OpenLink | Anillo de plata | — |
| | | Catarata → 31 | OpenLink | | |
| 31 | fondo del Lago | Grieta → 32 | DangerLink, necesita Talismán de Nieve | Inscripción | Doncella del Lago (Troll, quiere Talismán de Nieve) |
| | | Sendero dorado → 33 | DangerLink2, NO llevar Marmidosa | | |
| | | Reja → Escalera → 35 | PHidden (Tenazas → OpenLink) | | |
| 32 | la Cueva de Cristal | Grieta → 31 | OpenLink | Marmidosa | — |
| 33 | la orilla del Lago | Sendero dorado → 31 | DangerLink2, sin Marmidosa | — | — |
| | | Camino → 36 | OpenLink | | |
| 34 | un Oasis | Desierto → 21 | OpenLink | Cubo de agua | Pordiosero (Troll, quiere Bolsa) |
| | | Ruta de los camellos → 35 | OpenLink | | |
| 35 | la Catedral | Ruta de los camellos → 34 | OpenLink | Rosario | Obispo (Troll, quiere Silla) |
| | | Puerta → 36 | Siempre abierta | | |
| 36 | el Desierto otra vez | Camino → 33 | DangerLink2, sin Talismán Nieve | Inscripción, Escudo de Aquiles | Muralla (PHidden, Piedra verde → Avenida flores → 37) |
| | | Puerta → 35 | Siempre abierta | | |
| 37 | un extenso valle | Avenida flores → 36 | OpenLink | Bolsa de semillas | Camello (Troll, quiere Botella de vino) |
| | | Montañas → 38 | OpenLink | | |
| 38 | la cima del Pico Negro | Montañas → 37 | OpenLink | — | — |
| | | Precipicio → 40 | DangerLink, necesita Saltador | | |
| | | Ladera → 42 | OpenLink | | |
| | | Puerta de Madera → 39 | Siempre abierta | | |
| 39 | la choza de un monje | Puerta de Madera → 38 | Siempre abierta | — | Monje (Troll, quiere Rosario) |
| 40 | la Ciudad Abandonada | Túnel → 21 | OpenLink | Inscripción | Estatua de Cristal (PHidden, Corta-Cristales → Horante, Troll, quiere Muñeco diabólico) |
| | | Escalera → 37 | OpenLink | | |
| | | Puerta de Hierro → 41 | Siempre abierta | | |
| 41 | la choza del Sabio | Puerta de Hierro → 40 | Siempre abierta | Cinta de Moebius, Péndulo | Sabio (Troll, quiere Esqueleto de Murciélago) |
| 42 | un campo cultivado | Ladera → 38 | OpenLink | Tenazas | Labrador (Troll, quiere Bolsa de semillas) |
| | | Río → 43 | DangerLink, necesita Cuerda | | |
| 43 | el exterior de la Torre de Cristal | Río → 42 | DangerLink, Cuerda | — | Ébano (PHidden, NADA) |
| | | Puerta de Hierro → 47 | Siempre abierta | | |
| | | Escalera de Caracol → 44 | OpenLink | | |
| 44 | la punta de la Torre de Cristal | Escalera de Caracol → 43 | OpenLink | Tablilla de Madera (en PHidden Esfera, Marmidosa) | — |
| | | Puerta de Cristal → 45 | Acertijo: "¿Cuál es el nombre completo de la hija del Hechicero?" → "Aura Srka" | | |
| 45 | la alcoba de la hija del Hechicero | Puerta de Cristal → 44 | Siempre abierta | Espejo | Carta (PHidden → Puerta Secreta → 46, DangerLink necesita Lienzo) |
| 46 | la Alcoba Secreta | Puerta Secreta → 45 | OpenDoor | — | Hija del Hechicero (TDaugther, lethalweap: Aguja) |
| 47 | los Calabozos | Puerta de Hierro → 43 | Siempre abierta | — | Carcelero (Guard, lethalweap: Marmidosa) |
| | | Reja → 48 | Password: "Grifo" | | |
| | | Puerta Gris → 49 | Siempre abierta | | |
| 48 | una celda | Reja → 47 | Password: "Grifo" | — | Encapuchado (Troll, quiere Receta) |
| 49 | la Antesala de la Prueba | Puerta Gris → 47 | Siempre abierta | Inscripción, Arco | — |
| | | Túnel → 14 | DangerLink, necesita Arco | | |
| | | Puerta Verde → 50 | DangerLink2, NO Anillo de oro | | |
| 50 | el Salón Verde | Puerta Verde → 49 | DangerLink2, sin Anillo oro | — | — |
| | | Puerta Azul → 51 | DangerLink2, NO Anillo de plata | | |
| 51 | el Salón Azul | Puerta Azul → 50 | DangerLink2, sin Anillo plata | — | — |
| | | Puerta Blanca → 52 | DangerLink2, NO Anillo de bronce | | |
| 52 | el Salón Blanco | Puerta Blanca → 51 | DangerLink2, sin Anillo bronce | — | — |
| | | Puerta triangular → 53 | DangerLink, necesita Cinta de Moebius | | |
| 53 | los límites de la Fortaleza | Puerta triangular → 52 | DangerLink, Cinta Moebius | — | Guardián (Troll, quiere Sombrero), Muralla (PHidden, NADA) |
| | | Puente → 54 | DangerLink, necesita Grabado | | |
| 54 | la Pirámide del Hechicero | Puente → 53 | DangerLink, Grabado | — | Columna de Hielo (PHidden, Antorcha → Puerta de Roble, acertijo: "¿Quién invirtió el reloj de Caronte?" → "Yo" → 55) |
| 55 | las Habitaciones del Hechicero | Puerta de Roble → 54 | Siempre abierta | — | Hechicero (Troll, quiere Marmidosa) |
