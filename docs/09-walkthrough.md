# Guía Completa (Walkthrough) — Fortaleza Partes I y II

Secuencia exacta de comandos para ganar cada parte del juego.
Los comandos están en español, coincidiendo con el parser del juego.
Los nombres de objetos y personajes preservan el español original del código fuente.

---

# PARTE I: La Fortaleza (33 habitaciones + laberinto)

## Fase 1: Exterior y Entrada

### Paso 1: Examinar el exterior
```
mirar
```

Estás en "el exterior de la fortaleza". Hay: Roble, Maza, Pastel de cerezas, Llamador de bronce, Puerta principal, Túnel, Pared solitaria.

### Paso 2: Recoger objetos útiles
```
tomar maza
tomar pastel de cerezas
```

La Maza pesa 39 (pesada pero necesaria). El Pastel de cerezas es para Crunch en el laberinto.

### Paso 3: Examinar el Roble (pista contraseña)
```
ver roble
```

Dice: "Las palabras mágicas para abrir la puerta son obvias." La contraseña está codificada en el juego pero se obtiene observando el Roble y deduciendo. La frase sugiere que la contraseña es algo obvio como "abracadabra" o "ábrete sésamo".

### Paso 4 (OPCIONAL): Interrogar al Llamador de bronce
```
interrogar llamador de bronce
```

Pide un Cigarro. Lo encontraremos más adelante.

### Paso 5: Abrir la Puerta Principal
```
abrir puerta principal diciendo [contraseña]
ir puerta principal
```

Nota: La contraseña exacta está decodificada en key[2]. Si no la sabes, prueba variantes de "ábrete" o palabras mágicas comunes.

---

## Fase 2: Salón de Recepciones y Salas Iniciales

### Paso 6: Examinar el Salón (R2)
```
mirar
```

Hay: Monolito de mármol, Puerta principal, Puerta negra, Retrato.

### Paso 7: Romper el Monolito
```
romper monolito de marmol con maza
```

Revela un Trebol (Troll) que quiere Vaso de agua.

### Paso 8: Ir a la Sala de juegos (R3)
```
ir puerta negra
mirar
tomar escoba
tomar hilo de ariadna
tomar inscripcion
```

La Escoba es para la Bruja. El Hilo de Ariadna para la Araña en el puente.

### Paso 9: Ir al Patio interior (R4)
```
ir puerta azul
mirar
tomar balanza
```

Hay Estatua de Atenea (quiere Lanza) y Estatua de Hermes (quiere Paraguas).

### Paso 10: Abrir la Escalera (al Cuarto de espejos)
Regresar a R3:
```
ir puerta azul
abrir escalera respondiendo treinta y nueve
ir escalera
```

### Paso 11: Cuarto de espejos (R5)
```
mirar
tomar hueso de gato
romper espejo opaco con maza
```

Nota: El objeto para romper el Espejo opaco puede variar. La Maza funciona como intento genérico.

### Paso 12: Puerta oculta → Alcoba de la doncella (R14)
```
ir puerta oculta
mirar
tomar cuadro
tomar corazon de unicornio
```

---

## Fase 3: Biblioteca y Pasillo

### Paso 13: Volver a R3, ir a R4, luego a R6 (Biblioteca)
Desde R14: `ir puerta azul` (→R13 Jardín), `ir puerta azul` (→R4), `ir puerta verde` (→R6)

O volver por donde viniste: `ir puerta oculta` (→R5), `ir escalera` (→R3), `ir puerta azul` (→R4), `ir puerta verde` (→R6)

```
mirar
tomar vaso de agua
tomar candelabro
```

### Paso 14: Matar al Cíclope
```
matar ciclope con maza
```

El Cíclope muere y revela la contraseña de la Puerta gigante.

### Paso 15: Abrir Puerta gigante → Pasillo (R7)
```
abrir puerta diciendo [contraseña del ciclope]
ir puerta
mirar
tomar antorcha
```

### Paso 16: Ir al Laboratorio (R10)
```
abrir puerta prohibida diciendo [contraseña]
ir puerta prohibida
mirar
tomar piedra filosofal
tomar maquina del tiempo
```

