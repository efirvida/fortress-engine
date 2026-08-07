# 02 — Habitaciones

Todas las habitaciones de ambas partes. Referencias de código: descripciones de `RoomAr` en `FORT1.PAS` y `FORT2.PAS`, contenido de `SetData`.

## Parte I — 33 habitaciones (50 índices asignados)

### 1. El exterior de la fortaleza
- **Descripción**: "Las paredes son muy negras y al parecer, no tienen ventanas. Usted trata de ver el final de las torres, pero las nubes no se lo permiten." (`FORT1.PAS:100-101`)
- **Habitación inicial** de la Parte I
- **Contenido**:
  - Roble — árbol con inscripción
  - Maza — arma muy pesada
  - Pastel de cerezas — comida
  - Llamador de bronce (Troll) — quiere un cigarro
  - Puerta principal (Linking) — entrada a la Fortaleza (requiere contraseña)
  - Túnel (OpenLink) — conduce a la habitación 4 (Patio interior)
  - Pared solitaria (Hidden) — esconde una Puerta secreta (DangerLink, necesita Antorcha, va a la 27)

### 2. El Salón de recepciones
- **Descripción**: "Parece hecho para criaturas cientos de veces más grandes que los humanos. Está desierto, pero usted siente que es observado." (`FORT1.PAS:103-104`)
- **Contenido**:
  - Monolito de mármol (Hidden) — esconde un Trebol (Troll, quiere Vaso de agua)
  - Puerta principal (Linking) — regreso al exterior (1)
  - Puerta negra (Linking) — conduce a la Sala de juegos (3)
  - Retrato (Thing) — de Hitchcock

### 3. La Sala de juegos
- **Descripción**: "Usted trata de imaginar cómo eran los juegos del salón. Hay doce mesas y cada una tiene doce erizos." (`FORT1.PAS:106`)
- **Contenido**:
  - Escoba — escoba voladora
  - Escalera (RiddleLink) — acertijo: "¿Cuántos peldaños tiene la escalera?" → "treinta y nueve", conduce a habitación 5
  - Inscripción — "Cuando hayas llegado casi al final, tendrás que regresar, a no ser que hayas hablado con el murciélago."
  - Puerta negra (Linking) — regreso al Salón de recepciones (2)
  - Puerta azul (Linking) — conduce al Patio interior (4)
  - Hilo de Ariadna — cuerda de varios kilómetros

### 4. El Patio interior
- **Descripción**: "El patio tiene forma de caracol. Cada uno o dos pasos se levanta una columna de mármol negro y se confunde en la altura con los árboles. Usted siente el crujido de las hojas secas bajo sus zapatos." (`FORT1.PAS:108-109`)
- **Contenido**:
  - Puerta azul (Linking) — regreso a Sala de juegos (3)
  - Puerta verde (Linking) — conduce a Biblioteca (6)
  - Estatua de Atenea (Troll) — quiere un objeto (decodificado), diálogo: "¡Sal de mi presencia, estúpido mortal!"
  - Estatua de Hermes (Troll) — quiere un objeto (decodificado), diálogo: "La humedad me destruye."
  - Balanza — para pesar objetos

### 5. El Cuarto de espejos
- **Descripción**: "Hay tantos espejos que no puede reconocer si usted es real o es una imagen de sí mismo." (`FORT1.PAS:111`)
- **Contenido**:
  - Hueso de gato
  - Escalera (Linking) — regreso a Sala de juegos (3), pero con más escalones
  - Espejo opaco (Hidden) — esconde Puerta oculta que conduce a Alcoba de la doncella (14)

### 6. La Biblioteca
- **Descripción**: "Hay miles de libros en este lugar. Todos tienen alguna hoja marcada con una servilleta." (`FORT1.PAS:113`)
- **Contenido**:
  - Puerta verde (Linking) — regreso a Patio interior (4)
  - Vaso de agua
  - Candelabro — llama inmóvil como de cera
  - Libro (Linking) — "¡Usted ha atravesado el libro!" → conduce a Jardín (13)
  - Cíclope (Guard) — guardián, confesión decodificada, arma letal decodificada
  - Puerta (Linking) — puerta para gigantes (requiere contraseña), conduce a Pasillo (7)

### 7. Pasillo
- **Descripción**: "Tiene tres puertas al lado y una al final." (`FORT1.PAS:115`)
- **Contenido**:
  - Antorcha
  - Puerta (Linking) — regreso a Biblioteca (6)
  - Puerta vieja (Linking) — conduce a Alcoba de la bruja (8)
  - Puerta roja (Linking) — conduce a Cuarto del guerrero (9)
  - Puerta prohibida (Linking) — requiere contraseña, conduce a Laboratorio (10)
  - Puerta gris (Linking) — conduce a Sala de infusiones (15)

### 8. La Alcoba de la bruja
- **Descripción**: "Hasta un ciego descubriría que aquí habita una bruja. El cuarto tiene una ventana, pero usted no recuerda haberla visto desde afuera." (`FORT1.PAS:117-118`)
- **Contenido**:
  - Puerta vieja (Linking) — regreso a Pasillo (7)
  - Polvo mágico — hace invisible a cualquiera
  - Poción para crecer — olor repugnante
  - Escaparate (DangerLink) — peligroso, necesita Candelabro, conduce a Alcoba de la doncella (14)
  - Bruja (Troll) — quiere su Escoba, da consejo

### 9. El Cuarto del guerrero
- **Descripción**: "El cuarto está muy ordenado. A usted le sorprende que no hayan armas." (`FORT1.PAS:120`)
- **Contenido**:
  - Puerta roja (Linking) — regreso a Pasillo (7)
  - Vendajes — manchados de sangre
  - Cama (Hidden) — rompible, esconde Puerta al suelo que conduce a Sala de armas (11)
  - Grabado — muestra al jugador hablando con una muchacha

### 10. El Laboratorio de la Bestia
- **Descripción**: "Hay muchos frascos. A usted le llaman la atención los últimos: están llenos de homúnculos." (`FORT1.PAS:122`)
- **Contenido**:
  - Puerta prohibida (Linking) — regreso a Pasillo (7)
  - Homúnculo (Troll) — quiere Poción para crecer
  - Piedra filosofal — quinta esencia
  - Máquina del tiempo — parece una máquina de moler carne

### 11. La Sala de armas
- **Descripción**: "Este lugar parece salido del sueño de un guerrero." (`FORT1.PAS:124`)
- **Contenido**:
  - Espada — muy brillante (peso 5)
  - Lanza — de piedra (peso 10)
  - Arco — el arco de Odiseo (peso 5)
  - Daga — afilada como lengua de serpiente bíblica (peso 3)
  - Ariete — demasiado grande (peso LWeight - 10)
  - Látigo — parece una culebra (peso 2)
  - Puerta (Linking) — en el techo, regreso a Cuarto del guerrero (9)

