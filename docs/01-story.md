# 01 — Historia y Narrativa

## Ambientación General

La Fortaleza es un lugar sobrenatural y maldito que existe fuera del tiempo y el espacio normales. Es a la vez una construcción física y una entidad viva: la Bestia habita en cada pared, cada habitación, el aire mismo. Según la introducción (`INSTR1.PAS:31-37`):

> "La Bestia es una de las criaturas más temidas y misteriosas del universo. Según varios informes que nos han llegado últimamente, habita un lugar llamado la Fortaleza, aunque hay quienes dicen que la Bestia y la Fortaleza son una misma cosa. Nadie ha visto a la Bestia (quienes lo hicieron no pudieron contarlo nunca). Solo sabemos que la Fortaleza aparece todos los martes 24 de abril en los años bisiestos, o sea, casi nunca."

## Parte I — En las entrañas de la Bestia

### Introducción (`INSTR1.PAS:15-54`)

El protagonista es un hombre común, de vida rutinaria y mediocre. Una mañana encuentra una carta junto a la puerta:

> "Estimado señor:
>  Tengo el alto honor de comunicarle que usted ha sido designado para cumplir una de las misiones más importantes de la historia del hombre: Eliminar a la Bestia."

La carta, firmada por el "General X, Jefe de la Oficina de Casualidades", instruye al protagonista a adentrarse en la Fortaleza y matar a la Bestia.

La presentación en pantalla (`PRESENT1.PAS:103-120`) muestra:

> **L A  F O R T A L E Z A**
> *En las entrañas de la Bestia*

### La Misión

El jugador debe penetrar en la Fortaleza, llegar al interior del cuerpo de la Bestia y destruir sus cuatro centros vitales:

- **Centro de los pulmones** (habitación 19)
- **Centro del estómago** (habitación 20)
- **Centro del corazón** (habitación 21)
- **Centro del cerebro** (habitación 22)

Además, debe matar al **Troll** que habita los Baños de la Bestia (habitación 12).

### Condición de Victoria

La función `Fort.Goal` (`FORT1.PAS:28-35`):

> Que los cuatro centros vitales hayan sido eliminados (no estén en sus respectivas habitaciones) y que el Troll de los Baños tampoco esté.

### Final — Victoria

Al vencer, el juego muestra (`FORT1.PAS:830-838`):

> "Usted ha vencido a la Bestia."
> "Parece ser una persona persistente y eso es un mérito muy grande."
> "La persistencia es indispensable para los que luchan por el bien, sobre todo porque los que luchan por el mal son muy persistentes también."
> "Veremos si en la próxima versión de La Fortaleza tiene igual suerte."
> "                                             Un servidor:"
> "                                             M. Cepero"

### Final — Derrota (`FORT1.PAS:843`)

> "Su entierro se efectuará el próximo domingo a las 3:00 am. Está invitado."

---

## Parte II — La venganza de la Bestia

### Introducción (`INSTR2.PAS:15-43`)

Tras matar a la Bestia en la primera parte, el protagonista queda profundamente dormido mientras la Fortaleza se transforma:

> "La Bestia había planeado una venganza terrible. En el mismo instante en que usted la destruyó, ella echó a andar su diabólico plan. Usted quedó profundamente dormido mientras la Fortaleza cambiaba. Cada cosa se descompuso en un caudal único y luego, a partir de esa masa gigantesca, reapareció la Fortaleza."

> "Usted despierta en un cuarto, habiendo perdido toda noción de tiempo y espacio, y debe tratar de salir. La Bestia ha dejado una persona (si se le puede llamar así) encargada de que usted perezca irremediablemente."

La presentación (`PRESENT2.PAS:113-124`):

> **L A  F O R T A L E Z A  II**
> *La venganza de la Bestia*

Con epígrafe de Franz Kafka:

> "En la lucha entre tú y el mundo, apoya al mundo."

### La Hija del Hechicero

El antagonista principal es la **Hija del Hechicero**, cuyo nombre completo es **Aura Srka**. En realidad no es humana: es una serpiente gigante de quince metros con tres cabezas y piel de gruesas escamas (`FORT2.PAS:830-832`).

El Hechicero mismo no es el enemigo; está atrapado en la pirámide y revela que fue su hija quien elaboró el plan diabólico (`FORT2.PAS:937-941`):

> "No soy tu enemigo. Es mi hija quien ha elaborado este diabólico plan para eliminarnos. Rompe la carta que te dejó en la Torre de Cristal y ocurrirá un milagro."