### Paso 17: Dar Poción al Homúnculo
```
dar pocion para crecer a homunculo
interrogar homunculo
```

Necesitas la Poción para crecer de la Alcoba de la bruja (R8).

### Paso 18: Ir a la Alcoba de la bruja (R8)
```
ir puerta vieja
mirar
tomar polvo magico
tomar pocion para crecer
dar escoba a bruja
interrogar bruja
```

### Paso 19: Sala de infusiones (R15)
```
ir puerta gris
mirar
tomar taza de cafe
tomar cigarro
matar arpia con daga
```

### Paso 20: Calabozos (R16)
Desde R15: `ir puerta amarilla` → R13 (Jardín), `ir puerta de hierro` → R16
```
mirar
tomar paraguas
tomar talisman de aire
dar taza de cafe a esqueleto
interrogar esqueleto
```

---

## Fase 4: Sala de Armas y Jardín

### Paso 21: Volver al Pasillo, ir al Cuarto del guerrero (R9)
Desde R16: `ir puerta de hierro` → R13, `ir puerta azul` → R4, `ir puerta azul` → R3, `ir puerta negra` → R2, `ir puerta negra` → R3, `ir puerta azul` → R4, `ir puerta verde` → R6, `ir puerta` → R7, `ir puerta roja` → R9

O más directo: desde R7 ir al Jardín y luego rodear.

```
mirar
tomar vendajes
tomar grabado
```

### Paso 22: Romper la Cama → Sala de armas (R11)
Necesitas el Hacha de R23 (Almacén). Ve primero al Jardín:
Desde R9: `ir puerta roja` → R7, `ir puerta gris` → R15, `ir puerta amarilla` → R13

```
ir puerta de madera
mirar
tomar hacha
```

Desde R23: `ir puerta de madera` → R13, `ir puerta azul` → R4, `ir puerta azul` → R3, ve a R2, R3, R4, R6, R7, R9.

```
romper cama con hacha
ir puerta
```

### Paso 23: Recoger TODAS las armas (R11)
```
tomar espada
tomar lanza
tomar arco
tomar daga
tomar latigo
```

---

## Fase 5: Baños y Jardín

### Paso 24: Ir a los Baños de la Bestia (R12)
Desde R11: `ir puerta` → R9, `ir puerta roja` → R7, `ir puerta gris` → R15, `ir puerta amarilla` → R13, `ir puerta verde` → R12

```
mirar
tomar rosa
tomar espejo
tomar inscripcion
```

### Paso 25: Dar objetos a personajes del Jardín
```
ir puerta verde
dar rosa a doncella
interrogar doncella
```

(La Doncella está en R14, ve desde R13: `ir puerta azul`)

### Paso 26: Dar Cigarro al Llamador y Vaso al Trebol
Regresa al exterior: R13 → R4 → R3 → R2 → R1

```
dar cigarro a llamador de bronce
interrogar llamador de bronce
```

R2: Rompe el Monolito con Maza si no lo has hecho, luego:
```
dar vaso de agua a trebol
interrogar trebol
```

---

## Fase 6: Páramo y Salón de Cristal

### Paso 27: Volver al Almacén (R23) y al Páramo (R24)
```
ir puerta verde
mirar
matar lobo con latigo
```

### Paso 28: Abrir Puerta de cristal (R24 → R25)
```
abrir puerta de cristal diciendo [contraseña]
ir puerta de cristal
mirar
```

### Paso 29: Dar Máquina del tiempo a la Bailarina
```
dar maquina del tiempo a bailarina
interrogar bailarina
```

### Paso 30: Abrir Puerta triangular → Boca de la Bestia
```
abrir puerta triangular respondiendo crunch
ir puerta triangular
```

---

## Fase 7: Interior de la Bestia

### Paso 31: Entrar al Interior (R18)
```
ir garganta
mirar
```

### Paso 32: Matar los Centros

#### Pulmones (R19) — necesita Talismán de aire
```
ir traquea
matar centro de los pulmones con maza
ir traquea
```

#### Estómago (R20) — necesita Paraguas
```
ir esofago
matar centro del estomago con lanza
ir esofago
```