### 12. Los Baños de la Bestia
- **Descripción**: "El baño es tan grande que usted no puede ver las paredes que lo limitan." (`FORT1.PAS:126`)
- **Contenido**:
  - Puerta verde (Linking) — conduce al Jardín (13)
  - Rosa — hermosa
  - Inscripción — "¡Mate al Troll! Y no haga sus necesidades en el suelo."
  - Espejo — muestra al jugador entregándole polvos al Troll (peso 20)
  - Troll (Troll) — quiere Polvo mágico para volverse invisible; diálogo: "No me mates, por favor. Haz que nadie pueda ver mi fealdad."

### 13. El Jardín
- **Descripción**: "Se podrían construir varias ciudades en su interior." (`FORT1.PAS:128`)
- **Contenido**:
  - Inscripción — "Es un buen lugar para instalar una tienda de campaña ¿no cree?"
  - Cedro — le faltan ramas (peso > LWeight, no se puede cargar)
  - Puerta verde (Linking) — regreso a Baños (12)
  - Puerta azul (Linking) — conduce a Alcoba de la doncella (14)
  - Puerta amarilla (Linking) — conduce a Sala de infusiones (15)
  - Puerta de hierro (Linking) — conduce a Calabozos (16)
  - Puerta de madera (Linking) — conduce a Almacenes (23)

### 14. La Alcoba de la doncella
- **Descripción**: "Es una habitación muy pequeña y húmeda." (`FORT1.PAS:130`)
- **Contenido**:
  - Puerta azul (Linking) — regreso a Jardín (13)
  - Puerta oculta (Linking) — regreso a Cuarto de espejos (5)
  - Cuadro — completamente negro (peso 10)
  - Corazón de unicornio — aún late (peso 1)
  - Escaparate (Linking) — conduce a Alcoba de la bruja (8) (subida)
  - Doncella (Troll) — quiere un objeto (decodificado), diálogo: "¿Qué brusco! Un caballero debe dirigirse a una dama de otra forma."

### 15. La Sala de infusiones
- **Descripción**: "Hay varias mesas regadas por el suelo. Usted tiene la impresión de que ningún humano ha estado en ese lugar anteriormente." (`FORT1.PAS:132-133`)
- **Contenido**:
  - Puerta gris (Linking) — regreso a Pasillo (7)
  - Puerta amarilla (Linking) — regreso a Jardín (13)
  - Taza de café — humea
  - Cigarro — encendido
  - Arpía (Guard) — desayunando, confesión y arma letal decodificadas

### 16. Los Calabozos
- **Descripción**: "Son tan húmedos que usted no resistiría ni unas horas dentro de ellos." (`FORT1.PAS:135`)
- **Contenido**:
  - Puerta de hierro (Linking) — regreso a Jardín (13)
  - Paraguas — cerrado
  - Talismán de aire — hecho de cinco vientos
  - Esqueleto (Troll) — quiere Taza de café, diálogo: "Dame algo para calentarme la barriga, por favor."

### 17. Boca de la Bestia
- **Descripción**: "Es como una boca humana, pero del tamaño de una casa." (`FORT1.PAS:137`)
- **Contenido**:
  - Puerta triangular (Linking) — conduce a Salón de cristal (25)
  - Garganta (OpenLink) — conduce a Interior de la Bestia (18)

### 18. Interior de la Bestia
- **Descripción**: "Usted puede sentir los latidos del corazón de la Bestia, al igual que su respiración o el ruido de los líquidos revueltos en su estómago." (`FORT1.PAS:139-140`)
- **Contenido**:
  - Inscripción — "No continúe si no está protegido." (peso 10)
  - Garganta (Linking) — regreso a Boca (17)
  - Tráquea (DangerLink) — necesita Talismán de aire, conduce a Pulmones (19)
  - Esófago (DangerLink) — necesita Talismán de aire, conduce a Estómago (20)
  - Arteria principal (DangerLink) — necesita Corazón de unicornio, conduce a Corazón (21)

### 19. Pulmones de la Bestia
- **Descripción**: "Sopla un aire tan fuerte que usted se ha tirado al suelo." (`FORT1.PAS:142`)
- **Contenido**:
  - Tráquea (Linking) — regreso a Interior (18)
  - Centro de los pulmones (Guard) — confesión y arma letal decodificadas

### 20. El Estómago de la Bestia
- **Descripción**: "Hay varios esqueletos humanos." (`FORT1.PAS:144`)
- **Contenido**:
  - Esófago (Linking) — regreso a Interior (18)
  - Centro del estómago (Guard) — confesión decodificada, arma letal decodificada

### 21. El Corazón de la Bestia
- **Descripción**: "Todo palpita rítmicamente. Usted siente cómo los latidos se adueñan del lugar, especialmente de su propio corazón." (`FORT1.PAS:146-147`)
- **Contenido**:
  - Arteria principal (Linking) — regreso a Interior (18)
  - Centro del corazón (Guard) — confesión decodificada, arma letal decodificada

### 22. El Cerebro de la Bestia
- **Descripción**: "Es como un tarjetero gigante. Cada idea está escrita en una tarjeta y, cuando es necesario, la tarjeta es sacada por una mano invisible y leída al resto de la Bestia." (`FORT1.PAS:149-150`)
- **Contenido**:
  - Inscripción — (decodificada, peso 10)
  - Centro del cerebro (Guard) — "¡Usa la antorcha!", confesión: "XVBCZXV XBVCZX BVZXC!!!!!", arma letal decodificada

### 23. Los Almacenes de la Fortaleza
- **Descripción**: "Están llenos de carne humana. Usted aparta el cadáver de una mujer para poder observar bien el lugar." (`FORT1.PAS:152`)
- **Contenido**:
  - Hacha — muy afilada
  - Puerta de madera (Linking) — regreso a Jardín (13)
  - Puerta verde (Linking) — conduce a Páramo (24)
  - Ratón (Troll) — alquimista con delantal, quiere objeto decodificado; diálogo: "No tengo tiempo para atenderte. Llevo medio siglo buscando la quinta esencia."

### 24. Un extenso páramo
- **Descripción**: "Hay muy poca vegetación y el suelo es pantanoso. Usted nunca imaginó que el interior de la fortaleza fuera tan grande." (`FORT1.PAS:154-155`)
- **Contenido**:
  - Puerta verde (Linking) — regreso a Almacenes (23)
  - Puerta de cristal (Linking) — requiere contraseña, conduce a Salón de cristal (25)
  - Pozo (OpenLink) — caída al exterior de la fortaleza (1)
  - Túnel (DangerLink) — peligroso (necesita objeto decodificado), conduce al mismo Páramo (24)
  - Lobo (Guard) — tamaño de un ternero, bloquea la puerta de cristal; arma letal: Látigo

