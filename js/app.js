// Escudo medieval: interacciones sobre los materiales del GLB mediante la API de scene-graph de model-viewer.
// Materiales del modelo: "Madera", "Acero", "Bronce".
(() => {
  'use strict';

  const mv = document.getElementById('shield');
  const $ = (id) => document.getElementById(id);
  const ui = {
    wear: $('btn-wear'), steel: $('btn-steel'), bump: $('btn-bump'),
    rotate: $('btn-rotate'), reset: $('btn-reset'), status: $('status'),
    lblWear: $('lbl-wear'), lblSteel: $('lbl-steel'), lblBump: $('lbl-bump'),
  };

  const TEX_DIR = 'assets/textures/';
  const MATS = ['Madera', 'Acero', 'Bronce'];
  // Colores alternativos del acero (se multiplican por la textura base: baseColorFactor)
  const STEEL_TINTS = [
    { name: 'Natural', rgba: [1, 1, 1, 1] },
    { name: 'Azulado', rgba: [0.55, 0.7, 1.0, 1] },
    { name: 'Negro forjado', rgba: [0.3, 0.3, 0.34, 1] },
  ];

  const state = { worn: false, steelIdx: 0, bump: true };
  const mats = {};      // nombre -> material de model-viewer
  const clean = {};     // texturas originales (embebidas en el GLB)
  const worn = {};      // texturas desgastadas (se cargan bajo demanda)
  let wornLoaded = false;

  function showStatus(msg, info = false) {
    ui.status.textContent = msg;
    ui.status.className = 'status' + (info ? ' info' : '');
    ui.status.hidden = !msg;
  }

  // Texturas actuales segun el estado (limpio / desgastado)
  const set = () => (state.worn ? worn : clean);

  function applyTextures() {
    for (const name of MATS) {
      const m = mats[name], t = set()[name];
      m.pbrMetallicRoughness.baseColorTexture.setTexture(t.base);
      m.pbrMetallicRoughness.metallicRoughnessTexture.setTexture(t.orm);
      // Boton 3: el normal map del bronce puede quedar desactivado
      const useNormal = !(name === 'Bronce' && !state.bump);
      m.normalTexture.setTexture(useNormal ? t.normal : null);
    }
  }

  async function loadWornTextures() {
    if (wornLoaded) return;
    for (const name of MATS) {
      const k = name.toLowerCase();
      const [base, orm, normal] = await Promise.all(
        ['color', 'orm', 'normal'].map((s) => mv.createTexture(`${TEX_DIR}${k}_desgastado_${s}.png`)));
      worn[name] = { base, orm, normal };
    }
    wornLoaded = true;
  }

  const press = (btn, on) => btn.setAttribute('aria-pressed', String(on));

  // 1) Limpio <-> desgastado: cambia color base, rugosidad/metalico y normal de los tres materiales
  async function toggleWear() {
    ui.wear.disabled = true;
    try {
      if (!state.worn) {
        showStatus('Cargando texturas desgastadas…', true);
        await loadWornTextures();
        showStatus('');
      }
      state.worn = !state.worn;
      applyTextures();
      press(ui.wear, state.worn);
      ui.lblWear.textContent = state.worn ? 'Desgastado' : 'Limpio';
    } catch (e) {
      console.error(e);
      showStatus('No se pudieron cargar las texturas desgastadas. Revisa tu conexión y reintenta.');
    } finally {
      ui.wear.disabled = false;
    }
  }

  // 2) Color del acero: cicla entre tintes sobre el material "Acero"
  function cycleSteel() {
    state.steelIdx = (state.steelIdx + 1) % STEEL_TINTS.length;
    const t = STEEL_TINTS[state.steelIdx];
    mats.Acero.pbrMetallicRoughness.setBaseColorFactor(t.rgba);
    ui.lblSteel.textContent = t.name;
    press(ui.steel, state.steelIdx !== 0);
  }

  // 3) Relieve del bronce: activa/desactiva el normal map del material "Bronce"
  function toggleBump() {
    state.bump = !state.bump;
    mats.Bronce.normalTexture.setTexture(state.bump ? set().Bronce.normal : null);
    press(ui.bump, state.bump);
    ui.lblBump.textContent = state.bump ? 'Activado' : 'Desactivado';
  }

  // Controles de cámara
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
    for (const name of MATS) {
      const m = mv.model.materials.find((x) => x.name === name);
      if (!m) { showStatus(`El modelo no contiene el material "${name}".`); return; }
      mats[name] = m;
      clean[name] = {
        base: m.pbrMetallicRoughness.baseColorTexture.texture,
        orm: m.pbrMetallicRoughness.metallicRoughnessTexture.texture,
        normal: m.normalTexture.texture,
      };
    }
    showStatus('');
    document.querySelector('.progress')?.setAttribute('hidden', '');
    [ui.wear, ui.steel, ui.bump].forEach((b) => (b.disabled = false));
    ui.wear.addEventListener('click', toggleWear);
    ui.steel.addEventListener('click', cycleSteel);
    ui.bump.addEventListener('click', toggleBump);
  }, { once: true });

  mv.addEventListener('error', (e) => {
    console.error(e);
    showStatus('No se pudo cargar el modelo 3D (assets/shield.glb). Comprueba la conexión o que el archivo exista.');
  });
})();
