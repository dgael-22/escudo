# Escudo Medieval 3D

Escudo medieval modelado, texturizado (PBR) y exportado a GLB, mostrado en una página responsive con
[`<model-viewer>`](https://modelviewer.dev/) de Google (v4.4.0).

![Vista general](screenshots/escritorio-vista-general.png)
![Interacción activa](screenshots/escritorio-interaccion.png)

## Publicación

- **Página pública:** _pendiente de publicar_ (ver «Publicar» abajo; se añadirá aquí la URL verificada)
- **Repositorio:** _pendiente de subir_

## Descripción del modelo

Escudo heráldico (forma «heater») con cuerpo de tablas de madera ligeramente curvado, reborde de acero que envuelve
todo el canto, flejes de acero en cruz con remaches (13 en el reborde y 8 en los flejes) y un emblema de bronce
formado por una placa de estrella de 8 puntas y una cúpula (umbo) con anillos grabados. La silueta aporta la lectura
principal; el detalle fino (vetas, juntas entre tablas, cepillado, grabados, óxido, cardenillo) viene de las texturas.

## Materiales (nombres en el GLB)

| Material | Pieza | Metálico | Rugosidad |
|---|---|---|---|
| `Madera` | Cuerpo | 0 | alta (~0.55–0.8) |
| `Acero`  | Reborde, flejes, remaches | 1 | baja/media (~0.26–0.5) |
| `Bronce` | Placa estrella y cúpula | 1 | media-baja (~0.32–0.45) |

Los tres usan Principled BSDF en Blender y se exportan como `pbrMetallicRoughness` + `normalTexture` de glTF.

## Polígonos

≈ **3 650 triángulos** en total: Madera 1 536 · Acero 1 824 · Bronce 296 (3 mallas, 3 materiales, 3 draw calls).
Sin geometría oculta ni duplicada (se eliminan vértices duplicados y sueltos, normales recalculadas hacia fuera,
transformaciones aplicadas, escala real en metros ≈ 0.8 × 1.0 m).

## UVs y texturas

| Material | Resolución | Mapas (embebidos en el GLB, estado limpio) |
|---|---|---|
| Madera | 1024 × 1024 | Base Color, ORM (G = roughness, B = metallic), Normal |
| Acero  | 512 × 512   | Base Color, ORM, Normal |
| Bronce | 512 × 512   | Base Color, ORM, Normal |

- **Madera:** frente en la mitad izquierda de la textura y dorso (espejado) en la derecha, sin solapes; la pared del canto
  queda oculta bajo el reborde.
- **Acero:** `Smart UV Project` + empaquetado de islas en el espacio 0-1.
- **Bronce:** proyección planar frontal a modo de «calcomanía» (placa y cúpula comparten el mismo dibujo; solapamiento
  intencional y sin efecto visible porque la cúpula tapa esa zona de la placa).
- Variante **desgastada** (madera seca y rayada, acero oxidado, bronce con cardenillo): mismos tres mapas por material en
  `assets/textures/*_desgastado_*.png`, cargados bajo demanda por el botón 1.
- Las texturas se generan proceduralmente con `tools/make_textures.py` (numpy + Pillow). No se usó Substance Painter.

## Herramientas

Blender 5.2 (modelado con bmesh por script, UVs, materiales, export glTF), Python/numpy/Pillow (texturas PBR),
`<model-viewer>` 4.4.0, HTML/CSS/JS sin dependencias de build. Pruebas con Edge headless (`tools/shots.mjs`).

## Ejecutar localmente

```bash
python -m http.server 8123
# abrir http://localhost:8123
```
(Debe servirse por HTTP; abrir `index.html` con `file://` no carga el GLB por CORS.)

Regenerar el modelo (opcional): `python tools/make_textures.py` y
`blender -b -P tools/build_shield.py` (reescribe `assets/shield.glb`).

## Los tres botones

Todos actúan sobre los materiales del GLB mediante la API de scene-graph de model-viewer (`model.materials`).

1. **Acabado (limpio ↔ desgastado):** sustituye en `Madera`, `Acero` y `Bronce` la textura base, la de
   metálico/rugosidad y el normal map por las desgastadas (`setTexture`). Cambia color, rugosidad, metalicidad y relieve.
2. **Color del acero (Natural → Azulado → Negro forjado):** modifica el `baseColorFactor` del material `Acero`
   (`setBaseColorFactor`), que tiñe la textura sin reemplazarla.
3. **Relieve del bronce (activado ↔ desactivado):** quita o restaura el normal map del material `Bronce`
   (`normalTexture.setTexture`), eliminando o devolviendo los grabados y el martillado en la iluminación.

Además hay controles de cámara: órbita y zoom (ratón/táctil), **Auto-rotar** y **Reiniciar vista**.
Si el modelo o las texturas no cargan, se muestra un mensaje en el visor.

## Publicar (GitHub Pages)

```bash
gh auth login
gh repo create escudo-medieval-3d --public --source=. --push
gh api -X POST repos/<usuario>/escudo-medieval-3d/pages -f "source[branch]=main" -f "source[path]=/"
```
La URL será `https://<usuario>.github.io/escudo-medieval-3d/`.