### 25. Salón de cristal
- **Descripción**: "Es como un caleidoscopio gigante. Cada varios segundos las paredes cambian de color y usted siente como si lo hubieran trasladado a otro lugar." (`FORT1.PAS:157-158`)
- **Contenido**:
  - Puerta de cristal (Linking) — regreso a Páramo (24)
  - Puerta de tela (Linking) — conduce a Celda (26)
  - Puerta triangular (RiddleLink) — acertijo: "¿Cuál es el nombre del duende?" → respuesta decodificada, conduce a Boca (17)
  - Bailarina (Troll) — quiere Máquina del tiempo; diálogo: "Quiero ser joven para siempre."

### 26. Celda pequeña
- **Descripción**: "No hay forma alguna de salir." (`FORT1.PAS:160`)
- **Contenido**:
  - Inscripción — "Dice que usted pasará en esta celda el resto de sus días." (peso > LWeight)
- **Nota**: Trampa del laberinto; varias puertas del laberinto conducen aquí.

### 27. Un puente de mármol
- **Descripción**: "Es muy largo y estrecho." (`FORT1.PAS:162`)
- **Contenido**:
  - Araña (Troll) — mayor que el jugador, quiere Hilo de Ariadna; diálogo: "¡Pssssssss!" — al darle el hilo: "Busca al Minotauro y mátalo con la espada."
  - Martillo — dos mangos y tres cabezas
  - Puerta secreta (DangerLink) — necesita Antorcha, conduce a Exterior (1)
  - Estatua de Satanás (Hidden) — necesita Cuadro, esconde Puerta oculta que conduce a Antesala del Laberinto (28)
  - Puerta (DangerLink2) — NO debe llevar Espada, conduce a Antesala del Laberinto (28)

### 28. Antesala del Laberinto
- **Descripción**: "Es una habitación muy confortable, pero usted siente algo malvado flotando en el aire." (`FORT1.PAS:164`)
- **Contenido**:
  - Puerta (Linking) — regreso a Puente (27)
  - Crunch (Troll) — "Es muy similar a una boca con patas", quiere Pastel de cerezas; diálogo: "¡Qué hambre!" — al darle el pastel: "El 12 te guiará en el Laberinto. Luego solo debes dar un paso."
  - Columna de Cristal (Hidden) — necesita "Antorcha 3" para revelar Puerta de madera (Hidden), que necesita Martillo para revelar Puerta negra que conduce a Jardín falso (50)
  - Puerta verde (OpenLink) — conduce al Laberinto (31)
  - Dédalo (Troll) — herido, quiere Vendajes; diálogo: "Me muero..." — al darle vendajes: "Solo el hierro te protegerá contra las flores."

### 29. La cueva del Minotauro
- **Descripción**: "Hay siete antorchas." (`FORT1.PAS:167`)
- **Contenido**:
  - Puerta (OpenLink) — conduce al Laberinto (47)
  - Antorcha 1 a Antorcha 7 (6 brillantes, la 6 apagada)
  - Minotauro (Guard) — sentado en trono de rocas; arma letal: Espada; confesión: "¡Me has matado! Coge la antorcha del número divino y rompe la columna de cristal."

### 30. El Salón de los elegidos
- **Descripción**: "Usted se enorgullece: muy pocas personas han llegado hasta este salón. El cerebro de la Bestia está detrás de la puerta." (`FORT1.PAS:169`)
- **Contenido**:
  - Puerta dorada (RiddleLink) — acertijo: "Invente un alfabeto (el mayor que pueda) con el que no pueda crearse a la Bestia." → respuesta: `cdfghjklmnopqruvwxyz` (todas las letras excepto A, B, E, I, S, T = BESTIA), conduce a Cerebro de la Bestia (22)

### 31-48. Pasillos del Laberinto
- **Descripción 31-48**: "El techo está tan pegado al suelo que usted tiene que andar agachado. Hay tres puertas simétricas." (`FORT1.PAS:171`)
- **Descripción 49**: "Hay una puerta que le conducirá a la antesala del Laberinto." (`FORT1.PAS:173`)
- **Todas las puertas** son OpenLink (siempre abiertas). Es un laberinto de 18 nodos con 3 puertas numeradas en cada uno.
- La habitación 49 tiene la **Salida** que regresa a la Antesala (28).

### 50. El Jardín (falso)
- **Descripción**: "Se podrían construir varias ciudades en su interior." (misma que 13) (`FORT1.PAS:175`)
- **Contenido**:
  - Inscripción — "¡Cuidado! Este no es el Jardín verdadero."
  - Cedro — (igual que en jardín real)
  - Puerta verde, azul, amarilla, de madera (OpenLink) — todas conducen a la Celda (26) (trampa)
  - Puerta de hierro (RiddleLink) — acertijo: "¿Cuántas antorchas iluminan al Minotauro?" → respuesta: "Seis", conduce al Salón de los elegidos (30)

---

## Parte II — 55 habitaciones

### 1. Una habitación para huéspedes
- **Descripción**: "Está tan oscura que usted cree que las paredes y el techo se han avalanzado sobre su cuerpo. En la pared que tiene delante se distingue un plateado hilo de luz. Es el filo de una puerta." (`FORT2.PAS:85-87`)
- **Habitación inicial** de la Parte II
- **Contenido**:
  - Puerta (Linking) — conduce a Pasillo (2)

### 2. El pasillo
- **Descripción**: "Hay seis puertas distribuidas simétricamente. Las paredes son de mármol blanco, pero usted tiene la certeza de que hay algo terrible encerrado detrás de toda esa pulcritud." (`FORT2.PAS:89-90`)
- **Contenido**:
  - Puerta (Linking) — regreso a habitación de huéspedes (1)
  - Puerta de espinos (Linking) — conduce a Cuarto del Leñador (6)
  - Puerta de metal (DangerLink) — conduce a Cocina (7); **necesita Pañuelo** o muere
  - Puerta Negra (Linking) — conduce a Salón de Fumar (3)
  - Puerta Azul (RiddleLink) — acertijo: "¿Cuál es el nombre de la hija del Hechicero?" → "Aura", conduce a Cuarto de la hija (4)
  - Puerta de oro (Linking) — conduce a Terrazas (8)
  - Grifo (Guard) — medio león, medio águila, parece dormido; arma letal: Daga; confesión: "¡Aura!"

