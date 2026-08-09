# Fidelity Audit — fortress-engine vs. Turbo Pascal original (Fortaleza)

**Date:** 2026-08-09
**Sources:** `docs/original-source/FORT1.PAS` / `FORT2.PAS` (authoritative; CP850→UTF-8 at `/tmp/opencode/FORT1_utf8.pas`, `/tmp/opencode/FORT2_utf8.pas`), `docs/original-source/CASTLES.PAS` (class semantics), `docs/original-source/VOCABL.PAS`, `docs/original-source/PRESENT1.PAS`. YAML world under `worlds/fortaleza/`.
**Method:** per-item verdicts **FAITHFUL / DIVERGENT / INVENTED / MISSING**. FAITHFUL = YAML text equals Pascal text verbatim (allowing string-literal joins and `#13` newline escapes); DIVERGENT = recognizable Pascal item whose YAML text differs; INVENTED = YAML content with no Pascal counterpart; MISSING = Pascal content absent from YAML. Encoding-only fixes applied to quotes.

---

## 1. Executive summary

### 1.1 Counts per episode

**Episode 1 (FORT1.PAS)**

| Category | Total in YAML | FAITHFUL | DIVERGENT | INVENTED | MISSING (Pascal, no YAML) |
|---|---|---|---|---|---|
| Rooms | 33 | 0 | 27 | 6 | 22 Pascal rooms |
| Exits/macros | 46 | 0 | 30 | 16 | ~65 Pascal links |
| Items | 46 | 0 | 45 | 1 | 15 Pascal objects |
| NPCs | 25 | — | 24↔Pascal, 1 invented | 1 (troll_final) | 0 |
| Dialogues/texts | 22 dialogue sets | 0 | ~6 fragments | ~36 paraphrases | ~22 verbatim lines |

**Episode 2 (FORT2.PAS)**

| Category | Total in YAML | FAITHFUL | DIVERGENT | INVENTED | MISSING (Pascal, no YAML) |
|---|---|---|---|---|---|
| Rooms | 55 | 0 | 55 | 0 | 0 |
| Exits/macros | 61 | 0 | 61 | 0 | 0 (1 edge reshaped) |
| Items | 64 | 8 | 56 | 0 | 3 Pascal objects |
| NPCs | 23 | — | 23 | 0 | 0 |
| Dialogues/texts | 23 dialogue sets | 0 | ~8 fragments | ~36 paraphrases | ~23 verbatim lines |

### 1.2 Headline findings

1. **Room names/descriptions.** Episode 2 is structurally faithful (all 55 rooms map 1:1; descriptions are the Pascal text verbatim) but **every** room appends an invented `Ves: <exits>` list. Pascal narrates "Usted ve:" + *items*; the YAML lists *exit passage ids*, some of which are themselves invented (`garganta`, `pasadizo`, `tunel_banos`). Episode 1 is far worse: 17 rooms have wholly invented descriptions, 6 rooms have **no Pascal counterpart at all** (`cripta_final`, `cuarto_de_los_cuadros`, `cuarto_de_los_vendajes`, `cuarto_del_hechicero`, `torre_oscura`, `garganta`), and the whole second half of the map (Boca/Interior de la Bestia, Calabozos, Almacenes, Páramo, Celda, Laberinto, Jardín falso) was renamed/restructured.
2. **Every exit `passage_description` is an invented short label** ("Una puerta negra" vs Pascal "Es muy negra."). Zero macros are fully FAITHFUL.
3. **Almost every item description was rewritten.** Pascal one-liners ("Es muy pesada.", "Está cerrado.", "Humea.") become invented 2–3-sentence prose, often with gameplay hints appended ("...Útil para dar al X", "...condición de victoria") that do not exist in the original.
4. **All NPC dialogue is missing or paraphrased.** None of the ~45 verbatim troll/guard lines (e.g. "Tráeme mi escoba y te daré un consejo.", "¡Grrrr! ¡Hambre!", "El 12 te guiará en el Laberinto.") appear anywhere in the YAML. NPC `description` fields are invented flavor text; give/kill action outputs are invented paraphrases. **Gift items (`wants_item`) and lethal weapons are mechanically faithful** in both episodes.
5. **Episode-1 puzzle gates diverged:** internal Bestia gates (Tráquea/Esófago "Talismán de aire", Arteria "Corazón de unicornio") are **open** in YAML; Espejo opaco→Puerta oculta gate ("Hueso de gato") is **open**; the puerta triangular riddle answer was changed from "Rumpelstinskin" to "crunch"; kill weapons for Pulmones/Estómago/Corazón/Arpía differ from Pascal (Maza/Lanza/Arco/Daga vs Espada/Látigo/Daga/Espada); the goal's "Troll" is a new invented NPC in an invented room.
6. **Episode-2 gates are faithful** (riddle answers `Aura`, `Aura Srka`, `Omicuos Ihanti`, `Grifo`, `MIAU`, `Yo`, `Seis`; `forbids_item` ring-test/Marmidosa/Talismán gates; `death_message` present). One gate lost: `avenida_flores` (Desierto→Valle; Pascal Muralla hidden gated by **Piedra verde**) is `open: true`.
7. **Empty-output actions:** `episode-02/actions/he_mirar_ep2.yaml` has both edges with `output: ""` (stub — "mirar" emits no narration). Episode-1 `he_mirar_habitacion` renders `{description}`, i.e. the room text including the invented `Ves:` list.
8. **Encoded manuscript texts are missing:** the Cáliz text (FORT2.Goal), the Tablilla de Madera text, and the Piedra de Roseta bilingual text exist in YAML only as "texto codificado" placeholders.

---

## 2. Episode 1 — detail

### 2.1 Rooms (33 YAML files; Pascal rooms 1–33, SetData indices 1–50)

`+Ves` = YAML desc = Pascal desc verbatim **plus** an invented trailing "Ves: …" list (⇒ DIVERGENT, since the text differs from Pascal). Desc = invented means the description text itself is not the Pascal text.

