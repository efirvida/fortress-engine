# Exploration: fortaleza-walkthrough-complete

## Executive Summary

El walkthrough del doc (387 comandos: 146 Parte I + 241 Parte II) **NO es ejecutable verbatim contra el mundo real**: el harness de verificación reporta 135/146 fallos en la Parte I al ejecutar los comandos del doc tal cual. Las causas raíz, verificadas por ejecución:

1. **Los comandos del doc usan espacios** ("ir puerta principal") pero los pasajes YAML son snake_case ("puerta_principal") — el parser hace exact-match en `get_macro_edge_by_passage_name`, así que TODO movimiento multi-palabra falla. El héroe nunca sale del exterior.
2. **Placeholders sin resolver** en el doc: `[contraseña]`, `[contraseña del ciclope]`, `[objeto]` (paso 33) — valores decodificados del original existen pero no están en el script.
3. **`mirar` (21 usos en Parte I) no tiene hyper edge genérico** en el mundo — falla con no_action en cada uso.
4. **`interrogar` se mapea a `preguntar`** en el vocabulary del mundo, pero el edge `he_interrogar_npc` usa verb "interrogar" y `he_preguntar_npc` verb "preguntar" — el parser normaliza interrogar→preguntar y solo matchea el genérico preguntar (funciona como no-op).
5. **Peso**: maza (39) + pastel (1) = 40 lleno — cualquier `tomar` posterior falla con too_heavy hasta que el jugador deje algo. El dejar genérico (`he_dejar_item` ep1 / `he_dejar_item_ep2` ep2) tiene `operators: []` → **no mueve nada**, así que el juego es injugable más allá de tomar 2 objetos.
6. **Huérfanos**: `laberinto_salida`, `sala_de_lobos` (ep1) y `bajos_de_las_cataratas` (ep2) no tienen macro-edges → inalcanzables. `lobo` NPC existe en `sala_de_lobos` (paso 27 del doc) pero no se puede matar.
7. **Antorchas 1-7** del paso 38: solo existen `antorcha` y `antorcha_3` — el resto no modelado (decorativas según el original, solo importan antorcha + antorcha_3).
8. **Laberinto comprimido**: el doc usa "puerta 1/2/3" (R31-R37), el YAML comprime a laberinto_1→sala_del_minotauro→sala_del_columna con pasajes sendero_dorado/salida.
9. **Passwords probados en tests**: solo Abrete Sesamo (L2) y Aura (L5). Sin test en contexto: Nombus Rostomelaris, Luz, Agua, crunch, treinta y nueve, seis, cdfghjklmnopqruvwxyz, Aura Srka, MIAU, Omicuos Ihanti, Grifo, Yo.
10. **Muertes de lore no modeladas**: pañuelo en cocina al Goal() (nota 6), hija sin aguja (nota 7) — los edges `me_pasillo_cocina` (item panuelo + death) y `he_matar_hija_del_hechicero` existen pero el death del Goal con pañuelo no está.

## Grafos completos mapeados

### Parte I (45 macros, 25 NPCs, 86 hyper-edges)
- Exterior: puerta_principal (Abrete Sesamo), puerta_secreta (antorcha), garganta (open), tunel (open)
- Salon→juegos (puerta_negra open); juegos→espejos (escalera "treinta y nueve"), juegos→patio (puerta_azul open)
- Biblioteca: puerta (Nombus Rostomelaris); pasillo: puerta_prohibida (Luz)
- Laberinto: laberinto_1→minotauro (sendero_dorado open), minotauro→columna (salida open), columna→cripta (cripta open)
- Columna: puerta_triangular (crunch), puerta_hierro (seis), puerta_madera (flag madera_rota), bailarina→enigma puerta_cristal (Agua), enigma→cerebro puerta_dorada (cdfghjklmnopqruvwxyz)
- Centros: garganta→pulmones (traquea), →estomago (esofago), →corazon (arteria_principal); pulmones→corazon (vena); estomago→cerebro (conducto); cerebro→cripta (escondite)

### Parte II (61 macros, 23 NPCs, 122 hyper-edges)
- Ritual: antorcha→habitacion_para_huespedes, pendulo→salon_de_fumar, espejo_roto→cuarto_de_la_hija_del_hechicero, bote_carante→otra_orilla_del_rio_negro, rosa_diamante→fondo_del_lago, escudo_de_aquiles→ciudad_abandonada, cinta_de_moebius→exterior_de_la_torre_de_cristal
- Gates: Aura (pasillo→cuarto_hija), Aura Srka (punta_torre→alcoba_hija), MIAU (casa_munecas→baul), Omicuos Ihanti (jardines→tesoros), Grifo (calabozos→celda), Yo (piramide→habitaciones_hechicero)
- Danger: lienzo (alcoba_secreta, death), cuerda (rio, death), escudo_de_aquiles (subterraneos→catacumbas, death), tenazas (fondo→catedral), talisman_de_nieve (fondo→cueva, death), saltador (precipicio, death), grabado (puente, death), corta_cristales (pasadizo), panuelo (cocina, death)

## Enfoque recomendado

**Script curado completo de 387 comandos** derivado del doc con:
- Pasajes en snake_case YAML (resolución exacta)
- Placeholders resueltos con passwords decodificados
- `mirar` como no-op con edge genérico (o accept en el harness)
- Orden corregido (paso 17/18)
- Peso gestionado: dejar objetos (requiere fix del dejar genérico)

**Fixes necesarios**:
- **MOTOR (requiere propuesta/aprobación)**: el dejar genérico con target "*" necesita un TRANSFER dinámico al anchor actual — hoy no existe mecanismo. Alternativa de DATOS: edges de dejar específicos por objeto (como los 7 rituales).
- **DATOS**: conectar huérfanos (laberinto_salida, sala_de_lobos, bajos_de_las_cataratas) según el original; modelar antorchas 1/2/4/5/6/7; agregar edge genérico `mirar`; passwords ya corregidos pero sin test.
- **TEST**: script curado de 387 comandos con asserts por fase; verificación de cada password en contexto; muerte pañuelo al Goal; cada habitación visitada.
