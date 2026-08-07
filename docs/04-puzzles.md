# 04 — Puzles y Acertijos

## Mecánicas de Puzle

El motor `CASTLES.PAS` implementa varios tipos de interacciones:

| Tipo | Mecánica | Archivo:línea |
|------|----------|---------------|
| **RiddleLink** | Puerta con acertijo; hay que responder correctamente para abrir | `CASTLES.PAS:1288-1327` |
| **Hidden** | Objeto rompible que esconde otro objeto; requiere un ítem específico | `CASTLES.PAS:922-946` |
| **Guard** | Enemigo que solo muere con un arma específica (`lethalweap`) | `CASTLES.PAS:964-974` |
| **Troll** | NPC que da información al recibir el objeto correcto (`likeness`) | `CASTLES.PAS:854-859` |
| **DangerLink** | Pasaje que requiere un ítem específico; sin él, el jugador muere | `CASTLES.PAS:890-902` |
| **DangerLink2** | Pasaje que NO debe cruzarse con cierto ítem; si se lleva, el jugador muere | `CASTLES.PAS:906-918` |
| **Linking** | Puerta con contraseña (keyword) | `CASTLES.PAS:319-323` |
| **TDaugther** | Guard especial (Parte II): si se ataca con arma incorrecta, el jugador muere | `CASTLES.PAS:1329-1344` |

---

## Parte I — Puzles

### 1. Puerta principal (Exterior → Salón)
- **Tipo**: Linking (contraseña)
- **Ubicación**: Habitación 1 (Exterior)
- **Solución**: La contraseña está codificada en `decodeLine(key[2])`. La pista está en el Roble: *"Las palabras mágicas para abrir la puerta son obvias."*

### 2. Llamador de bronce (Exterior)
- **Tipo**: Troll
- **Quiere**: Cigarro
- **Ubicación del objeto**: Sala de infusiones (15)
- **Diálogo**: "¿Me puede regalar un cigarro?"
- **Recompensa**: Información al estar feliz (`decodeLine(key[1])`)

### 3. Pared solitaria → Puerta secreta (Exterior)
- **Tipo**: Hidden → DangerLink
- **Romper con**: Contraseña decodificada (`decodeLine(key[3])`)
- **Revela**: Puerta secreta (DangerLink) que conduce al Puente (27)
- **Protección necesaria**: Antorcha

### 4. Monolito de mármol → Trebol (Salón)
- **Tipo**: Hidden → Troll
- **Romper con**: Contraseña decodificada (`decodeLine(key[4])`)
- **Revela**: Trebol (Troll) que quiere Vaso de agua
- **Recompensa**: Información (`decodeLine(key[5])`)

### 5. Escalera (Sala de juegos → Cuarto de espejos)
- **Tipo**: RiddleLink
- **Acertijo**: "¿Cuántos peldaños tiene la escalera?"
- **Respuesta**: `treinta y nueve` (39) — `decodeLine(key[6])`
- **Conduce a**: Cuarto de espejos (5)

### 6. Espejo opaco → Puerta oculta (Cuarto de espejos)
- **Tipo**: Hidden → Linking
- **Romper con**: Contraseña decodificada (`decodeLine(key[11])`)
- **Revela**: Puerta oculta → Alcoba de la doncella (14)

### 7. Estatua de Atenea (Patio interior)
- **Tipo**: Troll
- **Quiere**: Objeto decodificado (`decodeLine(key[7])`)
- **Diálogo infeliz**: "¡Sal de mi presencia, estúpido mortal!"
- **Recompensa**: `decodeLine(key[8])`

### 8. Estatua de Hermes (Patio interior)
- **Tipo**: Troll
- **Quiere**: Objeto decodificado (`decodeLine(key[9])`)
- **Diálogo infeliz**: "La humedad me destruye."
- **Recompensa**: `decodeLine(key[10])`

### 9. Puerta para gigantes (Biblioteca → Pasillo)
- **Tipo**: Linking
- **Contraseña**: `decodeLine(key[14])`
- **Guardián**: Cíclope (Guard)