| YAML entity_id | Pascal idx | Pascal name / desc (trimmed) | YAML desc (trimmed) | Verdict | Notes |
|---|---|---|---|---|---|
| el_exterior_de_la_fortaleza | 1 | "el exterior de la fortaleza" / "Las paredes son muy negras y al parecer, no tienen ventanas. Usted trata de ver el final de las torres, pero las nubes no se lo permiten." | same + "Ves: garganta, puerta_principal, puerta_secreta, tunel." | DIVERGENT | +Ves; `garganta` is an invented exit |
| salon_de_recepciones | 2 | "el Salón de recepciones" / "Parece hecho para criaturas cientos de veces más grandes que los humanos. Está desierto, pero usted siente que es observado." | same + "Ves: puerta_negra, puerta_principal." | DIVERGENT | +Ves |
| sala_de_juegos | 3 | "la Sala de juegos" / "Usted trata de **imagainar** cómo eran los juegos del salón. Hay doce mesas y cada una tiene doce erizos." | "Usted trata de **imaginar** …" +Ves | DIVERGENT | typo fixed (imagainar→imaginar); +Ves |
| patio_interior | 4 | "el Patio interior" / "El patio tiene forma de caracol. … Usted siente el crujido de las hojas secas bajo sus zapatos." | same + "Ves: puerta_azul, puerta_dorada, puerta_verde, tunel." | DIVERGENT | +Ves; `puerta_dorada`/`tunel` invented exits |
| cuarto_de_espejos | 5 | "el Cuarto de espejos" / "Hay tantos espejos que no puede reconocer si usted es real o es una imagen de sí mismo." | same + "Ves: escalera, puerta_oculta." | DIVERGENT | +Ves |
| biblioteca | 6 | "la Biblioteca" / "Hay miles de libros en este lugar. Todos tienen alguna hoja marcada con una servilleta." | same + "Ves: libro, puerta, puerta_verde, tunel_banos." | DIVERGENT | +Ves; `tunel_banos` invented |
| pasillo | 7 | "Pasillo" / "Tiene tres puertas al lado y una al final." | same + "Ves: pasillo_armas, puerta, puerta_gris, puerta_prohibida, puerta_roja, puerta_vieja." | DIVERGENT | +Ves; `pasillo_armas` invented |
| alcoba_de_la_bruja | 8 | "la Alcoba de la bruja" / "Hasta un ciego descubriría que aquí habita una bruja. …" | same + "Ves: escaparate, pasadizo, puerta_vieja." | DIVERGENT | +Ves; `pasadizo` invented |
| cuarto_del_guerrero | 9 | "el Cuarto del guerrero" / "El cuarto está muy ordenado. A usted le sorprende que no hayan armas." | same + "Ves: cama, puerta_metal, puerta_roja." | DIVERGENT | +Ves; `puerta_metal` invented |
| laboratorio_de_la_bestia | 10 | "el Laboratorio de la Bestia" / "Hay muchos frascos. A usted le llaman la atención los últimos: están llenos de homúnculos." | same + "Ves: puerta_prohibida, tunel_laboratorio." | DIVERGENT | +Ves; `tunel_laboratorio` invented |
| sala_de_armas | 11 | "la Sala de armas" / "Este lugar parece salido del sueño de un guerrero." | same + "Ves: cama, pasillo_armas." | DIVERGENT | +Ves; `pasillo_armas` invented |
| sala_de_banos | 12 | "los Baños de la Bestia" / "El baño es tan grande que usted no puede ver las paredes que lo limitan" | "Baños enormes para criaturas enormes. Ves: puerta_blanca, tunel_banos." | DIVERGENT | desc invented |
| jardin | 13 | "el Jardín" / "Se podrían construir varias ciudades en su interior." | "Un jardín secreto con flores de todos los colores. Ves: libro, puerta_verde, ventana." | DIVERGENT | desc invented |
| alcoba_de_la_doncella | 14 | "la Alcoba de la doncella" / "Es una habitación muy pequeña y húmeda." | "Un cuarto delicado con cortinas de seda. Ves: escaparate, puerta_oculta, ventana." | DIVERGENT | desc invented |
| sala_de_infusiones | 15 | "la Sala de infusiones" / "Hay varias mesas regadas por el suelo. Usted tiene la impresión de que ningún humano ha estado en ese lugar anteriormente." | "Hay hierbas por todas partes. El olor es dulzón y mareante. Ves: …" | DIVERGENT | desc invented |
| garganta | 17+18 | "Boca de la Bestia" + "Interior de la Bestia" | "Estás dentro de la Bestia. Todo es carne y líquido. Ves: arteria_principal, esofago, garganta, traquea." | INVENTED | amalgam room; no Pascal name/desc |
| centro_de_los_pulmones | 19 | "Pulmones de la Bestia" / "Sopla un aire tan fuerte que usted se ha tirado al suelo." | "El centro vital de los pulmones de la Bestia. Ves: traquea, vena." | DIVERGENT | guard-of-room turned into a room; desc invented |
| centro_del_estomago | 20 | "el Estómago de la Bestia" / "Hay varios esqueletos humanos." | "El centro vital del estómago de la Bestia. Ves: conducto, esofago." | DIVERGENT | desc invented |
| centro_del_corazon | 21 | "el Corazón de la Bestia" / "Todo palpita rítmicamente. …" | "El centro vital del corazón de la Bestia. Ves: arteria_principal, vena." | DIVERGENT | desc invented |
| centro_del_cerebro | 22 | "el Cerebro de la Bestia" / "Es como un tarjetero gigante. …" | "El centro vital del cerebro de la Bestia. Ves: conducto, escondite, puerta_dorada, puerta_hierro." | DIVERGENT | desc invented |
| sala_de_lobos | 24 | "un extenso páramo" / "Hay muy poca vegetación y el suelo es pantanoso. …" | "Una sala oscura donde aúllan los lobos. Ves: puerta_verde." | DIVERGENT | renamed; desc invented |
| sala_de_la_bailarina | 25 | "Salón de cristal" / "Es como un caleidoscopio gigante. …" | "Una sala con espejos y una bailarina. Ves: puerta_cristal, puerta_triangular." | DIVERGENT | renamed; desc invented |
| sala_de_la_arana | 27 | "un puente de mármol" / "Es muy largo y estrecho." | "Una sala llena de telarañas con una araña gigante. Ves: estatua_satanas, puerta_oculta, puerta_secreta." | DIVERGENT | renamed; desc invented |
| sala_del_columna | 28 | "la Antesala del Laberinto" / "Es una habitación muy confortable, pero usted siente algo malvado flotando en el aire." | "Una sala con una columna de cristal gigante. Ves: cripta, …" | DIVERGENT | renamed; desc invented |
| sala_del_minotauro | 29 | "la cueva del Minotauro" / "Hay siete antorchas." | "La sala donde vive el Minotauro. Ves: salida, sendero_dorado." | DIVERGENT | renamed; desc invented |
| sala_del_enigma | 30 | "el Salón de los elegidos" / "Usted se enorgullece: muy pocas personas han llegado hasta este salón. …" | "Una sala con enigmas y puertas doradas. Ves: puerta_cristal, puerta_dorada." | DIVERGENT | renamed; desc invented |
| laberinto_1 | 31 | "un pasillo del Laberinto" / "El techo está tan pegado al suelo que usted tiene que andar agachado. Hay tres puerta simétricas." | "Sala del laberinto. Tres puertas. Ves: puerta_madera, sendero_dorado." | DIVERGENT | desc invented |
| laberinto_salida | 49 | "un pasillo del Laberinto" / "Hay una puerta que le conducirá a la antesala del Laberinto." | "La salida del laberinto." | DIVERGENT | desc invented |
| cripta_final | — | — | "La cripta donde descansa el Troll. Ves: cripta, escondite." | INVENTED | no Pascal room; hosts invented `troll_final` |
| cuarto_de_los_cuadros | — | — | "Un cuarto lleno de cuadros valiosos. Ves: puerta_dorada." | INVENTED | no Pascal room |
| cuarto_de_los_vendajes | — | — | "Un cuarto con vendajes y medicinas. Ves: puerta_metal." | INVENTED | no Pascal room |
| cuarto_del_hechicero | — | — | "Un cuarto oscuro con pociones y libros de magia. Ves: escalera, …" | INVENTED | no Pascal room |
| torre_oscura | — | — | "Una torre alta con ventanas estrechas. Ves: escalera_madera." | INVENTED | no Pascal room |