Para matar a la Hija del Hechicero se necesita la **Aguja** (arma específica). Si se intenta matarla con cualquier otra arma, la serpiente devora al jugador (`CASTLES.PAS:1339-1340`):

> "Usted fracasa en su intento. La enorme serpiente se lanza sobre usted y lo devora en pocos segundos."

Su confesión al morir (`FORT2.PAS:834-835`):

> "¡Mata a todos los que te mintieron si quieres salir!"

### Los Horantes

Raza ancestral de constructores. Según la inscripción en la Ciudad Abandonada (`FORT2.PAS:736-738`):

> "Aquí habitaron los horantes durante mucho tiempo, hasta que La Bestia ocupó el lugar. Ellos levantaron cada pared de la Fortaleza, solo ellos saben cómo salir."

El último Horante sobreviviente está atrapado en una Estatua de Cristal en la Ciudad Abandonada (habitación 40). Necesita el Muñeco Diabólico para liberarse. A cambio, da la clave final:

> "Busca las dos mitades del Manuscrito de los Horantes y descífralo. Luego coloca las marcas para abrir la Fortaleza."

### El Plan de Escape

La condición de victoria (`FORT2.PAS:71-79`) requiere:

1. **Matar** al Monstruo (habitación 9) y a la Hija del Hechicero (habitación 46)
2. **Colocar** objetos específicos en habitaciones específicas (como un ritual):
   - Antorcha en la habitación de huéspedes (1)
   - Péndulo en el Salón de Fumar (3)
   - Espejo en el cuarto de Aura (4)
   - Bote en la orilla 2 del Río Negro (12)
   - Rosa diamante en el fondo del Lago (31)
   - Escudo de Aquiles en la Ciudad Abandonada (40)
   - Cinta de Moebius en el exterior de la Torre de Cristal (43)

### El Hechicero y Marmidosa

La espada **Marmidosa**, rival de Excalibur, es necesaria para enfrentar al Hechicero. Se encuentra en la Cueva de Cristal (habitación 32), protegida por una grieta que requiere el Talismán de Nieve.

Al darle Marmidosa al Hechicero (habitación 55), este revela la verdad sobre su hija. La carta en la Torre de Cristal debe ser rota.

### Final — Victoria (`FORT2.PAS:1101-1135`)

> "De repente las paredes comienzan a desvanecerse. ¡Ha logrado salir de la Fortaleza!"

**Epílogo:**

> "Usted mira al cielo agradecido y besa la tierra."
> "Después de que la emoción del primer momento hubo pasado usted se sienta sobre una piedra al borde de la carretera (recuerde que ha regresado a la civilización) y comienza a pensar. '¿Para qué salí?', se pregunta, 'si el exterior nunca me gustó tanto'."
> "Usted recuerda a la Doncella del Lago, y piensa en la vida que hubiera podido llevar junto a ella."
> "Piensa también en el Hechicero, un poderoso amigo, y en la remota y hermosa posibilidad de hacer renacer la civilización de los horantes."

Reflexión final:

> "¿Quién está al otro extremo de los hilos que manejan al hombre?"
> "¿Quién nos hace confundir lo que somos y lo que queremos ser?"
> "¿Quién es el responsable de nuestros errores?"
> "¿Quién sino nosotros mismos?"

El giro final:

> "Usted vuelve la cabeza hacia el lugar que ocupó la Fortaleza. Ahora lo comprende todo claramente, esta era la venganza de la Bestia: dejarlo vivir, pero fuera de la Fortaleza."
> "¿Quería un final feliz? Espere la próxima versión."

### Final — Derrota

Igual que en la Parte I (`FORT2.PAS:1141`):

> "Su entierro se efectuará el próximo domingo a las 3:00 am. Está invitado."

---

## Personajes Principales

| Personaje | Rol | Parte |
|-----------|-----|-------|
| **El Protagonista** | Hombre común ("Indy"), elegido para eliminar a la Bestia | I, II |
| **La Bestia** | Entidad maligna que es la Fortaleza misma | I, II |
| **General X** | Jefe de la Oficina de Casualidades, envía la carta | I |
| **La Hija del Hechicero (Aura Srka)** | Serpiente de 3 cabezas, antagonista principal de la Parte II | II |
| **El Hechicero** | Padre de Aura, prisionero en su propia pirámide, aliado potencial | II |
| **Los Horantes** | Raza ancestral que construyó la Fortaleza | II (lore) |
| **M. Cepero** | Autor del juego (aparece en los créditos y epílogos) | I, II |