### 10. Cíclope (Biblioteca)
- **Tipo**: Guard
- **Arma letal**: `decodeLine(key[13])`
- **Confesión**: `decodeLine(key[12])`

### 11. Puerta prohibida (Pasillo → Laboratorio)
- **Tipo**: Linking
- **Contraseña**: `decodeLine(key[15])`

### 12. Bruja (Alcoba de la bruja)
- **Tipo**: Troll
- **Quiere**: Escoba
- **Ubicación**: Sala de juegos (3)
- **Diálogo**: "Tráeme mi escoba y te daré un consejo."
- **Recompensa**: `decodeLine(key[17])`

### 13. Escaparate (Alcoba bruja → Alcoba doncella)
- **Tipo**: DangerLink
- **Protección necesaria**: Candelabro
- **Sin él**: Muerte (`decodeLine(key[16])`)

### 14. Cama → Puerta al suelo (Cuarto del guerrero)
- **Tipo**: Hidden → Linking
- **Romper con**: `decodeLine(key[18])`
- **Revela**: Puerta → Sala de armas (11)

### 15. Homúnculo (Laboratorio)
- **Tipo**: Troll
- **Quiere**: Poción para crecer
- **Ubicación**: Alcoba de la bruja (8)
- **Diálogo**: "¡Quiero crecer!"
- **Recompensa**: `decodeLine(key[20])`

### 16. Troll de los Baños
- **Tipo**: Troll
- **Quiere**: Polvo mágico
- **Ubicación**: Alcoba de la bruja (8)
- **Diálogo**: "No me mates, por favor. Haz que nadie pueda ver mi fealdad."
- **Recompensa**: `decodeLine(key[22])`
- **Nota**: Debe ser eliminado para ganar el juego (parte de `Fort.Goal`)

### 17. Doncella (Alcoba de la doncella)
- **Tipo**: Troll
- **Quiere**: Objeto decodificado (`decodeLine(key[24])`)
- **Diálogo**: "¿Qué brusco! Un caballero debe dirigirse a una dama de otra forma."
- **Recompensa**: `decodeLine(key[25])`

### 18. Arpía (Sala de infusiones)
- **Tipo**: Guard
- **Confesión**: `decodeLine(key[26])`
- **Arma letal**: `decodeLine(key[27])`

### 19. Esqueleto (Calabozos)
- **Tipo**: Troll
- **Quiere**: Taza de café
- **Ubicación**: Sala de infusiones (15)
- **Diálogo**: "Dame algo para calentarme la barriga, por favor."
- **Recompensa**: `decodeLine(key[29])`

### 20. Tráquea (Interior → Pulmones)
- **Tipo**: DangerLink
- **Protección necesaria**: `decodeLine(key[30])` = Talismán de aire

### 21. Esófago (Interior → Estómago)
- **Tipo**: DangerLink
- **Protección necesaria**: `decodeLine(key[31])` = Talismán de aire

### 22. Arteria principal (Interior → Corazón)
- **Tipo**: DangerLink
- **Protección necesaria**: Corazón de unicornio

### 23. Centro de los pulmones (Pulmones)
- **Tipo**: Guard
- **Confesión**: `decodeLine(key[35])`
- **Arma letal**: `decodeLine(key[32])`

### 24. Centro del estómago
- **Tipo**: Guard
- **Confesión**: "¡Usted ha matado al centro del estómago!" (texto directo)
- **Arma letal**: `decodeLine(key[33])`

### 25. Centro del corazón
- **Tipo**: Guard
- **Confesión**: `decodeLine(key[37])`
- **Arma letal**: `decodeLine(key[34])`

### 26. Centro del cerebro (Cerebro)
- **Tipo**: Guard
- **Pista**: "¡Usa la antorcha!"
- **Confesión**: "XVBCZXV XBVCZX BVZXC!!!!!"
- **Arma letal**: `decodeLine(key[38])`