**MISSING Pascal rooms (no YAML counterpart):** 16 los Calabozos, 17 Boca de la Bestia, 23 los Almacenes de la Fortaleza, 26 celda pequeña, 32–48 (17 labyrinth rooms; only 31 and 49 exist), 50 el Jardín (falso). → **22 rooms.**

### 2.2 Exits / macros (46 YAML files)

All `passage_description` fields are invented short labels (Pascal descriptions like "Inmensa y oprimente." are dropped), so **no macro is fully FAITHFUL**.

| macro_edge_id | from → to | passage | Pascal link (idx) | Pascal gate | YAML gate | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| me_exterior_salon | exterior→salon | puerta_principal | 1 Puerta principal | key "Abrete Sesamo" | req_text "Abrete Sesamo" | DIVERGENT | gate ✓, desc invented |
| me_exterior_patio | exterior→patio | tunel | 1 Túnel (Open) →4 | open | open | DIVERGENT | dest ✓ |
| me_exterior_arana | exterior→sala_arana | puerta_secreta | 1 Pared solitaria (PHidden breaker **Ariete**) → Puerta secreta (PDanger **Antorcha**) →27 | Ariete then Antorcha | requires_item "antorcha" | DIVERGENT | only inner DangerLink gate; Ariete step lost; dest ≠27 |
| me_exterior_garganta | exterior→garganta | garganta | — | — | open | INVENTED | no Pascal exit |
| me_bailarina_enigma | sala_bailarina→sala_enigma | puerta_cristal | 25 Puerta de cristal (keyword "Agua") →24 (Páramo) | Agua | req_text "Agua" | DIVERGENT | gate ✓ but dest wrong (→sala_del_enigma) |
| me_salon_juegos | salon→sala_juegos | puerta_negra | 2 Puerta negra →3 | open | open | DIVERGENT | desc invented |
| me_juegos_espejos | sala_juegos→cuarto_espejos | escalera | 3 Escalera (Riddle → **Treinta y nueve**) →5 | "Treinta y nueve" | req_text "treinta y nueve" | DIVERGENT | gate ✓ (case-normalized) |
| me_juegos_patio | sala_juegos→patio | puerta_azul | 3 Puerta azul →4 | open | open | DIVERGENT | dest ✓ |
| me_juegos_inscripcion | sala_juegos→sala_juegos | inscripcion | — (Inscripción is a PThing, not a door) | — | open (self-loop) | INVENTED | self-loop modeled as passage |
| me_patio_biblioteca | patio→biblioteca | puerta_verde | 4 Puerta verde →6 | open | open | DIVERGENT | dest ✓ |
| me_patio_cuadros | patio→cuarto_cuadros | puerta_dorada | — | — | open | INVENTED | no Pascal exit |
| me_espejos_doncella | cuarto_espejos→alcoba_doncella | puerta_oculta | 5 Espejo opaco (PHidden breaker **Hueso de gato**) → Puerta oculta →14 | Hueso de gato | open | DIVERGENT | **gate MISSING** |
| me_espejos_hechicero2 | cuarto_espejos→cuarto_hechicero | escalera | 5 Escalera (keyword "treinta y nueve") →3 | treinta y nueve | open | DIVERGENT | wrong dest + gate lost |
| me_biblioteca_jardin | biblioteca→jardin | libro | 6 Libro (Linking) →13 | open | open | DIVERGENT | dest ✓; desc invented |
| me_biblioteca_pasillo | biblioteca→pasillo | puerta | 6 Puerta (keyword "Nombus Rostomelaris") →7 | Nombus Rostomelaris | req_text "Nombus Rostomelaris" | DIVERGENT | gate ✓ |
| me_banos_biblioteca | sala_banos→biblioteca | tunel_banos | — | — | open | INVENTED | no Pascal exit |
| me_pasillo_bruja | pasillo→alcoba_bruja | puerta_vieja | 7 Puerta vieja →8 | open | open | DIVERGENT | dest ✓ |
| me_pasillo_guerrero | pasillo→cuarto_guerrero | puerta_roja | 7 Puerta roja →9 | open | open | DIVERGENT | dest ✓ |
| me_pasillo_laboratorio | pasillo→laboratorio | puerta_prohibida | 7 Puerta prohibida (keyword "Luz") →10 | Luz | req_text "Luz" | DIVERGENT | gate ✓ |
| me_pasillo_infusiones | pasillo→sala_infusiones | puerta_gris | 7 Puerta gris →15 | open | open | DIVERGENT | dest ✓ |
| me_bruja_doncella | alcoba_bruja→alcoba_doncella | escaparate | 8 Escaparate (PDanger **Candelabro**) →14 | Candelabro | requires_item "candelabro" | DIVERGENT | gate ✓ |
| me_bruja_infusiones | alcoba_bruja→sala_infusiones | pasadizo | — | — | open | INVENTED | no Pascal exit |
| me_guerrero_armas | cuarto_guerrero→sala_armas | cama | 9 Cama (PHidden breaker **Hacha**) → Puerta →11 | Hacha | requires_flag "cama_rota" | DIVERGENT | gate equivalent (he_romper_cama requires hacha) |
| me_guerrero_vendajes | cuarto_guerrero→cuarto_vendajes | puerta_metal | — | — | open | INVENTED | no Pascal exit |
| me_laboratorio_hechicero | laboratorio→cuarto_hechicero | tunel_laboratorio | — | — | open | INVENTED | no Pascal exit |
| me_hechicero_espejos | cuarto_hechicero→torre_oscura | escalera_madera | — | — | open | INVENTED | no Pascal exit |
| me_armas_pasillo | sala_armas→pasillo | pasillo_armas | 11 Puerta (techo) →9 | open | open | INVENTED | wrong passage + dest (should go to cuarto_guerrero) |
| me_jardin_lobos | jardin→sala_lobos | puerta_verde | 13 Puerta verde →12 (Baños) | open | open | INVENTED | wrong dest (invented room) |
| me_doncella_jardin | alcoba_doncella→jardin | ventana | 14 Puerta azul →13 | open | open | DIVERGENT | passage renamed "ventana" |
| me_infusiones_banos | sala_infusiones→sala_banos | puerta_blanca | — | — | open | INVENTED | no Pascal exit |
| me_infusiones_hechicero | sala_infusiones→cuarto_hechicero | puerta_amarilla | 15 Puerta amarilla →13 (Jardín) | open | open | INVENTED | wrong dest (invented room) |
| me_garganta_pulmones | garganta→centro_pulmones | traquea | 18 Tráquea (PDanger **Talisman de aire**) →19 | Talismán de aire | open | DIVERGENT | **gate MISSING** |
| me_garganta_estomago | garganta→centro_estomago | esofago | 18 Esófago (PDanger **Talisman de aire**) →20 | Talismán de aire | open | DIVERGENT | **gate MISSING** |
| me_garganta_corazon | garganta→centro_corazon | arteria_principal | 18 Arteria (PDanger **Corazon de unicornio**) →21 | Corazón de unicornio | open | DIVERGENT | **gate MISSING** |
| me_pulmones_corazon | centro_pulmones→centro_corazon | vena | — | — | open | INVENTED | no Pascal exit |
| me_estomago_cerebro | centro_estomago→centro_cerebro | conducto | — | — | open | INVENTED | no Pascal exit |
| me_cerebro_cripta | centro_cerebro→cripta_final | escondite | — | — | open | INVENTED | no Pascal exit |
| me_columna_cripta | sala_columna→cripta_final | cripta | — | — | open | INVENTED | no Pascal exit |
| me_columna_hierro | sala_columna→centro_cerebro | puerta_hierro | 50 Puerta de hierro (Riddle → **Seis**) →30 | Seis | req_text "seis" | DIVERGENT | gate ✓ but dest wrong (→centro_cerebro, not Salón de los elegidos) |
| me_enigma_dorada | sala_enigma→centro_cerebro | puerta_dorada | 30 Puerta dorada (Riddle "Invente un alfabeto…" → **cdfghjklmnopqruvwxyz**) →22 | cdfghjklmnopqruvwxyz | req_text "cdfghjklmnopqruvwxyz" | DIVERGENT | gate ✓ and dest ✓; desc invented |
| me_columna_bailarina | sala_columna→sala_bailarina | puerta_triangular | 25 Puerta triangular (Riddle → **Rumpelstinskin**) →17 | Rumpelstinskin | req_text "crunch" | DIVERGENT | **riddle answer changed to "crunch"** |
| me_columna_madera | sala_columna→laberinto_1 | puerta_madera | 28 Puerta de madera (PHidden breaker **Martillo**) →50 | Martillo | requires_flag "madera_rota" | DIVERGENT | dest should be Jardín falso (missing) |
| me_satanas_columna | sala_arana→sala_columna | puerta_oculta | 27 Estatua de Satanás (PHidden breaker **Cuadro**) → Puerta oculta →28 | Cuadro | open | DIVERGENT | **gate MISSING** |
| me_arana_satanas | sala_arana→sala_arana | estatua_satanas | 27 Estatua de Satanás (PHidden) | Cuadro | requires_flag "satanas_roto" (self-loop) | INVENTED | self-loop hack, not a traversal |
| me_laberinto_minotauro | laberinto_1→sala_minotauro | sendero_dorado | — | — | open | INVENTED | no Pascal exit |
| me_minotauro_columna | sala_minotauro→sala_columna | salida | 29 Puerta (Open) →47 (laberinto) | open | open | DIVERGENT | wrong dest (laberinto room) |

