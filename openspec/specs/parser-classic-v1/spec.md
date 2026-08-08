# Classic Parser V1 Specification

## Purpose

Define the deterministic Spanish parser required by TDD §4.15 and PRD §5.

## ADDED Requirements

### Requirement: Fortaleza vocabulary and command parsing

`ClassicParser` MUST expose `language` (default `"es"`), normalize input with NFKD and combining-mark removal, use V2 stopwords `{el, la, los, las, un, una, al, del, por}`, and return a `ParsedCommand` with the active protagonist as subject. The exact 37-constant inventory is:

|#|Constant|Canonical result|
|-:|---|---|
|1|ATRAVESAR|ir|
|2|IR|ir|
|3|TOMAR|tomar|
|4|COGER|tomar|
|5|SOLTAR|dejar|
|6|DEJAR|dejar|
|7|ABRIR|abrir|
|8|MATAR|matar|
|9|ASESINAR|matar|
|10|OBSERVAR|mirar|
|11|MIRAR|mirar|
|12|LEER|examinar|
|13|VER|examinar|
|14|ROMPER|romper|
|15|FORZAR|romper|
|16|PREGUNTAR|interrogar|
|17|INTERROGAR|interrogar|
|18|INVENTARIO|inventario|
|19|REGALAR|dar|
|20|DAR|dar|
|21|CON|con|
|22|A|a|
|23|ABANDONAR|terminar|
|24|TERMINAR|terminar|
|25|RESPONDIENDO|respondiendo|
|26|DICIENDO|diciendo|
|27|EJECUTAR|ejecutar|
|28|SALVAR|salvar|
|29|DESTROZAR|romper|
|30|CRUZAR|ir|
|31|PORCIENTO|porciento|
|32|TODO|todo|
|33|PESAR|pesar|
|34|MIAR|orinar|
|35|ORINAR|orinar|
|36|CLS|cls|
|37|PASAR|ir|

The parser MUST also recognize `EXAMINAR` as the `examinar` synonym documented by TDD §4.15. Unknown verbs MUST remain non-throwing. Entity names MUST resolve only against the current spatial anchor and active protagonist inventory. Exact matches win; partial matches use all input words and shortest-name-wins; equal candidates return the raw phrase unresolved. `CON` MUST route to `instrument`; `A` MUST route to `context`. `DICIENDO` and `RESPONDIENDO` MUST route their remainder to `text`, while standalone `DECIR` and `RESPONDER` MUST put their remainder in `text`.

#### Scenario: Normalize and resolve a command

- GIVEN an entity in the active protagonist's anchor or inventory
- WHEN `abrir la puerta diciendo ábrete ñandú` is parsed
- THEN names and verb are normalized, the target resolves, and `text` is `abre te nandu` without stopword filtering

#### Scenario: Partial matching and ambiguity

- GIVEN candidates `Puerta principal` and `Puerta secreta`
- WHEN an exact, unique partial, or equally short phrase is parsed
- THEN exact wins, the shortest partial wins, or the ambiguous raw phrase is returned

## ADDED Requirements

### Requirement: Vocabulary load cascade

The parser MUST prefer a constructor override, then the world's `shared/vocabulary.yaml`, then `DEFAULT_SPANISH_VOCABULARY`. Vocabulary MUST support verbs/synonyms, stopwords, prepositions, speech markers, and language.

#### Scenario: Missing vocabulary file

- GIVEN no override and no world vocabulary file
- WHEN the parser is constructed
- THEN the Fortaleza inventory and V2 stopwords remain available
