# 06 — Mecánicas del Juego

## Motor Principal

Todo el juego se ejecuta sobre el objeto `Castle` (`CASTLES.PAS:158-191`). El bucle principal es:

```pascal
while not((f^.Goal) or (f^.IsOver)) do
  begin
    f^.AskMan;      // preguntar al jugador
    f^.ClearWish;   // limpiar deseo anterior
    f^.MakeManWish; // ejecutar comando
  end;
```

Si `Goal` es verdadero → victoria. Si `IsOver` → derrota (jugador muerto).

## Sistema de Inventario

- **Capacidad máxima**: `LWeight = 40` "bolsas de arena del Río Negro" (`CASTLES.PAS:11`)
- Cada objeto tiene un atributo `mase` (peso)
- Si `bag^.Heaviness + whatP^.mase > LWeight` → "Sería demasiado peso."
- Si el objeto pesa más de `LWeight` individualmente → "Usted no puede cargar con eso."
- Implementado como `Suitcase` (`CASTLES.PAS:66-71`), una colección con cálculo de peso

## Movimiento

El jugador se mueve a través de **uniones** (puertas, túneles, escaleras, etc.) usando verbos de movimiento. El flujo es:

1. `Castle.Go` → `Man.WalkT(door)` (`CASTLES.PAS:723-757`)
2. Busca el objeto `door` en la habitación actual
3. Si es un `Linking` (o subtipo), obtiene su `Dest`
4. Si está abierto (`opn = TRUE`), mueve al jugador con `Man.Go(newRoom)`
5. Ejecuta `link^.Pass(body)` que puede tener efectos (mensaje, muerte por DangerLink)
6. Marca la habitación como visitada

## Tipos de Puertas/Uniones

| Tipo | Constructor | Mecánica |
|------|------------|----------|
| `Linking` | `Init(nm, desc, keyword, pscm, destt)` | Puerta con contraseña opcional; si `keyword = ''`, siempre abierta |
| `OpenLink` | Hereda de `Linking`, siempre `opn = TRUE` | Pasaje siempre abierto |
| `DangerLink` | `Init(nm, desc, keyword, pscm, tlsm, destt)` | Requiere ítem `tlsm` en inventario; sin él, `Man.Die` |
| `DangerLink2` | Hereda de `DangerLink` | **No debe** llevar `tlsm`; si lo lleva, `Man.Die` |
| `RiddleLink` | `Init(nm, desc, rddle, answ, pscm, destt)` | Acertijo; `Open(psKey)` compara con `answer` |

## Sistema de Combate

1. `Castle.Kill` → `Man.Kill(who, weapon)` (`CASTLES.PAS:586-609`)
2. Busca al objetivo en la habitación actual
3. Verifica que el arma esté en el inventario
4. Si el objetivo es `Troll` o `Guard` → `whoP^.Die(weapon)`
5. **Guard**: compara `weapon` con `lethalweap`; si coincide → muere y confiesa; si no → "Todos sus esfuerzos son en vano."
6. **Troll**: siempre muere con cualquier arma (grita "AAAAARRRGGGGG!!!")
7. **TDaugther**: si `weapon ≠ lethalweap` → **el jugador muere**

## Sistema de Regalos (Dar)

1. `Castle.Give` → `Man.Give(what, who)` (`CASTLES.PAS:678-707`)
2. Solo funciona con `Troll` (los `Guard` rechazan regalos)
3. `Troll.Acept(gift)`: compara `gift^.name` con `likeness`
4. Si coincide → `happy = TRUE` → al interrogar revela información

## Sistema de Ruptura (Romper)

1. `Castle.Break` → `Man.Break(what, how)` → `Room.Break(nm, nw)` (`CASTLES.PAS:437-462`)
2. Solo funciona con objetos `Hidden`
3. `Hidden.Break(weapon)`: compara `weapon` con `breaker`
4. Si coincide o `breaker = nil` → revela el objeto oculto