**MISSING Pascal exits (no YAML macro):** 12 Baños→Puerta verde→13; 13 Jardín→Puerta azul→14, Puerta amarilla→15, Puerta de hierro→16, Puerta de madera→23; 15→Puerta amarilla→13; 17 Boca→Puerta triangular→25, Garganta→18; 18→Garganta→17; 23 Almacenes→Puerta de madera→13, Puerta verde→24; 24 Páramo→Puerta verde→23, Puerta de cristal→25, Pozo→1, Túnel(self); 25→Puerta de tela→26, Puerta triangular→17; 26 Celda (dead end); 27→Puerta secreta→1, Puerta(DangerLink2 Espada)→28; 28→Puerta→27, Puerta verde→31; 31–48 labyrinth doors (~54); 50 Jardín falso doors. ≈ **65 links.**

### 2.3 Items (46 YAML files)

All descriptions were rewritten. Representative table (Pascal verbatim vs YAML):

| entity_id | Pascal name / desc (verbatim, trimmed) | YAML desc (trimmed) | Verdict |
|---|---|---|---|
| roble | Roble — "Está completamente seco y lleno de mordiscos. Tiene las siguientes palabras talladas en el tronco: «Las palabras mágicas…»" | "Un roble centenario. En su corteza hay una inscripción grabada que parece esconder una contraseña." | DIVERGENT |
| maza | "Es muy pesada." | "Una maza de guerra descomunal. Pesa tanto que apenas se puede cargar nada más con ella." | DIVERGENT |
| pastel_cerezas | "¿Qué hace un pastel de cerezas en un lugar como este?" | "Un pastel de cerezas recién horneado. Su olor abre el apetito de cualquiera." | DIVERGENT |
| retrato | "Es de Hitchcock (un anacronismo). Usted recuerda instintivamente algunas películas…" | "Un retrato de Alfred Hitchcock. Su mirada le sigue por toda la sala." | DIVERGENT |
| escoba | "Es una escoba voladora." | "Una escoba de madera vieja que flota unos centímetros sobre el suelo." | DIVERGENT |
| inscripcion | "Dice: «Cuando hayas llegado casi al final, tendrás que regresar, a no ser que hayas hablado con el murciélago." | "…«Cuando hayas llegado casi al final, tendrás que regresar…»" | DIVERGENT | truncated |
| hilo_ariadna | "Debe tener varios kilómetros de largo." | "Un ovillo de hilo interminable. Con él nadie se pierde jamás." | DIVERGENT |
| balanza | "…el plato en forma de mano. La aguja es muy delgada, hecha con varios bigotes de gato trenzados entre sí." | "Una balanza de dos platillos, precisa hasta el último gramo." | DIVERGENT |
| hueso_gato | "Este es un hueso de gato (o de la imagen de un gato)." | "Un hueso pequeño y blanquecino, roído por el tiempo." | DIVERGENT |
| vaso_agua | "Por un momento cree ver un bote en el vaso." | "Un vaso de cristal lleno de agua fresca, olvidado sobre un atril." | DIVERGENT |
| candelabro | "La llama en su extremo está inmóvil, como si fuera de cera." | "Un candelabro cuya llama permanece inmóvil, como congelada en el aire." | DIVERGENT |
| antorcha | "La llama parece bailar en su propia luz." | "Una antorcha encendida que arde con una llama firme y anaranjada." | DIVERGENT |
| polvo_magico | "Puede hacer invisible a cualquiera." | "Un frasco con un polvo brillante. Quien lo espolvorea… deja de ser visto." | DIVERGENT |
| pocion_crecer | "Tiene un olor muy repugnante." | "…líquido verdoso. La etiqueta dice: «Beber para crecer»." | DIVERGENT |
| vendajes | "Están manchados de sangre." | "Un rollo de vendajes limpios, listos para curar una herida." | DIVERGENT |
| grabado | "En el grabado está usted, hablando con una muchacha." | "…que le muestra a usted mismo conversando con una muchacha." | DIVERGENT |
| piedra_filosofal | "Usted es el primer humano en ver la quinta escencia." | "Una piedra rojiza y cálida al tacto. Los alquimistas morirían por ella." | DIVERGENT |
| maquina_tiempo | "Es muy parecida a una máquina de moler carne." | "Un artefacto de engranajes y esferas capaz de adelantar o retrasar las horas." | DIVERGENT |
| espada / lanza / arco / daga / ariete / latigo | "Es muy brillante." / "Está hecha de piedra." / "Es el arco de Odiseo." / "Es afilada como la lengua de la serpiente bíblica." / "Demasiado grande y pesado." / "Parece una culebra." | all rewritten into new prose | DIVERGENT |
| rosa | "Es más hermosa que todas las doncellas que usted no ha visto." | "Una rosa roja de tallo espinoso, la más hermosa del jardín." | DIVERGENT |
| cuadro | "Está completamente pintado de negro." | "Un cuadro pesado con un marco macizo. Serviría para golpear algo con fuerza." | DIVERGENT |
| corazon_unicornio | "Aún late." | "Un corazón de unicornio que aún late débilmente, guardado en un cofrecillo." | DIVERGENT |
| taza_cafe | "Humea." | "Una taza de café humeante y muy cargado. Despertaría hasta a un muerto." | DIVERGENT |
| cigarro | "Está encendido." | "Un cigarro grueso y aromático, de los que se fuman sin prisa." | DIVERGENT |
| paraguas | "Está cerrado." | "Un paraguas negro plegado, en perfecto estado pese a los años." | DIVERGENT | placement moved (Pascal: Calabozos 16) |
| talisman_aire | "Está hecho de cinco vientos amarrados con un cordón negro." | "Un talismán grabado con el símbolo del aire. Al sostenerlo se respira mejor." | DIVERGENT | placement moved (Pascal: Calabozos 16) |
| hacha | "Está muy afilada." | "Un hacha de leña con el filo todavía brillante." | DIVERGENT | placement moved (Pascal: Almacenes 23) |
| martillo | "Tiene dos mangos y tres cabezas." | "Un martillo de carpintero con la cabeza de hierro mellada." | DIVERGENT | placement moved (Pascal: Puente 27) |
| antorcha_3 | Antorcha 3 — "Es muy brillante." | "Una tercera antorcha, de llama azulada y extrañamente fría." | DIVERGENT | Pascal: all 7 "Es muy brillante." / #6 "Está apagada." |
| libro | "Es un libro normal." | "Un libro de tapas gastadas. Al abrirlo, el suelo parece desaparecer bajo sus pies." | DIVERGENT |
| cama | "Es tan fuerte que solo con un hacha podría romperla." | "Una cama enorme que esconde una puerta al suelo. Hay que romperla." | DIVERGENT |
| monolito_marmol | "Es muy oscuro, pero a usted le parece que hay algo vivo en su interior." | "Un monolito de mármol macizo. Suena hueco: algo se oculta en su interior." | DIVERGENT |
| pared_solaria | "Usted no puede imaginar con qué motivo fue colocada ahí." | "Una pared solitaria que esconde un secreto tras de sí." | DIVERGENT |
| espejo_opaco | "En realidad, usted no tiene idea de por qué es un espejo. Hay algo muy extraño en él." | "Un espejo cubierto por una capa opaca que no refleja nada. Detrás se adivina un hueco." | DIVERGENT |
| estatua_atenea / estatua_hermes / item_llamador_bronce / item_trebol / item_homunculo | Pascal living things (Trolls) with desc + dialogue | item files with invented desc (duplicated as NPCs too) | DIVERGENT |
| rosa_oculta | — (no Pascal object) | "Una rosa escondida entre los vendajes, intacta y perfumada." | INVENTED |