#### Corazón (R21) — necesita Corazón de unicornio
```
ir arteria principal
matar centro del corazon con arco
ir arteria principal
```

---

## Fase 8: Puente y Laberinto

### Paso 33: Ir al Puente (R27)
Regresa al exterior (R1) vía: R18 → R17 → R25 → R24 → [pozo a R1? o ruta inversa]

O mejor: desde R1, romper Pared solitaria:
```
romper pared solitaria con [objeto]
ir puerta secreta
```

### Paso 34: Puente (R27)
```
mirar
tomar martillo
dar hilo de ariadna a araña
interrogar araña
romper estatua de satanas con cuadro
ir puerta oculta
```

### Paso 35: Antesala del Laberinto (R28)
```
mirar
dar pastel de cerezas a crunch
interrogar crunch
dar vendajes a dedalo
interrogar dedalo
```

### Paso 36: Navegar el Laberinto al Minotauro (R29)

```
ir puerta verde      {R28→R31}
ir puerta 1          {R31→R32}
ir puerta 2          {R32→R33}
ir puerta 3          {R33→R34}
ir puerta 1          {R34→R35}
ir puerta 2          {R35→R36}
ir puerta 3          {R36→R37}
ir puerta 1          {R37→R29, Minotauro!}
```

### Paso 37: Matar al Minotauro
```
matar minotauro con espada
```

El Minotauro confiesa: "Coge la antorcha del número divino y rompe la columna de cristal."

### Paso 38: Recoger las antorchas
```
tomar antorcha 1
tomar antorcha 2
tomar antorcha 3
tomar antorcha 4
tomar antorcha 5
tomar antorcha 6
tomar antorcha 7
```

### Paso 39: Salir del Laberinto
```
ir puerta         {R29→R47}
ir puerta 3       {R47→R48}
ir puerta 2       {R48→R49}
ir salida         {R49→R28}
```

---

## Fase 9: Jardín Falso y Cerebro

### Paso 40: Romper Columna de Cristal (R28)
```
romper columna de cristal con antorcha 3
romper puerta de madera con martillo
ir puerta negra
```

### Paso 41: Jardín falso (R50)
```
mirar
```

### Paso 42: Abrir Puerta de hierro → Salón de los Elegidos
```
abrir puerta de hierro respondiendo seis
ir puerta de hierro
```

### Paso 43: Abrir Puerta dorada → Cerebro
```
abrir puerta dorada respondiendo cdfghjklmnopqruvwxyz
ir puerta dorada
```

### Paso 44: Matar al Centro del cerebro (R22)
```
matar centro del cerebro con antorcha
```

---

## Fase 10: Matar al Troll → Victoria

### Paso 45: Regresar a los Baños (R12)
Regresa al Jardín verdadero (R13) luego a R12.

### Paso 46: Matar al Troll
```
matar troll
```

---

## ¡VICTORIA!

Si todos los Centros están muertos y el Troll también, el juego evalúa `Goal() = true`.

---

# PARTE II: La Fortaleza (55 habitaciones)

## Fase 1: Inicio, Pasillo, Preparación

### Paso 1: Salir de la habitación
```
mirar
ir puerta
```

### Paso 2: Explorar el Pasillo (R2)
```
mirar
```

Ves: Puerta (a R1), Puerta de espinos, Puerta de metal, Puerta Negra, Puerta Azul, Puerta de oro, y un Grifo.

### Paso 3: Ir al cuarto del Leñador (R6)
```
ir puerta de espinos
mirar
tomar daga
tomar botella de vino
tomar hacha
```

### Paso 4: Volver al Pasillo y matar al Grifo
```
ir puerta de espinos
matar grifo con daga
```

El Grifo muere gritando "¡Aura!" → este es el nombre de la hija del Hechicero.

### Paso 5: Entrar al cuarto de la hija (R4)
```
abrir puerta azul respondiendo aura
ir puerta azul
mirar
tomar panuelo
tomar carta
ver carta
```

La Carta dice que la hija está encerrada en la Torre de Cristal, más allá del segundo río.

### Paso 6: Ir a la Cocina (R7) — ¡NECESITAS el Pañuelo!
```
ir puerta azul
ir puerta de metal
mirar
tomar receta
tomar muslo de carnero
tomar pescado
```

