# Dependencias de Puzzles — Fortaleza Partes I y II

Grafo de dependencias mostrando qué puzzles desbloquean qué, y la ruta crítica a través de cada juego.

---

## PARTE I: Resumen de Puzzles

### Puzzle 1: Puerta Principal (R1 → R2)
- **Qué bloquea**: Acceso al interior de la Fortaleza
- **Solución**: Contraseña del Roble. El Roble dice "Las palabras mágicas para abrir la puerta son obvias." La contraseña está decodificada en key[2].
- **Comando**: `abrir puerta principal diciendo [contraseña]`

### Puzzle 2: Escalera al Cuarto de Espejos (R3 → R5)
- **Acertijo**: "¿Cuántos peldaños tiene la escalera?"
- **Respuesta**: "treinta y nueve" (39)
- **Comando**: `abrir escalera respondiendo treinta y nueve`

### Puzzle 3: Espejo Opaco (R5 → R14)
- **Tipo**: PHidden — romper para revelar
- **Necesita**: Objeto específico (decodificado de key[11])
- **Revela**: Puerta oculta → Alcoba de la doncella (R14)
- **Comando**: `romper espejo opaco con [objeto]`

### Puzzle 4: Puerta Gigante Biblioteca → Pasillo (R6 → R7)
- **Necesita**: Contraseña (decodificada de key[14])
- **Cómo obtenerla**: Matar al Cíclope (Guard) con Maza
- **Comando**: `matar ciclope con maza` → revela contraseña → `abrir puerta diciendo [contraseña]`

### Puzzle 5: Cama del Guerrero → Sala de Armas (R9 → R11)
- **Tipo**: PHidden "Cama"
- **Necesita**: Hacha (de R23, Almacén)
- **Revela**: Puerta → Sala de armas
- **Comando**: `romper cama con hacha`
- **DESBLOQUEA**: Todas las armas (Espada, Lanza, Arco, Daga, Látigo, Ariete)

### Puzzle 6: Pared Solitaria → Puente (R1 → R27)
- **Tipo**: PHidden "Pared solitaria"
- **Necesita**: Objeto (decodificado de key[3])
- **Revela**: Puerta secreta (DangerLink, necesita Antorcha)
- **Comando**: `romper pared solitaria con [objeto]` → `ir puerta secreta`

### Puzzle 7: Estatua de Satanás → Antesala (R27 → R28)
- **Tipo**: PHidden
- **Necesita**: Cuadro (de R14)
- **Revela**: Puerta oculta → Antesala del Laberinto
- **Comando**: `romper estatua de satanas con cuadro`

### Puzzle 8: Puerta del Puente → Antesala (R27 → R28)
- **Tipo**: DangerLink2 (NO llevar Espada → MUERTE)
- **Solución**: Dejar la Espada antes de cruzar
- **Comando**: `dejar espada` → `ir puerta`

### Puzzle 9: Columna de Cristal → Jardín Falso (R28 → R50)
- **Tipo**: PHidden anidado
- **Necesita**: Antorcha 3 (del Minotauro, R29) → luego Martillo (de R27)
- **Comando**: `romper columna de cristal con antorcha 3` → `romper puerta de madera con martillo` → `ir puerta negra`

### Puzzle 10: Puerta de Hierro → Salón Elegidos (R50 → R30)
- **Acertijo**: "¿Cuántas antorchas iluminan al Minotauro?"
- **Respuesta**: "Seis" (de 7 antorchas, 1 está apagada)
- **Comando**: `abrir puerta de hierro respondiendo seis`

### Puzzle 11: Puerta Dorada → Cerebro (R30 → R22)
- **Acertijo**: "Invente un alfabeto (el mayor que pueda) con el que no pueda crearse a la Bestia"
- **Respuesta**: "cdfghjklmnopqruvwxyz" (todas las letras menos A,B,E,I,S,T = BESTIA)
- **Comando**: `abrir puerta dorada respondiendo cdfghjklmnopqruvwxyz`