**MISSING Pascal objects (no YAML):** Antorcha 1, 2, 4, 5, 6 ("Está apagada."), 7 (6); Cedro ×2 (Jardín 13 y Jardín falso 50); Espejo de los Baños (12, "Usted se ve a sí mismo entregándole unos polvos al Troll."); Inscripciones de Baños 12 ("¡Mate al Troll!…"), Jardín 13 ("Es un buen lugar para instalar una tienda…"), Interior 18 ("No continúe si no está protegido."), Cerebro 22 ("¿Mataste al Troll?"), Celda 26 ("Dice que usted pasará en esta celda el resto de sus días."), Jardín falso 50 ("¡Cuidado! Este no es el Jardín verdadero."). → **15 objects.**

### 2.4 NPCs / dialogues (25 YAML npc files)

All 22 Pascal living things exist as NPCs, plus `columna_cristal` and `estatua_satanas` (Pascal PHidden objects promoted to NPCs) and one **invented** NPC `troll_final`. Gift items (`wants_item`) match Pascal `likeness` for all 14 trolls. Lethal weapons match for Cíclope (Maza), Lobo (Látigo), Minotauro (Espada), Cerebro (Antorcha) but **differ** for Arpía (YAML Daga vs Pascal Espada), Pulmones (Maza vs Espada), Estómago (Lanza vs Látigo), Corazón (Arco vs Daga).

**Dialogue fidelity — ZERO Pascal lines are present verbatim.** Pascal troll dialogue = `lD` (default line) + `hD` (after receiving gift); guards have `confession` (death line):

| Pascal source text (verbatim) | In YAML? | Where | Verdict |
|---|---|---|---|
| "Tráeme mi escoba y te daré un consejo." (Bruja lD) | no | — | MISSING |
| "Escucha bien, hijo. Cuando te digan «Prohibido», invoca la luz…" (Bruja hD, key[17]) | paraphrase | he_dar_escoba_bruja "…'Toma mi consejo: cuando te digan Prohibido, invoca la luz.'" | DIVERGENT |
| "No me mates, por favor. Haz que nadie pueda ver mi fealdad." (Troll lD) | no | — | MISSING |
| "El corazón de unicornio te protegerá en el corazón de la Bestia." (Troll hD, key[22]) | no | — | MISSING |
| "¡Qué brusco! Un caballero debe dirigirse a una dama de otra forma." (Doncella lD) | no | — | MISSING |
| "La última habitación está al principio." (Doncella hD, key[25]) | no | — | MISSING |
| "Dame algo para calentarme la barriga, por favor." (Esqueleto lD) | no | — | MISSING |
| "Al entrar al estómago, lleva contigo un pastel." (Esqueleto hD, key[29]) | no | invented "…'La puerta de hierro se abre con seis.'" | DIVERGENT (hint replaced) |
| "No tengo tiempo para atenderte. Llevo medio siglo buscando la quinta escencia." (Ratón lD) | no | — | MISSING |
| "¡Pssssssss!" / "Busca al Minotauro y mátalo con la espada." (Araña lD/hD) | no | invented "'Puedes cruzar el puente.'" | DIVERGENT |
| "¡Qué hambre!" / "El 12 te guiará en el Laberinto. Luego solo debes dar un paso." (Crunch) | no | invented "'…La puerta triangular se abre con mi nombre: crunch.'" | DIVERGENT (also invents wrong puzzle hint) |
| "Me muero..." / "Solo el hierro te protegerá contra las flores." (Dédalo) | no | invented | DIVERGENT |
| "Quiero ser joven para siempre." / "Solo con una daga podrás matar el corazón." (Bailarina) | no | invented | DIVERGENT |
| "¡Sal de mi presencia, estúpido mortal!" (Atenea) / "La humedad me destruye." (Hermes) | partial | he_dar_paraguas_hermes reuses "La humedad me destruye." | DIVERGENT |
| "¡Arrrggghhhh! ¡Me has matado! Puedes pasar, la contraseña es «Nombus Rostomelaris»" (Cíclope confession) | paraphrase | he_matar_ciclope "'…murmura: Nombus Rostomelaris…'" | DIVERGENT |
| "Imnus humiscuol rastomislakis!! Con esta esapada matarás a los pulmones de la Bestia." (Arpía confession) | no | — | MISSING |
| "¡Me has matado! Coge la antorcha del número divino y rompe la columna de cristal." (Minotauro) | partial | "¡Me has matado! Coge la antorcha del número divino..." (truncated) | DIVERGENT |
| "AAARRRRGGGG!!!! La palabra mágica es «Agua»." (Lobo confession) | no | — | MISSING |
| "XVBCZXV XBVCZX BVZXC!!!!!" (Cerebro confession) | partial | kept in he_matar_centro_cerebro output | DIVERGENT |

