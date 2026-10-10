# Escudo Medieval 3D

Escudo heráldico vertical de punta inferior, hecho de tablones de madera oscura con un ancho marco de hierro remachado,
dos rombos decorativos de bronce (arriba y abajo), un gran boss central y cuatro ornamentos góticos puntiagudos
(arriba, abajo, izquierda y derecha). Modelado y texturizado desde cero y mostrado con
[`<model-viewer>`](https://modelviewer.dev/) 4.4.0. La referencia visual se usó solo como inspiración.

![Vista general](screenshots/escritorio-vista-general.png)
![Interacción activa](screenshots/escritorio-interaccion.png)

- **Sitio publicado:** https://dgael-22.github.io/escudo/
- **Repositorio:** https://github.com/dgael-22/escudo
- **Modelo:** [`assets/shield.glb`](assets/shield.glb) (≈ 0,65 MB)

## Modelo

Solo se modela lo importante: silueta heráldica, marco ancho con perfil, boss de revolución, ornamentos góticos en placa fina,
rombos biselados y remaches. Vetas, juntas entre tablones, grietas, óxido, rayones, pátina y el relieve ornamental
(líneas grabadas, flor de lis de los rombos) vienen de las texturas PBR.

| Pieza | Material | Triángulos |
|---|---|---|
| Cuerpo de tablones (frente y dorso) | `Madera` | 736 |
| Marco, ~35 remaches, boss, 4 ornamentos góticos | `Acero` | 2 588 |
| 2 rombos, collar del boss, 4 tachuelas | `Bronce` | 404 |
| **Total** | 3 mallas, 3 materiales | **≈ 3 730** |

## Materiales y texturas (PBR metal/rough; embebidas en el GLB como JPEG q85)

| Material | Uso | Resolución | Mapas |
|---|---|---|---|
| `Madera` oscura envejecida | tablones verticales | 1024² | Base Color, ORM (G = roughness, B = metallic), Normal |
| `Acero` / hierro oscuro | marco, remaches, boss, ornamentos | 1024² | Base Color, ORM, Normal |
| `Bronce` | rombos, collar, tachuelas | 512² | Base Color, ORM, Normal |

El GLB incluye el acabado **envejecido**. El acabado **limpio** son 9 JPEG en `assets/textures/` (`<material>_limpio_<mapa>.jpg`),
que se cargan al pulsar el botón 1 (≈ 0,5 MB).

**UVs:** madera con proyección planar (frente en la mitad izquierda de la textura, dorso en la derecha); marco con una franja
del atlas de acero repetible 2 veces alrededor del perímetro; boss, ornamentos y remaches como decal planar frontal en el resto
del atlas de acero (engrabados alineados con la geometría); rombos, collar y tachuelas en cuadrantes separados del atlas de bronce.
Sin solapes entre piezas.

## Controles

Los tres botones cambian de verdad los materiales del GLB mediante la API de scene-graph de model-viewer:

1. **Acabado limpio** – sustituye base color, roughness/metallic y normal de `Madera`, `Acero` y `Bronce` por la variante limpia
   (madera cuidada, acero pulido, bronce brillante).
2. **Acabado envejecido** – restaura la variante con óxido, grietas, suciedad y pátina (estado inicial).
3. **Relieve normal activado/desactivado** – quita o restaura el normal map de los tres materiales.

Además: órbita, zoom, **Auto-rotar** y **Reiniciar vista**. Si el modelo o las texturas fallan, se muestra un mensaje.

## Herramientas

Blender 5.2 (modelado por script con bmesh, UVs, nodos Principled BSDF, export glTF), Python + numpy + Pillow (texturas procedurales
periódicas), model-viewer 4.4.0, HTML/CSS/JS sin build, Edge headless para pruebas y capturas.

## Ejecutar en local

```bash
python -m http.server 8123   # abrir http://localhost:8123 (debe servirse por HTTP)
```

Regenerar: `python fuente-3d/make_textures.py` y `blender -b -P fuente-3d/build_shield.py` (reescribe `assets/shield.glb`).

## Qué sustituyó a la versión anterior (escudo circular)

- **Reemplazados:** `assets/shield.glb`, `index.html`, `js/app.js` (nuevos materiales y botones) y este `README.md`;
  `fuente-3d/make_textures.py` y `fuente-3d/build_shield.py` reescritos.
- **Eliminados:** texturas del escudo circular (`bronce_limpio_*.jpg` antiguas, mapas de cuero/escamas) y capturas previas.
- **Nuevos:** `assets/textures/{madera,acero,bronce}_limpio_*.jpg`, `fuente-3d/escudo.blend` y capturas nuevas.