### 3. El Salón de Fumar
- **Descripción**: "Hay sesenta y seis sillas en el salón. Al lado de cada silla crece un tentáculo rosado con un pitillo en el extremo. Los pitillos humean." (`FORT2.PAS:92-93`)
- **Contenido**:
  - Puerta Negra (Linking) — regreso a Pasillo (2)
  - Balanza — plato en forma de mano
  - Inscripción — "La muerte es un acto de la vida. Yo, la Bestia, he de morir como he vivido. Esta es mi venganza, y tú mismo serás el instrumento que la lleve a cabo. La naturaleza humana es el arma más poderosa que puede utilizarse contra el hombre."
  - Piedra de Roseta — con texto codificado bilingüe

### 4. El cuarto de la hija del Hechicero
- **Descripción**: "Se pregunta cómo luciría la hija de un hechicero. En las paredes hay cientos de retratos, todos de muchachas diferentes. ¿Cuál será la real?... ¿O todas son una misma?" (`FORT2.PAS:95-96`)
- **Contenido**:
  - Puerta Azul (Linking) — regreso a Pasillo (2)
  - Pañuelo — bordado con A y S
  - Carta — "¡Dios te salve, mi única esperanza! Mi padre me ha encerrado en la Torre de Cristal, que está más allá del segundo río. El sabe que solo yo podría mostrarte el camino de salida. Búscame."
  - Agujero (OpenLink) — conduce a Casa de muñecas (5)

### 5. La casa de muñecas
- **Descripción**: "Es tan pequeña como cualquier casa de muñecas. Usted no comprende cómo pudo entrar. Hay un baúl en el fondo." (`FORT2.PAS:98`)
- **Contenido**:
  - Agujero (OpenLink) — regreso a cuarto de Aura (4)
  - Ventana (Hidden) — necesita Corta-cristales, esconde Pasadizo a Jardines (13)
  - Puerta del baúl (Linking) — contraseña: "MIAU", conduce a Interior del baúl (10)

### 6. El cuarto del Leñador
- **Descripción**: "Las paredes, el suelo y el techo están hechos de madera. Usted camina con cuidado: hay espinas por todas partes." (`FORT2.PAS:100-101`)
- **Contenido**:
  - Puerta de espinos (Linking) — regreso a Pasillo (2)
  - Daga — empuñadura de dragón (peso 2)
  - Botella de vino — parece agua sucia (peso 3)
  - Hacha — muy mohosa (peso 17)

### 7. La Cocina
- **Descripción**: "En realidad, se parece mucho más a un matadero. El olor a sangre coagulada y carroña no le permite apartar el pañuelo de la nariz. Hay unas marcas de sangre en la pared que le llaman mucho la atención: fueron hechas por una mano de siete dedos." (`FORT2.PAS:103-105`)
- **Contenido**:
  - Puerta de metal (DangerLink) — regreso a Pasillo (2); necesita Pañuelo
  - Receta — "5 Ojos de rana, 1 Mano de gigante, 2 Cucharadas de puré de lombrices, 1 Hígado de muchacha virgen, 9 Libras de azúcar, 1 Tanque de agua del pantano verde"
  - Muslo de carnero — parece muslo de persona
  - Pescado

### 8. Las Terrazas
- **Descripción**: "No puede reprimir su asombro: las terrazas están invertidas. Usted se siente muy natural parado cabeza abajo. Se escucha el correr de un río." (`FORT2.PAS:107-108`)
- **Contenido**:
  - Inscripción — "No todos los dragones merecen la muerte."
  - Puerta de oro (Linking) — regreso a Pasillo (2)
  - Escalera de caracol (OpenLink) — conduce a Orilla 1 del Río Negro (11)
  - Reloj de arena — emite tic-tac
  - Silla — para tomar el sol; alguien estaba sentado

### 9. El calabozo del Monstruo
- **Descripción**: "Las paredes son de barro. Hay cientos de cadenas embotadas en el techo, moviéndose constantemente, como si las arrastrara un viento de acero." (`FORT2.PAS:110-111`)
- **Contenido**:
  - Escalera de caracol (OpenLink) — regreso a Terrazas (8)
  - Inscripción — "No alimente al monstruo."
  - Monstruo (Troll) — quiere Muslo de carnero; diálogo hambriento: "¡Grrrr! ¡Hambre!"; al darle comida: "¡Tú cuidarte de Hechicero! ¡Hechicero ser malo! ¡Malo! ¡Muy malo! Hechicero puso yo feo. A tí no poner feo... ¡A tí arrancal tripa, sacal ojo, rompel hueso y echal dragón hambroso! Yo consejo tú: Busca espada Marmidosa... ¡y pincha todo!"

### 10. El interior del baúl
- **Descripción**: "Ahora sí está confundido. El baúl es inmensamente mayor que la casa de muñecas, a pesar de que está dentro de ella. Luce como una habitación cualquiera." (`FORT2.PAS:113-115`)
- **Contenido**:
  - Puerta del baúl (Linking) — en el techo, regreso a Casa de muñecas (5)
  - Piedra verde — increíblemente sólida (peso 9)
  - Gato (Troll) — come cabeza de pescado, quiere Pescado; diálogo: "¡No molestes!"; al darle pescado: "La piedra verde te servirá para romper la segunda muralla."

### 11. Una orilla del Río Negro
- **Descripción**: "Las aguas del Río Negro hacen honor a su nombre. Más que aguas parecen una mezcla de muerte y olvido." (`FORT2.PAS:117`)
- **Contenido**:
  - Escalera de caracol (OpenLink) — asciende a Calabozo del Monstruo (9)
  - Caronte (Troll) — capucha negra, mano descarnada, quiere Reloj de arena; diálogo: "Tráeme el reloj de arena, pero víralo antes de entregármelo."; al darlo: "Dentro del blanco está la llave de la muralla."
  - Bote — el célebre bote de Caronte (peso casi LWeight)
  - Río Negro (OpenLink) — nadando a Orilla 2 (12)

### 12. Una orilla del Río Negro (orilla 2)
- **Descripción**: "La espesa niebla casi no deja ver las terrazas al otro lado." (`FORT2.PAS:119`)
- **Contenido**:
  - Río Negro (OpenLink) — regreso nadando a Orilla 1 (11)
  - Árbol de marfil (Hidden) — infinitamente blanco, necesita Hacha, esconde Maza
  - Muralla (Hidden) — necesita Maza, esconde Avenida de hierro (OpenLink) que conduce a Jardines (13)

