// Escudo medieval: interacciones sobre los materiales del GLB mediante la API de scene-graph de model-viewer.
// Materiales del modelo: "Madera", "Acero", "Bronce".
(() => {
  'use strict';

  const mv = document.getElementById('shield');
  const $ = (id) => document.getElementById(id);
  const ui = {
    clean: $('btn-clean'), aged: $('btn-aged'), bump: $('btn-bump'), lblBump: $('lbl-bump'),
    rotate: $('btn-rotate'), reset: $('btn-reset'), status: $('status'),
  };
  const TEX_DIR = 'assets/textures/';
  const NAMES = ['Madera', 'Acero', 'Bronce'];
  const state = { finish: 'aged', bump: true };
  const mats = {};      // nombre -> material de model-viewer
  const aged = {};      // texturas originales (embebidas en el GLB = acabado envejecido)
  let clean = null;     // texturas del acabado limpio (se cargan bajo demanda)

  function showStatus(msg, info = false) {
    ui.status.textContent = msg;
    ui.status.className = 'status' + (info ? ' info' : '');
    ui.status.hidden = !msg;
  }
  const press = (btn, on) => btn.setAttribute('aria-pressed', String(on));

  // Aplica a los tres materiales las texturas del acabado actual; el normal map depende del botón 3
  function applyTextures() {
    const set = state.finish === 'clean' ? clean : aged;
    for (const n of NAMES) {
      const m = mats[n], t = set[n];
      m.pbrMetallicRoughness.baseColorTexture.setTexture(t.base);
      m.pbrMetallicRoughness.metallicRoughnessTexture.setTexture(t.orm);
      m.normalTexture.setTexture(state.bump ? t.normal : null);
    }
  }

  // 1 y 2) Acabado limpio / envejecido: cambian color base, rugosidad, metalicidad y relieve de los materiales
  async function setFinish(finish) {
    if (finish === state.finish) return;
    ui.clean.disabled = ui.aged.disabled = true;
    try {
      if (finish === 'clean' && !clean) {
        showStatus('Cargando acabado limpio…', true);
        const loaded = {};
        for (const n of NAMES) {
          const [base, orm, normal] = await Promise.all(
            ['color', 'orm', 'normal'].map((s) => mv.createTexture(`${TEX_DIR}${n.toLowerCase()}_limpio_${s}.jpg`)));
          loaded[n] = { base, orm, normal };
        }
        clean = loaded;
        showStatus('');
      }
      state.finish = finish;
      applyTextures();
      press(ui.clean, finish === 'clean');
      press(ui.aged, finish === 'aged');
    } catch (e) {
      console.error(e);
      showStatus('No se pudieron cargar las texturas del acabado limpio. Revisa tu conexión y reintenta.');
    } finally {
      ui.clean.disabled = ui.aged.disabled = false;
    }
  }

  // 3) Relieve normal: activa/desactiva el normal map de madera, acero y bronce
  function toggleBump() {
    state.bump = !state.bump;
    applyTextures();
    press(ui.bump, state.bump);
    ui.lblBump.textContent = state.bump ? 'activado' : 'desactivado';
  }

  // Cámara
  const initialOrbit = mv.getAttribute('camera-orbit');
  ui.rotate.addEventListener('click', () => {
    const on = !mv.hasAttribute('auto-rotate');
    on ? mv.setAttribute('auto-rotate', '') : mv.removeAttribute('auto-rotate');
    press(ui.rotate, on);
  });
  ui.reset.addEventListener('click', () => {
    mv.cameraOrbit = initialOrbit;
    mv.fieldOfView = 'auto';
    mv.cameraTarget = 'auto auto auto';
    mv.jumpCameraToGoal();
  });

  mv.addEventListener('load', () => {
    for (const n of NAMES) {
      const m = mv.model.materials.find((x) => x.name === n);
      if (!m) { showStatus(`El modelo no contiene el material "${n}".`); return; }
      mats[n] = m;
      aged[n] = {
        base: m.pbrMetallicRoughness.baseColorTexture.texture,
        orm: m.pbrMetallicRoughness.metallicRoughnessTexture.texture,
        normal: m.normalTexture.texture,
      };
    }
    showStatus('');
    document.querySelector('.progress')?.setAttribute('hidden', '');
    [ui.clean, ui.aged, ui.bump].forEach((b) => (b.disabled = false));
    ui.clean.addEventListener('click', () => setFinish('clean'));
    ui.aged.addEventListener('click', () => setFinish('aged'));
    ui.bump.addEventListener('click', toggleBump);
  }, { once: true });

  mv.addEventListener('error', (e) => {
    console.error(e);
    showStatus('No se pudo cargar el modelo 3D (assets/shield.glb). Comprueba la conexión o que el archivo exista.');
  });
})();