### Puzzle 12: Puerta Triangular → Boca Bestia (R25 → R17)
- **Acertijo**: "¿Cuál es el nombre del duende?"
- **Respuesta**: "Crunch" (el Troll en R28)
- **Comando**: `abrir puerta triangular respondiendo crunch`

### Puzzle 13: Los Cuatro Centros (R18 → R19, R20, R21, R22)
- **Tráquea → Pulmones**: DangerLink, talismán: Talismán de aire (R16). Guard: lethalweap: Maza
- **Esófago → Estómago**: DangerLink, talismán: Paraguas (R16). Guard: lethalweap: Lanza
- **Arteria → Corazón**: DangerLink, talismán: Corazón de unicornio (R14). Guard: lethalweap: Arco
- **Cerebro**: Guard: lethalweap: Antorcha (confirmado por descripción "Usa la antorcha!")

### Puzzle 14: Minotauro (R29)
- **Tipo**: Guard
- **Arma letal**: Espada
- **Al morir revela**: "Coge la antorcha del número divino y rompe la columna de cristal"
- **Comando**: `matar minotauro con espada`

### Puzzle 15: Troll en Baños (R12)
- **Tipo**: Troll (muere con cualquier arma)
- **Quiere**: Polvo mágico (R8)
- **Al recibirlo**: Pista
- **Para ganar**: DEBES matarlo después
- **Comando**: `dar polvo magico a troll` → `interrogar troll` → `matar troll`

---

## PARTE I: Ruta Crítica (Orden de dependencias)

```
1. Roble (R1) → contraseña Puerta principal
2. Puerta principal → R2 (interior)
3. Escoba (R3) + Vaso agua (R6) + Hilo Ariadna (R3)
4. Cigarro (R15) → Llamador bronce (R1) → pista
5. Escoba → Bruja (R8) → pista
6. Vaso agua → Trebol (R2) → pista
7. Escalera → acertijo "39" → R5
8. Espejo opaco → romper → Puerta oculta → R14
9. Corazón unicornio + Cuadro (R14)
10. Paraguas + Talismán aire (R16)
11. Hacha (R23) → Cama (R9) → Puerta → Sala armas (R11)
12. TODAS las armas: Espada, Lanza, Arco, Daga, Maza, Látigo
13. Maza → Cíclope (R6) → contraseña Puerta gigante
14. Puerta gigante → Pasillo (R7) → Antorcha
15. Pared solitaria → Puerta secreta (Antorcha) → Puente (R27)
16. Hilo Ariadna → Araña (R27) → pista Minotauro
17. Cuadro → Estatua Satanás → Puerta oculta → Antesala (R28)
18. Pastel cerezas → Crunch (R28) → "El 12 te guiará"
19. Vendajes → Dédalo (R28) → "Hierro protege contra flores"
20. Laberinto: ruta al Minotauro (R29)
21. Espada → Minotauro → Antorchas (1-7)
22. Antorcha 3 → Columna Cristal → Martillo → Jardín falso (R50)
23. Acertijo "Seis" → Salón Elegidos (R30)
24. Acertijo alfabeto sin BESTIA → Cerebro (R22)
25. Antorcha → Centro del cerebro
26. Salón cristal (R25) → acertijo "Crunch" → Boca Bestia (R17)
27. Garganta → Interior (R18)
28. Talismán aire → Tráquea → Pulmones: matar con Maza
29. Paraguas → Esófago → Estómago: matar con Lanza
30. Corazón unicornio → Arteria → Corazón: matar con Arco
31. Matar Troll (R12) → ¡VICTORIA!
```

---

## PARTE II: Resumen de Puzzles

### Puzzle 1: Nombre de la Hija (R2 → R4)
- **Acertijo**: "¿Cuál es el nombre de la hija del Hechicero?"
- **Respuesta**: "Aura" (revelado por el Grifo al morir con Daga)
- **Comando**: `abrir puerta azul respondiendo aura`

