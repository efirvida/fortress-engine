# Exploration: fortaleza-walkthrough-acceptance — Resolución contra el juego original

Investigación de solo lectura sobre `docs/09-walkthrough.md`, `docs/original-source/` (FORT1.PAS, FORT2.PAS, CASTLES.PAS, EQSTRING.PAS) y el mundo YAML, para resolver TODOS los placeholders/alternativas del walkthrough, decidir la Parte II (muralla/marmidosa/maza) y confirmar la especificación de edges bidireccionales.

Fuentes convertidas CP437/CP850→UTF-8 para lectura (`/tmp/opencode/FORT1_utf8.pas`, `FORT2_utf8.pas`, `CASTLES_utf8.pas`); los números de línea citados corresponden a los archivos UTF-8, que preservan las líneas originales.

---

## 1. Mecánica verificada del motor original (CASTLES.PAS)

- `LWeight = 40` (CASTLES.PAS:11). Maza Parte I = `pred(LWeight)` = 39 (FORT1.PAS:184). Maza Parte II = `LWeight - 3` = 37 (FORT2.PAS:401).
- `Linking.Open(psKey)`: `opn := (key='') or (upper(psKey)=upper(key))` (CASTLES.PAS:319-323). Contraseñas insensibles a mayúsculas.
- `Hidden.Break(weapon)`: `Equals(upper(breaker), upper(weapon))` (CASTLES.PAS:936-941). El instrumento debe estar en el inventario (`Man.Break`, CASTLES.PAS:767-772).
- `Guard.Die(weapon)`: muere solo si `Equals(lethalweap, weapon)` (CASTLES.PAS:964-974). El arma debe estar en el bolso (`Man.Kill`, CASTLES.PAS:598).
- `Troll.Die(weapon)`: muere con CUALQUIER arma (CASTLES.PAS:862-866). `matar troll` sin instrumento funciona (weapon='').
- `DangerLink.Pass`: si falta el talismán → `Man.Die('')` = MUERTE (CASTLES.PAS:890-902). `DangerLink2.Pass`: si LLEVAS el talismán → muerte (CASTLES.PAS:906-918).
- `Equals` (EQSTRING.PAS): coincidencia por subconjunto de palabras (todas las palabras de s2 deben aparecer en s1). No es prefix-match.
- Mapa de habitaciones: `rooms[i] := new(PRoom, RoomAr[i])` con i=1..N (FORT2.PAS:1037-1038, FORT1.PAS:760) → `rooms[n]` = habitación R<n> del walkthrough.
- `At(x) = rooms[x+1]` (deducido: `Castle.Start` hace `m^.Go(At(0))` = habitación de huéspedes R1, CASTLES.PAS:1006).

## 2. Tabla de placeholders resueltos (Parte I)

Cifrado original: `DecodeLine` = byte−20 (FORT1.PAS:37-44). El array `key[1..47]` está en FORT1.PAS:47-95; TODOS los 48 strings decodificados con Python (byte−20, decodificación CP437):