**IMPORTANTE**: Nunca dejes el Pañuelo en esta habitación. Si lo haces, mueres al evaluar Goal().

### Paso 7: Casa de muñecas (R5) → Baúl (R10)
```
ir puerta azul
ir agujero
mirar
abrir puerta del baul diciendo miau
ir puerta del baul
mirar
tomar piedra verde
dar pescado a gato
interrogar gato
```

El Gato dice: "La piedra verde te servirá para romper la segunda muralla."

### Paso 8: Volver a R5, Pasadizo secreto → Jardines (más tarde)
Por ahora volvemos:
```
ir puerta del baul
ir agujero
```

---

## Fase 2: Terrazas, Río Negro y Jardines

### Paso 9: Ir a las Terrazas (R8)
```
ir puerta azul
ir puerta de oro
mirar
tomar reloj de arena
tomar silla
```

### Paso 10: Bajar al calabozo del Monstruo (R9) por ruta alternativa
La Escalera de caracol desde R8 va a R11 (Orilla 1), no a R9 directamente. Desde R11 se puede subir a R9.

```
ir escalera de caracol
mirar
```

### Paso 11: Dar Muslo al Monstruo
```
ir escalera de caracol
mirar
dar muslo de carnero a monstruo
interrogar monstruo
```

El Monstruo habla del Hechicero y recomienda buscar la "espada Marmidosa".

### Paso 12: Volver a la Orilla 1 (R11)
```
ir escalera de caracol
```

### Paso 13: Dar Reloj a Caronte (¡VOLTEADO!)
Caronte pide el Reloj de arena pero VOLTEADO. Dale el reloj:
```
dar reloj de arena a caronte
interrogar caronte
```

Dice: "Dentro del blanco está la llave de la muralla."

### Paso 14: Cruzar el Río Negro
```
ir rio negro
mirar
```

### Paso 15: Romper Árbol de marfil → obtener Maza
```
romper arbol de marfil con hacha
tomar maza
```

### Paso 16: Romper Muralla → Avenida de hierro
```
romper muralla con maza
ir avenida de hierro
```

### Paso 17: Jardines del Hechicero (R13)
```
mirar
tomar piedra
dar hacha a jardinero
interrogar jardinero
```

El Jardinero advierte sobre elegir bien entre los anillos.

---

## Fase 3: Tesoros, Velas, Inmortal, Juguetes

### Paso 18: Ir al Salón de las velas (R18)
```
ir puerta roja
mirar
dar daga a dragon
interrogar dragon
```

El Dragón revela: "Las palabras mágicas para entrar en el cuarto del tesoro son: Omicuos Ihanti."

### Paso 19: Bajar al cuarto del Inmortal (R19)
```
ir escalera
mirar
```

Por ahora no tenemos Arco para matarlo. Volvemos.

```
ir escalera
```

### Paso 20: Ir a los Tesoros (R17)
```
ir puerta roja
abrir puerta amarilla diciendo omicuos ihanti
ir puerta amarilla
mirar
tomar rosa diamante
tomar anillo de oro
tomar arpa
tomar bolsa
```

### Paso 21: Cuarto de juguetes (R20)
```
ir puerta amarilla
ir puerta roja
ir puerta blanca
mirar
tomar saltador
tomar sonajero
tomar talisman de nieve
```

### Paso 22: Ir al Comedor (R14) — Huevo → Dinosaurio
```
ir puerta blanca
ir puerta roja
ir puerta de madera
mirar
romper huevo con piedra
dar sonajero a dinosaurio
interrogar dinosaurio
```

Dice: "Maúllale al gato."

### Paso 23: Sastrería (R15) y Jardinero (R16)
```
ir puerta de madera
ir puerta de tela
mirar
tomar muneco diabolico
tomar aguja
ir puerta de tela
ir puerta verde
mirar
tomar corta-cristales
tomar sombrero
```

### Paso 24: Usar Corta-cristales en la Ventana de R5
Regresa a R5 (Casa de muñecas):
```
ir puerta verde          {→R13}
ir puerta amarilla (o ruta inversa)
...
```

