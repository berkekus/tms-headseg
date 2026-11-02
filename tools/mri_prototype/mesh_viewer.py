"""VTK inside Qt. Mesh vertices and MRI planes share RAS millimeter coordinates."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSlider,
    QVBoxLayout, QWidget,
)

from viewer import label_color


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


class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.canvas = None
        self.renderer = None
        self.actors = {}
        self.planes = []
        self.indices = [0, 0, 0]
        self.level, self.width = 0., 1.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        sidebar = QWidget()
        sidebar.setFixedWidth(265)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(0, 0, 18, 0)
        self.summary = QLabel("Open an existing head model to inspect its 3D surfaces.")
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
        reset = QPushButton("Reset camera")
        reset.clicked.connect(self.reset_camera)
        controls.addWidget(reset)
        self.show_planes = QCheckBox("Show MRI slice planes")
        self.show_planes.toggled.connect(self.update_planes)
        controls.addWidget(self.show_planes)
        controls.addWidget(QLabel("Tissue visibility / opacity"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.tissue_controls = QWidget()
        self.tissue_layout = QVBoxLayout(self.tissue_controls)
        self.tissue_layout.setContentsMargins(0, 0, 8, 0)
        self.tissue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.tissue_controls)
        controls.addWidget(scroll, 1)
        note = QLabel("RAS world coordinates · mm\nDrag: rotate · Shift-drag: pan\nScroll: zoom")
        note.setWordWrap(True)
        controls.addWidget(note)
        layout.addWidget(sidebar)
        self.viewport = QVBoxLayout()
        self.empty = QLabel("3D model appears here after opening a model folder.")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet("background: #101c21; color: #c6d9d8; border-radius: 5px;")
        self.viewport.addWidget(self.empty)
        layout.addLayout(self.viewport, 1)
        self.checks = {}
        self.sliders = {}
        self.presets = {}

    def clear(self):
        self.model = None
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
        self.summary.setText("Open an existing head model to inspect its 3D surfaces.")

    def set_model(self, model):
        self.clear()
        self.model = model
        count = sum(len(surface.triangles) for surface in model.surfaces)
        self.summary.setText("\n".join((model.directory.name, f"{len(model.surfaces)} surfaces · {count:,} triangles",
                                         "Subject space · original mesh geometry", *model.notes)))
        self.summary.setToolTip(str(model.mesh_path))
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
        self.add_orientation_marker()
        self.update_planes()
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
        selected = self.presets["brain" if brain else "head"]
        for tag, check in self.checks.items():
            check.setChecked(tag == selected)
        if not brain:
            self.sliders[selected].setValue(100)
        self.reset_camera()

    def reset_camera(self):
        if not self.actors:
            return
        center = np.mean([surface.points.mean(axis=0) for surface in self.model.surfaces], axis=0)
        camera = self.renderer.GetActiveCamera()
        camera.SetFocalPoint(*center)
        camera.SetPosition(*(center + [250, 400, 120]))
        camera.SetViewUp(0, 0, 1)
        self.renderer.ResetCamera()
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
            self.canvas.GetRenderWindow().Render()

    def shutdown(self):
        if self.canvas is not None:
            if hasattr(self, "marker"):
                self.marker.SetEnabled(False)
            self.canvas.Finalize()