### 13. Los Jardines del Hechicero
- **Descripción**: "Son tan extensos que usted no puede ver dónde terminan. Todos los árboles tienen el mismo tamaño y la misma forma. El jardín parece un gran juego de espejos." (`FORT2.PAS:121-122`)
- **Contenido**:
  - Avenida de hierro (OpenLink) — regreso a Río (12)
  - Puerta de madera (Linking) — conduce a Comedor (14)
  - Puerta amarilla (Linking) — contraseña: "Omicuos Ihanti", conduce a Tesoros (17)
  - Puerta de tela (Linking) — conduce a Sastrería (15)
  - Puerta verde (Linking) — conduce a Cuarto del jardinero (16)
  - Puerta roja (Linking) — conduce a Salón de las velas (18)
  - Piedra — común y corriente
  - Jardinero (Troll) — anciano encorvado, quiere Hacha; diálogo: "El jardinero no le presta atención. Está muy ocupado cortando un abeto con una navaja."; al darle hacha: "En tu camino encontrarás varios anillos. Debes guardar el que tú consideres más apropiado, el que se ajuste más a tu espíritu y a tu empresa. Los otros anillos solo te traerán peligros y muerte. Elige bien."

### 14. El Comedor
- **Descripción**: "La mesa es tan alta que usted no puede ver lo que hay servido. Alguien se lamenta allá arriba." (`FORT2.PAS:124-125`)
- **Contenido**:
  - Puerta de Madera (Linking) — regreso a Jardines (13)
  - Túnel (DangerLink) — necesita Arco, conduce a Antesala de la Prueba (49)
  - Huevo (Hidden) — necesita Piedra, esconde Dinosaurio (Troll)

### 15. La Sastrería
- **Descripción**: "Parece la casa de una araña gigantesca. Hay hilos por todas partes." (`FORT2.PAS:127`)
- **Contenido**:
  - Puerta de Tela (Linking) — regreso a Jardines (13)
  - Muñeco diabólico — artefacto de brujería, alfiler en la pierna
  - Aguja — de plata, muy larga

### 16. El cuarto del jardinero
- **Descripción**: "Es una habitación muy modesta. A usted le sorprende que los instrumentos no sean de jardinería, sino de fabricar espejos." (`FORT2.PAS:129-130`)
- **Contenido**:
  - Puerta verde (Linking) — regreso a Jardines (13)
  - Corta-cristales — diamante en la punta
  - Sombrero — muy grande

### 17. La habitación de los tesoros
- **Descripción**: "Nunca había visto tanta riqueza. Las paredes están forradas de láminas de platino y hasta el fuego de las antorchas es de oro. Usted no comprende de dónde viene la luz." (`FORT2.PAS:132-133`)
- **Contenido**:
  - Puerta amarilla (Linking) — regreso a Jardines (13)
  - Rosa diamante — increíblemente hermosa
  - Anillo de oro — sencillo, sin adornos
  - Arpa — de dieciocho cuerdas
  - Bolsa — llena de oro

### 18. El salón de las velas
- **Descripción**: "Deben ser varios kilómetros sembrados de velas. En el centro hay un círculo vacío." (`FORT2.PAS:135`)
- **Contenido**:
  - Puerta roja (Linking) — regreso a Jardines (13)
  - Puerta blanca (Linking) — conduce a Cuarto de juguetes (20)
  - Escalera (OpenLink) — baja a Cuarto del Inmortal (19)
  - Dragón (Troll) — hermoso y terrible, quiere Daga; en silencio; al darle Daga: "Las palabras mágicas para entrar en el cuarto del tesoro son: 'Omicuos Ihanti'."

### 19. El cuarto del Inmortal
- **Descripción**: "Esta habitación luce más vieja que el resto de la Fortaleza. Hay muchas cosas colgadas de la pared: retratos, cartas, reconocimientos, estandartes y muchas telas de arañas." (`FORT2.PAS:137-138`)
- **Contenido**:
  - Escalera (OpenLink) — regreso a Salón de velas (18)
  - Inscripción — "¿Quién quiere vivir para siempre?"
  - Inmortal (Guard) — cansancio en el rostro; arma letal: Arco; confesión: "No confundas la tercera muralla con la tercera barrera que tienes que romper. La tercera barrera está en ti mismo."

### 20. El cuarto de juguetes
- **Descripción**: "Hay miles de juguetes regados por todas partes. Usted siente deseos de volver a ser un niño." (`FORT2.PAS:139`)
- **Contenido**:
  - Puerta blanca (Linking) — regreso a Salón de velas (18)
  - Puerta de piedra (Linking) — conduce a Ruinas (21)
  - Saltador — tronco de abeto con resorte
  - Sonajero — juguete para recién nacidos
  - Talismán de Nieve — tormenta de nieve encerrada en cristal

### 21. Las Ruinas
- **Descripción**: "Este lugar debe haber sido abandonado hace siglos. Usted trata de imaginar cómo eran las construcciones originalmente, pero no lo consigue. Al sur se extiende un desierto y al oeste se encuentra la casa del Ogro." (`FORT2.PAS:142-144`)
- **Contenido**:
  - Puerta de piedra (Linking) — regreso a Cuarto de juguetes (20)
  - Puerta de hierro (Linking) — conduce a Salón de Recepciones/Ogro (22)
  - Escalera (OpenLink) — desciende a Subterráneos (27)
  - Desierto (OpenLink) — largo y abrasador, conduce a Oasis (34)

### 22. El Salón de Recepciones (del Ogro)
- **Descripción**: "Todo está muy sucio y descuidado. Un fuerte olor a carroña le hace perder el equilibrio por momentos. Seguramente el Ogro usa este lugar para recibir a sus enemigos." (`FORT2.PAS:146-147`)
- **Contenido**:
  - Puerta de hierro (Linking) — regreso a Ruinas (21)
  - Puerta gris (Linking) — conduce a Patio Interior (24)
  - Anillo de bronce — más pesado que los demás anillos

### 23. El cuarto de un pintor
- **Descripción**: "Hay muchos cuadros en las paredes, pero ninguno está terminado." (`FORT2.PAS:149`)
- **Contenido**:
  - Puerta azul (Linking) — regreso a Patio (24)
  - Lienzo — tres líneas que se cortan en puntos distintos
  - Grabado — el jugador cruzando un puente con el grabado en la mano (estructura en abismo)

### 24. El Patio Interior (Parte II)
- **Descripción**: "Por el patio están diseminados varios árboles gigantescos, todos sin hojas. Parece como si el invierno reinase siempre en este lugar." (`FORT2.PAS:151-152`)
- **Contenido**:
  - Puerta gris (Linking) — regreso a Salón de Recepciones (22)
  - Puerta azul (Linking) — conduce a Cuarto del pintor (23)
  - Puerta verde (Linking) — conduce a Habitaciones del Juglar (25)
  - Puerta negra (Linking) — conduce a Alcoba del Ogro (26)