### Puzzle 2: Puerta del Baúl (R5 → R10)
- **Password**: "MIAU"
- **Comando**: `abrir puerta del baul diciendo miau`

### Puzzle 3: Puerta Amarilla → Tesoros (R13 → R17)
- **Password**: "Omicuos Ihanti"
- **Cómo obtenerla**: Dar Daga al Dragón (R18) → revela las palabras
- **Comando**: `abrir puerta amarilla diciendo omicuos ihanti`

### Puzzle 4: Nombre Completo de la Hija (R44 → R45)
- **Acertijo**: "¿Cuál es el nombre completo de la hija del Hechicero?"
- **Respuesta**: "Aura Srka" (Aura del cuarto + Srka: pista del Camello "KA" al final)
- **Verificación**: 8 letras, A(3 veces), R(2 veces) — confirmado por Encapuchado (R48)
- **Comando**: `abrir puerta de cristal respondiendo aura srka`

### Puzzle 5: Reja de la Celda (R47 → R48)
- **Password**: "Grifo"
- **Cómo obtenerla**: Matar al Carcelero (R47) con Marmidosa → confiesa
- **Comando**: `abrir reja diciendo grifo`

### Puzzle 6: Puerta de Roble → Hechicero (R54 → R55)
- **Acertijo**: "¿Quién invirtió el reloj de Caronte?"
- **Respuesta**: "Yo" (el jugador, que le dio el reloj a Caronte)
- **Comando**: `abrir puerta de roble respondiendo yo`

### Puzzle 7: La Prueba de los Anillos (R49 → R53)
Ruta: R49 → R50 → R51 → R52 → R53
- Pta Verde: DangerLink2 (NO llevar Anillo de oro)
- Pta Azul: DangerLink2 (NO llevar Anillo de plata)
- Pta Blanca: DangerLink2 (NO llevar Anillo de bronce)
- Pta triangular: DangerLink (SÍ llevar Cinta de Moebius)
- Debes DEJAR los 3 anillos (oro, plata, bronce) antes de la prueba
- Debes LLEVAR la Cinta de Moebius

### Puzzle 8: El Ritual Final
Colocar 7 objetos en ubicaciones específicas:
1. Antorcha (de R27) → R1
2. Péndulo (de R41) → R3
3. Espejo (de R45) → R4
4. Bote (de R11) → R12
5. Rosa diamante (de R17) → R31
6. Escudo de Aquiles (de R36) → R40
7. Cinta de Moebius (de R41) → R43

Matar: Monstruo (R9) + Hija del Hechicero (R46, con Aguja)

### Puzzle 9: Ventana Casa Muñecas (R5 → R13)
- **Tipo**: PHidden
- **Necesita**: Corta-cristales (R16)
- **Revela**: Pasadizo → Jardines (R13) — acceso alternativo
- **Comando**: `romper ventana con corta-cristales`

### Puzzle 10: Huevo del Comedor (R14)
- **Tipo**: PHidden
- **Necesita**: Piedra (R13)
- **Revela**: Dinosaurio (Troll, quiere Sonajero de R20)
- **Comando**: `romper huevo con piedra`

### Puzzle 11: Ogro (R26)
- **Guard**, lethalweap: Cubo de agua (de R34)
- **Pista**: Pordiosero (R34) dice "Si el Ogro se baña, se muere"
- **Comando**: `matar ogro con cubo de agua`
- **Confesión**: "¡No saldrás del lago con Marmidosa tan fácilmente!"

### Puzzle 12: Inmortal (R19)
- **Guard**, lethalweap: Arco (de R49)
- **Confesión**: "No confundas la 3ª muralla con la 3ª barrera que tienes que romper. La 3ª barrera está en ti mismo."

