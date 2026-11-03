"""Approximate display surfaces from tissue labels; no FEM mesh or label editing."""

import html
from pathlib import Path

import nibabel as nib
import numpy as np

COLORS = {1: "#fca685", 2: "#ead675", 3: "#408cff", 4: "#ad60cf", 5: "#e4e7ed"}
OPACITY = {1: .12, 2: .3, 3: .25, 4: 1., 5: 1.}


def extract_surfaces(labels, affine, step_size=2, max_faces=360_000):
    from skimage.measure import marching_cubes

    labels, affine = np.asarray(labels), np.asarray(affine)
    if labels.ndim != 3 or not 0 < labels.size <= 100_000_000 or not np.isfinite(labels).all():
        raise ValueError("Expected bounded finite 3D labels.")
    if not np.all((labels >= 0) & (labels <= 5) & (labels == np.round(labels))):
        raise ValueError("Expected integer labels 0–5.")
    if affine.shape != (4, 4) or not np.isfinite(affine).all() or abs(np.linalg.det(affine[:3, :3])) < 1e-10:
        raise ValueError("Invalid source affine.")
    if not 1 <= step_size <= 4 or max_faces < 1 or not np.any(labels):
        raise ValueError("Invalid surface extraction settings or empty labels.")
    ids = [int(value) for value in np.unique(labels) if value]
    # shortcut: coarser marching-cubes sampling is for display only; use validated full-resolution meshing for simulation.
    for step in range(step_size, 5):
        surfaces = []
        for label in ids:
            mask = labels == label
            positions = np.where(mask)
            lower = np.array([int(p.min()) for p in positions])
            upper = np.array([int(p.max()) + 1 for p in positions])
            cropped = mask[tuple(slice(a, b) for a, b in zip(lower, upper))]
            used = step
            padded = np.pad(cropped, used)
            try:
                vertices, faces, _, _ = marching_cubes(padded, .5, step_size=used, allow_degenerate=False)
            except (ValueError, RuntimeError):
                used = 1
                vertices, faces, _, _ = marching_cubes(np.pad(cropped, 1), .5, step_size=1, allow_degenerate=False)
            vertices = nib.affines.apply_affine(affine, vertices + lower - used).astype(np.float32)
            surfaces.append({"label": label, "vertices": vertices, "faces": faces.astype(np.int32), "step_size": used})
        if sum(len(mesh["faces"]) for mesh in surfaces) <= max_faces:
            return surfaces
    raise ValueError("Surface geometry is too complex for the bounded browser preview.")


def make_view(labels, affine, names):
    import plotly.graph_objects as go

    surfaces = extract_surfaces(labels, affine)
    figure = go.Figure()
    controls = []
    for index, mesh in enumerate(surfaces):
        label, points, faces = mesh["label"], mesh["vertices"], mesh["faces"]
        visible = label in (1, 4)
        alpha = OPACITY[label]
        name = html.escape(names[label])
        figure.add_trace(go.Mesh3d(x=points[:, 0], y=points[:, 1], z=points[:, 2],
                                  i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
                                  color=COLORS[label], opacity=alpha, visible=visible, name=names[label],
                                  showlegend=False, hoverinfo="name", flatshading=False,
                                  lighting={"ambient": .6, "diffuse": .75, "specular": .08, "roughness": .75},
                                  lightposition={"x": 100, "y": 200, "z": 400}))
        controls.append(f'''<div class="surface-row"><label>
<input type="checkbox" data-surface-index="{index}" data-surface-label="{label}" {'checked' if visible else ''} disabled>
<span style="color:{COLORS[label]}">●</span> {name}</label>
<label class="opacity-label">Saydamlık / görünürlük
<input aria-label="{name} görünürlük oranı" type="range" min="0" max="100" value="{round(alpha * 100)}" data-opacity-index="{index}" disabled></label></div>''')
    figure.update_layout(height=620, margin={"l": 0, "r": 0, "t": 5, "b": 0}, paper_bgcolor="#f4f6f9",
                         scene={"aspectmode": "data", "dragmode": "orbit", "bgcolor": "#f4f6f9",
                                "xaxis": {"title": "R ↔ L", "visible": False},
                                "yaxis": {"title": "A ↔ P", "visible": False},
                                "zaxis": {"title": "S ↔ I", "visible": False},
                                "camera": {"up": {"x": 0, "y": 0, "z": 1}, "eye": {"x": 1.6, "y": -1.8, "z": 1.1}}})
    script = Path(__file__).with_name("surface_controls.js").read_text()
    plot = figure.to_html(full_html=False, include_plotlyjs=True, include_mathjax=False, div_id="e1-surface-plot",
                          config={"responsive": True, "displaylogo": False, "scrollZoom": True}, post_script=script)
    steps = sorted({mesh["step_size"] for mesh in surfaces})
    buttons = "".join(f'<button type="button" data-surface-preset="{key}" disabled>{title}</button>'
                      for key, title in (("brain", "Beyin"), ("head", "Kafa"), ("all", "Tümü"), ("reset", "Sıfırla")))
    fragment = f'''<section aria-label="Üç boyutlu segmentasyon yüzeyleri"><h2>3B doku yüzeyleri</h2>
<p>Sürükle: döndür · tekerlek: yakınlaştır · dokuları kutucuklardan seç. Sıfır görünürlük tamamen saydamdır.</p>
<style>.surface-layout{{display:grid;grid-template-columns:210px minmax(0,1fr);gap:12px;background:#f4f6f9;border-radius:12px;padding:12px}}.surface-row{{padding:12px 0;border-bottom:1px solid #dce1e8}}.surface-row label{{display:block}}.opacity-label{{font-size:12px;color:#53606c}}.surface-row input[type=range]{{width:100%}}.surface-buttons{{display:flex;flex-wrap:wrap;gap:6px}}.surface-buttons button{{padding:7px 10px;background:white;border:1px solid #cbd3dd;border-radius:6px;cursor:pointer}}@media(max-width:700px){{.surface-layout{{grid-template-columns:1fr}}}}</style>
<div class="surface-layout"><aside><div class="surface-buttons">{buttons}</div>{''.join(controls)}
<small id="e1-surface-status" role="status">3B görünüm hazırlanıyor. Görünmezse indirilen HTML raporunu Chrome'da aç.</small></aside>{plot}</div>
<p><small>Gösterim için yaklaşık yüzeyler · örnekleme adımı: {', '.join(map(str, steps))} voksel.
Koordinatlar kaynak NIfTI affine'inden alınır; fiziksel ölçek ayrıca doğrulanmalıdır.
Bu görünüm SimNIBS/FEM hacim mesh'i değildir. Skorlar sadeleştirilmiş yüzeylerden değil, özgün etiket hacminden hesaplanır.</small></p></section>'''
    metadata = {"visualization_only": True, "fem_mesh": False, "labels": [mesh["label"] for mesh in surfaces],
                "triangles": sum(len(mesh["faces"]) for mesh in surfaces),
                "vertices": sum(len(mesh["vertices"]) for mesh in surfaces), "step_sizes": steps,
                "source_affine_preserved": True, "physical_scale_validated": False}
    return fragment, metadata