## Interrogatorio (Preguntar)

1. `Castle.Ask` → `Man.Ask(who)` → `whoP^.Speak` (`CASTLES.PAS:522-538`)
2. `Troll.Speak`: si `happy` → `HiData`, sino → `LowData`
3. `LivingThing.Speak`: por defecto → `_Silence` ("No desea hablar con usted.")

## Sistema de Porciento

`Castle.Percent` (`CASTLES.PAS:1171-1177`):

```
% = (habitaciones visitadas / total de habitaciones) × 100
```

## Sistema de Rastros (Save/Replay)

Innovador sistema de persistencia:

- **Salvar** (`Castle.SaveTrack`): guarda todos los comandos "relevantes" (los que cambian el estado) en un archivo de texto
- **Ejecutar** (`Castle.ExecTrack`): reproduce los comandos desde un archivo
- Los comandos no relevantes (mirar, inventario, interrogar, etc.) no se guardan
- El archivo puede editarse externamente; soporta comentarios `{ }`
- Flag `VerboseExec` controla si se muestra la salida durante la reproducción

## Muerte y Fin del Juego

- `Man.Die(weapon)` (`CASTLES.PAS:540-546`): establece `dead = TRUE`, muestra "Lamento informarle que usted está muerto."
- `Castle.IsOver` = `m^.dead`
- Causas de muerte:
  - Cruzar `DangerLink` sin el ítem requerido
  - Cruzar `DangerLink2` con el ítem prohibido
  - Atacar a `TDaugther` con arma incorrecta
  - Comando `TERMINAR` / `ABANDONAR`
  - Tener el Pañuelo al final de la Parte II (`FORT2.PAS:69-70`)
  - Atacar al Hechicero sin Marmidosa

## Sonido

Sistema de sonido vía PC Speaker (`SOUNDS.PAS` y `SE.ASM`):

| Procedimiento | Uso |
|--------------|-----|
| `Thunder` | Presentación (trueno) |
| `Ouch` | Golpe, muerte, transición |
| `LaserShoot` | Efecto base |
| `SuccessSound` | Victoria (secuencia compleja in-situ en FORT1/FORT2) |
| `DefeatSound` | Derrota (tono descendente) |

## Configuración

Archivo `FORT.INI` (`CMDLINE.PAS:53-85`):

| Clave | Efecto |
|-------|--------|
| `USEEGA=1` | Forzar modo EGA |
| `CHECKSNOW=1` | Verificar snow de CGA |
| `VERBOSEEXEC=1` | Mostrar salida al ejecutar rastros |
| `EXECTRACK=archivo` | Ejecutar rastro al iniciar |

Parámetros de línea de comandos: `/I-` (silencioso), `/S-`, `/E-`, o archivo de rastro.

## Inicialización

1. Verificar memoria disponible (≥ 80000 bytes Parte I, ≥ 90000 Parte II)
2. Crear habitaciones con `RoomAr` (nombre + descripción)
3. Crear al jugador: `ManX := new( PMan, Init( 'Indy', 'Sad' ))`
4. Crear el castillo: `f := new( PFort, Init( ManX, voc ))`
5. Insertar habitaciones en el castillo
6. Poblar habitaciones con `SetData`
7. `f^.Start` (mover jugador a habitación 1)
8. Si hay rastro, ejecutarlo
9. Saludo según hora: "Buenos días/tardes/noches."
10. Bucle principal

## Pantalla e Interfaz

- 80×25 modo texto
- Soporte EGA (colores mejorados, bordes de menú)
- `Tele` — sistema de teletype para output (`TELETYPE.PAS`, `TTY.PAS`)
- Editor de comandos con historial (cursores arriba/abajo)
- Atajos: Alt+M = "matar ", Alt+Q = "terminar", F2 = "salvar", F9 = "ejecutar"
- Ctrl+L = nuevo papiro (limpiar pantalla)