### Puzzle 13: Carcelero (R47)
- **Guard**, lethalweap: Marmidosa (de R32)
- **Confesión**: "La palabra mágica es el nombre de la primera criatura que viste al salir del cuarto de huéspedes" → Grifo
- **Comando**: `matar carcelero con marmidosa`

### Puzzle 14: Hija del Hechicero (R46)
- **TDaugther**: si fallas el arma → MUERTE instantánea
- **Arma letal**: Aguja (de R15, Sastrería)
- **Al morir**: Aparece Cáliz con inscripción (segunda mitad del manuscrito)
- **Comando**: `matar hija del hechicero con aguja`

### Puzzle 15: Hechicero (R55)
- **Troll**: quiere Marmidosa
- **Al recibirla**: "No soy tu enemigo. Rompe la carta que te dejó en la Torre de Cristal y ocurrirá un milagro"
- **NO debes matarlo** para ganar (si lo matas sin secuencia, desaparece)

---

## PARTE II: Ruta Crítica

```
FASE 1: INICIO Y EXPLORACION
  1. R1 → Puerta → R2 (Pasillo)
  2. R6: tomar Daga, Botella vino, Hacha
  3. R2: matar Grifo con Daga → "Aura!"
  4. R2: abrir Puerta Azul respondiendo Aura → R4
  5. R4: tomar Pañuelo, Carta (pista: Torre Cristal)
  6. R7 (Cocina): Pañuelo necesario (DangerLink). Tomar Receta, Muslo, Pescado
  7. R5 (Casa muñecas): Puerta baúl diciendo MIAU → R10
  8. R10: tomar Piedra verde, dar Pescado a Gato → pista 2da muralla

FASE 2: TERRAZAS Y RIO
  9. R2 → Puerta de oro → R8 (Terrazas): Reloj arena, Silla
 10. R8 → Escalera → R11 (Orilla 1): Caronte (dar Reloj arena VOLTEADO)
 11. R11 → Río Negro → R12 (Orilla 2)
 12. R12: romper Árbol marfil con Hacha → Maza
 13. R12: romper Muralla con Maza → Avenida hierro → R13

FASE 3: JARDINES, TESOROS, VELAS
 14. R13: dar Hacha a Jardinero → pista anillos
 15. R13 → Puerta roja → R18 (Velas): Dragón
 16. R18: dar Daga a Dragón → "Omicuos Ihanti"
 17. R18 → Escalera → R19 (Inmortal): Guard, matar con Arco
 18. R13 → Puerta amarilla diciendo Omicuos Ihanti → R17 (Tesoros)
 19. R17: tomar Rosa diamante, Anillo oro, Arpa, Bolsa
 20. R13 → Puerta blanca → R20 (Juguetes): Saltador, Sonajero, Talismán Nieve

FASE 4: RUINAS, OGRO, SUBTERRANEOS
 21. R20 → Puerta piedra → R21 (Ruinas)
 22. R21 → Desierto → R34 (Oasis): Cubo agua, dar Bolsa a Pordiosero
 23. R21 → Puerta hierro → R22 → Puerta gris → R24 (Patio)
 24. R24 → Puerta azul → R23 (Pintor): Lienzo, Grabado
 25. R24 → Puerta verde → R25 (Juglar): Cuerda, dar Arpa a Juglar
 26. R24 → Puerta negra → R26 (Ogro): matar con Cubo de agua
 27. R21 → Escalera → R27 (Subterráneos): tomar Antorcha
 28. R27 → Túnel (DangerLink, Escudo Aquiles) → R28 (Catacumbas)
 29. R28: tomar Esqueleto Murciélago

FASE 5: CATARATAS, LAGO, MARMIDOSA
 30. R28 → Pasadizo → R29 (Cataratas): Anillo plata
 31. R29 → Catarata → R31 (Lago): Doncella Lago (dar Talismán Nieve)
 32. R31 → Grieta (Talismán Nieve) → R32 (Cueva): ¡Marmidosa!
 33. R31 → Sendero dorado (SIN Marmidosa) → R33 (Orilla)

FASE 6: DESIERTO, VALLE, MONTANA
 34. R33 → Camino → R36 (Desierto): tomar Escudo Aquiles
 35. R36: Muralla (Piedra verde) → Avenida flores → R37 (Valle)
 36. R37: dar Botella vino a Camello → "KA"
 37. R37 → Montañas → R38 (Pico Negro)
 38. R38 → Puerta Madera → R39 (Monje): dar Rosario → pista Saltador
 39. R38 → Precipicio (Saltador) → R40 (Ciudad Abandonada)
 40. R40: romper Estatua Cristal con Corta-cristales → Horante

FASE 7: SABIO, CAMPO, TORRE CRISTAL
 41. R40 → Puerta Hierro → R41 (Sabio): Cinta Moebius, Péndulo
 42. R41: dar Esqueleto Murciélago a Sabio
 43. R40 → Escalera → R37 → Valle → R38
 44. R38 → Ladera → R42 (Campo): Tenazas, dar semillas a Labrador
 45. R42 → Río (Cuerda) → R43 (Torre Cristal)
 46. R43 → Escalera Caracol → R44 (Torre arriba)
 47. R44: romper Esfera con Marmidosa → Tablilla Madera
 48. R44 → Puerta Cristal respondiendo Aura Srka → R45
 49. R45: tomar Espejo roto

FASE 8: HIJA DEL HECHICERO
 50. R45: romper Carta → Puerta Secreta (DangerLink Lienzo) → R46
 51. R46: matar Hija del Hechicero con Aguja → aparece Cáliz

FASE 9: CALABOZOS, PRUEBA, PIRAMIDE
 52. R43 → Puerta Hierro → R47 (Calabozos)
 53. R47: matar Carcelero con Marmidosa → "Grifo"
 54. R47 → Reja diciendo Grifo → R48 (Celda): dar Receta a Encapuchado
 55. R47 → Puerta Gris → R49 (Antesala Prueba): tomar Arco
 56. R49: dejar Anillo oro, Anillo plata, Anillo bronce
 57. R49 → Puerta Verde (sin Anillo oro) → R50
 58. R50 → Puerta Azul (sin Anillo plata) → R51
 59. R51 → Puerta Blanca (sin Anillo bronce) → R52
 60. R52 → Puerta triangular (Cinta Moebius) → R53 (Límites)
 61. R53: dar Sombrero a Guardián
 62. R53 → Puente (Grabado) → R54 (Pirámide)
 63. R54: romper Columna Hielo con Antorcha → Puerta Roble
 64. R54 → Puerta Roble respondiendo Yo → R55 (Hechicero)
 65. R55: dar Marmidosa a Hechicero → pista final

FASE 10: RITUAL FINAL (colocar objetos)
 66. dejar Antorcha en R1
 67. dejar Péndulo en R3
 68. dejar Espejo en R4
 69. dejar Bote en R12
 70. dejar Rosa diamante en R31
 71. dejar Escudo de Aquiles en R40
 72. dejar Cinta de Moebius en R43
 73. matar Monstruo (R9) con cualquier arma
 74. matar Hija del Hechicero (R46) con Aguja (ya hecho en paso 51)

 → ¡VICTORIA!
```