Desde R2: `ir puerta azul respondiendo aura`, `ir puerta azul`, `ir agujero`

```
romper ventana con corta-cristales
ir pasadizo
```

¡Llegas a R13 por ruta alternativa!

---

## Fase 4: Ruinas, Desierto, Oasis, Ogro

### Paso 25: Ruinas (R21)
```
ir puerta de piedra
mirar
```

### Paso 26: Cruzar el Desierto → Oasis (R34)
```
ir desierto
mirar
tomar cubo de agua
dar bolsa a pordiosero
interrogar pordiosero
```

El Pordiosero: "Si el Ogro se baña, se muere."

### Paso 27: Regresar a las Ruinas
```
ir desierto
```

### Paso 28: Salón de Recepciones (R22) y Patio (R24)
```
ir puerta de hierro
mirar
tomar anillo de bronce
ir puerta gris
mirar
```

### Paso 29: Cuarto del Pintor (R23)
```
ir puerta azul
mirar
tomar lienzo
tomar grabado
```

### Paso 30: Cuarto del Juglar (R25)
```
ir puerta azul
ir puerta verde
mirar
tomar cuerda
dar arpa a juglar
interrogar juglar
```

Dice: "Lleva algo de la fragua de Vulcano al bajar a las Catacumbas."

La "fragua de Vulcano" = fragua de Hefesto = Escudo de Aquiles.

### Paso 31: Matar al Ogro (R26)
```
ir puerta verde
ir puerta negra
mirar
matar ogro con cubo de agua
```

El Ogro: "¡No saldrás del lago con Marmidosa tan fácilmente!"

```
ir puerta negra
```

---

## Fase 5: Subterráneos, Catacumbas, Cataratas, Lago

### Paso 32: Subterráneos (R27)
```
ir puerta verde
ir puerta gris
ir puerta de hierro
ir puerta de piedra
ir escalera
mirar
tomar antorcha
```

### Paso 33: Catacumbas (R28) — ¡necesitas Escudo de Aquiles!
NO tenemos el Escudo todavía. Primero debemos obtenerlo. Ve al Desierto (R36).

El Escudo de Aquiles está en R36 (Desierto), pero para llegar necesitamos pasar por las Catacumbas y el Lago. Hay un ciclo de dependencia:
- Para cruzar los DangerLinks de Catacumbas necesitas Escudo de Aquiles
- El Escudo está en R36
- Para llegar a R36 necesitas pasar por Catacumbas → Cataratas → Lago → Orilla → Desierto

**Solución**: El Pasadizo en R28 NO es DangerLink. Ve por ahí:

```
ir pasadizo
```

### Paso 34: Cataratas (R29)
```
mirar
tomar anillo de plata
```

### Paso 35: Saltar por la Catarata → Lago (R31)
```
ir catarata
mirar
```

### Paso 36: Hablar con la Doncella del Lago
La Doncella está en R31. NO tiene objeto para darle todavía.

```
interrogar doncella del lago
```

Dice algo sobre la Cueva de Cristal.

### Paso 37: Buscar el Talismán de Nieve
El Talismán de Nieve está en R20 (Juguetes). Ya lo tenemos.

### Paso 38: Entrar a la Cueva de Cristal (R32) — necesita Talismán de Nieve
```
ir grieta
mirar
tomar marmidosa
```

### Paso 39: Salir del Lago por Sendero Dorado — DangerLink2 (SIN Marmidosa)
Para cruzar el Sendero dorado, NO debes llevar Marmidosa. Déjala aquí o en otro lado:
```
dejar marmidosa
ir sendero dorado
mirar
```

### Paso 40: Desierto (R36)
```
ir camino
mirar
tomar escudo de aquiles
```

**PRECAUCIÓN**: La inscripción en R36 advierte NO cruzar el Camino con el Talismán de Nieve. Si intentas regresar por el Camino llevando el Talismán, mueres (DangerLink2).

### Paso 41: Romper la 2da Muralla → Valle (R37)
```
romper muralla con piedra verde
ir avenida de las flores
mirar
tomar bolsa de semillas
dar botella de vino a camello
interrogar camello
```

El Camello: "Las dos últimas letras del segundo nombre de la Hija del Hechicero son KA."

