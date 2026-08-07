# Condiciones de Victoria — Fortaleza Partes I y II

Análisis exacto extraído del código fuente de `FORT1.PAS` y `FORT2.PAS`.

---

## PARTE I: Victoria sobre la Bestia

### Código fuente (`FORT1.PAS` líneas 28-35)

```pascal
function Fort.Goal : boolean;
  begin
    Goal := (PRoom( At(21) )^.Get( 'Centro del cerebro' ) = nil) and
            (PRoom( At(20) )^.Get( 'Centro del corazon' ) = nil) and
            (PRoom( At(19) )^.Get( 'Centro del estomago' ) = nil) and
            (PRoom( At(18) )^.Get( 'Centro de los pulmones' ) = nil) and
            (PRoom( At(11) )^.Get( 'Troll' ) = nil)
  end;
```

### Traducción del estado requerido

| Condición | At(x) | Habitación | Significado |
|-----------|-------|------------|-------------|
| `Centro del cerebro = nil` | At(21) → room 22 | el Cerebro de la Bestia | Debes **matar** al Guard "Centro del cerebro" con la **Antorcha** |
| `Centro del corazon = nil` | At(20) → room 21 | el Corazón de la Bestia | Debes **matar** al Guard "Centro del corazón" |
| `Centro del estomago = nil` | At(19) → room 20 | el Estómago de la Bestia | Debes **matar** al Guard "Centro del estomago" |
| `Centro de los pulmones = nil` | At(18) → room 19 | Pulmones de la Bestia | Debes **matar** al Guard "Centro de los pulmones" |
| `Troll = nil` | At(11) → room 12 | los Baños de la Bestia | Debes **matar** al Troll (cualquier arma sirve) |

### Mapeo de habitaciones (índices Castle.Insert)

Las habitaciones se insertan secuencialmente con `f^.insert(rooms[i])` para `i := 1 to NRooms`. `At(0)` = primera insertada = rooms[1]:

| At(n) | Room # | Nombre |
|-------|--------|--------|
| At(0) | 1 | el exterior de la fortaleza |
| At(10) | 11 | la Sala de armas |
| At(11) | 12 | los Baños de la Bestia |
| At(12) | 13 | el Jardín |
| At(17) | 18 | Interior de la Bestia |
| At(18) | 19 | Pulmones de la Bestia |
| At(19) | 20 | el Estómago de la Bestia |
| At(20) | 21 | el Corazón de la Bestia |
| At(21) | 22 | el Cerebro de la Bestia |

### Requisitos para matar cada Centro

Los Guards (tipo `Guard`) tienen una propiedad `lethalweap`: solo mueren si los atacas con el arma correcta.

| Guard | Habitación | Arma letal | Cómo llegar |
|-------|------------|------------|-------------|
| Centro de los pulmones | 19 (Pulmones) | Maza (probable, decodificado de key[32]) | Desde 18 vía Tráquea (DangerLink, needs ¿Talismán de aire?) |
| Centro del estomago | 20 (Estómago) | Lanza (probable, decodificado de key[33]) | Desde 18 vía Esófago (DangerLink, needs ¿Paraguas?) |
| Centro del corazón | 21 (Corazón) | Arco (probable, decodificado de key[34]) | Desde 18 vía Arteria principal (DangerLink, needs Corazón de unicornio) |
| Centro del cerebro | 22 (Cerebro) | Antorcha (decodificado de key[38]) | Desde 30 vía Puerta dorada (acertijo) |
| Troll | 12 (Baños) | Cualquiera (Troll.Die acepta cualquier arma) | Desde Jardín (13) vía Puerta verde |

### Armas disponibles para los Centros

Todas las armas están en la **Sala de armas (room 11)**:
- **Maza** (peso 39, también en exterior room 1)
- **Lanza** (peso 10)
- **Arco** (peso 5)
- **Espada** (peso 5)
- **Daga** (peso 3)
- **Ariete** (peso 30)
- **Látigo** (peso 2)

Las armas letales de los Centros están codificadas en el array `key` usando `DecodeLine` (resta 20 a cada byte). Según el contexto del juego:

