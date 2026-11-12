"""VTK inside Qt. Mesh vertices and MRI planes share RAS millimeter coordinates."""

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap, QSurfaceFormat
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget,
)

REGION_ATLASES = (("Off", ""), ("DK40 · 34 regions per side", "DK40"), ("a2009s · 74 regions per side", "a2009s"),
                  ("HCP-MMP1 · 180 regions per side", "HCP_MMP1"))
PICK_RADIUS_MM = 5.0

from viewer import label_color
from visual_theme import compact_action, compact_choice


def configure_surface_format():
    """Choose the FBO adapter's GL format before creating the top-level window."""
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setVersion(3, 2)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    for setter in (fmt.setRedBufferSize, fmt.setGreenBufferSize, fmt.setBlueBufferSize,
                   fmt.setDepthBufferSize, fmt.setAlphaBufferSize):
        setter(8)
    fmt.setStencilBufferSize(0)
    fmt.setSamples(0)
    QSurfaceFormat.setDefaultFormat(fmt)


def plane_geometry(volume, axis, index):
    """Three corners at voxel edges, since a texture fills whole voxels; world space applied once."""
    other = [value for value in range(3) if value != axis]
    points = np.full((3, 3), -.5)
    points[:, axis] = index
    points[1, other[0]] = volume.data.shape[other[0]] - .5
    points[2, other[1]] = volume.data.shape[other[1]] - .5
    return points @ volume.image.affine[:3, :3].T + volume.image.affine[:3, 3]


def plane_actor(volume, axis, index, level, width):
    """One MRI slice as a textured quad in world coordinates."""
    from vtkmodules.util.numpy_support import numpy_to_vtk
    from vtkmodules.vtkCommonDataModel import vtkImageData
    from vtkmodules.vtkFiltersSources import vtkPlaneSource
    from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkTexture
    plane = np.take(volume.data, index, axis=axis)
    gray = (np.clip((plane - (level - width / 2)) / max(width, .001), 0, 1) * 255).astype(np.uint8)
    image = vtkImageData()
    image.SetDimensions(*gray.shape, 1)
    image.GetPointData().SetScalars(numpy_to_vtk(gray.ravel(order="F"), deep=True))
    texture = vtkTexture()
    texture.SetInputData(image)
    texture.InterpolateOn()
    corners = plane_geometry(volume, axis, index)
    source = vtkPlaneSource()
    source.SetOrigin(*corners[0])
    source.SetPoint1(*corners[1])
    source.SetPoint2(*corners[2])
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.SetTexture(texture)
    actor.GetProperty().LightingOff()
    return actor


def regions_module():
    """tools/brain_regions, imported on demand so the viewer starts without it."""
    import sys
    from pathlib import Path
    tools = str(Path(__file__).resolve().parents[1])
    if tools not in sys.path:
        sys.path.insert(0, tools)
    from brain_regions import regions
    return regions


def region_triangles(hemi, hidden):
    """Triangles to draw: those whose first vertex lies in a region that is not hidden."""
    hidden_labels = [label for name, label in hidden if name == hemi.name]
    return ~np.isin(hemi.labels[hemi.triangles[:, 0]], hidden_labels)


def colored_actor(points, triangles, colors):
    """A surface actor that takes its color from per-vertex RGB values."""
    from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
    from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
    from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
    vtk_points = vtkPoints()
    vtk_points.SetData(numpy_to_vtk(np.ascontiguousarray(points, float), deep=True))
    cells = vtkCellArray()
    cells.SetData(numpy_to_vtkIdTypeArray(np.arange(0, triangles.size + 1, 3, dtype=np.int64), deep=True),
                  numpy_to_vtkIdTypeArray(triangles.astype(np.int64).ravel(), deep=True))
    poly = vtkPolyData()
    poly.SetPoints(vtk_points)
    poly.SetPolys(cells)
    scalars = numpy_to_vtk(np.ascontiguousarray(colors, np.uint8), deep=True)
    scalars.SetName("region_rgb")
    poly.GetPointData().SetScalars(scalars)
    normals = vtkPolyDataNormals()
    normals.SetInputData(poly)
    normals.SplittingOff()
    normals.ConsistencyOn()
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    mapper.ScalarVisibilityOn()
    mapper.SetScalarModeToUsePointData()
    mapper.SetColorModeToDirectScalars()
    actor = vtkActor()
    actor.SetMapper(mapper)
    return actor