---

## 3. Episode 2 — detail

### 3.1 Rooms (55 YAML files)

All 55 YAML rooms map 1:1 to Pascal rooms 1–55 by name. **51 rooms** carry the Pascal description **verbatim** followed by an invented `Ves:` list (**DIVERGENT**). **4 rooms** differ beyond the suffix:

| YAML entity_id | Pascal idx | Difference | Verdict |
|---|---|---|---|
| bajos_de_las_cataratas | 30 | desc fully invented ("El agua se desploma desde una altura imposible…") vs Pascal "Hay un ruido ensordecedor, como si millones de tambores redoblaran…" | DIVERGENT (invented) |
| catacumbas | 28 | "dice: 'Este es para ti'." — ASCII quotes + typo fix (tí→ti) vs Pascal `dice: "Este es para tí".` | DIVERGENT (normalization) |
| celda | 48 | "donde se supone que **está** el prisionero" vs Pascal "esté" | DIVERGENT (typo fix) |
| cima_del_pico_negro | 38 | ASCII quotes around 'El Pico Negro' vs Pascal `"El Pico Negro"` | DIVERGENT (normalization) |

Representative rows (the other 50 are the same pattern):

| YAML entity_id | Pascal name / desc (trimmed) | Verdict |
|---|---|---|
| habitacion_para_huespedes | "una habitación para huéspedes" / "Está tan oscura que usted cree que las paredes y el techo se han avalanzado…" +Ves | DIVERGENT (+Ves) |
| pasillo | "el pasillo" / "Hay seis puertas distribuidas simétricamente…" +Ves | DIVERGENT (+Ves) |
| salon_de_fumar | "el Salón de Fumar" / "Hay sesenta y seis sillas… Los pitillos humean." +Ves | DIVERGENT (+Ves) |
| antesala_de_la_prueba | "la Antesala de la Prueba" / "Es un salón circular…" +Ves | DIVERGENT (+Ves) |
| habitaciones_del_hechicero | "las Habitaciones del Hechicero" / "Las habitaciones del Hechicero están dentro de una pirámide interior…" +Ves | DIVERGENT (+Ves) |
| … 50 more (all) | Pascal desc verbatim + invented Ves list | DIVERGENT (+Ves) |

**MISSING: 0. INVENTED: 0.**

### 3.2 Exits / macros (61 YAML files)

Gates are faithful (riddle answers, `requires_item`, `forbids_item`, `death_message`), but **all `passage_description` fields are invented short labels** → all DIVERGENT. No INVENTED, no MISSING.

Gate audit (Pascal gate → YAML gate):

| macro_edge_id | passage | Pascal gate | YAML gate | Verdict |
|---|---|---|---|---|
| me_pasillo_cuarto_hija | puerta_azul | Riddle "¿Cuál es el nombre de la hija del Hechicero?" → **Aura** | req_text "Aura" | ✓ |
| me_pasillo_cocina | puerta_metal | PDanger **Pañuelo** | requires_item panuelo | ✓ |
| me_casa_munecas_interior_baul | puerta_baul | keyword **MIAU** | req_text "MIAU" | ✓ |
| me_casa_munecas_jardines | pasadizo | PHidden Ventana breaker **Corta-cristales** → Pasadizo | requires_item corta_cristales | ✓ |
| me_jardines_tesoros | puerta_amarilla | keyword **Omicuos Ihanti** | req_text "Omicuos Ihanti" | ✓ |
| me_juglar_catacumbas | escalera | PDanger **Escudo de Aquiles** | requires_item escudo_de_aquiles | ✓ |
| me_subterraneos_catacumbas | tunel | PDanger **Escudo de Aquiles** | requires_item escudo_de_aquiles | ✓ |
| me_campo_cultivado_torre | rio | PDanger **Cuerda** | requires_item cuerda | ✓ |
| me_fondo_lago_cueva_cristal | grieta | PDanger **Talismán de Nieve** | requires_item talisman_de_nieve | ✓ |
| me_fondo_lago_orilla_lago | sendero_dorado | PDangerLink2 **must NOT carry Marmidosa** | forbids_item marmidosa | ✓ |
| me_desierto_orilla_lago_inv | camino | PDangerLink2 **must NOT carry Talismán de Nieve** | forbids_item talisman_de_nieve | ✓ |
| me_antesala_salon_verde | puerta_verde | PDangerLink2 **must NOT carry Anillo de oro** | forbids_item anillo_de_oro | ✓ |
| me_salon_verde_salon_azul | puerta_azul | PDangerLink2 **must NOT carry Anillo de plata** | forbids_item anillo_de_plata | ✓ |
| me_salon_azul_salon_blanco | puerta_blanca | PDangerLink2 **must NOT carry Anillo de bronce** | forbids_item anillo_de_bronce | ✓ |
| me_salon_blanco_limites | puerta_triangular | PDanger **Cinta de Moebius** | requires_item cinta_de_moebius | ✓ |
| me_limites_piramide | puente | PDanger **Grabado** | requires_item grabado | ✓ |
| me_alcoba_aura_alcoba_secreta | puerta_secreta | PHidden Carta → PDanger **Lienzo** | requires_item lienzo | ✓ |
| me_punta_torre_alcoba_aura | puerta_cristal | Riddle "¿Cuál es el nombre completo…?" → **Aura Srka** | req_text "Aura Srka" | ✓ |
| me_piramide_habitaciones_hechicero | puerta_roble | Riddle "¿Quién invirtió el reloj de Caronte?" → **Yo** | req_text "Yo" | ✓ |
| me_calabozos_celda | reja | keyword **Grifo** | req_text "Grifo" | ✓ |
| me_orilla2_jardines | avenida_hierro | PHidden Muralla breaker **Maza** → Avenida | requires_flag muralla_rota | ✓ (via he_romper_muralla with maza) |
| me_desierto_valle | avenida_flores | PHidden Muralla breaker **Piedra verde** → Avenida | **open: true — gate lost** | DIVERGENT (gate MISSING) |
| me_fondo_lago_catedral | reja | PHidden Reja breaker **Tenazas** → Escalera | requires_item tenazas | ✓ |