### 25. Las habitaciones del Juglar
- **Descripción**: "El ambiente de la habitación le induce a creer que el juglar no era exactamente lo que se llama una persona alegre." (`FORT2.PAS:154-155`)
- **Contenido**:
  - Puerta verde (Linking) — regreso a Patio (24)
  - Escalera (DangerLink) — necesita Escudo de Aquiles, conduce a Catacumbas (28)
  - Cuerda — con gancho en un extremo
  - Juglar (Troll) — cara larga como de caballo, quiere Arpa; diálogo: "¡Qué aburrimiento!"; al darle arpa: "Lleva algo de la fragua de Vulcano al bajar a las Catacumbas."

### 26. La alcoba del Ogro
- **Descripción**: "El aire se ha hecho casi irrespirable. Ahora usted comprende de dónde venía el mal olor reinante en el Salón de Recepciones. Nunca antes había estado en un lugar tan repulsivo." (`FORT2.PAS:157-158`)
- **Contenido**:
  - Puerta negra (Linking) — regreso a Patio (24)
  - Inscripción — "¡BUUUU!"
  - Ogro (Guard) — mezcla de hombre, cerdo y buitre; arma letal: Cubo de agua; confesión: "¡No saldrás del lago con Marmidosa tan fácilmente!"

### 27. Los Subterráneos
- **Descripción**: "Deben ser contemporáneos de las Ruinas. Usted siente como la humedad lo invade y le perfora los huesos." (`FORT2.PAS:160-161`)
- **Contenido**:
  - Escalera (OpenLink) — regreso a Ruinas (21)
  - Túnel (DangerLink) — necesita Escudo de Aquiles, conduce a Catacumbas (28)
  - Antorcha — muy brillante

### 28. Las Catacumbas
- **Descripción**: "Nunca antes había visto tantos esqueletos juntos. Más que enterrados en ese lugar, parecían haber muerto ahí. En el fondo usted divisa un hueco sin cadáver con una inscripción. La inscripción dice: 'Este es para ti'." (`FORT2.PAS:163-165`)
- **Contenido**:
  - Túnel (DangerLink) — necesita Escudo de Aquiles, regreso a Subterráneos (27)
  - Escalera (DangerLink) — necesita Escudo de Aquiles, regreso a Juglar (25)
  - Pasadizo (OpenLink) — seguro, conduce a Cataratas (29)
  - Esqueleto de Murciélago — 3 metros de ala a ala

### 29. El punto donde comienzan unas enormes cataratas
- **Descripción**: "Un repentino acceso de vértigo hace que sus rodillas se doblen. A menos de un pie de donde usted se encuentra el agua se precipita hacia el abismo." (`FORT2.PAS:167-168`)
- **Contenido**:
  - Pasadizo (OpenLink) — regreso a Catacumbas (28)
  - Anillo de plata — muy brillante
  - Catarata (OpenLink) — salto al vacío, conduce a Fondo del Lago (31)

### 30. Los bajos de las cataratas *(no referenciado en SetData, posiblemente no usado, ver Goal)*

### 31. Fondo del Lago
- **Descripción**: "Contrariamente a lo que le dijeron en su infancia, usted puede respirar debajo del agua. Usted siente una paz extraña al estar en el fondo del Lago, tal vez debida a posibles asociaciones subconcientes con su pasado embrionario, en el vientre de su madre." (`FORT2.PAS:173-175`)
- **Contenido**:
  - Grieta (DangerLink) — necesita Talismán de Nieve, conduce a Cueva de Cristal (32)
  - Reja (Hidden) — necesita Tenazas, esconde Escalera a Catedral (35)
  - Sendero dorado (DangerLink2) — **no debe** llevar Marmidosa, conduce a Orilla del Lago (33)
  - Inscripción — "Has llegado hasta Marmidosa, la rival de Excalibur. Hazla parte de tu mano y ella será parte de tu andar. Tómala, está detrás de la grieta."
  - Doncella del Lago (Troll) — hermosísima, quiere Talismán de Nieve; diálogo: "La doncella le mira con cierto aire de complicidad y exclama: ¡La cueva de cristal es tan hermosa! Si pudiera entrar al menos una vez..."; al darlo: "Las dos partes del manuscrito están guardadas en la Torre de Cristal. Y cuando vayas en busca de la segunda parte, lleva el triángulo contigo."

### 32. La Cueva de Cristal
- **Descripción**: "Hay resplandores de cristales por todas partes. En este lugar el agua se ha hecho más densa y le resulta difícil respirar." (`FORT2.PAS:177-178`)
- **Contenido**:
  - Grieta (OpenLink) — regreso a Fondo del Lago (31)
  - Marmidosa — la espada rival de Excalibur

### 33. La orilla del Lago
- **Descripción**: "Frente a usted se extiende el Lago, de aguas claras y tranquilas." (`FORT2.PAS:180`)
- **Contenido**:
  - Sendero dorado (DangerLink2) — no debe llevar Marmidosa, regreso a Fondo del Lago (31)
  - Camino (OpenLink) — conduce a Desierto (36)

### 34. Un Oasis
- **Descripción**: "Es un oasis tradicional, con varias palmeras de dátiles y un pequeño estanque de agua turbia en el centro." (`FORT2.PAS:182-183`)
- **Contenido**:
  - Desierto (OpenLink) — regreso a Ruinas (21)
  - Ruta de los camellos (OpenLink) — conduce a Catedral (35)
  - Cubo de agua — balde lleno
  - Pordiosero (Troll) — quiere Bolsa; diálogo: "El pordiosero guarda silencio y extiende su mano pidiendo una limosna."; al darla: "Si el Ogro se baña, se muere."

### 35. La Catedral
- **Descripción**: "Es un lugar impresionante. Las paredes crecen hasta una altura increíble y se unen en una serie de simétricas torres. Usted se siente oprimido por la arquitectura, como si en realidad estuviese ante los ojos de Dios, en el día del juicio final." (`FORT2.PAS:185-187`)
- **Contenido**:
  - Ruta de los camellos (OpenLink) — regreso a Oasis (34)
  - Puerta (Linking) — salida a Desierto (36)
  - Rosario — bastante común
  - Obispo (Troll) — anciano venerable, quiere Silla; diálogo: "El Obispo lo mira y fuerza una sonrisa. Está muy cansado para conversar y en toda la Catedral no hay dónde sentarse."; al darla: "Solo con el Talismán de Nieve podrás entrar hasta Marmidosa."