- key[32] ≈ "Maza" (para Centro de los pulmones)
- key[33] ≈ "Lanza" (para Centro del estómago)
- key[34] ≈ "Arco" (para Centro del corazón)
- key[38] ≈ "Antorcha" (para Centro del cerebro, confirmado por la descripción "Usa la antorcha!")

### Pasos para la victoria (resumen)

1. Obtener las 4 armas de la Sala de armas (room 11)
2. Llevar la Antorcha del Pasillo (room 7)
3. Entrar a la Boca de la Bestia (room 17) desde el Salón de cristal (room 25)
4. Atravesar la Garganta hacia el Interior (room 18)
5. Usar los talismanes correctos para cruzar cada DangerLink:
   - Talismán de aire (room 16) → Tráquea → Pulmones (room 19)
   - Paraguas (room 16) → Esófago → Estómago (room 20)
   - Corazón de unicornio (room 14) → Arteria principal → Corazón (room 21)
6. Matar cada Centro con su arma correcta
7. Resolver el acertijo del Salón de los elegidos (room 30) para entrar al Cerebro
8. Matar al Centro del cerebro con la Antorcha
9. Matar al Troll en los Baños (room 12)

### Mensaje de victoria (Parte I)

```
Usted ha vencido a la Bestia.
Parece ser una persona persistente y eso es un mérito muy grande.
La persistencia es indispensable para los que luchan por el bien,
sobre todo porque los que luchan por el mal son muy persistentes también.
Veremos si en la próxima versión de La Fortaleza tiene igual suerte.

                                             Un servidor:
                                             M. Cepero
```

---

## PARTE II: Victoria sobre el Hechicero

### Código fuente (`FORT2.PAS` líneas 31-80)

```pascal
function Fort.Goal : boolean;
  const
    SourcerDead  : boolean = false;
    DaugtherDead : boolean = false;

  procedure SourcererDie;
    begin
      Output( 'Usted solo alcanza a herir al Hechicero, que ha desaparecido misteriosamente.' );
      Output( 'Se escucha una voz que dice: "¡Estúpido! Vas por el camino equivocado."' );
    end;

  procedure DaugtherDie;
    begin
      Output( 'En el lugar que ocupaba la Hija del Hechicero ha aparecido un objeto.' );
      PRoom(At(45))^.Insert( new( PThing, Init( 'Cáliz', '...', 3 )));
    end;

  begin
    if (PRoom( At(54) )^.Get( 'Hechicero' ) = nil) and not SourcerDead
      then
        begin
          SourcererDie;
          SourcerDead := true
        end;
    if (PRoom( At(45) )^.Get( 'Hija del Hechicero' ) = nil) and not DaugtherDead
      then
        begin
          DaugtherDie;
          DaugtherDead := true
        end;
    if PRoom( At(6) )^.Get( 'Pañuelo' ) <> nil
      then ManX^.Die( '' );
    Goal := (PRoom( At(30) )^.Get( 'Rosa diamante' ) <> nil) and
            (PRoom( At(11) )^.Get( 'Bote' ) <> nil) and
            (PRoom( At(0) )^.Get( 'Antorcha' ) <> nil) and
            (PRoom( At(42) )^.Get( 'Cinta de Moebius' ) <> nil) and
            (PRoom( At(39) )^.Get( 'Escudo de Aquiles' ) <> nil) and
            (PRoom( At(3) )^.Get( 'Espejo' ) <> nil) and
            (PRoom( At(2) )^.Get( 'Péndulo' ) <> nil) and
            (PRoom( At(45) )^.Get( 'Hija del Hechicero' ) = nil) and
            (PRoom( At(8) )^.Get( 'Monstruo' ) = nil)
  end;
```

### Estado requerido para la victoria

| Condición | At(x) → Room | Significado |
|-----------|-------------|-------------|
| `Rosa diamante <> nil` | At(30) → 31 (fondo del Lago) | Debe haber una Rosa diamante **en el fondo del Lago** |
| `Bote <> nil` | At(11) → 12 (orillas Río Negro) | Debe haber un Bote **en la orilla 2** |
| `Antorcha <> nil` | At(0) → 1 (habitación huéspedes) | Debe haber una Antorcha **en la habitación inicial** |
| `Cinta de Moebius <> nil` | At(42) → 43 (Torre Cristal exterior) | Cinta de Moebius en la base de la torre |
| `Escudo de Aquiles <> nil` | At(39) → 40 (Ciudad Abandonada) | Escudo de Aquiles en la ciudad |
| `Espejo <> nil` | At(3) → 4 (cuarto hija Hechicero) | Espejo en el cuarto de la hija |
| `Péndulo <> nil` | At(2) → 3 (Salón de Fumar) | Péndulo en el salón |
| `Hija del Hechicero = nil` | At(45) → 46 (Alcoba Secreta) | Matar a la Hija con **Aguja** |
| `Monstruo = nil` | At(8) → 9 (calabozo) | Matar al Monstruo (Troll, cualquier arma) |