### 27. Ratón (Almacenes)
- **Tipo**: Troll
- **Quiere**: Objeto decodificado (`decodeLine(key[40])`)
- **Diálogo**: "No tengo tiempo para atenderte. Llevo medio siglo buscando la quinta esencia."
- **Recompensa**: `decodeLine(key[41])`

### 28. Lobo (Páramo)
- **Tipo**: Guard
- **Bloquea**: Puerta de cristal (hacia Salón de cristal)
- **Arma letal**: Látigo
- **Confesión**: `decodeLine(key[44])`

### 29. Puerta de cristal (Páramo → Salón de cristal)
- **Tipo**: Linking
- **Contraseña**: `decodeLine(key[42])`

### 30. Túnel peligroso (Páramo)
- **Tipo**: DangerLink
- **Protección necesaria**: `decodeLine(key[43])`
- **Destino**: El mismo Páramo (24) — ¿trampa?

### 31. Puerta triangular (Salón de cristal → Boca)
- **Tipo**: RiddleLink
- **Acertijo**: "¿Cuál es el nombre del duende?"
- **Respuesta**: `decodeLine(key[23])`
- **Conduce a**: Boca de la Bestia (17)

### 32. Bailarina (Salón de cristal)
- **Tipo**: Troll
- **Quiere**: Máquina del tiempo
- **Ubicación**: Laboratorio (10)
- **Diálogo**: "Quiero ser joven para siempre."
- **Recompensa**: `decodeLine(key[47])`

### 33. Araña (Puente)
- **Tipo**: Troll
- **Quiere**: Hilo de Ariadna
- **Ubicación**: Sala de juegos (3)
- **Diálogo**: "¡Pssssssss!"
- **Recompensa**: "Busca al Minotauro y mátalo con la espada."

### 34. Puerta secreta (Puente → Exterior)
- **Tipo**: DangerLink
- **Protección necesaria**: Antorcha

### 35. Estatua de Satanás → Puerta oculta (Puente → Antesala)
- **Tipo**: Hidden → Linking
- **Romper con**: Cuadro
- **Revela**: Puerta oculta → Antesala del Laberinto (28)

### 36. Puerta con espada (Puente → Antesala)
- **Tipo**: DangerLink2
- **NO debe llevar**: Espada
- **Si la lleva**: Muerte

### 37. Crunch (Antesala del Laberinto)
- **Tipo**: Troll
- **Quiere**: Pastel de cerezas
- **Ubicación**: Exterior (1)
- **Diálogo**: "¡Qué hambre!"
- **Recompensa**: "El 12 te guiará en el Laberinto. Luego solo debes dar un paso."
- **Significado**: En el laberinto, tomar la puerta 1 dos veces (1→1 = 12 en dígitos contiguos) = secuencia de escape

### 38. Columna de Cristal → Puerta negra (Antesala → Jardín falso)
- **Tipo**: Hidden → Hidden → Linking
- **Primer paso**: Romper Columna con "Antorcha 3" (de la cueva del Minotauro)
- **Segundo paso**: Romper Puerta de madera revelada con Martillo
- **Revela**: Puerta negra → Jardín falso (50)

### 39. Dédalo (Antesala)
- **Tipo**: Troll
- **Quiere**: Vendajes
- **Ubicación**: Cuarto del guerrero (9)
- **Diálogo**: "Me muero..."
- **Recompensa**: "Solo el hierro te protegerá contra las flores."

### 40. Minotauro (Cueva del Minotauro)
- **Tipo**: Guard
- **Arma letal**: Espada
- **Confesión**: "¡Me has matado! Coge la antorcha del número divino y rompe la columna de cristal."
- **"Número divino"**: El 7 — pero la Antorcha 6 está apagada, así que la "antorcha del número divino" es la **Antorcha 3** (la Trinidad, otro número divino). También podría referirse a la 7.

### 41. Puerta dorada (Salón de los elegidos → Cerebro)
- **Tipo**: RiddleLink
- **Acertijo**: "Invente un alfabeto (el mayor que pueda) con el que no pueda crearse a la Bestia."
- **Respuesta**: `cdfghjklmnopqruvwxyz` (todas las letras menos A, B, E, I, S, T = BESTIA)
- **Conduce a**: Cerebro de la Bestia (22)

