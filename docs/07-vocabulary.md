# 07 — Vocabulario

## Funcionamiento del Parser

El parser está implementado en `LEXIC.PAS` (lexicográfico) y `VOCABL.PAS` (vocabulario). El flujo es:

1. `Castle.AskMan` → lee la entrada del jugador
2. `voc^.SetStr(wish)` → asigna el string
3. `voc^.SetToken` → extrae el primer token
4. `voc^.IsKWord(voc^.token)` → clasifica el verbo
5. Según el verbo, extrae el resto de la línea como objeto/sujeto

**Palabras ignoradas** (artículos y preposición, `VOCABL.PAS:180-183`):
- `LA`, `EL`, `POR`, `AL`

**Normalización** (`VOCABL.PAS:128-141`): Las tildes y caracteres especiales del español se convierten:
- `áéíóúüñÁÉÍÓÚÜÑ` → `aeiounN` (las mayúsculas también)

## Verbos Reconocidos

Definidos en `ComAr` (`VOCABL.PAS:185-191`), mapeados a constantes:

| # | Constante | Verbo(s) | Acción |
|---|-----------|----------|--------|
| 1 | `vGo1` | ATRAVESAR | Moverse a través de una unión |
| 2 | `vGo2` | IR | Moverse a través de una unión |
| 3 | `vTake1` | TOMAR | Coger un objeto |
| 4 | `vTake2` | COGER | Coger un objeto |
| 5 | `vLeave1` | SOLTAR | Dejar un objeto |
| 6 | `vLeave2` | DEJAR | Dejar un objeto |
| 7 | `vOpen` | ABRIR | Abrir una puerta/unión |
| 8 | `vKill1` | MATAR | Atacar a un ser vivo |
| 9 | `vKill2` | ASESINAR | Atacar a un ser vivo |
| 10 | `vLook1` | OBSERVAR | Mirar la habitación |
| 11 | `vLook2` | MIRAR | Mirar la habitación o un objeto |
| 12 | `vSee1` | LEER | Examinar un objeto |
| 13 | `vSee2` | VER | Examinar un objeto |
| 14 | `vBreak1` | ROMPER | Destruir un objeto oculto |
| 15 | `vBreak2` | FORZAR | Destruir un objeto oculto |
| 16 | `vAsk1` | PREGUNTAR | Interrogar a un NPC |
| 17 | `vAsk2` | INTERROGAR | Interrogar a un NPC |
| 18 | `vInvent` | INVENTARIO | Listar pertenencias |
| 19 | `vGive1` | REGALAR | Dar un objeto a un NPC |
| 20 | `vGive2` | DAR | Dar un objeto a un NPC |
| 21 | `vWith` | CON | Preposición (para armas, contraseñas) |
| 22 | `vTo` | A | Preposición (para destinatario) |
| 23 | `vQuit1` | ABANDONAR | Terminar el juego (morir) |
| 24 | `vQuit2` | TERMINAR | Terminar el juego (morir) |
| 25 | `vSay1` | RESPONDIENDO | Introducir respuesta a acertijo |
| 26 | `vSay2` | DICIENDO | Introducir palabras mágicas |
| 27 | `vExec` | EJECUTAR | Ejecutar archivo de rastro |
| 28 | `vSave` | SALVAR | Guardar rastro |
| 29 | `vBreak3` | DESTROZAR | Romper objeto (alias de ROMPER) |
| 30 | `vGo3` | CRUZAR | Moverse a través de una unión |
| 31 | `vPerc` | PORCIENTO | Mostrar progreso |
| 32 | `vAll` | TODO | Con DEJAR: soltar todo |
| 33 | `vWeigh` | PESAR | Pesar un objeto (requiere Balanza) |
| 34 | `vPiss1` | MIAR | Easter egg |
| 35 | `vPiss2` | ORINAR | Easter egg |
| 36 | `vCls` | CLS | Rechazado: "Recuerde que se encuentra dentro de La Fortaleza, y no en el sistema operativo." |
| 37 | `vGo4` | PASAR | Moverse a través de una unión |

