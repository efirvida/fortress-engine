# 05 — NPCs y Enemigos

## Tipos de Personajes en el Motor

| Tipo Pascal | Clase | Comportamiento |
|-------------|-------|----------------|
| `Troll` | `CASTLES.PAS:99-110` | NPC amistoso/neutral; acepta un regalo (`likeness`); si es el correcto, revela información |
| `Guard` | `CASTLES.PAS:149-156` | Enemigo; solo muere con un arma específica (`lethalweap`); al morir confiesa (`confession`) |
| `TDaugther` | `CASTLES.PAS:193-196` | Guard especial (solo Parte II); si se ataca con arma incorrecta, **mata al jugador** |
| `Man` | `CASTLES.PAS:73-97` | El jugador ("Indy") |

**Mecánica de Troll** (`CASTLES.PAS:854-859`):
- Si el objeto entregado (`gift`) coincide con `likeness` → `happy = TRUE` → al interrogar habla (`HiData`)
- Si no coincide → `happy = FALSE` → responde con desdén (`LowData`)

**Mecánica de Guard** (`CASTLES.PAS:964-974`):
- Si el arma usada coincide con `lethalweap` → muere, revela `confession`
- Si no → "Todos sus esfuerzos son en vano. Probablemente no esté usando el objeto indicado." (`_Ja_ja_ja`)

---

## Parte I — NPCs

### Trolls (aliados potenciales)

| NPC | Habitación | Quiere | Ubicación del objeto | Diálogo infeliz | Recompensa |
|-----|-----------|--------|---------------------|-----------------|------------|
| **Llamador de bronce** | 1 (Exterior) | Cigarro | 15 (Sala infusiones) | "¿Me puede regalar un cigarro?" | Información codificada |
| **Trebol** (5 hojas) | 2 (Salón, dentro de Monolito) | Vaso de agua | 6 (Biblioteca) | "Dame agua, por favor..." | Información codificada |
| **Estatua de Atenea** | 4 (Patio) | (decodificado) | ? | "¡Sal de mi presencia, estúpido mortal!" | Información codificada |
| **Estatua de Hermes** | 4 (Patio) | (decodificado) | ? | "La humedad me destruye." | Información codificada |
| **Bruja** | 8 (Alcoba) | Escoba | 3 (Sala juegos) | "Tráeme mi escoba y te daré un consejo." | Consejo codificado |
| **Homúnculo** | 10 (Laboratorio) | Poción para crecer | 8 (Alcoba bruja) | "¡Quiero crecer!" | Información codificada |
| **Troll** | 12 (Baños) | Polvo mágico | 8 (Alcoba bruja) | "No me mates, por favor. Haz que nadie pueda ver mi fealdad." | Información codificada |
| **Doncella** | 14 (Alcoba doncella) | (decodificado) | ? | "¿Qué brusco! Un caballero debe dirigirse a una dama de otra forma." | Información codificada |
| **Esqueleto** | 16 (Calabozos) | Taza de café | 15 (Sala infusiones) | "Dame algo para calentarme la barriga, por favor." | Información codificada |
| **Ratón** | 23 (Almacenes) | (decodificado) | ? | "No tengo tiempo para atenderte. Llevo medio siglo buscando la quinta esencia." | Información codificada |
| **Araña** | 27 (Puente) | Hilo de Ariadna | 3 (Sala juegos) | "¡Pssssssss!" | "Busca al Minotauro y mátalo con la espada." |
| **Crunch** | 28 (Antesala) | Pastel de cerezas | 1 (Exterior) | "¡Qué hambre!" | "El 12 te guiará en el Laberinto. Luego solo debes dar un paso." |
| **Dédalo** | 28 (Antesala) | Vendajes | 9 (Cuarto guerrero) | "Me muero..." | "Solo el hierro te protegerá contra las flores." |
| **Bailarina** | 25 (Salón cristal) | Máquina del tiempo | 10 (Laboratorio) | "Quiero ser joven para siempre." | Información codificada |

### Guards (enemigos)

| Enemigo | Habitación | Arma letal | Confesión al morir |
|---------|-----------|------------|-------------------|
| **Cíclope** | 6 (Biblioteca) | (decodificado) | "¡Arrrggghhhh! ¡Me has matado!" + decodificado |
| **Arpía** | 15 (Sala infusiones) | (decodificado) | (decodificado) |
| **Lobo** | 24 (Páramo) | **Látigo** | (decodificado) |
| **Centro de los pulmones** | 19 (Pulmones) | (decodificado) | (decodificado) |
| **Centro del estómago** | 20 (Estómago) | (decodificado) | "¡Usted ha matado al centro del estómago!" |
| **Centro del corazón** | 21 (Corazón) | (decodificado) | (decodificado) |
| **Centro del cerebro** | 22 (Cerebro) | (decodificado) | "XVBCZXV XBVCZX BVZXC!!!!!" |
| **Minotauro** | 29 (Cueva) | **Espada** | "¡Me has matado! Coge la antorcha del número divino y rompe la columna de cristal." |

---

## Parte II — NPCs

### Trolls (aliados potenciales)