### 42. Puerta de hierro (Jardín falso → Salón de los elegidos)
- **Tipo**: RiddleLink
- **Acertijo**: "¿Cuántas antorchas iluminan al Minotauro?"
- **Respuesta**: `Seis` (la séptima está apagada)
- **Conduce a**: Salón de los elegidos (30)

### 43. El Laberinto (habitaciones 31-48)
- **Tipo**: Navegación por grafo de 18 nodos
- **Pista de Crunch**: "El 12 te guiará... Luego solo debes dar un paso."
- **Interpretación**: Tomar Puerta 1, luego Puerta 2, luego un paso más. O: secuencia de dígitos.
- **Salida**: Habitación 49 tiene única puerta "Salida" → Antesala (28)

---

## Parte II — Puzles

### 1. Puerta de metal (Pasillo → Cocina)
- **Tipo**: DangerLink
- **Protección necesaria**: Pañuelo
- **Ubicación**: Cuarto de Aura (4)

### 2. Grifo (Pasillo)
- **Tipo**: Guard
- **Arma letal**: Daga
- **Ubicación**: Cuarto del Leñador (6)
- **Confesión**: "¡Aura!"
- **Pista**: La contraseña de la Reja (Calabozos, 47) es "Grifo"

### 3. Puerta Azul (Pasillo → Cuarto de Aura)
- **Tipo**: RiddleLink
- **Acertijo**: "¿Cuál es el nombre de la hija del Hechicero?"
- **Respuesta**: `Aura`
- **Conduce a**: Cuarto de Aura (4)

### 4. Puerta del baúl (Casa de muñecas → Interior del baúl)
- **Tipo**: Linking
- **Contraseña**: `MIAU`
- **Conduce a**: Interior del baúl (10)

### 5. Ventana → Pasadizo (Casa de muñecas → Jardines)
- **Tipo**: Hidden → OpenLink
- **Romper con**: Corta-cristales
- **Revela**: Pasadizo a Jardines (13)
- **Mensaje**: "Usa tu equilibrio para vencer la corriente"

### 6. Gato (Interior del baúl)
- **Tipo**: Troll
- **Quiere**: Pescado
- **Ubicación**: Cocina (7)
- **Diálogo**: "¡No molestes!"
- **Recompensa**: "La piedra verde te servirá para romper la segunda muralla."

### 7. Caronte (Orilla 1 del Río Negro)
- **Tipo**: Troll
- **Quiere**: Reloj de arena
- **Ubicación**: Terrazas (8)
- **Diálogo**: "Tráeme el reloj de arena, pero víralo antes de entregármelo."
- **Recompensa**: "Dentro del blanco está la llave de la muralla." → el Árbol de marfil (infinitamente blanco) en la Orilla 2

### 8. Árbol de marfil → Maza (Orilla 2)
- **Tipo**: Hidden → Thing
- **Romper con**: Hacha
- **Revela**: Maza

### 9. Muralla → Avenida de hierro (Orilla 2 → Jardines)
- **Tipo**: Hidden → OpenLink
- **Romper con**: Maza
- **Revela**: Avenida de hierro → Jardines (13)

### 10. Puerta amarilla (Jardines → Tesoros)
- **Tipo**: Linking
- **Contraseña**: `Omicuos Ihanti`
- **Pista**: El Dragón (Salón de velas, 18) la revela al recibir la Daga

### 11. Dragón (Salón de velas)
- **Tipo**: Troll
- **Quiere**: Daga
- **Ubicación**: Cuarto del Leñador (6)
- **Diálogo**: Silencio total (el único NPC mudo antes de recibir su objeto)
- **Recompensa**: "Las palabras mágicas para entrar en el cuarto del tesoro son: 'Omicuos Ihanti'."

### 12. Jardinero (Jardines)
- **Tipo**: Troll
- **Quiere**: Hacha
- **Diálogo**: "El jardinero no le presta atención. Está muy ocupado cortando un abeto con una navaja."
- **Recompensa**: "En tu camino encontrarás varios anillos. Debes guardar el que tú consideres más apropiado..."

