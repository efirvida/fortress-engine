# La Fortaleza — Documentación de Diseño

Este directorio contiene la documentación completa del diseño de juego extraída del código fuente original en Turbo Pascal 7 de **La Fortaleza**, un juego de aventura conversacional (ficción interactiva) en español, escrito por **Miguel Enrique Cepero** bajo el sello **Merchise Software**.

## El Juego

**La Fortaleza** se compone de dos partes independientes que comparten el mismo motor:

| Parte | Archivo | Título | Habitaciones | Objetivo |
|-------|---------|--------|-------------|----------|
| I | `FORT1.PAS` | *En las entrañas de la Bestia* | 33 (50 asignadas) | Matar a los cuatro centros vitales de la Bestia |
| II | `FORT2.PAS` | *La venganza de la Bestia* | 55 | Escapar de la Fortaleza tras la muerte de la Bestia |

Ambas partes usan el motor definido en `CASTLES.PAS` (1346 líneas), un sistema de aventura conversacional orientado a objetos construido sobre Turbo Vision (`Objects` unit).

## Índice de Documentos

| Archivo | Contenido |
|---------|-----------|
| [`01-story.md`](01-story.md) | Narrativa completa: ambientación, trama Parte I, trama Parte II, personajes, lore |
| [`02-rooms.md`](02-rooms.md) | Todas las habitaciones: número, nombre, descripción, salidas, objetos, NPCs |
| [`03-items.md`](03-items.md) | Todos los objetos: nombre, ubicación, uso, relevancia en puzles |
| [`04-puzzles.md`](04-puzzles.md) | Todos los puzles: descripción, ubicación, objetos necesarios, solución |
| [`05-npcs.md`](05-npcs.md) | Todos los NPCs y enemigos: nombre, ubicación, comportamiento, diálogo |
| [`06-mechanics.md`](06-mechanics.md) | Sistema de comandos, inventario, movimiento, combate, guardado/carga |
| [`07-vocabulary.md`](07-vocabulary.md) | Todos los verbos y sustantivos reconocidos por el parser |

## Resumen Técnico

- **Lenguaje**: Turbo Pascal 7 con ensamblador (`TASM`)
- **Plataforma**: MS-DOS
- **Motor**: Orientado a objetos (hereda de Turbo Vision `TCollection`)
- **Parser**: Sistema de tokens con lexicográfico propio
- **Interfaz**: Modo texto 80×25, soporte EGA/CGA
- **Sonido**: PC Speaker vía `SOUNDS.PAS` y `SE.ASM`
- **Persistencia**: Sistema de "rastros" (archivos de comandos reproducibles)