| NPC | Habitación | Quiere | Ubicación del objeto | Diálogo infeliz | Recompensa |
|-----|-----------|--------|---------------------|-----------------|------------|
| **Gato** | 10 (Baúl) | Pescado | 7 (Cocina) | "¡No molestes!" | "La piedra verde te servirá para romper la segunda muralla." |
| **Monstruo** | 9 (Calabozo) | Muslo de carnero | 7 (Cocina) | "¡Grrrr! ¡Hambre!" | Advertencia sobre el Hechicero y Marmidosa |
| **Caronte** | 11 (Orilla 1) | Reloj de arena | 8 (Terrazas) | "Tráeme el reloj de arena, pero víralo antes de entregármelo." | "Dentro del blanco está la llave de la muralla." |
| **Jardinero** | 13 (Jardines) | Hacha | 6 (Leñador) | "El jardinero no le presta atención..." | Consejo sobre los anillos |
| **Dinosaurio** | 14 (Comedor, en Huevo) | Sonajero | 20 (Juguetes) | "¡Guaaaaaa! ¡Guaaaaaa!" | "Maúllale al gato." |
| **Dragón** | 18 (Velas) | Daga | 6 (Leñador) | (Silencio) | "Las palabras mágicas para entrar en el cuarto del tesoro son: 'Omicuos Ihanti'." |
| **Juglar** | 25 (Juglar) | Arpa | 17 (Tesoros) | "¡Qué aburrimiento!" | "Lleva algo de la fragua de Vulcano al bajar a las Catacumbas." |
| **Doncella del Lago** | 31 (Lago) | Talismán de Nieve | 20 (Juguetes) | "¡La cueva de cristal es tan hermosa! Si pudiera entrar al menos una vez..." | Ubicación del Manuscrito |
| **Pordiosero** | 34 (Oasis) | Bolsa (oro) | 17 (Tesoros) | "El pordiosero guarda silencio y extiende su mano..." | "Si el Ogro se baña, se muere." |
| **Obispo** | 35 (Catedral) | Silla | 8 (Terrazas) | "El Obispo lo mira y fuerza una sonrisa..." | "Solo con el Talismán de Nieve podrás entrar hasta Marmidosa." |
| **Camello** | 37 (Valle) | Botella de vino | 6 (Leñador) | "¡Dame más!" | "Las dos últimas letras del segundo nombre de la Hija del Hechicero son 'KA'." |
| **Monje** | 39 (Pico Negro) | Rosario | 35 (Catedral) | "El monje no le responde. Está muy ocupado recogiendo las cuentas..." | Pista sobre el Saltador |
| **Horante** | 40 (Ciudad, en Estatua) | Muñeco diabólico | 15 (Sastrería) | Dolor en la pierna | "Busca las dos mitades del Manuscrito de los Horantes..." |
| **Sabio** | 41 (Choza) | Esqueleto de Murciélago | 28 (Catacumbas) | Haciendo anillo de papel torcido | Reflexión sobre la cinta de Moebius |
| **Labrador** | 42 (Campo) | Bolsa de semillas | 37 (Valle) | "¡Qué cansancio!" | "No siempre las cosas son lo que parecen..." |
| **Encapuchado** | 48 (Celda) | Receta | 7 (Cocina) | "Pareces haber estado viajando..." | Pista sobre el nombre de Aura |
| **Guardián** | 53 (Límites) | Sombrero | 16 (Jardinero) | "¡Qué calor!" | Historia de la serpiente y la aguja |
| **Hechicero** | 55 (Pirámide) | Marmidosa | 32 (Cueva Cristal) | (Silencio) | Revelación: la hija es la villana |

### Guards (enemigos)

| Enemigo | Habitación | Arma letal | Confesión |
|---------|-----------|------------|-----------|
| **Grifo** | 2 (Pasillo) | Daga | "¡Aura!" → la contraseña de la Reja es "Grifo" |
| **Inmortal** | 19 (Cuarto Inmortal) | Arco | "No confundas la tercera muralla con la tercera barrera..." |
| **Ogro** | 26 (Alcoba Ogro) | Cubo de agua | "¡No saldrás del lago con Marmidosa tan fácilmente!" |
| **Carcelero** | 47 (Calabozos) | Marmidosa | "La palabra mágica es el nombre de la primera criatura que viste al salir del cuarto de huéspedes." |

### TDaugther (jefe final especial)

| Enemigo | Habitación | Arma letal | Arma incorrecta → |
|---------|-----------|------------|-------------------|
| **Hija del Hechicero** | 46 (Alcoba Secreta) | **Aguja** | El jugador es devorado: "Usted fracasa en su intento. La enorme serpiente se lanza sobre usted y lo devora en pocos segundos." |

**Descripción**: "Usted está a punto de desmayarse. La hija del Hechicero no es exactamente como usted esperaba. En realidad se parece más a una serpiente de quince metros y tres cabezas, con la piel llena de gruesas escamas." (`FORT2.PAS:830-832`)

**Confesión**: "Usted clava fuertemente la aguja entre las escamas. Las cabezas le miran llenas de ira y hay una que exclama: '¡Mata a todos los que te mintieron si quieres salir!'" (`FORT2.PAS:833-835`)

### Apariciones al morir (eventos especiales)

Cuando la Hija del Hechicero muere, aparece el **Cáliz**:

> "En el lugar que ocupaba la Hija del Hechicero ha aparecido un objeto." (`FORT2.PAS:44`)

Cuando el Hechicero es atacado (sin Marmidosa), hay un evento especial (`FORT2.PAS:37-39`):

> "Usted solo alcanza a herir al Hechicero, que ha desaparecido misteriosamente."
> "Se escucha una voz que dice: '¡Estúpido! Vas por el camino equivocado.'"