### Efectos secundarios al evaluar Goal

1. **Si mataste al Hechicero (room 55) sin secuencia correcta:** `SourcererDie` — el Hechicero desaparece y una voz te dice que vas por camino equivocado. No impide ganar pero es advertencia.

2. **Si mataste a la Hija del Hechicero:** `DaugtherDie` — aparece un **Cáliz** en la Alcoba Secreta (room 46) con una inscripción críptica que es la clave para descifrar los manuscritos.

3. **Si dejaste el Pañuelo en el cuarto del Leñador (room 6):** **MUERTE INSTANTÁNEA** (`ManX^.Die( '' )`). Esto significa que NUNCA debes dejar (drop) el Pañuelo en room 6.

### Significado de la condición de victoria

La victoria en Parte II **NO** requiere matar al Hechicero, sino realizar un **ritual de colocación de objetos** en ubicaciones específicas de la Fortaleza, inspirado en las pistas de los manuscritos horantes.

El objetivo es colocar 7 objetos en 7 lugares específicos, matar a 2 enemigos, y NO matar al Hechicero (o al menos no antes de completar el ritual).

### Mapeo At() → Room para Parte II

| At(n) | Room | Nombre |
|-------|------|--------|
| At(0) | 1 | una habitación para huéspedes |
| At(1) | 2 | el pasillo |
| At(2) | 3 | el Salón de Fumar |
| At(3) | 4 | el cuarto de la hija del Hechicero |
| At(6) | 7 | la Cocina |
| At(8) | 9 | el calabozo del Monstruo |
| At(11) | 12 | una orillas del Río Negro |
| At(30) | 31 | fondo del Lago |
| At(39) | 40 | la Ciudad Abandonada |
| At(42) | 43 | el exterior de la Torre de Cristal |
| At(45) | 46 | la Alcoba Secreta |
| At(54) | 55 | las Habitaciones del Hechicero |

### Origen de cada objeto requerido

| Objeto | Dónde se obtiene |
|--------|-----------------|
| Antorcha | Subterráneos (room 27) |
| Péndulo | Choza del Sabio (room 41) |
| Espejo | Alcoba de Aura (room 45), está roto |
| Rosa diamante | Habitación de los tesoros (room 17) |
| Bote | Orilla 1 del Río Negro (room 11), peso: pred(LWeight) = 39 |
| Escudo de Aquiles | Desierto (room 36) |
| Cinta de Moebius | Choza del Sabio (room 41) |

### Orden lógico del ritual

Los objetos deben ser **dejados** (`dejar`) en las habitaciones objetivo. El orden exacto no importa mientras todos estén en su lugar al momento de evaluar `Goal()`.

### Mensaje de victoria (Parte II)

```
De repente las paredes comienzan a desvanecerse.
¡Ha logrado salir de la Fortaleza!

                               EPILOGO

Usted mira al cielo agradecido y besa la tierra.

Después de que la emoción del primer momento hubo pasado usted se sienta sobre una
piedra al borde de la carretera y comienza a pensar. "¿Para qué salí?", se pregunta,
"si el exterior nunca me gustó tanto".

Usted recuerda a la Doncella del Lago, y piensa en la vida que hubiera podido llevar
junto a ella. Piensa también en el Hechicero, un poderoso amigo, y en la remota y
hermosa posibilidad de hacer renacer la civilización de los horantes. Ahora, sin la
Bestia y sin la Hija del Hechicero, la Fortaleza podría ser convertida en un
verdadero paraíso.

¿Quién está al otro extremo de los hilos que manejan al hombre?
¿Quién nos hace confundir lo que somos y lo que queremos ser?
¿Quién es el responsable de nuestros errores?
¿Quién sino nosotros mismos?

Usted vuelve la cabeza hacia el lugar que ocupó la Fortaleza. Ahora lo comprende
todo claramente, esta era la venganza de la Bestia: dejarlo vivir, pero fuera de la
Fortaleza.

¿Quería un final feliz? Espere la próxima versión.

                                                       M. Cepero
```