---

## Tabla de Intercambios (Trolls y sus objetos)

### Parte I

| Troll | Habitación | Quiere | Da (al recibir) |
|-------|-----------|--------|-----------------|
| Llamador de bronce | R1 | Cigarro (R15) | Pista (decodificada key[1]) |
| Trebol | R2 (oculto en Monolito) | Vaso de agua (R6) | Pista (decodificada key[5]) |
| Estatua de Atenea | R4 | Lanza (R11) | Pista (decodificada key[8]) |
| Estatua de Hermes | R4 | Paraguas (R16) | Pista (decodificada key[10]) |
| Bruja | R8 | Escoba (R3) | Pista (decodificada key[17]) |
| Homúnculo | R10 | Poción para crecer (R8) | Pista (decodificada key[20]) |
| Troll | R12 | Polvo mágico (R8) | Pista (decodificada key[22]) |
| Doncella | R14 | Rosa (R12) | Pista (decodificada key[25]) |
| Esqueleto | R16 | Taza de café (R15) | Pista (decodificada key[29]) |
| Ratón | R23 | Piedra filosofal (R10) | Pista (decodificada key[41]) |
| Araña | R27 | Hilo de Ariadna (R3) | "Busca al Minotauro y mátalo con la espada" |
| Crunch | R28 | Pastel de cerezas (R1) | "El 12 te guiará en el Laberinto" |
| Dédalo | R28 | Vendajes (R9) | "Solo el hierro te protegerá contra las flores" |
| Bailarina | R25 | Máquina del tiempo (R10) | Pista (decodificada key[47]) |