### 13. Inmortal (Cuarto del Inmortal)
- **Tipo**: Guard
- **Arma letal**: Arco
- **Ubicación**: Antesala de la Prueba (49) o en el propio Comedor
- **Confesión**: "No confundas la tercera muralla con la tercera barrera que tienes que romper. La tercera barrera está en ti mismo."

### 14. Monstruo (Calabozo del Monstruo)
- **Tipo**: Troll
- **Quiere**: Muslo de carnero
- **Ubicación**: Cocina (7)
- **Diálogo**: "¡Grrrr! ¡Hambre!"
- **Recompensa**: "¡Tú cuidarte de Hechicero! ¡Hechicero ser malo! (...) Busca espada Marmidosa... ¡y pincha todo!"
- **Nota**: Debe ser eliminado para ganar

### 15. Dinosaurio (Comedor)
- **Tipo**: Troll (dentro de Hidden Huevo → Piedra)
- **Quiere**: Sonajero
- **Ubicación**: Cuarto de juguetes (20)
- **Recompensa**: "Maúllale al gato." → pista para la contraseña "MIAU" del baúl

### 16. Túnel del Comedor (Comedor → Antesala de la Prueba)
- **Tipo**: DangerLink
- **Protección necesaria**: Arco
- **Peligro**: Banda de murciélagos gigantes

### 17. Juglar (Habitaciones del Juglar)
- **Tipo**: Troll
- **Quiere**: Arpa
- **Ubicación**: Tesoros (17)
- **Diálogo**: "¡Qué aburrimiento!"
- **Recompensa**: "Lleva algo de la fragua de Vulcano al bajar a las Catacumbas." → Escudo de Aquiles (forjado por Hefestos/Vulcano)

### 18. Escaleras al inframundo (Juglar ↔ Catacumbas)
- **Tipos**: DangerLink (ambas direcciones)
- **Protección necesaria**: Escudo de Aquiles
- **Peligro**: Precipicio de lava

### 19. Túnel de los Subterráneos (Subterráneos ↔ Catacumbas)
- **Tipo**: DangerLink (ambas direcciones)
- **Protección necesaria**: Escudo de Aquiles
- **Peligro**: Dardo envenenado

### 20. Ogro (Alcoba del Ogro)
- **Tipo**: Guard
- **Arma letal**: Cubo de agua
- **Ubicación**: Oasis (34)
- **Confesión**: "¡No saldrás del lago con Marmidosa tan fácilmente!"

### 21. Pordiosero (Oasis)
- **Tipo**: Troll
- **Quiere**: Bolsa (de oro)
- **Ubicación**: Tesoros (17)
- **Recompensa**: "Si el Ogro se baña, se muere."

### 22. Obispo (Catedral)
- **Tipo**: Troll
- **Quiere**: Silla
- **Ubicación**: Terrazas (8)
- **Recompensa**: "Solo con el Talismán de Nieve podrás entrar hasta Marmidosa."

### 23. Grieta (Fondo del Lago → Cueva de Cristal)
- **Tipo**: DangerLink
- **Protección necesaria**: Talismán de Nieve

### 24. Sendero dorado (Fondo del Lago ↔ Orilla del Lago)
- **Tipo**: DangerLink2 (ambas direcciones)
- **NO debe llevar**: Marmidosa
- **Si la lleva**: Muerte

### 25. Doncella del Lago (Fondo del Lago)
- **Tipo**: Troll
- **Quiere**: Talismán de Nieve
- **Diálogo**: "La doncella le mira con cierto aire de complicidad y exclama: ¡La cueva de cristal es tan hermosa! Si pudiera entrar al menos una vez..."
- **Recompensa**: "Las dos partes del manuscrito están guardadas en la Torre de Cristal. Y cuando vayas en busca de la segunda parte, lleva el triángulo contigo."

### 26. Camino del Desierto (Desierto → Orilla del Lago)
- **Tipo**: DangerLink2
- **NO debe llevar**: Talismán de Nieve
- **Pista**: Inscripción en el Desierto (36)