---

## Fase 6: Montaña, Ciudad, Sabio

### Paso 42: Subir al Pico Negro (R38)
```
ir montanas
mirar
```

### Paso 43: Choza del Monje (R39)
```
ir puerta de madera
mirar
```

No tenemos Rosario aún. Volvemos después.

```
ir puerta de madera
```

### Paso 44: Bajar al precipicio → Ciudad (R40)
Necesitas Saltador (de R20):
```
ir precipicio
mirar
```

### Paso 45: Ciudad Abandonada (R40)
```
romper estatua de cristal con corta-cristales
dar muneco diabolico a horante
interrogar horante
```

El Horante: "Busca las dos mitades del Manuscrito de los Horantes y descífralo. Luego coloca las marcas para abrir la Fortaleza."

### Paso 46: Choza del Sabio (R41)
```
ir puerta de hierro
mirar
tomar cinta de moebius
tomar pendulo
dar esqueleto de murcielago a sabio
interrogar sabio
```

Habla sobre la cinta de Moebius.

### Paso 47: Regresar al Pico Negro
```
ir puerta de hierro
ir escalera
```

---

## Fase 7: Campo, Torre de Cristal

### Paso 48: Bajar al Campo (R42)
```
ir ladera
mirar
tomar tenazas
dar bolsa de semillas a labrador
interrogar labrador
```

### Paso 49: Cruzar el Río → Torre de Cristal (R43)
Necesitas Cuerda (de R25):
```
ir rio
mirar
```

### Paso 50: Subir la Torre (R44)
```
ir escalera de caracol
mirar
```

### Paso 51: Romper la Esfera → Tablilla de Madera
```
romper esfera con marmidosa
tomar tablilla de madera
ver tablilla de madera
```

Es la primera mitad del manuscrito horante (críptico).

### Paso 52: Abrir Puerta de Cristal → Alcoba de Aura (R45)
Nombre completo: "Aura Srka" (Aura del acertijo + Srka confirmado por "KA" del camello)
```
abrir puerta de cristal respondiendo aura srka
ir puerta de cristal
mirar
tomar espejo
```

### Paso 53: Puerta Secreta → Alcoba Secreta (R46)
```
romper carta
ir puerta secreta
```

---

## Fase 8: La Hija del Hechicero

### Paso 54: Matar a la Hija del Hechicero
**CRÍTICO**: Debes usar Aguja. Cualquier otra arma = MUERTE INSTANTÁNEA.

```
matar hija del hechicero con aguja
```

La Hija muere, confiesa algo, y aparece un Cáliz con inscripción (segunda mitad del manuscrito).

```
tomar caliz
ver caliz
```

---

## Fase 9: Calabozos, La Prueba

### Paso 55: Bajar de la Torre, ir a Calabozos (R47)
```
ir puerta de cristal
ir escalera de caracol
ir puerta de hierro
mirar
```

### Paso 56: Matar al Carcelero
```
matar carcelero con marmidosa
```

Confiesa: "La palabra mágica es el nombre de la primera criatura que viste al salir del cuarto de huéspedes" → Grifo.

### Paso 57: Entrar a la Celda (R48)
```
abrir reja diciendo grifo
ir reja
mirar
dar receta a encapuchado
interrogar encapuchado
```

El Encapuchado: "El nombre de la hija del Hechicero tiene ocho letras, una está repetida tres veces y otra dos."
→ A U R A   S R K A = 8 letras, A = 3 veces, R = 2 veces. Confirmado.

### Paso 58: Ir a la Antesala de la Prueba (R49)
```
ir reja
ir puerta gris
mirar
tomar arco
```

### Paso 59: DEJAR los anillos antes de La Prueba
```
dejar anillo de oro
dejar anillo de plata
dejar anillo de bronce
```

La inscripción lo advierte: "Deja los demás anillos."

### Paso 60: Cruzar La Prueba
```
ir puerta verde
ir puerta azul
ir puerta blanca
ir puerta triangular
```

### Paso 61: Límites de la Fortaleza (R53)
```
mirar
dar sombrero a guardian
interrogar guardian
```

Cuenta la historia del héroe que mata una serpiente con una aguja.