---

## Condiciones de Derrota

### Muerte por DangerLink sin talismán

En `CASTLES.PAS` (líneas 890-902), `DangerLink.Pass`:
```pascal
procedure DangerLink.Pass( body: PThing );
  var
    auxP: PThing;
  begin
    auxP := PMan(body)^.bag^.Get( talisman^ );
    if auxP = nil
      then
        begin
          Output( _No_protection );
          PMan(body)^.Die( '' );
        end
      else Linking.Pass( body );
  end;
```

### Muerte por DangerLink2 con talismán

En `CASTLES.PAS` (líneas 906-918), `DangerLink2.Pass`:
```pascal
procedure DangerLink2.Pass( body: PThing );
  var
    auxP: PThing;
  begin
    auxP := PMan(body)^.bag^.Get( talisman^ );
    if auxP <> nil
      then
        begin
          Output( _Undesirable_object );
          PMan(body)^.Die( '' );
        end
      else Linking.Pass( body );
  end;
```

### Muerte al enfrentar enemigos sin el arma correcta

En `CASTLES.PAS` (líneas 964-974), `Guard.Die`:
```pascal
function Guard.Die( weapon: string ): boolean;
  begin
    if Equals(upper(lethalweap^), upper(weapon))
      then
        begin
          Output( confession^ );
          LivingThing.Die( weapon );
        end
      else Output( _Ja_ja_ja );
    Die := dead;
  end;
```

Si no usas el arma correcta, el Guard se ríe y no muere.

### Muerte al enfrentar a la Hija del Hechicero sin Aguja

En `CASTLES.PAS` (líneas 1329-1344), `TDaugther.Die`:
```pascal
function TDaugther.Die( weapon: string ): boolean;
  begin
    if upper(weapon) = upper(lethalweap^)
      then
        begin
          Output( confession^ );
          LivingThing.Die( weapon );
        end
      else
        begin
          Output( 'Usted fracasa en su intento. La enorme serpiente se lanza sobre usted '+
                  'y lo devora en pocos segundos.' );
          ManX^.Die( '' );
        end;
    Die := dead;
  end;
```

Si no usas la **Aguja** contra la Hija del Hechicero, **mueres instantáneamente**.

### Muerte por Pañuelo en room 6 (Parte II)

```pascal
if PRoom( At(6) )^.Get( 'Pañuelo' ) <> nil
  then ManX^.Die( '' );
```

Si en algún momento el Pañuelo está en la Cocina (room 7 → At(6)), mueres. Nota: `At(6)` = rooms[7] = la Cocina, NO el cuarto del Leñador. El Pañuelo se obtiene en room 4 (cuarto de la hija del Hechicero) y es necesario para cruzar la Puerta de metal (DangerLink) hacia la Cocina sin morir. Pero si lo dejas en la Cocina, mueres.

### Muerte por comando Terminar/Abandonar

```pascal
vQuit1, vQuit2:
  begin
    m^.Die( '' );
    relevant := false
  end;
```

---

## Resumen: Diferencias clave entre ambas partes

| Aspecto | Parte I | Parte II |
|---------|---------|----------|
| Tipo de victoria | Matar 5 enemigos | Colocar 7 objetos + matar 2 enemigos |
| Número de habitaciones | 33 (efectivas) + 18 de laberinto = 51 | 55 |
| Mecánica principal | Combate | Recolección y colocación de objetos |
| Laberinto | Sí (rooms 28-49) | No |
| Peligro ambiental | DangerLinks dentro de la Bestia | DangerLinks en pasajes y La Prueba |
| Villano final | La Bestia (múltiples Centros) | La Hija del Hechicero (no el Hechicero) |
| Acertijos | 4 (Escalera, Puerta triangular, Puerta dorada, Puerta de hierro) | 3 (Puerta Azul, Puerta Cristal, Puerta Roble) |