### 27. Segunda Muralla → Avenida de las flores (Desierto → Valle)
- **Tipo**: Hidden → OpenLink
- **Romper con**: Piedra verde
- **Revela**: Avenida de las flores (con flores carnívoras) → Valle (37)
- **Pista de Dédalo (P1)**: "Solo el hierro te protegerá contra las flores."

### 28. Camello (Valle)
- **Tipo**: Troll
- **Quiere**: Botella de vino
- **Ubicación**: Cuarto del Leñador (6)
- **Recompensa**: "Las dos últimas letras del segundo nombre de la Hija del Hechicero son 'KA'." → Aura Srka

### 29. Precipicio (Pico Negro → Ciudad Abandonada)
- **Tipo**: DangerLink
- **Protección necesaria**: Saltador
- **Pista del Monje**: "Para descender por el precipicio debes llevar algo que amortigüe el golpe al final."

### 30. Monje (Choza del monje, Pico Negro)
- **Tipo**: Troll
- **Quiere**: Rosario
- **Ubicación**: Catedral (35)
- **Recompensa**: "Para descender por el precipicio debes llevar algo que amortigüe el golpe al final."

### 31. Estatua de Cristal → Horante (Ciudad Abandonada)
- **Tipo**: Hidden → Troll
- **Romper con**: Corta-Cristales
- **Revela**: Horante (último de su raza)

### 32. Horante (Ciudad Abandonada)
- **Tipo**: Troll
- **Quiere**: Muñeco diabólico
- **Ubicación**: Sastrería (15)
- **Diálogo**: "El horante trata de articular algo, pero un terrible dolor en su pierna derecha no lo deja."
- **Recompensa**: "Busca las dos mitades del Manuscrito de los Horantes y descífralo. Luego coloca las marcas para abrir la Fortaleza."

### 33. Sabio (Choza del Sabio, Ciudad)
- **Tipo**: Troll
- **Quiere**: Esqueleto de Murciélago
- **Ubicación**: Catacumbas (28)
- **Recompensa**: "De todas las cosas sobre la tierra, la que más me fascina es la cinta de Moebius..."

### 34. Labrador (Campo cultivado)
- **Tipo**: Troll
- **Quiere**: Bolsa de semillas
- **Ubicación**: Valle (37)
- **Recompensa**: "No siempre las cosas son lo que parecen..."

### 35. Río (Campo ↔ Torre de Cristal)
- **Tipo**: DangerLink (ambas direcciones)
- **Protección necesaria**: Cuerda
- **Mecánica**: El jugador lanza la cuerda con garfio y cruza haciendo equilibrio

### 36. Reja (Fondo del Lago → Catedral)
- **Tipo**: Hidden → OpenLink
- **Romper con**: Tenazas
- **Revela**: Escalera → Catedral (35)

### 37. Esfera → Tablilla (Punta de la Torre de Cristal)
- **Tipo**: Hidden → Thing
- **Romper con**: Marmidosa
- **Revela**: Tablilla de Madera (primera mitad del Manuscrito de los Horantes)

### 38. Puerta de Cristal (Punta de la Torre → Alcoba de Aura)
- **Tipo**: RiddleLink
- **Acertijo**: "¿Cuál es el nombre completo de la hija del Hechicero?"
- **Respuesta**: `Aura Srka`
- **Pista**: El Camello da "KA" como últimas letras del segundo nombre; el Encapuchado da "8 letras, una repetida 3 veces, otra 2"

### 39. Carta → Puerta Secreta (Alcoba de Aura → Alcoba Secreta)
- **Tipo**: Hidden (sin breaker) → DangerLink
- **Revela**: Puerta Secreta → Alcoba Secreta (46)
- **Protección para cruzar**: Lienzo

### 40. Hija del Hechicero (Alcoba Secreta)
- **Tipo**: TDaugther (Guard especial)
- **Arma letal**: Aguja
- **Si se usa otra arma**: El jugador es devorado
- **Confesión**: "¡Mata a todos los que te mintieron si quieres salir!"