| # | Placeholder / paso | Valor del ORIGINAL (evidencia) | Mundo YAML actual | Decisión propuesta |
|---|---|---|---|---|
| 1 | Paso 5 `abrir puerta principal diciendo [contraseña]` | **"Abrete Sesamo"** — key[2], FORT1.PAS:189 (`Puerta principal` PLinking, keyword key[2]) | `me_exterior_salon` requires_text literal `"password_key[2]"` | Reemplazar el token por `"Abrete Sesamo"` en YAML |
| 2 | Paso 15 `[contraseña del ciclope]` | **"Nombus Rostomelaris"** — key[14] en `Puerta` R6→R7 (FORT1.PAS:270); el Cíclope (arma 'Maza', key[13]) confiesa key[12] = `' Puedes pasar, la contraseña es "Nombus Rostomelaris"'` (FORT1.PAS:268-269) | `me_biblioteca_pasillo` requires_text literal `"password_key[14]"` | `"Nombus Rostomelaris"` en YAML |
| 3 | Paso 16 `[contraseña]` (puerta prohibida) | **"Luz"** — key[15] en `Puerta prohibida` R7→R10 (FORT1.PAS:282); pista de la Bruja key[18]: `'Cuando te digan "Prohibido", invoca la luz'` (FORT1.PAS:295-297 usa key[18] como HiData) | `me_pasillo_laboratorio` requires_text literal `"password_key[15]"` | `"Luz"` en YAML |
| 4 | Paso 28 `[contraseña]` (puerta de cristal) | **Literal original: la frase de advertencia** `"Cuidado con el túnel y la puerta de tela. Solo conducen a la muerte."` — key[42] en `Puerta de cristal` R24→R25 (FORT1.PAS:455) y en el retorno R25→R24 (FORT1.PAS:468). **Quirk/bug del original**: key[43]='Agua' se usa como talismán del Túnel trampa (FORT1.PAS:460-461) y key[45]='AAARRRRGGGG!!!! La palabra mágica es "Agua".' queda SIN USAR → el valor INTENCIONADO era "Agua". El original es literalmente injugable por aquí sin leer el código | `me_bailarina_enigma` requires_text literal `"key[42]"` | **Decisión del usuario**: (a) `"Agua"` (valor intencionado, respaldado por key[43]+key[45]) documentando el bug del original, o (b) la frase literal. Recomiendo (a) |
| 5 | Paso 33 `romper pared solitaria con [objeto]` | **"Ariete"** — key[3], PHidden en R1 (FORT1.PAS:195-198); el Ariete es un item de la Sala de Armas R11, peso `LWeight-10`=30 (FORT1.PAS:325). La `Puerta secreta` revelada es un PDangerLink que exige llevar **Antorcha** (sin texto; keyword='') | `he_romper_pared_solaria` instrument `"antorcha"`; `me_exterior_arana` requires_item `antorcha` + requires_text literal `"key[3]"` | El YAML simplificó: NO existe item ariete. Decisión: (a) añadir ariete y alinear al original, o (b) mantener antorcha como rompedor y **quitar el requires_text spurious `"key[3]"`** (el original no tenía gate de texto). El texto literal `"key[3]"` es un placeholder roto SÍ o SÍ |
| 6 | Paso 36 `puerta 1/2/3` (laberinto) | Ruta verificada puerta a puerta contra FORT1.PAS:531-643: R28→R31 (puerta verde, POpenLink), P1→R32, P2→R33, P3→R34, P1→R35, P2→R36, P3→R37, P1→R29 ✓; salida R29→R47 (Puerta), P3→R48, P2→R49, Salida→R28 ✓ | Laberinto comprimido: solo `laberinto_1` + `sala_del_minotauro` + `sala_del_columna` (paso 36 no es ejecutable verbatim en YAML) | El script curado seguirá los pasajes YAML reales; el laberinto de 20 celdas original queda documentado, no replicado |
| 7 | Paso 38 `tomar antorcha 1..7` | Original: 7 antorchas en R29 (FORT1.PAS:513-519); solo importan antorcha (cerebro, key[39]) y antorcha 3 (columna, FORT1.PAS:501-502). Las otras 5 son decorativas | YAML: solo `antorcha` (anclada en `pasillo`) y `antorcha_3` (anclada en `centro_del_cerebro` — ¡distinto sitio que el original!) | Caminos abiertos por el original: tomar antorchas 1-7 es opcional. Script curado: omitir 1/2/4/5/6/7; **verificar orden** antorcha_3 (en YAML está en el cerebro, el walkthrough la usa en el paso 40 antes de llegar al cerebro → reordenar o anclar antorcha_3 en el minotauro como el original) |
| 8 | Paso 4 OPCIONAL `interrogar llamador de bronce` | Original: PTroll, acepta 'Cigarro', HiData key[1]=`'Hay un nombre que vas a necesitar mucho: Rumpelstinskin.'` (FORT1.PAS:186-188) | YAML: `item_llamador_bronce` existe | El paso OPCIONAL funciona; PERO la pista (Rumpelstinskin) es el nombre del duende = respuesta original de la puerta triangular (ver #10). Mantener como paso opcional del script |

## 3. Alternativas en prosa y orden bug (Parte I)

| # | Paso | Problema | Resolución |
|---|---|---|---|
| 1 | Paso 13 "O volver por donde viniste" | La 1ª subruta tiene anotación ERRÓNEA: `R13 puerta azul → R4` NO existe; la puerta azul de R13 va a R14 (FORT1.PAS:348-349). La 2ª subruta (puerta oculta→escalera→puerta azul→puerta verde) es correcta (FORT1.PAS:361-362, 250-252, 227-228, 235-236) | El script curado usa la ruta correcta: R14 `puerta oculta` → R5 `escalera` → R3 `puerta azul` → R4 `puerta verde` → R6. Corregir la anotación del doc |
| 2 | Paso 17/18 orden | "dar pocion para crecer a homunculo" (paso 17) antes de obtenerla (paso 18, R8). Original: el Homúnculo pide 'Poción para crecer' (FORT1.PAS:312-315), la poción está en R8 (FORT1.PAS:291) | Invertir: primero el paso 18 (ir puerta vieja → tomar pocion), luego dar al homúnculo |
| 3 | Paso 21 "O más directo: desde R7 ir al Jardín y luego rodear" | Ambas rutas son válidas en el original; la directa no está desarrollada en el doc | El script curado usa la ruta larga desarrollada (pasajes verificados en FORT1.PAS:276-285, 280-281, 350-351, 348-349, 227-228, 209-210, 235-236, 270-271, 280-281) |
| 4 | Paso 33 "Regresa al exterior vía R18→R17→R25→R24→[pozo a R1?]" | El pozo SÍ existe: POpenLink 'Pozo' R24→R1 (FORT1.PAS:457-459) | Ruta de retorno: `garganta` → `puerta triangular` → `puerta de cristal` → `pozo`. Luego la pared solitaria (paso 33) para ir al puente R27 |
| 5 | Paso 11 "El objeto para romper el Espejo opaco puede variar. La Maza funciona" | **Original: solo 'Hueso de gato'** (key[11], FORT1.PAS:253-258). El walkthrough dice maza; YAML `he_romper_espejo_opaco` instrument `maza` | Divergencia documentada: original exige hueso de gato (se toma en la misma sala R5). El YAML + walkthrough usan maza → el script curado usa maza (consistente con el mundo); documentar la diferencia |
| 6 | Paso 30 `abrir puerta triangular respondiendo crunch` | **Original: acertijo `¿Cuál es el nombre del duende?` respuesta `Rumpelstinskin`** (key[23], FORT1.PAS:472-474; pista del Llamador key[1]). "crunch" es el troll de la antesala, no el duende | YAML `me_columna_bailarina` requires_text `"crunch"` — el mundo y el walkthrough coinciden entre sí, DIVERGEN del original. Camino que el original dejó: respuesta correcta Rumpelstinskin. Decisión: documentar (recomendado) o alinear a Rumpelstinskin |

## 4. Armas de los Centros (Parte I) — divergencia documentada

Original (FORT1.PAS:415-438): pulmones=`Pastel de cerezas` (key[32]), estómago=`Espada` (key[33]), corazón=`Látigo` (key[34]), cerebro=`Antorcha` (key[38]/key[39]); y las confesiones están corridas (pulmones imprime `Daga`, etc.). Las confesiones clave 36-38 revelan la cadena INTENCIONADA (látigo→estómago, daga→corazón, fuego→cerebro). El walkthrough y el YAML (`he_matar_ep1`: maza/daga/látigo/maza/lanza/arco/antorcha/espada/maza) usan maza-lanza-arco para los centros — coherentes entre sí, distintos del original (que tiene un cluster de bugs de índice en las claves). El script curado sigue el YAML; documentar.

## 5. DECISIÓN PARTE II (muralla / marmidosa / maza) — CON EVIDENCIA

**Veredicto: DEFECTO DE LA IMPLEMENTACIÓN YAML.** Ni diseño intencional ni error del juego original.

Evidencia del original (FORT2.PAS, Orilla 2 = rooms[12]):

```pascal
FORT2.PAS:400-401  PHidden 'Arbol de marfil' → breaker 'Hacha' → PThing 'Maza' (peso LWeight-3=37)
FORT2.PAS:402-406  PHidden 'Muralla' → breaker 'Maza' → POpenLink 'Avenida de hierro' → rooms[13] Jardines
FORT2.PAS:687-690  Muralla 2 (Desierto rooms[36]) → breaker 'Piedra verde' → 'Avenida de las flores' → rooms[37]
FORT2.PAS:915-916  Muralla 3 (rooms[53]) → breaker 'NADA', hidd=nil → INROMPIBLE (decoy: "la tercera barrera está en ti mismo")
```

Marmidosa en el original se usa SOLO en 4 lugares — NINGUNO es una muralla:
1. Inscripción del Lago + DangerLink2 'Sendero dorado' (prohibido llevarla) (FORT2.PAS:617-622)
2. **Esfera** de la Torre → Tablilla (FORT2.PAS:797-807) — walkthrough paso 51 ✓
3. **Carcelero** PGuard arma 'Marmidosa' (FORT2.PAS:847-851) — walkthrough paso 56 ✓
4. **Hechicero** PTroll acepta 'Marmidosa' como regalo (FORT2.PAS:937-938) — walkthrough paso 65 ✓

El walkthrough pasos 15-16 (hacha → árbol → maza → muralla 1) coincide EXACTAMENTE con el original. La secuencia del YAML, en cambio:
- `he_romper_muralla` exige instrument `marmidosa` (he_romper_ep2.yaml) — instrumento que solo se obtiene en la Cueva de Cristal (R32), mucho más tarde → **deadlock**.
- `he_romper_arbol_de_marfil` solo pone un FLAG (`arbol_marfil_roto`); **no crea ningún item Maza**.
- **No existe item maza en episode-02** (grep: cero coincidencias).
- El item `muralla` está anclado en `jardines_del_hechicero` (el original: Orilla 2) y el pasaje `avenida_hierro` es `open: true` sin `requires_flag muralla_rota` → la muralla no tiene función de juego (decorativa rota).

**Recomendación (rediseño fiel al original):**
1. Añadir item `maza` (peso 37, anclado donde se crea) + operador TRANSFER en `he_romper_arbol_de_marfil` para crear la maza.
2. Cambiar `he_romper_muralla` instrument → `maza` (mantener marmidosa para esfera/carcelero/hechicero, que ya están correctos).
3. Re-anclar el item `muralla` a `otra_orilla_del_rio_negro` y poner `requires_flag: muralla_rota` en `me_orilla2_jardines` (acoplar muralla↔avenida como el original).
4. Documentar la muralla 3 del original (rooms[53], 'NADA' nil) como decoy — el YAML ya no la modela (solo muralla + muralla_2) ✓.

## 6. Edges bidireccionales — CONFIRMADO con cita textual

La especificación del motor SÍ define edges unidireccionales y bidireccionales:

- **docs/tdd.md:198** — esquema del dataclass: `direction: str  # "bidirectional" | "unidirectional"`
- **docs/gdd.md:261** — "El Grafo Macro define la topología del mundo: … Es un grafo dirigido (o bidireccional, según la arista) donde los nodos son rooms y las aristas son puertas/pasajes."
- **docs/gdd.md:281-285** — ejemplo: `# Conexión bidireccional simple (room-01 ↔ room-02) — sin predicados = abierta` con `direction: "bidirectional"`; y ejemplos unidireccionales en gdd.md:317, 328.
- **docs/08-room-graph.md:29** — implementación en el juego original: "La flecha indica la dirección. Si es bidireccional, cada habitación tiene su propio `PLinking`/`POpenLink` hacia la otra."

Comportamiento HOY del motor (verificado):
- `loader.py:310-326` `_macro_edge_from_model` copia `direction` al dataclass y NO hace nada más.
- `graph.py:245-254` `build_macro_graph` registra cada edge SOLO bajo `from_anchor` (`add_macro_edge`, graph.py:201-203) — `direction` nunca se lee.
- Los 106 edges YAML declaran `direction: "bidirectional"`; en runtime solo una dirección es transitable.

**Conclusión**: implementar la expansión bidireccional COMPLETA el diseño especificado (el campo y la semántica están documentados en GDD 2.2 y TDD), NO es una extensión nueva. Lo que NO está especificado es el MECANISMO (expandir en el loader/graph vs. archivos gemelos); el original usaba dos objetos link (08-room-graph.md:29). La implementación actual ignorando `direction` es una brecha de implementación frente a la spec.

## 7. Inventario pasos 66-73 (ritual) — TODO verificado contra el original

`Fort.Goal` (FORT2.PAS:71-80) con `At(x)=rooms[x+1]`:

| Paso walkthrough | Colocar/matar | YAML goal (episode-02.yaml) | Original (FORT2 Goal) | ¿Coincide? |
|---|---|---|---|---|
| 66 | antorcha en R1 (habitación huéspedes) | `antorcha_subterraneos` → `habitacion_para_huespedes` | At(0)=rooms[1] 'Antorcha' | ✓ |
| 67 | péndulo en R3 (Salón de Fumar) | `pendulo` → `salon_de_fumar` | At(2)=rooms[3] 'Péndulo' | ✓ |
| 68 | espejo en R4 (cuarto hija) | `espejo_roto` → `cuarto_de_la_hija_del_hechicero` | At(3)=rooms[4] 'Espejo' | ✓ (item espejo_roto, fiel) |
| 69 | bote en R12 (orilla 2) | `bote_carante` → `otra_orilla_del_rio_negro` | At(11)=rooms[12] 'Bote' | ✓ |
| 70 | rosa diamante en R31 (fondo del Lago) | `rosa_diamante` → `fondo_del_lago` | At(30)=rooms[31] 'Rosa diamante' | ✓ |
| 71 | escudo de Aquiles en R40 (Ciudad Abandonada) | `escudo_de_aquiles` → `ciudad_abandonada` | At(39)=rooms[40] 'Escudo de Aquiles' | ✓ |
| 72 | cinta de Moebius en R43 (Torre exterior) | `cinta_de_moebius` → `exterior_de_la_torre_de_cristal` | At(42)=rooms[43] 'Cinta de Moebius' | ✓ |
| 73 | matar Monstruo (R9) | flag `monstruo_muerto` | At(8)=rooms[9] 'Monstruo' = nil | ✓ |
| (54) | matar Hija | flag `hija_muerta` | At(45)=rooms[46] 'Hija del Hechicero' = nil | ✓ |

Los 7 `[viajar a X]`/`[tomar bote]/[ir a R12]` se resuelven con rutas verificadas en el grafo original (ej.: R1→R2 puerta; R11→R12 Río Negro; R28→R29 pasadizo→R30 catarata→R31; etc.). Los placeholders de viaje son solo "recorre el grafo" — el script curado usa los pasajes YAML reales.

## 8. Caminos que el original dejó abiertos / sin contemplar (a documentar o cerrar)

1. **Puerta de cristal (paso 28)**: el original exige la frase de advertencia literal (bug de índice key[42] vs key[43]/key[45]='Agua'); el valor intencionado "Agua" nunca aparece en juego. → documentar + usar "Agua".
2. **Puerta triangular (paso 30)**: original responde al acertijo del duende con "Rumpelstinskin" (pista del Llamador); el mundo usa "crunch". → documentar divergencia.
3. **Pared solitaria (paso 33)**: original = Ariete (item que existe en R11); el mundo lo simplificó a antorcha y dejó el token literal `"key[3]"` como gate de texto (roto). → quitar el requires_text y decidir instrumento.
4. **Armas de los Centros**: original con cluster de bugs de índice (pastel/espada/látigo + confesiones corridas); mundo coherente con maza/lanza/arco. → documentar, no replicar el bug.
5. **Cama (paso 22)**: el original tiene breaker=key[18] (la frase de la bruja) en vez de 'Hacha' (FORT1.PAS:303-305 vs key[19]) → la cama es inrompible en el original; mundo + walkthrough usan hacha. → documentar.
6. **Espejo opaco (paso 11)**: original = hueso de gato; mundo/walkthrough = maza. → documentar.
7. **Antorchas 1-7 (paso 38)**: las 5 decorativas no existen en el mundo; antorcha_3 anclada en el cerebro (reordenar vs. original). → decisión de inventario del script.
8. **Habitaciones huérfanas del mundo YAML**: `laberinto_salida`, `sala_de_lobos` (ep1) y `bajos_de_las_cataratas` (ep2) NO tienen ningún macro edge → inalcanzables (el lobo del paso 27 no se puede matar en el mundo; no afecta al goal). → limpieza de mundo opcional.
9. **Talismanes de los centros (paso 32)**: el original mata sin talismán de aire/paraguas/corazón de unicornio (DangerLinks FORT1.PAS:402-409); el mundo YAML no modela esos gates (pasajes abiertos). → el script NO necesita los talismanes; documentar que los danger links del doc no aplican al mundo.
10. **Peso**: original LWeight=40, maza=39, pastel=2 → maza+pastel=41 > 40 (el paso 2 del walkthrough es imposible en el original). El mundo YAML ajustó pastel=1 (39+1=40 ✓) pero el fixture del test fuerza max_weight=20 (explore.md) → debe usar 40 / el player del mundo.

## 9. Estado del arte para el script curado

- El mundo YAML es una REINTERPRETACIÓN estructural (33→33 anchors distintas: laberinto comprimido, centros como anchors separados, salas extra) — el script curado se construye contra los macros YAML reales (45 ep1 + 61 ep2), con el walkthrough como fuente de ORDEN de la historia y estas tablas como resolución.
- El goal del episode-02 es transcripción FIEL del Goal() original (7 objetos + 2 muertes, incl. espejo_roto y otra_orilla).
- Falta resolver en propose: (a) puerta de cristal "Agua" vs literal; (b) pared solitaria ariete vs antorcha; (c) Part II maza (recomendación arriba); (d) antorcha_3 en el cerebro vs minotauro; (e) pasajes del laberinto comprimido; (f) puerta triangular crunch vs Rumpelstinskin.

## Fuentes citadas

- docs/09-walkthrough.md (1170 líneas)
- docs/original-source/FORT1.PAS (857), FORT2.PAS (1154), CASTLES.PAS (1345), EQSTRING.PAS
- docs/gdd.md:250-261, 281-340; docs/tdd.md:198; docs/08-room-graph.md:29
- worlds/fortaleza/{episode-01,episode-02}/** (macros, actions, items, rooms, episodes)
- src/fortress_engine/entities/loader.py:310-326; src/fortress_engine/engine/graph.py:201-203, 245-274