### 36. El Desierto otra vez
- **Descripción**: "El calor lo asfixia. Usted no comprende cómo es posible que el clima varíe tanto de un lugar a otro de la Fortaleza." (`FORT2.PAS:189-190`)
- **Contenido**:
  - Inscripción — "El Obispo le recomendó cierto objeto para protegerse a la hora de coger a Marmidosa. ¡No intente cruzar el camino en esta dirección con dicho objeto encima!"
  - Camino (DangerLink2) — **no debe** llevar Talismán de Nieve (en esta dirección), conduce a Orilla del Lago (33)
  - Puerta (Linking) — entrada a Catedral (35)
  - Muralla (Hidden) — necesita Piedra verde, esconde Avenida de las flores (OpenLink) a Valle (37)
  - Escudo de Aquiles — escudo forjado por Hefestos

### 37. Un extenso valle
- **Descripción**: "Siente deseos de construir una casa y quedarse a vivir en el valle. Por todos lados crece una especie de árbol frutal que, valiéndose de dos manos que salen de su tronco, es capaz de cultivarse ella misma." (`FORT2.PAS:192-194`)
- **Contenido**:
  - Avenida de las flores (OpenLink) — regreso a Desierto (36)
  - Montañas (OpenLink) — conduce a Pico Negro (38)
  - Camello (Troll) — viejo y maltratado, quiere Botella de vino; diálogo: "¡Dame más!"; al darla: "Las dos últimas letras del segundo nombre de la Hija del Hechicero son 'KA'."
  - Bolsa de semillas — semillas de los árboles del valle

### 38. La cima del Pico Negro
- **Descripción**: "Nunca antes había estado a tanta altura. Usted se pregunta por qué la montaña es llamada 'El Pico Negro' si en realidad está cubierta de nieve." (`FORT2.PAS:196-197`)
- **Contenido**:
  - Montañas (OpenLink) — regreso a Valle (37)
  - Precipicio (DangerLink) — necesita Saltador, conduce a Ciudad Abandonada (40)
  - Ladera (OpenLink) — conduce a Campo cultivado (42)
  - Puerta de Madera (Linking) — entrada a Choza del monje (39)

### 39. La choza de un monje
- **Descripción**: "El suelo está muy limpio, al igual que los muebles y las ventanas. Hay una gran cantidad de cuentas regadas por el suelo." (`FORT2.PAS:199-200`)
- **Contenido**:
  - Puerta de Madera (Linking) — regreso a Pico Negro (38)
  - Monje (Troll) — bastante joven, quiere Rosario; diálogo: "El monje no le responde. Está muy ocupado recogiendo las cuentas del suelo."; al darlo: "Para descender por el precipicio debes llevar algo que amortigüe el golpe al final."

### 40. La Ciudad Abandonada
- **Descripción**: "A pesar de ser más antigua que las ruinas, la ciudad se conserva intacta. Usted oye el ruido de la gente en las calles y siente los olores de los alimentos en las cocinas, pero no son más que ilusiones. La ciudad está abandonada desde hace siglos." (`FORT2.PAS:203-205`)
- **Contenido**:
  - Inscripción — "Aquí habitaron los horantes durante mucho tiempo, hasta que La Bestia ocupó el lugar. Ellos levantaron cada pared de la Fortaleza, solo ellos saben cómo salir."
  - Túnel (OpenLink) — conduce a Ruinas (21)
  - Escalera (OpenLink) — regreso a Valle (37)
  - Puerta de Hierro (Linking) — entrada a Choza del Sabio (41)
  - Estatua de Cristal (Hidden) — necesita Corta-Cristales, esconde Horante (Troll)

### 41. La choza del Sabio
- **Descripción**: "El lugar se ajusta perfectamente a su concepto de desorden. Usted se pregunta cómo el sabio puede vivir en semejante caos. Hay varios esqueletos, al parecer, una colección incipiente." (`FORT2.PAS:206-207`)
- **Contenido**:
  - Puerta de Hierro (Linking) — regreso a Ciudad Abandonada (40)
  - Sabio (Troll) — pequeño, espejuelos enormes, quiere Esqueleto de Murciélago; diálogo: "El sabio está muy distraído haciendo un anillo de papel algo torcido."; al darlo: "De todas las cosas sobre la tierra, la que más me fascina es la cinta de Moebius. Empiezas a recorrerla por adentro y cuando vienes a ver... ¡estás afuera!"
  - Cinta de Moebius — papel con torcedura, extremos pegados
  - Péndulo — oscila colgado de un punto invisible

### 42. Un campo cultivado
- **Descripción**: "Todos los sembrados parecen bastante descuidados. Probablemente el labrador no sea capaz de atender una cantidad tan grande de tierra al mismo tiempo." (`FORT2.PAS:209-210`)
- **Contenido**:
  - Ladera (OpenLink) — regreso a Pico Negro (38)
  - Río (DangerLink) — necesita Cuerda, conduce a Torre de Cristal abajo (43)
  - Tenazas — muy fuertes
  - Labrador (Troll) — hombre robusto y maltratado, quiere Bolsa de semillas; diálogo: "¡Qué cansancio! Creo que es demasiada tierra para una sola persona."; al darla: "No siempre las cosas son lo que parecen. La realidad tiene muchas caras y nunca sabemos si estamos mirando la verdadera. Mantén tu mente abierta."

### 43. El exterior de la Torre de Cristal
- **Descripción**: "La Torre de Cristal crece vertiginosamente hasta perderse entre las nubes." (`FORT2.PAS:211`)
- **Contenido**:
  - Río (DangerLink) — necesita Cuerda, regreso a Campo (42)
  - Ébano (Hidden) — muy alto, breaker: "NADA" (no rompible)
  - Puerta de Hierro (Linking) — entrada a Calabozos (47)
  - Escalera de Caracol (OpenLink) — asciende a Punta de la Torre (44)

### 44. La punta de la Torre de Cristal
- **Descripción**: "Probablemente se encuentre a varios kilómetros de altura. Usted se alegra de que no hayan ventanas en el lugar." (`FORT2.PAS:214-215`)
- **Contenido**:
  - Escalera de Caracol (OpenLink) — regreso a base de Torre (43)
  - Esfera (Hidden) — tres metros de diámetro, parece de carne; necesita Marmidosa para abrir; esconde Tablilla de Madera (primera mitad del Manuscrito de los Horantes, texto codificado)
  - Puerta de Cristal (RiddleLink) — acertijo: "¿Cuál es el nombre completo de la hija del Hechicero?" → "Aura Srka", conduce a Alcoba de Aura (45)