### Parte II

| Troll | Habitación | Quiere | Da (al recibir) |
|-------|-----------|--------|-----------------|
| Gato | R10 | Pescado (R7) | "Piedra verde rompe 2da muralla" |
| Monstruo | R9 | Muslo de carnero (R7) | Pista sobre Marmidosa y Hechicero |
| Caronte | R11 | Reloj de arena (R8) VOLTEADO | "Dentro del blanco está la llave" |
| Jardinero | R13 | Hacha (R6) | Pista sobre anillos |
| Dragón | R18 | Daga (R6) | "Omicuos Ihanti" |
| Dinosaurio | R14 | Sonajero (R20) | "Maúllale al gato" |
| Pordiosero | R34 | Bolsa (R17) | "Si el Ogro se baña, se muere" |
| Obispo | R35 | Silla (R8) | "Talismán de Nieve para Marmidosa" |
| Camello | R37 | Botella de vino (R6) | "KA" al final del nombre |
| Monje | R39 | Rosario (R35) | "Lleva algo que amortigue" (Saltador) |
| Horante | R40 | Muñeco diabólico (R15) | "Busca las dos mitades del Manuscrito" |
| Sabio | R41 | Esqueleto Murciélago (R28) | Pista sobre Moebius |
| Labrador | R42 | Bolsa de semillas (R37) | Pista filosófica |
| Encapuchado | R48 | Receta (R7) | "8 letras, A(3), R(2)" |
| Guardián | R53 | Sombrero (R16) | "Héroe mata serpiente con aguja" |
| Hechicero | R55 | Marmidosa (R32) | "No soy tu enemigo. Rompe la carta" |
| Doncella del Lago | R31 | Talismán de Nieve (R20) | "Manuscritos en Torre Cristal" |

---

## Tabla de Enemigos (Guards) y Armas Letales

### Parte I

| Guard | Habitación | Arma Letal | Bloquea |
|-------|-----------|------------|---------|
| Cíclope | R6 | Maza | Contraseña Puerta gigante |
| Arpía | R15 | ¿Daga? | Paso en Sala infusiones |
| Lobo | R24 | Látigo | Puerta de cristal |
| Minotauro | R29 | Espada | Antorchas |
| Centro de los pulmones | R19 | Maza | Victoria |
| Centro del estomago | R20 | Lanza | Victoria |
| Centro del corazón | R21 | Arco | Victoria |
| Centro del cerebro | R22 | Antorcha | Victoria |

### Parte II

| Guard | Habitación | Arma Letal | Bloquea |
|-------|-----------|------------|---------|
| Grifo | R2 | Daga | Revela nombre "Aura" |
| Inmortal | R19 | Arco | Pista 3ra barrera |
| Ogro | R26 | Cubo de agua | Pista Marmidosa |
| Carcelero | R47 | Marmidosa | Password "Grifo" |
| Hija del Hechicero | R46 | Aguja (obligatorio o MUERTE) | Victoria (y revela Cáliz) |