## Sintaxis de Comandos

### Movimiento
```
IR <puerta>
ATRAVESAR <puerta>
CRUZAR <puerta>
PASAR <puerta>
IR POR LA <puerta>
```
Si la puerta está abierta, se cruza automáticamente. Si está cerrada, el motor intenta abrirla primero.

### Abrir
```
ABRIR <puerta>
ABRIR <puerta> CON <contraseña>
ABRIR <puerta> DICIENDO <contraseña>
ABRIR <puerta> RESPONDIENDO <respuesta>
```
`DICIENDO`, `RESPONDIENDO` y `CON` son equivalentes para este comando.

### Coger / Tomar
```
COGER <objeto>
TOMAR <objeto>
```

### Dejar / Soltar
```
DEJAR <objeto>
SOLTAR <objeto>
DEJAR TODO        — vacía todo el inventario en la habitación
```

### Mirar
```
MIRAR             — describe la habitación actual
OBSERVAR          — describe la habitación actual
```

### Ver / Leer / Examinar
```
VER <objeto>
MIRAR <objeto>
LEER <objeto>
```

### Romper / Forzar / Destrozar
```
ROMPER <objeto> CON <herramienta>
FORZAR <objeto> CON <herramienta>
DESTROZAR <objeto> CON <herramienta>
```

### Matar / Asesinar
```
MATAR <enemigo>
MATAR <enemigo> CON <arma>
ASESINAR <enemigo> CON <arma>
```
Si no se especifica arma, se intenta con `''` (manos desnudas).

### Preguntar / Interrogar
```
PREGUNTAR <npc>
INTERROGAR <npc>
```

### Dar / Regular
```
DAR <objeto> A <npc>
REGALAR <objeto> A <npc>
```
El `A` entre objeto y destinatario es obligatorio.

### Inventario
```
INVENTARIO
```
Muestra cada objeto con su peso en "bolsas".

### Pesar
```
PESAR <objeto>
```
Requiere tener la Balanza en el inventario.

### Porciento
```
PORCIENTO
```

### Salvar / Ejecutar rastro
```
SALVAR            — guarda comandos en archivo
EJECUTAR          — reproduce comandos desde archivo
```

### Terminar
```
TERMINAR
ABANDONAR
```
Provoca la muerte del jugador.

---

## Objetos del Juego (Nombres Reconocidos por el Parser)

### Parte I

`Roble`, `Maza`, `Pastel de cerezas`, `Llamador de bronce`, `Puerta principal`, `Túnel`, `Pared solitaria`, `Puerta secreta`, `Monolito de mármol`, `Trebol`, `Puerta negra`, `Retrato`, `Escoba`, `Escalera`, `Inscripción`, `Puerta azul`, `Hilo de Ariadna`, `Puerta verde`, `Estatua de Atenea`, `Estatua de Hermes`, `Balanza`, `Hueso de gato`, `Espejo opaco`, `Puerta oculta`, `Vaso de agua`, `Candelabro`, `Libro`, `Cíclope`, `Puerta`, `Antorcha`, `Puerta vieja`, `Puerta roja`, `Puerta prohibida`, `Puerta gris`, `Polvo mágico`, `Poción para crecer`, `Escaparate`, `Bruja`, `Vendajes`, `Cama`, `Grabado`, `Homúnculo`, `Piedra filosofal`, `Máquina del tiempo`, `Espada`, `Lanza`, `Arco`, `Daga`, `Ariete`, `Látigo`, `Rosa`, `Espejo`, `Troll`, `Jardín`, `Cedro`, `Puerta amarilla`, `Puerta de hierro`, `Puerta de madera`, `Cuadro`, `Corazón de unicornio`, `Doncella`, `Taza de café`, `Cigarro`, `Arpía`, `Paraguas`, `Talismán de aire`, `Esqueleto`, `Puerta triangular`, `Garganta`, `Tráquea`, `Esofago`, `Arteria principal`, `Centro de los pulmones`, `Centro del estomago`, `Centro del corazon`, `Centro del cerebro`, `Hacha`, `Ratón`, `Lobo`, `Puerta de cristal`, `Pozo`, `Puerta de tela`, `Bailarina`, `Araña`, `Martillo`, `Estatua de Satanás`, `Crunch`, `Columna de Cristal`, `Dédalo`, `Minotauro`, `Antorcha 1`-`7`, `Puerta dorada`, `Puerta 1`-`3`, `Salida`