def color_icon(rgb):
    pixmap = QPixmap(14, 14)
    pixmap.fill(QColor(*rgb))
    return QIcon(pixmap)


class MeshView(QWidget):
    detail_requested = Signal(object, float)
    regions_requested = Signal(str)
    region_picked = Signal(str)

    def __init__(self):
        super().__init__()
        self.model = None
        self.canvas = None
        self.renderer = None
        self.actors = {}
        self.planes = []
        self.indices = [0, 0, 0]
        self.level, self.width = 0., 1.
        self.detail_available = True
        self.regions = None
        self.region_actors = []
        self.region_trees = {}
        self.hidden_regions = set()
        self.regions_supported = False
        self.restore_brain = None
        self.press_position = None
        self.picker = None
        self.pick_props = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        sidebar = QWidget()
        controls = QVBoxLayout(sidebar)
        self.controls = controls
        controls.setContentsMargins(0, 0, 12, 0)
        controls.setSpacing(10)
        self.controls_scroll = QScrollArea()
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.controls_scroll.setFixedWidth(310)
        self.controls_scroll.setWidget(sidebar)
        self.summary = QLabel("No result is open. Open a saved result or create a segmentation, then return to 3D view.")
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.summary.setWordWrap(True)
        controls.addWidget(self.summary)
        presets = QHBoxLayout()
        self.preset_buttons = {}
        for text, brain in (("Brain", True), ("Head", False)):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, brain=brain: self.preset(brain))
            presets.addWidget(button)
            button.setEnabled(False)
            self.preset_buttons[brain] = button
        controls.addLayout(presets)
        self.reset_button = QPushButton("Reset camera")
        compact_action(self.reset_button)
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_camera)
        controls.addWidget(self.reset_button)
        appearance = QGroupBox("Surface appearance")
        self.appearance = appearance
        appearance_layout = QVBoxLayout(appearance)
        appearance_layout.setContentsMargins(12, 16, 12, 12)
        appearance_layout.setSpacing(9)
        appearance_layout.addWidget(QLabel("Surface detail · voxel step"))
        self.detail = QComboBox()
        self.detail.setAccessibleName("Surface voxel step")
        for title, value in (("Auto · fast preview", None), ("4 voxels · coarse", 4),
                             ("2 voxels · medium", 2), ("1 voxel · full detail", 1)):
            self.detail.addItem(title, value)
        compact_choice(self.detail)
        self.detail.setToolTip("Step in source voxels, not millimetres. Smaller steps retain more detail and require more memory. Applies to E1/E2 display surfaces.")
        appearance_layout.addWidget(self.detail)
        appearance_layout.addWidget(QLabel("Surface smoothing"))
        self.smoothing = QDoubleSpinBox()
        self.smoothing.setRange(0.0, 1.0)
        self.smoothing.setSingleStep(0.1)
        self.smoothing.setDecimals(2)
        self.smoothing.setAccessibleName("Surface smoothing factor")
        self.smoothing.setSpecialValueText("0 · raw surface")
        self.smoothing.setToolTip("0 keeps the raw surface; 0.50 matches Slicer's default smoothing strength. Stronger smoothing can remove small features. Display only.")
        appearance_layout.addWidget(self.smoothing)
        self.surface_hint = QLabel()
        self.surface_hint.setObjectName("subtitle")
        self.surface_hint.setWordWrap(True)
        appearance_layout.addWidget(self.surface_hint)
        self.detail_button = QPushButton("Apply surface settings")
        self.detail_button.setObjectName("primary")
        compact_action(self.detail_button)
        self.detail_button.clicked.connect(lambda: self.detail_requested.emit(self.detail.currentData(), self.smoothing.value()))
        appearance_layout.addWidget(self.detail_button)
        controls.addWidget(appearance)
        self.build_region_controls(controls)
        self.set_detail_available(True)
        self.show_planes = QCheckBox("Show MRI slice planes")
        self.show_planes.toggled.connect(self.update_planes)
        controls.addWidget(self.show_planes)
        self.tissue_label = QLabel("Tissue visibility / opacity")
        controls.addWidget(self.tissue_label)
        self.tissue_controls = QWidget()
        self.tissue_layout = QVBoxLayout(self.tissue_controls)
        self.tissue_layout.setContentsMargins(0, 0, 8, 0)
        self.tissue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        controls.addWidget(self.tissue_controls)
        controls.addStretch(1)
        self.coordinate_note = QLabel("RAS world coordinates · mm\nDrag: rotate · Shift-drag: pan\nScroll: zoom")
        self.coordinate_note.setWordWrap(True)
        controls.addWidget(self.coordinate_note)
        layout.addWidget(self.controls_scroll)
        self.viewport = QVBoxLayout()
        self.empty = QLabel("Your 3D preview will appear here.\nOpen a saved result, or create one in AI segmentation.")
        self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet("background: #101c21; color: #c6d9d8; border-radius: 5px;")
        self.viewport.addWidget(self.empty)
        layout.addLayout(self.viewport, 1)
        self.checks = {}
        self.sliders = {}
        self.presets = {}

    def group_inspector(self):
        """Keep the existing controls in three pages within the same viewer."""
        tabs = QTabWidget()
        tabs.tabBar().setObjectName("inspectorTabs")
        for title, widgets in (("Tissues", (self.tissue_label, self.tissue_controls)),
                               ("Surface", (self.appearance,)),
                               ("Brain regions", (self.regions_box,))):
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(6, 8, 6, 4)
            for widget in widgets:
                self.controls.removeWidget(widget)
                layout.addWidget(widget)
            layout.addStretch(1)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            tabs.addTab(scroll, title)
        self.controls.insertWidget(self.controls.indexOf(self.show_planes) + 1, tabs, 1)
        self.controls.takeAt(self.controls.indexOf(self.coordinate_note) - 1)
        self.inspector = tabs
        self.show_planes.setToolTip("Planes follow the slice positions in MRI images.")

    def view_state(self):
        camera = self.renderer.GetActiveCamera() if self.renderer is not None else None
        return {
            "camera": None if camera is None else {
                "position": list(camera.GetPosition()), "focal": list(camera.GetFocalPoint()),
                "up": list(camera.GetViewUp()), "parallel": bool(camera.GetParallelProjection()),
                "scale": camera.GetParallelScale(), "angle": camera.GetViewAngle(),
            },
            "tissues": {str(tag): [check.isChecked(), self.sliders[tag].value()]
                        for tag, check in self.checks.items()},
            "planes": self.show_planes.isChecked(),
            "surface_step": self.model.surface_step,
            "surface_smoothing": self.model.surface_smoothing,
            "atlas": self.regions.atlas if self.regions is not None else "",
            "hidden_regions": [list(key) for key in sorted(self.hidden_regions)],
            "highlight": self.region_targets.isChecked(),
            "restore_brain": self.restore_brain,
        }

    def restore_view(self, state, regions):
        if self.regions is not regions:
            self.set_regions(regions)
        self.region_atlas.blockSignals(True)
        self.region_atlas.setCurrentIndex(max(0, self.region_atlas.findData(state["atlas"])))
        self.region_atlas.blockSignals(False)
        self.region_targets.blockSignals(True)
        self.region_targets.setChecked(state["highlight"])
        self.region_targets.blockSignals(False)
        self.hidden_regions = {tuple(key) for key in state["hidden_regions"]}
        self.restore_brain = state["restore_brain"]
        self.region_list.blockSignals(True)
        for row in range(self.region_list.count()):
            item = self.region_list.item(row)
            key = tuple(item.data(Qt.ItemDataRole.UserRole))
            item.setCheckState(Qt.CheckState.Unchecked if key in self.hidden_regions else Qt.CheckState.Checked)
        self.region_list.blockSignals(False)
        for tag, (visible, opacity) in state["tissues"].items():
            tag = int(tag)
            if tag in self.checks:
                self.checks[tag].setChecked(visible)
                self.sliders[tag].setValue(opacity)
        self.show_planes.setChecked(state["planes"])
        if state["camera"] is not None and self.renderer is not None:
            view = state["camera"]
            camera = self.renderer.GetActiveCamera()
            camera.SetPosition(*view["position"])
            camera.SetFocalPoint(*view["focal"])
            camera.SetViewUp(*view["up"])
            camera.SetParallelProjection(view["parallel"])
            camera.SetParallelScale(view["scale"])
            camera.SetViewAngle(view["angle"])
            self.renderer.ResetCameraClippingRange()
        self.refresh_regions()

    def clear(self):
        self.reset_regions()
        self.model = None
        self.reset_button.setEnabled(False)
        self.actors.clear()
        self.planes.clear()
        if hasattr(self, "marker"):
            self.marker.SetEnabled(False)
        if self.renderer is not None:
            self.renderer.RemoveAllViewProps()
            self.render()
        while self.tissue_layout.count():
            item = self.tissue_layout.takeAt(0)
            item.widget().deleteLater()
        self.checks.clear()
        self.sliders.clear()
        self.presets.clear()
        for button in self.preset_buttons.values():
            button.setEnabled(False)
        self.summary.setText("No result is open. Open a saved result or create a segmentation, then return to 3D view.")
        self.set_detail_available(self.detail_available)

    def set_detail_available(self, available):
        self.detail_available = available
        enabled = available and self.model is not None and self.model.kind == "e1"
        self.detail.setEnabled(enabled)
        self.smoothing.setEnabled(enabled)
        self.detail_button.setEnabled(enabled)
        if self.model is None:
            hint = "Open or create an AI segmentation to adjust its surfaces."
        elif self.model.kind != "e1":
            hint = "Imported meshes keep their original shape. These settings apply to AI segmentations."
        else:
            hint = "Smaller voxel steps show more detail and use more memory. 0 keeps the raw surface. Display only; saved labels stay unchanged."
        self.surface_hint.setText(hint)

    def set_model(self, model):
        self.clear()
        self.model = model
        self.detail.setCurrentIndex(self.detail.findData(model.surface_step))
        self.smoothing.setValue(model.surface_smoothing)
        self.set_detail_available(self.detail_available)
        self.update_region_support(model)
        count = sum(len(surface.triangles) for surface in model.surfaces)
        title = model.labels[0].name if model.kind == "e1" else model.directory.name
        self.summary.setText("\n".join((title, f"{len(model.surfaces)} surfaces · {count:,} triangles",
                                         model.geometry_note, *model.notes)))
        self.summary.setToolTip(str(model.mesh_path or model.labels[0]))
        units = "assumed mm · physical scale unverified" if model.units_assumed else "mm"
        self.coordinate_note.setText(f"RAS coordinates · {units}\nDrag: rotate · Shift-drag: pan\nScroll: zoom")
        self.presets = {surface.role: surface.tag for surface in model.surfaces if surface.role}
        for surface in model.surfaces:
            name = surface.name or f"Surface {surface.tag}"
            check = QCheckBox(f"{name} · {surface.tag}")
            check.setToolTip(f"{len(surface.triangles):,} triangles")
            check.setChecked(surface.role is not None)
            check.toggled.connect(lambda checked, tag=surface.tag: self.set_visibility(tag, checked))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(20 if surface.role == "head" else 100)
            slider.setAccessibleName(f"{name} opacity")
            slider.valueChanged.connect(lambda value, tag=surface.tag: self.set_opacity(tag, value))
            self.checks[surface.tag], self.sliders[surface.tag] = check, slider
            self.tissue_layout.addWidget(check)
            self.tissue_layout.addWidget(slider)
        if not any(check.isChecked() for check in self.checks.values()):
            next(iter(self.checks.values())).setChecked(True)
        self.preset_buttons[True].setEnabled("brain" in self.presets)
        self.preset_buttons[False].setEnabled("head" in self.presets)
        if self.renderer is not None:
            self.build_scene()

    def replace_model(self, model):
        """Keep the user's tissue controls and camera when changing surface detail."""
        states = {tag: (check.isChecked(), self.sliders[tag].value()) for tag, check in self.checks.items()}
        camera = None
        if self.renderer is not None:
            current = self.renderer.GetActiveCamera()
            camera = current.NewInstance()
            camera.DeepCopy(current)
        self.set_model(model)
        for tag, (visible, opacity) in states.items():
            if tag in self.checks:
                self.checks[tag].setChecked(visible)
                self.sliders[tag].setValue(opacity)
        if camera is not None:
            self.renderer.GetActiveCamera().DeepCopy(camera)
            self.renderer.ResetCameraClippingRange()
            self.render()

    def ensure_renderer(self):
        if self.model is None:
            return
        if self.canvas is None:
            # The FBO adapter avoids Qt 6.10+ native-window repaint loops on macOS.
            from pyvistaqt.rwi import QVTKRenderWindowInteractor
            from vtkmodules.vtkRenderingCore import vtkRenderer
            import vtkmodules.vtkRenderingOpenGL2  # register OpenGL renderer
            self.canvas = QVTKRenderWindowInteractor(self)
            self.canvas.setAccessibleName("Interactive 3D head model")
            self.viewport.removeWidget(self.empty)
            self.empty.hide()
            self.viewport.addWidget(self.canvas)
            window = self.canvas.GetRenderWindow()
            window.SetAlphaBitPlanes(1)
            window.SetMultiSamples(0)
            self.renderer = vtkRenderer()
            self.renderer.SetBackground(.063, .110, .129)
            self.renderer.SetUseDepthPeeling(True)
            self.renderer.SetMaximumNumberOfPeels(8)
            self.renderer.SetOcclusionRatio(.1)
            window.AddRenderer(self.renderer)
            from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
            self.canvas.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
            self.canvas.Initialize()
            self.install_picker()
            self.build_scene()

    def build_scene(self):
        from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
        from vtkmodules.vtkCommonCore import vtkPoints
        from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
        from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
        from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
        self.renderer.RemoveAllViewProps()
        self.actors.clear()
        self.planes.clear()
        for surface in self.model.surfaces:
            points = vtkPoints()
            points.SetData(numpy_to_vtk(surface.points, deep=True))
            cells = vtkCellArray()
            offsets = np.arange(0, surface.triangles.size + 1, 3, dtype=np.int64)
            cells.SetData(numpy_to_vtkIdTypeArray(offsets, deep=True),
                          numpy_to_vtkIdTypeArray(surface.triangles.astype(np.int64).ravel(), deep=True))
            poly = vtkPolyData()
            poly.SetPoints(points)
            poly.SetPolys(cells)
            normals = vtkPolyDataNormals()
            normals.SetInputData(poly)
            normals.SplittingOff()
            normals.ConsistencyOn()
            mapper = vtkPolyDataMapper()
            mapper.SetInputConnection(normals.GetOutputPort())
            mapper.ScalarVisibilityOff()
            actor = vtkActor()
            actor.SetMapper(mapper)
            color = surface.color or label_color(surface.tag)
            actor.GetProperty().SetColor(*(channel / 255 for channel in color))
            actor.GetProperty().SetOpacity(self.sliders[surface.tag].value() / 100)
            actor.SetVisibility(self.checks[surface.tag].isChecked())
            self.renderer.AddActor(actor)
            self.actors[surface.tag] = actor
        self.region_actors = []  # RemoveAllViewProps dropped them; draw them again
        self.pick_props = []
        self.build_region_actors()
        self.add_orientation_marker()
        self.update_planes()
        self.reset_button.setEnabled(True)
        self.reset_camera()

    def add_orientation_marker(self):
        from vtkmodules.vtkRenderingAnnotation import vtkAnnotatedCubeActor
        from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
        if hasattr(self, "marker"):
            self.marker.SetEnabled(False)
        cube = vtkAnnotatedCubeActor()
        for axis, positive, negative in (("X", "R", "L"), ("Y", "A", "P"), ("Z", "S", "I")):
            getattr(cube, f"Set{axis}PlusFaceText")(positive)
            getattr(cube, f"Set{axis}MinusFaceText")(negative)
        cube.GetCubeProperty().SetColor(.65, .79, .74)
        self.marker = vtkOrientationMarkerWidget()
        self.marker.SetOrientationMarker(cube)
        self.marker.SetInteractor(self.canvas.GetRenderWindow().GetInteractor())
        self.marker.SetViewport(0, 0, .16, .16)
        self.marker.SetEnabled(True)
        self.marker.InteractiveOff()

    def set_visibility(self, tag, checked):
        if tag in self.actors:
            self.actors[tag].SetVisibility(checked)
            self.render()

    def set_opacity(self, tag, value):
        if tag in self.actors:
            self.actors[tag].GetProperty().SetOpacity(value / 100)
            self.render()

    def preset(self, brain):
        selected = self.presets.get("brain" if brain else "head")
        if selected is None:
            return
        for tag, check in self.checks.items():
            check.setChecked(tag == selected)
        if not brain:
            self.sliders[selected].setValue(100)
        elif self.regions is not None:
            # The colored pial layer replaces the gray matter surface it would otherwise overlap.
            self.checks[selected].setChecked(False)
            self.restore_brain = selected
        self.reset_camera()

    def reset_camera(self):
        if self.renderer is None or not self.actors:
            return
        from vtkmodules.vtkCommonDataModel import vtkBoundingBox
        box = vtkBoundingBox()
        box.SetBounds(self.renderer.ComputeVisiblePropBounds())
        if not box.IsValid():
            for actor in self.actors.values():
                box.AddBounds(actor.GetBounds())
        bounds = [0.0] * 6
        box.GetBounds(bounds)
        center = np.asarray(bounds).reshape(3, 2).mean(axis=1)
        camera = self.renderer.GetActiveCamera()
        camera.SetFocalPoint(*center)
        camera.SetPosition(*(center + [250, 400, 120]))
        camera.SetViewUp(0, 0, 1)
        camera.SetParallelProjection(False)
        camera.SetViewAngle(30.0)
        camera.SetWindowCenter(0.0, 0.0)
        self.renderer.ResetCamera(bounds)
        self.renderer.ResetCameraClippingRange(bounds)
        self.render()

    def update_planes(self, *args):
        if self.renderer is None or self.model is None:
            return
        for actor in self.planes:
            self.renderer.RemoveActor(actor)
        self.planes.clear()
        if self.show_planes.isChecked():
            for axis, index in enumerate(self.indices):
                actor = plane_actor(self.model.volume, axis, index, self.level, self.width)
                self.renderer.AddActor(actor)
                self.planes.append(actor)
        self.render()

    def render(self):
        if self.canvas is not None:
            self.canvas.Render()

    # Brain regions: an atlas mapped onto charm's pial surface, drawn as a separate colored layer.

    def build_region_controls(self, controls):
        box = QGroupBox("Brain regions")
        self.regions_box = box
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Atlas"))
        self.region_atlas = QComboBox()
        self.region_atlas.setAccessibleName("Brain region atlas")
        for title, value in REGION_ATLASES:
            self.region_atlas.addItem(title, value)
        compact_choice(self.region_atlas)
        self.region_atlas.currentIndexChanged.connect(
            lambda *_: self.regions_requested.emit(self.region_atlas.currentData() or ""))
        layout.addWidget(self.region_atlas)
        self.region_targets = QCheckBox("Highlight TMS targets (M1, DLPFC)")
        self.region_targets.setToolTip("Motor cortex in red; middle frontal regions around DLPFC in orange. "
                                       "The DLPFC mark is an atlas approximation, not a treatment target.")
        self.region_targets.toggled.connect(lambda *_: self.refresh_regions())
        layout.addWidget(self.region_targets)
        self.region_hint = QLabel()
        self.region_hint.setObjectName("subtitle")
        self.region_hint.setWordWrap(True)
        layout.addWidget(self.region_hint)
        self.region_picked_label = QLabel("Click the cortex to name a region.")
        self.region_picked_label.setTextFormat(Qt.TextFormat.PlainText)
        self.region_picked_label.setWordWrap(True)
        self.region_picked_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.region_picked_label)
        self.region_list = QListWidget()
        self.region_list.setAccessibleName("Brain regions shown in 3D")
        self.region_list.setMinimumHeight(180)
        self.region_list.itemChanged.connect(self.region_item_changed)
        layout.addWidget(self.region_list)
        buttons = QHBoxLayout()
        self.region_buttons = []
        for text, visible in (("Show all", True), ("Hide all", False)):
            button = QPushButton(text)
            compact_action(button)
            button.clicked.connect(lambda checked=False, visible=visible: self.set_all_regions(visible))
            buttons.addWidget(button)
            self.region_buttons.append(button)
        layout.addLayout(buttons)
        controls.addWidget(box)
        self.set_region_controls(False, "Open a charm or hybrid model folder to color brain regions.")

    def set_region_controls(self, supported, hint=None):
        self.regions_supported = supported
        shown = supported and self.regions is not None
        self.region_atlas.setEnabled(supported)
        for widget in (self.region_targets, self.region_list, *self.region_buttons):
            widget.setEnabled(shown)
        if hint is not None:
            self.region_hint.setText(hint)

    def update_region_support(self, model):
        try:
            regions = regions_module()
        except ImportError:
            self.set_region_controls(False, "Brain regions are unavailable: tools/brain_regions is missing.")
            return
        if model.kind != "simnibs":
            self.set_region_controls(False, "Brain regions need charm's cortical surfaces. AI segmentations and "
                                            "exported models do not have them yet.")
        elif not regions.has_cortex(model.directory):
            self.set_region_controls(False, "This model folder has no charm cortical surfaces (surfaces/*.pial.gii).")
        else:
            available = regions.available_atlases()
            for index in range(self.region_atlas.count()):
                value = self.region_atlas.itemData(index)
                if value:
                    item = self.region_atlas.model().item(index)
                    item.setEnabled(value in available)
                    item.setToolTip("" if value in available else
                                    "Needs a SimNIBS 4 install; its data use terms keep it out of this repository.")
            missing = "" if "HCP_MMP1" in available else " HCP-MMP1 needs SimNIBS 4 installed."
            self.set_region_controls(bool(available), "Choose an atlas to color the cortex, then click the cortex "
                                                      "to name a region." + missing)

    def reset_regions(self):
        self.set_regions(None)
        self.region_atlas.blockSignals(True)
        self.region_atlas.setCurrentIndex(0)
        self.region_atlas.blockSignals(False)

    def set_regions(self, regions):
        """Show an atlas (CortexRegions) on the cortex, or remove it with None."""
        self.regions = regions
        self.hidden_regions.clear()
        self.region_trees = {}
        self.region_list.blockSignals(True)
        self.region_list.clear()
        self.clear_pick()
        if regions is None:
            if self.restore_brain is not None:
                tag = self.restore_brain
                self.restore_brain = None
                if tag in self.checks:
                    self.checks[tag].setChecked(True)
        else:
            from scipy.spatial import cKDTree
            by_name = {hemi.name: hemi for hemi in regions.hemispheres}
            for hemi_name, label, name, color in regions.regions():
                target = regions.target_of(by_name[hemi_name], label)
                item = QListWidgetItem(color_icon(color), f"{name} · {target}" if target else name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, (hemi_name, label))
                self.region_list.addItem(item)
            self.region_trees = {hemi.name: cKDTree(hemi.points) for hemi in regions.hemispheres}
            brain = self.presets.get("brain")
            if brain in self.checks and self.checks[brain].isChecked() and self.restore_brain is None:
                self.restore_brain = brain  # the pial layer sits on the gray matter surface; avoid overlap
                self.checks[brain].setChecked(False)
            count = len(regions.regions())
            self.region_hint.setText(f"{regions.atlas} on charm's pial surface · {count} regions, left and right "
                                     "listed separately. Gray marks the medial wall, which is not cortex.")
        self.region_list.blockSignals(False)
        self.set_region_controls(self.regions_supported)
        self.refresh_regions()

    def refresh_regions(self):
        if self.renderer is not None:
            self.build_region_actors()
            self.render()

    def build_region_actors(self):
        if self.renderer is None:
            return
        for actor in self.region_actors:
            self.renderer.RemoveActor(actor)
        self.region_actors = []
        if self.regions is None:
            return
        for hemi in self.regions.hemispheres:
            keep = region_triangles(hemi, self.hidden_regions)
            if not keep.any():
                continue
            colors = self.regions.vertex_colors(hemi, self.region_targets.isChecked())
            actor = colored_actor(hemi.points, hemi.triangles[keep], colors)
            self.renderer.AddActor(actor)
            self.region_actors.append(actor)

    def region_item_changed(self, item):
        key = tuple(item.data(Qt.ItemDataRole.UserRole))
        if item.checkState() == Qt.CheckState.Checked:
            self.hidden_regions.discard(key)
        else:
            self.hidden_regions.add(key)
        self.refresh_regions()

    def set_all_regions(self, visible):
        self.region_list.blockSignals(True)
        state = Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
        self.hidden_regions.clear()
        for row in range(self.region_list.count()):
            item = self.region_list.item(row)
            item.setCheckState(state)
            if not visible:
                self.hidden_regions.add(tuple(item.data(Qt.ItemDataRole.UserRole)))
        self.region_list.blockSignals(False)
        self.refresh_regions()

    def region_at(self, point):
        """Name of the region at a world point (mm), or None when no cortex lies within PICK_RADIUS_MM."""
        if self.regions is None:
            return None
        module = regions_module()
        best = None
        for hemi in self.regions.hemispheres:
            distance, index = self.region_trees[hemi.name].query(point)
            if distance <= PICK_RADIUS_MM and (best is None or distance < best[0]):
                best = (distance, hemi, int(index))
        if best is None:
            return None
        _, hemi, index = best
        label = int(hemi.labels[index])
        if label == module.UNKNOWN:
            return f"{module.HEMISPHERE_NAMES[hemi.name]} medial wall · not cortex"
        name = module.display_name(hemi, label)
        target = self.regions.target_of(hemi, label)
        return f"{name} · {target}" if target else name

    def install_picker(self):
        """A click (press and release without dragging) on the colored cortex names its region."""
        from vtkmodules.vtkRenderingCore import vtkCellPicker
        self.picker = vtkCellPicker()
        self.picker.SetTolerance(0.0005)
        interactor = self.canvas.GetRenderWindow().GetInteractor()
        interactor.AddObserver("LeftButtonPressEvent", self.on_press, 1.0)
        interactor.AddObserver("LeftButtonReleaseEvent", self.on_release, 1.0)

    def on_press(self, interactor, event):
        self.press_position = interactor.GetEventPosition()

    def on_release(self, interactor, event):
        start, self.press_position = self.press_position, None
        if start is None or not self.region_actors:
            return
        x, y = interactor.GetEventPosition()
        if abs(x - start[0]) + abs(y - start[1]) > 4:  # a drag rotated the view
            return
        self.picker.InitializePickList()
        for actor in self.region_actors:
            self.picker.AddPickList(actor)
        self.picker.PickFromListOn()
        if self.picker.Pick(x, y, 0, self.renderer):
            point = np.array(self.picker.GetPickPosition())
            name = self.region_at(point)
            if name:
                self.show_pick(point, name)

    def show_pick(self, point, name):
        """Mark the clicked point and name its region in the sidebar, the 3D corner and the status line."""
        self.clear_pick()
        self.region_picked_label.setText(name)
        self.region_picked.emit(name)
        if self.renderer is None:
            return
        from vtkmodules.vtkFiltersSources import vtkSphereSource
        from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkTextActor
        sphere = vtkSphereSource()
        sphere.SetCenter(*point)
        sphere.SetRadius(2.5)
        sphere.SetThetaResolution(24)
        sphere.SetPhiResolution(24)
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        marker = vtkActor()
        marker.SetMapper(mapper)
        marker.GetProperty().SetColor(1.0, 1.0, 1.0)
        marker.PickableOff()
        text = vtkTextActor()
        text.SetInput(name)
        text.GetTextProperty().SetFontSize(20)
        text.GetTextProperty().SetColor(1.0, 1.0, 1.0)
        text.GetTextProperty().SetBackgroundColor(0.0, 0.0, 0.0)
        text.GetTextProperty().SetBackgroundOpacity(0.55)
        text.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        text.SetPosition(0.02, 0.93)
        for prop in (marker, text):
            self.renderer.AddActor(prop)
            self.pick_props.append(prop)
        self.render()

    def clear_pick(self):
        if self.renderer is not None:
            for prop in self.pick_props:
                self.renderer.RemoveActor(prop)
        self.pick_props = []
        if hasattr(self, "region_picked_label"):
            self.region_picked_label.setText("Click the cortex to name a region.")

    def shutdown(self):
        if self.canvas is not None:
            if hasattr(self, "marker"):
                self.marker.SetEnabled(False)
            self.canvas.Finalize()
