// Escudo solar: interacciones sobre los materiales del GLB mediante la API de scene-graph de model-viewer.
// Materiales del modelo: "Bronce", "Acero", "Madera", "Cuero".
(() => {
  'use strict';

  const mv = document.getElementById('shield');
  const $ = (id) => document.getElementById(id);
  const ui = {
    clean: $('btn-clean'), aged: $('btn-aged'), bump: $('btn-bump'), lblBump: $('lbl-bump'),
    rotate: $('btn-rotate'), reset: $('btn-reset'), status: $('status'),
  };
  const TEX_DIR = 'assets/textures/';
  const state = { finish: 'aged', bump: true };
  let bronze, leather;          // materiales de model-viewer
  const aged = {};              // texturas originales del bronce (embebidas en el GLB)
  let clean = null;             // texturas del bronce limpio (carga bajo demanda)
  let leatherNormal = null;

  function showStatus(msg, info = false) {
    ui.status.textContent = msg;
    ui.status.className = 'status' + (info ? ' info' : '');
    ui.status.hidden = !msg;
  }
  const press = (btn, on) => btn.setAttribute('aria-pressed', String(on));

  // Aplica al bronce las texturas del acabado actual; el normal map depende del botón de relieve
  function applyBronze() {
    const t = state.finish === 'clean' ? clean : aged;
    const pbr = bronze.pbrMetallicRoughness;
    pbr.baseColorTexture.setTexture(t.base);
    pbr.metallicRoughnessTexture.setTexture(t.orm);
    bronze.normalTexture.setTexture(state.bump ? t.normal : null);
  }

  // 1 y 2) Bronce limpio / envejecido: cambian color base, rugosidad y metalicidad (pátina) del material "Bronce"
  async function setFinish(finish) {
    if (finish === state.finish) return;
    ui.clean.disabled = ui.aged.disabled = true;
    try {
      if (finish === 'clean' && !clean) {
        showStatus('Cargando bronce limpio…', true);
        const [base, orm, normal] = await Promise.all(
          ['color', 'orm', 'normal'].map((s) => mv.createTexture(`${TEX_DIR}bronce_limpio_${s}.jpg`)));
        clean = { base, orm, normal };
        showStatus('');
      }
      state.finish = finish;
      applyBronze();
      press(ui.clean, finish === 'clean');
      press(ui.aged, finish === 'aged');
    } catch (e) {
      console.error(e);
      showStatus('No se pudo cargar la textura del bronce limpio. Revisa tu conexión y reintenta.');
    } finally {
      ui.clean.disabled = ui.aged.disabled = false;
    }
  }

  // 3) Relieve: activa/desactiva el normal map del bronce y de los paneles de cuero
  function toggleBump() {
    state.bump = !state.bump;
    applyBronze();
    leather.normalTexture.setTexture(state.bump ? leatherNormal : null);
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
    const find = (n) => mv.model.materials.find((m) => m.name === n);
    bronze = find('Bronce');
    leather = find('Cuero');
    if (!bronze || !leather) { showStatus('El modelo no contiene los materiales esperados (Bronce, Cuero).'); return; }
    aged.base = bronze.pbrMetallicRoughness.baseColorTexture.texture;
    aged.orm = bronze.pbrMetallicRoughness.metallicRoughnessTexture.texture;
    aged.normal = bronze.normalTexture.texture;
    leatherNormal = leather.normalTexture.texture;
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