### Parte II

`Puerta`, `Puerta de espinos`, `Puerta de metal`, `Puerta Negra`, `Puerta Azul`, `Puerta de oro`, `Grifo`, `Balanza`, `Inscripción`, `Piedra de Roseta`, `Pañuelo`, `Carta`, `Agujero`, `Ventana`, `Pasadizo`, `Puerta del baúl`, `Daga`, `Botella de vino`, `Hacha`, `Receta`, `Muslo de carnero`, `Pescado`, `Reloj de arena`, `Silla`, `Escalera de caracol`, `Monstruo`, `Piedra verde`, `Gato`, `Caronte`, `Bote`, `Río Negro`, `Arbol de marfil`, `Maza`, `Muralla`, `Avenida de hierro`, `Puerta de madera`, `Puerta amarilla`, `Puerta de tela`, `Puerta verde`, `Puerta roja`, `Piedra`, `Jardinero`, `Túnel`, `Huevo`, `Dinosaurio`, `Muñeco diabólico`, `Aguja`, `Corta-cristales`, `Sombrero`, `Rosa diamante`, `Anillo de oro`, `Arpa`, `Bolsa`, `Puerta blanca`, `Escalera`, `Dragón`, `Inmortal`, `Puerta de piedra`, `Saltador`, `Sonajero`, `Talismán de Nieve`, `Puerta de hierro`, `Desierto`, `Puerta gris`, `Puerta negra`, `Anillo de bronce`, `Lienzo`, `Grabado`, `Escalera`, `Cuerda`, `Juglar`, `Ogro`, `Cubo de agua`, `Túnel`, `Antorcha`, `Pasadizo`, `Esqueleto de Murciélago`, `Catarata`, `Anillo de plata`, `Lago`, `Grieta`, `Reja`, `Sendero dorado`, `Doncella del Lago`, `Marmidosa`, `Camino`, `Ruta de los camellos`, `Pordiosero`, `Catedral`, `Rosario`, `Obispo`, `Camino`, `Avenida de las flores`, `Montañas`, `Camello`, `Bolsa de semillas`, `Precipicio`, `Ladera`, `Puerta de Madera`, `Monje`, `Ciudad`, `Escalera`, `Puerta de Hierro`, `Estatua de Cristal`, `Horante`, `Sabio`, `Cinta de Moebius`, `Péndulo`, `Río`, `Tenazas`, `Labrador`, `Ebano`, `Escalera de Caracol`, `Esfera`, `Tablilla de Madera`, `Puerta de Cristal`, `Espejo`, `Puerta Secreta`, `Hija del Hechicero`, `Reja`, `Carcelero`, `Encapuchado`, `Arco`, `Puerta Verde`, `Puerta Blanca`, `Puerta triangular`, `Puente`, `Guardián`, `Columna de Hielo`, `Puerta de Roble`, `Hechicero`

## Comparación de Strings

La función `Equals` en `EQSTRING.PAS:44-67` implementa un matching por palabras:

- Divide ambos strings en palabras
- Cada palabra del segundo string debe aparecer en el primero
- Esto permite matching parcial: `"Puerta Principal"` coincide con `"Puerta"` o `"Principal"`
- **Importante**: el orden de búsqueda importa — `Equals` busca que todas las palabras del segundo string estén en el primero, pero es más permisivo que una igualdad exacta

La función `Room.Get` (`CASTLES.PAS:352-380`) usa dos niveles:
1. `ExactNameMatch`: coincidencia exacta (después de normalizar)
2. `NonExactNameMatch`: coincidencia por `Equals` (matching parcial)