Graph reshape (minor): Pascal orilla 11 → Monstruo 9 via "Escalera de caracol"; YAML routes orilla↔terrazas + terrazas↔monstruo. Path preserved, edge differs.

### 3.3 Items (64 YAML files)

**8 inscriptions are FAITHFUL** (verbatim text kept; `Dice:` prefix dropped): inscripcion_ciudad, inscripcion_desierto, inscripcion_lago, inscripcion_calabozo_monstruo, inscripcion_antesala, inscripcion_terrazas, inscripcion_alcoba_ogro, inscripcion_inmortal. All other items **DIVERGENT** (rewritten / abridged + gameplay hints). No INVENTED.

| entity_id | Pascal desc (verbatim, trimmed) | YAML desc | Verdict |
|---|---|---|---|
| arco_inmortal | "Con este arco mataron a Hycrk, uno de los doce inmortales." | same + "…Arma letal contra el Inmortal y protección…" | DIVERGENT (+hint) |
| rosa_diamante | "Es increíblemete hermosa." | "Increíblemente hermosa. Debe colocarse en el Fondo del Lago — condición de victoria." | DIVERGENT (+hint) |
| piedra_de_roseta | "Esta no es la piedra original. Tiene grabadas las siguientes palabras: «Fuimos grandes una vez, │ Fio rne n e,atsd absi / antes de la Bestia │ Umsgadsuavz ne el eta»" | "Texto bilingüe codificado: 'Fuimos grandes una vez' ↔ texto alterado. Clave para descifrar los manuscritos." | DIVERGENT (encoded columns dropped) |
| tablilla_de_madera | full encoded 8-line Horantes text | "Primera mitad del Manuscrito de los Horantes, con texto codificado." | DIVERGENT (text dropped) |
| caliz | "Tiene grabadas las siguientes palabras: ' Lsmra elshrne o: …' (encoded, FORT2.Goal)" | "…Contiene texto codificado, posible segunda mitad del manuscrito." | DIVERGENT (text dropped) |
| carta_aura | "La carta dice: «¡Dios te salve, mi única esperanza! Mi padre me ha encerrado en la Torre de Cristal, que está más allá del segundo río… Búscame.»" | "¡Dios te salve, mi única esperanza! Mi padre me ha encerrado en la Torre de Cristal… Pista sobre la Torre." | DIVERGENT (truncated) |
| carta_alcoba | "«Mi querido salvador: ¿Por qué has demorado tanto? … trata de que no sufra.»" | "¿Por qué has demorado tanto? Mi padre me llevó al Abismo Infranqueable… Debe romperse según el Hechicero." | DIVERGENT (truncated) |
| marmidosa | "Es algo más allá de la comprensión humana. Usted se siente orgulloso de haberla encontrado antes del Hechicero, que lleva siglos buscándola." | "La espada rival de Excalibur. Arma letal contra el Carcelero y el Hechicero…" | DIVERGENT |
| escudo_de_aquiles | "Usted nunca había visto algo tan hermoso. Este escudo formaba parte de la nueva armadura que Hefestos le hizo a Aquiles cuando la anterior cayó en manos de los troyanos al morir Patroclo." | "Escudo forjado por Hefestos. Protección… condición de victoria." | DIVERGENT (abridged) |
| bote_carante | "Es el célebre bote de Caronte." | "El célebre bote de Caronte. Debe colocarse en la Orilla 2 — condición de victoria." | DIVERGENT (+hint) |
| reloj_de_arena | "Usted escucha un callado tic-tac." | "Emite tic-tac. Debe voltearse antes de entregar a Caronte…" | DIVERGENT (+hint) |
| huevo / reja / esfera / ventana / muralla / muralla_2 / arbol_de_marfil / estatua_cristal / columna_hielo | PHidden objects with a Pascal description | generic "Un objeto que puede ser roto." | DIVERGENT (desc dropped) |
| pescado | "¿Qué tiempo llevará en este lugar?" | "Útil para dar al Gato en el Interior del baúl." | DIVERGENT (desc replaced by hint) |
| receta | "Es una receta de cocina. Dice: 5 Ojos de rana… Usted recuerda haber probado esto en alguna parte." | ingredient list kept, closing line dropped, +hint | DIVERGENT |
| … (~50 more) | rewritten + hint | — | DIVERGENT |

**MISSING Pascal objects:** Balanza (Salón de Fumar 3), Ébano (exterior Torre 43, PHidden "NADA"), Muralla 3ª (Límites de la Fortaleza 53, PHidden "NADA"). → **3.**

### 3.4 NPCs / dialogues (23 YAML npc files)

All 23 Pascal living things present (18 Trolls, Grifo/Inmortal/Ogro/Carcelero guards, Hija del Hechicero PDaugther). Gift items and lethal weapons **faithful** (all 18 trolls want the Pascal `likeness`; Grifo=Daga, Inmortal=Arco, Ogro=Cubo de agua, Carcelero=Marmidosa, Hija=Aguja). Dialogue verbatim: **0 lines present**.