### 45. La alcoba de la hija del Hechicero (Aura)
- **Descripción**: "Esta es la alcoba donde la hija del Hechicero se alojaba temporalmente. Es muy cómoda y tiene muchos cuadros iguales al que usted lleva." (`FORT2.PAS:217-218`)
- **Contenido**:
  - Puerta de Cristal (Linking) — regreso a Punta de la Torre (44)
  - Carta (Hidden) — sin breaker (siempre visible), esconde Puerta Secreta (DangerLink, necesita Lienzo) a Alcoba Secreta (46)
  - Espejo — roto

### 46. La Alcoba Secreta
- **Descripción**: "Es mucho mayor que la otra alcoba. Es casi seguro que la hija del Hechicero viva en este lugar permanentemente." (`FORT2.PAS:220-221`)
- **Contenido**:
  - Puerta Secreta (Linking) — regreso a Alcoba (45)
  - Hija del Hechicero (PDaugther, tipo especial de Guard) — serpiente de 15 metros, 3 cabezas, escamas; arma letal: Aguja; confesión: "¡Mata a todos los que te mintieron si quieres salir!"; si se usa arma incorrecta, el jugador muere devorado

### 47. Los Calabozos (Parte II)
- **Descripción**: "Los calabozos están formados por varios pasillos paralelos, llenos de celdas a ambos lados." (`FORT2.PAS:223-224`)
- **Contenido**:
  - Puerta de Hierro (Linking) — regreso a Torre de Cristal (43)
  - Reja (Linking) — contraseña: "Grifo", conduce a Celda (48)
  - Puerta Gris (Linking) — conduce a Antesala de la Prueba (49)
  - Carcelero (Guard) — hombre rudo; arma letal: Marmidosa; confesión: "¡Te será muy difícil abrir la celda, porque la palabra mágica es el nombre de la primera criatura que viste al salir del cuarto de huéspedes!" (= Grifo)

### 48. Una celda
- **Descripción**: "Debe ser un verdadero suplicio el estar encerrado aquí. Todo el suelo está cubierto de afiladas hojas, excepto en una esquina, donde se supone que está el prisionero." (`FORT2.PAS:226-227`)
- **Contenido**:
  - Reja (Linking) — regreso a Calabozos (47)
  - Encapuchado (Troll) — criatura regida por el número 7 (7 brazos, 7 pies, 7 dedos), quiere Receta; diálogo: "Pareces haber estado viajando. Seguramente has visto algo que me pertenece por ahí... ¿podrías traérmelo?"; al darla: "El nombre de la hija del Hechicero tiene ocho letras, una está repetida tres veces y otra dos." (= AURA SRKA: A repetida 3 veces, R repetida 2 veces)

### 49. La Antesala de la Prueba
- **Descripción**: "Es un salón circular. La luz del sol entra por unos vitrales rojos y el lugar luce como pintado con sangre." (`FORT2.PAS:229-230`)
- **Contenido**:
  - Puerta Gris (Linking) — regreso a Calabozos (47)
  - Inscripción — "En este punto comienza la prueba de los anillos. Continúa con el que hayas elegido y deja los demás."
  - Arco — con este arco mataron a Hycrk, uno de los doce inmortales
  - Túnel (DangerLink) — necesita Arco, regreso a Comedor (14) (murciélagos gigantes)
  - Puerta Verde (DangerLink2) — **no debe** llevar Anillo de oro, conduce a Salón Verde (50)

### 50. El Salón Verde
- **Descripción**: "Es un salón de pruebas tradicional. Este tipo de salón fue usado ampliamente por los horantes para educar a sus hijos." (`FORT2.PAS:232-233`)
- **Contenido**:
  - Puerta Verde (DangerLink2) — no debe llevar Anillo de oro, regreso a Antesala (49)
  - Puerta Azul (DangerLink2) — **no debe** llevar Anillo de plata, conduce a Salón Azul (51)

### 51. El Salón Azul
- **Descripción**: "Es un salón de pruebas tradicional..." (`FORT2.PAS:235-236`)
- **Contenido**:
  - Puerta Azul (DangerLink2) — no debe llevar Anillo de plata, regreso a Salón Verde (50)
  - Puerta Blanca (DangerLink2) — **no debe** llevar Anillo de bronce, conduce a Salón Blanco (52)

### 52. El Salón Blanco
- **Descripción**: "Es un salón de pruebas tradicional... Es el último de la prueba." (`FORT2.PAS:238-239`)
- **Contenido**:
  - Puerta Blanca (DangerLink2) — no debe llevar Anillo de bronce, regreso a Salón Azul (51)
  - Puerta triangular (DangerLink) — **necesita** Cinta de Moebius, conduce a Límites/Muralla (53)

### 53. Los límites de la Fortaleza
- **Descripción**: "A su derecha crece la tercera muralla, hasta una altura irracional. Usted no puede creer que aquí termine la Fortaleza. Del otro lado de la muralla se escucha (usted no entiende cómo) el canto de los pájaros y el sonido del viento en los árboles." (`FORT2.PAS:241-243`)
- **Contenido**:
  - Puerta triangular (DangerLink) — necesita Cinta de Moebius, regreso a Salón Blanco (52)
  - Puente (DangerLink) — necesita Grabado, conduce a Pirámide (54)
  - Muralla (Hidden) — tercera muralla, breaker: "NADA" (no rompible)
  - Guardián (Troll) — viejo, quemado por el sol, quiere Sombrero; diálogo: "¡Qué calor!"; al darlo: "El anciano le cuenta una historia incoherente sobre un héroe que derrota a una serpiente gigante armado de una aguja."

### 54. La Pirámide del Hechicero
- **Descripción**: "Es una construcción gigantesca, a base de piedras. Al parecer, las piedras fueron colocadas sin orden alguno, olvidando las ventanas. El lugar está iluminado con numerosas antorchas." (`FORT2.PAS:245-247`)
- **Contenido**:
  - Puente (DangerLink) — necesita Grabado, regreso a Límites (53)
  - Columna de Hielo (Hidden) — necesita Antorcha, esconde Puerta de Roble (RiddleLink) a Habitaciones del Hechicero (55)

### 55. Las Habitaciones del Hechicero
- **Descripción**: "Las habitaciones del Hechicero están dentro de una pirámide interior. Todo es igual a la gran pirámide, pero en una escala menor. Hay miles de espadas colgadas de la pared." (`FORT2.PAS:248-249`)
- **Contenido**:
  - Puerta de Roble (Linking) — regreso a Pirámide (54)
  - Hechicero (Troll) — hombre inmenso, barba blanca, túnica negra, vara con carabela; quiere Marmidosa; en silencio; al darle Marmidosa: "No soy tu enemigo. Es mi hija quien ha elaborado este diabólico plan para eliminarnos. Rompe la carta que te dejó en la Torre de Cristal y ocurrirá un milagro."