### 41. Carcelero (Calabozos)
- **Tipo**: Guard
- **Arma letal**: Marmidosa
- **Confesión**: "¡Te será muy difícil abrir la celda, porque la palabra mágica es el nombre de la primera criatura que viste al salir del cuarto de huéspedes!" → "Grifo"

### 42. Reja de la celda (Calabozos → Celda)
- **Tipo**: Linking
- **Contraseña**: `Grifo`
- **Pista**: El Carcelero al morir

### 43. Encapuchado (Celda)
- **Tipo**: Troll
- **Quiere**: Receta
- **Ubicación**: Cocina (7)
- **Recompensa**: "El nombre de la hija del Hechicero tiene ocho letras, una está repetida tres veces y otra dos." → AURA SRKA

### 44. La Prueba de los Anillos (habitaciones 49-52)
- **Mecánica**: DangerLink2 en cada puerta

| Puerta | NO debe llevar |
|--------|---------------|
| Puerta Verde (49→50) | Anillo de oro |
| Puerta Azul (50→51) | Anillo de plata |
| Puerta Blanca (51→52) | Anillo de bronce |

- **Anillo correcto**: Cinta de Moebius (no es un anillo tradicional)
- **Pista del Jardinero**: Elegir el anillo "más apropiado a tu espíritu y empresa"

### 45. Puerta triangular (Salón Blanco → Límites)
- **Tipo**: DangerLink
- **Protección necesaria**: Cinta de Moebius

### 46. Puente al Abismo (Límites → Pirámide)
- **Tipo**: DangerLink (ambas direcciones)
- **Protección necesaria**: Grabado

### 47. Guardián (Límites)
- **Tipo**: Troll
- **Quiere**: Sombrero
- **Recompensa**: Historia del héroe que derrota a la serpiente con una aguja (pista para la Hija del Hechicero)

### 48. Columna de Hielo → Puerta de Roble (Pirámide → Habitaciones del Hechicero)
- **Tipo**: Hidden → RiddleLink
- **Romper con**: Antorcha
- **Revela**: Puerta de Roble con acertijo

### 49. Puerta de Roble (Pirámide → Habitaciones del Hechicero)
- **Tipo**: RiddleLink
- **Acertijo**: "¿Quién invirtió el reloj de Caronte?"
- **Respuesta**: `Yo` (el jugador, porque Caronte pidió que lo volteara antes de entregárselo)
- **Conduce a**: Habitaciones del Hechicero (55)

### 50. Hechicero (Habitaciones del Hechicero)
- **Tipo**: Troll
- **Quiere**: Marmidosa
- **Diálogo**: Silencio
- **Recompensa**: "No soy tu enemigo. Es mi hija quien ha elaborado este diabólico plan para eliminarnos. Rompe la carta que te dejó en la Torre de Cristal y ocurrirá un milagro."

---

## El Ritual Final (condición de victoria)

La función `Fort.Goal` en `FORT2.PAS:71-79` requiere colocar 7 objetos en ubicaciones específicas y eliminar 2 enemigos:

| Condición | Significado |
|-----------|-------------|
| Antorcha en habitación 1 (Cuarto de huéspedes) | Marca de fuego/luz |
| Péndulo en habitación 3 (Salón de Fumar) | Marca de tiempo |
| Espejo en habitación 4 (Cuarto de Aura) | Marca de reflejo/verdad |
| Monstruo muerto (habitación 9) | Eliminar al guardián |
| Bote en habitación 12 (Orilla 2 del Río Negro) | Marca de travesía |
| Rosa diamante en habitación 31 (Fondo del Lago) | Marca de belleza/amor |
| Escudo de Aquiles en habitación 40 (Ciudad Abandonada) | Marca de protección |
| Cinta de Moebius en habitación 43 (Torre de Cristal) | Marca de infinito/paradoja |
| Hija del Hechicero muerta (habitación 46) | Eliminar a la antagonista |

Esto constituye el "colocar las marcas para abrir la Fortaleza" mencionado por el Horante.