| Pascal source text (verbatim) | In YAML? | Verdict |
|---|---|---|
| "¡Tú cuidarte de Hechicero! ¡Hechicero ser malo! … ¡A tú arrancal tripa, sacal ojo, rompel hueso y echal dragrón hambroso! … ¡y pincha todo!" (Monstruo hD) | no — invented "'…se desploma. La inscripción lo advertía…'" | MISSING |
| "¡Grrrr! ¡Hambre!" (Monstruo lD) | no | MISSING |
| "Tráeme el reloj de arena, pero víralo antes de entregármelo." (Caronte lD) | no | MISSING |
| "Dentro del blanco está la llave de la muralla." (Caronte hD) | no | MISSING |
| "La piedra verde te servirá para romper la segunda muralla." (Gato hD) | no | MISSING |
| "¡No molestes!" (Gato lD) | no | MISSING |
| "En tu camino encontrarás varios anillos. Debes guardar el que tú consideres más apropiado… Elige bien." (Jardinero hD) | no | MISSING |
| "Las palabras mágicas para entrar en el cuarto del tesoro son: «Omicuos Ihanti»." (Dragon hD) | partial — password lives in the macro gate, not in dialogue | DIVERGENT |
| "No soy tu enemigo. Es mi hija quien ha elaborado este diabólico plan para eliminarnos. Rompe la carta que te dejó en la Torre de Cristal y ocurrirá un milagro." (Hechicero hD) | no | MISSING |
| "De todas las cosas sobre la tierra, la que más me fascina es la cinta de Moebius. Empiezas a recorrerla por adentro y cuando vienes a ver... ¡estás afuera!" (Sabio hD) | no | MISSING |
| "Busca las dos mitades del Manuscrito de los Horantes y descífralo. Luego coloca las marcas para abrir la Fortaleza." (Horante hD) | no | MISSING |
| "Las dos partes del manuscrito están guardadas en la Torre de Cristal. Y cuando vayas en busca de la segunda parte, lleva el triángulo contigo." (Doncella del Lago hD) | no | MISSING |
| "Si el Ogro se baña, se muere." (Pordiosero hD) | no | MISSING |
| "Solo con el Talismán de Nieve podrás entrar hasta Marmidosa." (Obispo hD) | no | MISSING |
| "No confundas la tercera muralla con la tercera barrera que tienes que romper. La tercera barrera está en tí mismo." (Inmortal confession) | no | MISSING |
| "El grifo se contorsiona tratando de arrancarse la daga y grita: «¡Aura!»" (Grifo confession) | no | MISSING |
| "¡No saldrás del lago con Marmidosa tan fácilmente!" (Ogro confession) | no | MISSING |
| "¡Mata a todos los que te mintieron si quieres salir!" (Hija del Hechicero confession) | no | MISSING |
| "ARRRGG!!! ¡Te será muy difícil abrir la celda, porque la palabra mágica es el nombre de la primera criatura que viste al salir del cuarto de huéspedes!" (Carcelero confession) | no — answer "Grifo" encoded only as the Reja keyword | MISSING |
| "El nombre de la hija del Hechicero tiene ocho letras, una está repetida tres veces y otra dos." (Encapuchado hD) | no | MISSING |

---

## 4. Top 10 most impactful gaps

1. **Episode-1 map restructure.** Rooms 16–30, 32–50 are renamed/rewritten or absent: the entire Laberinto (rooms 32–48, ~54 doors), Celda 26, Calabozos 16, Almacenes 23, Boca 17, Páramo 24/25, Salón de cristal, and Jardín falso 50 have no faithful counterpart. Blocks 100% structural fidelity and breaks traversal parity (Minotauro connects to `sala_del_columna` instead of the labyrinth; Pozo, Puerta de tela, Páramo doors missing).
2. **All NPC dialogue is absent/paraphrased (~45 lines).** Every troll lD/hD and guard confession is either missing or replaced by invented paraphrase. The single biggest "text fidelity" gap — the user's core requirement.
3. **Episode-1 Bestia gates are open.** Tráquea/Esófago (Talismán de aire) and Arteria principal (Corazón de unicornio) are `open: true`; the player can walk into the pulmones/estómago/corazón without the required items, changing difficulty and story.
4. **Espejo opaco→Puerta oculta and Estatua de Satanás→Puerta oculta are open.** The "Hueso de gato" and "Cuadro" breaker gates are lost (only he_romper flags exist, but the macros ignore them).
5. **Puerta triangular riddle answer changed** from "Rumpelstinskin" to "crunch" (me_columna_bailarina + he_dar_pastel_crunch), altering a puzzle from the original.
6. **Kill-weapon mismatches in episode 1:** Pulmones (YAML Maza / Pascal Espada), Estómago (Lanza / Látigo), Corazón (Arco / Daga), Arpía (Daga / Espada). The four "centros" become killable with the wrong weapons.
7. **`he_mirar_ep2.yaml` emits nothing** (`output: ""` on both edges) — "mirar" in episode 2 produces no narration; and ep1 `he_mirar_habitacion` renders the invented `Ves:` list baked into room descriptions.
8. **In every room description, the trailing `Ves: …` list is invented**, and in ep1 many listed exits are themselves invented (`garganta`, `pasadizo`, `tunel_banos`, `puerta_metal`, `escalera_madera`…). It also replaces Pascal's "Usted ve:" (which lists items, not exits).
9. **Encoded lore texts dropped:** Cáliz, Tablilla de Madera, Piedra de Roseta bilingual text — all reduced to "texto codificado" placeholders; the puzzle of deciphering the Horantes manuscript is lost.
10. **Missing items that block puzzles:** 6 of 7 Minotauro torches, both Cedros, the Baños Espejo, 6 inscriptions, ep2 Balanza, Ébano and the 3rd Muralla — several are needed objects (e.g. torches 1/3+ for the column puzzle; Balanza for "pesar" flavor).

---

## 5. Mapping resolutions (Pascal room → YAML entity_id)

Disambiguation performed by content (exits + NPCs present), cross-checked with `docs/02-rooms.md`:

| Pascal room (idx, name) | YAML entity_id | Basis |
|---|---|---|
| 24 un extenso páramo | sala_de_lobos | contains the Lobo guard (Pascal room 24 has Lobo) |
| 25 Salón de cristal | sala_de_la_bailarina | contains the Bailarina troll + Puerta de cristal (Agua) |
| 27 un puente de mármol | sala_de_la_arana | contains the Araña troll |
| 28 la Antesala del Laberinto | sala_del_columna | contains Columna de Cristal, Crunch, Dédalo |
| 29 la cueva del Minotauro | sala_del_minotauro | contains the Minotauro guard |
| 30 el Salón de los elegidos | sala_del_enigma | contains the Puerta dorada riddle |
| 31 un pasillo del Laberinto | laberinto_1 | only labyrinth room kept |
| 49 salida del laberinto | laberinto_salida | Pascal room 49 uses RoomAr[32].desc |
| 17 Boca + 18 Interior | garganta | amalgam (Boca/Interior both absent) |
| 19/20/21/22 Pulmones/Estómago/Corazón/Cerebro | centro_de_los_pulmones / centro_del_estomago / centro_del_corazon / centro_del_cerebro | Pascal: the organ is the room, "Centro de X" is the Guard *inside* it; YAML promotes the guard to a room |
| — (none) | cripta_final, cuarto_de_los_cuadros, cuarto_de_los_vendajes, cuarto_del_hechicero, torre_oscura | INVENTED — no Pascal counterpart |
| 50 el Jardín (falso) | — | MISSING (Pascal has two "el Jardín" rooms 13 & 50; YAML has one `jardin`) |
| 32–48 labyrinth | — | MISSING (only 31 and 49 represented) |

Notes:
- Pascal `Castle.At(i)` is 0-based over the inserted room collection, so Fort.Goal `At(11)` = rooms[12] = los Baños de la Bestia (the Troll). The YAML goal instead uses the invented `troll_final` in `cripta_final` (killed with Maza), plus 4 `centro_*_dead` flags — goal targets are mechanically parallel but textually invented.
- `LWeight = 40` (CASTLES.PAS); the YAML `max_weight: 40` matches. Player name differs: Pascal "Indy"/"Sad" vs YAML "hero"/"Aventurero".
- Episode-2 room names keep the Pascal capitalization quirks (e.g. "otra orilla del Río Negro" vs Pascal "una orillas del Río Negro" typo) — treated as name-faithful.
