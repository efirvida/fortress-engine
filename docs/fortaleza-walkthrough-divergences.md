# Fortaleza — Divergencias entre el juego original y el mundo YAML

Este documento registra cada desviación deliberada entre el juego original
(Turbo Pascal, `docs/original-source/`) y la implementación YAML del mundo
(`worlds/fortaleza/`), junto con su justificación. El objetivo es que ningún
comportamiento del mundo se confunda con el del original.

## Proveniencia de las contraseñas

Las contraseñas del walkthrough se decodificaron del código fuente original
usando el cifrado de línea del juego (byte − 20, CP437), del array `key[1..47]`
en `FORT1.PAS:47-95`. Tabla resuelta:

| Puerta | Valor YAML | Clave original | Evidencia |
|---|---|---|---|
| Puerta principal (exterior → salón) | `Abrete Sesamo` | key[2] | FORT1.PAS:189 |
| Puerta del cíclope (biblioteca → pasillo) | `Nombus Rostomelaris` | key[14] | FORT1.PAS:270 |
| Puerta prohibida (pasillo → laboratorio) | `Luz` | key[15] | FORT1.PAS:282 |
| Puerta de cristal (bailarina → enigma) | `Agua` | key[42]/43/45 | ver bug de índices abajo |
| Pared solitaria (romper) | ariete (instrumento) | key[3] | FORT1.PAS:195-198 |

## Divergencias documentadas

### 1. Puerta de cristal: "Agua" vs frase literal (bug de índices del original)
En el original, key[42] contenía la frase "Cuidado con el túnel y la puerta de
tela. Solo conducen a la muerte." y key[43] = "Agua" se usó como talismán del
Túnel. key[45] = "La palabra mágica es 'Agua'" quedó **sin usar** en el código
original (FORT1.PAS:455, :460-461, :468). El valor intencionado era "Agua".
El mundo usa `Agua`, documentando el bug de índices del original.

### 2. Puerta triangular: "crunch" vs "Rumpelstinskin"
El original respondía "Rumpelstinskin" al acertijo del duende (key[23],
FORT1.PAS:472-474). El mundo y el walkthrough usan "crunch", coherentes entre
sí pero divergentes del original. Decisión: mantener "crunch" (consistencia
interna del mundo); se documenta para no confundir.

### 3. Armas de los centros vitales
El original tenía un cluster de bugs de índices: pulmones = pastel de cerezas,
estómago = espada, corazón = látigo (FORT1.PAS:415-438), con confesiones
corridas. El mundo usa maza/lanza/arco como el walkthrough, coherentes entre
sí. Decisión: no replicar el bug.

### 4. Espejo opaco: hueso de gato vs maza
El original solo aceptaba "Hueso de gato" para el espejo opaco (key[11],
FORT1.PAS:253-258). El mundo usa maza. Divergencia documentada.

### 5. Cama: breaker original vs hacha
El original declaraba la cama con breaker = frase de la bruja (inrompible en
la práctica, FORT1.PAS:303-305). El mundo la rompe con hacha (key[19]).
Divergencia documentada.

### 6. Antorchas 1-7
El original tenía 7 antorchas decorativas en R29 (FORT1.PAS:513-519); solo
importaban `antorcha` (cerebro, key[39]) y `antorcha_3` (columna, :501-502).
El mundo modela solo `antorcha` (pasillo) y `antorcha_3` (sala del minotauro).
Las demás no se modelan por ser decorativas.

### 7. Muralla 3 (episodio 2): decoy
La tercera muralla del original es deliberadamente inrompible
(breaker = "NADA", `hidd = nil`, FORT2.PAS:915-916). El mundo la documenta
como decoy: no es una meta alcanzable.

### 8. Peso del héroe y capacidad
El original: maza (39) + pastel (1) = 40 (límite LWeight=40). En el paso 2 del
walkthrough original maza+pastel=41>40 era imposible; el mundo arregló el peso
del pastel a 1. La capacidad del héroe se toma de `shared/player.yaml`
(max_weight 40), no hardcodeada.

### 9. Habitaciones huérfanas del mundo
`laberinto_salida` y `sala_de_lobos` (episodio 1) y `bajos_de_las_cataratas`
(episodio 2) no tienen macro-edges de entrada: son inalcanzables. El lobo del
paso 27 no se puede matar; no afecta al goal. Documentado como no-goal.

### 10. Order bug del walkthrough (pasos 17/18)
El walkthrough original daba la poción antes de obtenerla (paso 17 antes del
18). El script curado invierte el orden: primero se toma la poción en R8,
luego se da al homúnculo.

### 11. Pasaje "puerta_secreta" del exterior
En el original la puerta secreta (pared solitaria rota) era un DangerLink con
talismán **antorcha** y **sin** gate de texto. El YAML tenía un token roto
`key[3]` como `requires_text`; se eliminó y quedó `requires_item: antorcha`
con `open: true` (el requisito de item se evalúa siempre).

## Notas de lore no modeladas (referencia)

- Pañuelo en la cocina: el original mata al evaluar Goal() si el pañuelo está
  en la Cocina (R7). El mundo no modela este death por el momento; solo existe
  `me_pasillo_cocina` con `requires_item: panuelo` + `death_message`.
- Hija sin aguja: en el original, dar muerte a la hija sin aguja mata al
  jugador. El mundo modela `he_matar_ep2` como kill simple.