### Paso 62: Cruzar el Puente → Pirámide (R54)
```
ir puente
mirar
```

---

## Fase 10: El Hechicero y el Ritual Final

### Paso 63: Romper Columna de Hielo → Puerta de Roble
```
romper columna de hielo con antorcha
```

### Paso 64: Abrir Puerta de Roble (acertijo)
"¿Quién invirtió el reloj de Caronte?" → Fuiste TÚ (el jugador) quien le dio el reloj a Caronte.

```
abrir puerta de roble respondiendo yo
ir puerta de roble
```

### Paso 65: Habitaciones del Hechicero (R55)
```
mirar
dar marmidosa a hechicero
interrogar hechicero
```

El Hechicero: "No soy tu enemigo. Es mi hija quien ha elaborado este diabólico plan para eliminarnos. Rompe la carta que te dejó en la Torre de Cristal y ocurrirá un milagro."

---

## Fase 11: EL RITUAL FINAL

Ahora debes recorrer la Fortaleza dejando objetos específicos en ubicaciones específicas:

### Paso 66: Dejar Antorcha en R1 (habitación inicial)
Regresa a R1 (usa rutas existentes o el túnel desde R21 a R40 a R21... la ruta más corta es volver por donde viniste).

```
[viajar a R1]
dejar antorcha
```

### Paso 67: Dejar Péndulo en R3 (Salón de Fumar)
```
ir puerta
ir puerta negra
dejar pendulo
```

### Paso 68: Dejar Espejo en R4 (cuarto de la hija)
```
ir puerta negra
abrir puerta azul respondiendo aura
ir puerta azul
dejar espejo
```

### Paso 69: Dejar Bote en R12 (orilla 2 Río Negro)
El Bote está en R11 (orilla 1). Ve a R11, toma el Bote, cruza a R12, déjalo allí.
```
[tomar bote en R11]
[ir a R12]
dejar bote
```

### Paso 70: Dejar Rosa diamante en R31 (fondo del Lago)
Ve al Lago (R31) por la ruta de cataratas:
R28 → R29 → catarata → R31
```
dejar rosa diamante
```

### Paso 71: Dejar Escudo de Aquiles en R40 (Ciudad Abandonada)
```
[viajar a R40]
dejar escudo de aquiles
```

### Paso 72: Dejar Cinta de Moebius en R43 (Torre Cristal exterior)
```
[viajar a R43]
dejar cinta de moebius
```

### Paso 73: Matar al Monstruo (R9)
Si aún no lo has matado (en Paso 11 solo le diste el Muslo, no lo mataste):
```
[ir a R9]
matar monstruo
```

(Paso 54 ya mataste a la Hija del Hechicero)

### PASO FINAL: Verificar victoria

Después de colocar los 7 objetos y matar a los 2 enemigos, el juego evalúa Goal() en cada turno. Si todo está correcto:

**¡VICTORIA!**

---

## Notas Importantes

1. **Peso máximo**: LWeight = 40. Administra tu inventario. Algunos objetos pesan mucho (Bote = 39, Maza = 39).

2. **Dejar objetos**: Usa `dejar todo` para vaciar tu inventario en una habitación central (como R13 Jardines) y recoger solo lo necesario.

3. **DangerLinks**: Siempre verifica qué talismán necesitas antes de cruzar. Si cruzas sin el talismán correcto, ¡MUERTE!

4. **DangerLink2**: Estos son INVERTIDOS. Si LLEVAS el objeto mencionado, mueres. Si NO lo llevas, pasas bien.

5. **Guard vs Troll**: Los Guards necesitan un arma específica. Los Trolls aceptan regalos y mueren con cualquier arma.

6. **Pañuelo (Parte II)**: NUNCA lo dejes en la Cocina (R7). Si está allí cuando se evalúa Goal(), mueres instantáneamente.

7. **Hija del Hechicero**: Si intentas matarla sin la Aguja, MUERTE INSTANTÁNEA. Es el único enemigo con esta mecánica.

8. **Comandos abreviados**: El parser acepta `coger` o `tomar`, `matar` o `asesinar`, `dar` o `regalar`, `ir` o `cruzar` o `atravesar`.
