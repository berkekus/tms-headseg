"""Explicit native GPU/Qt check; reads an existing model and never runs CHARM."""

import argparse
from pathlib import Path
import time
from types import SimpleNamespace

import nibabel as nib
import numpy as np
from PySide6.QtCore import QEventLoop, QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkRenderWindow, vtkWindowToImageFilter
import vtkmodules.vtkRenderingOpenGL2  # register OpenGL renderer

from mesh_viewer import plane_actor, plane_geometry
from prototype import Window


def pump(app):
    app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 40)


def wait_for_model(app, window):
    deadline = time.monotonic() + 60
    while window.task is not None and time.monotonic() < deadline:
        pump(app)
        time.sleep(.01)
    assert window.task is None, "Model loading timed out"
    assert window.head_model is not None, window.feedback.text()


def capture(window):
    grabber = vtkWindowToImageFilter()
    grabber.SetInput(window)
    grabber.ReadFrontBufferOff()
    grabber.Update()
    image = grabber.GetOutput()
    width, height, _ = image.GetDimensions()
    return vtk_to_numpy(image.GetPointData().GetScalars()).reshape(height, width, -1)


def rendered_voxel_position(voxel, count=256, size=1024):
    """World x of one bright 1 mm voxel, measured from an orthographic render of its plane."""
    data = np.zeros((count, count, 3), np.float32)
    data[voxel, count // 2, 1] = 1
    volume = SimpleNamespace(data=data, image=nib.Nifti1Image(data, np.eye(4)))
    renderer = vtkRenderer()
    renderer.AddActor(plane_actor(volume, 2, 1, .5, 1))
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(size, size)
    window.AddRenderer(renderer)
    camera = renderer.GetActiveCamera()
    camera.ParallelProjectionOn()
    center = (count - 1) / 2
    camera.SetFocalPoint(center, center, 1)
    camera.SetPosition(center, center, 500)
    camera.SetViewUp(0, 1, 0)
    span = count + 8
    camera.SetParallelScale(span / 2)
    renderer.ResetCameraClippingRange()
    window.Render()
    profile = capture(window)[..., 0].astype(float).sum(axis=0)
    pixels = np.nonzero(profile > profile.max() / 4)[0]
    centroid = (pixels * profile[pixels]).sum() / profile[pixels].sum() + .5
    return center + (centroid - size / 2) * span / size


def check_plane_texture_registration():
    for voxel in (10, 64, 128, 192, 245):
        error = rendered_voxel_position(voxel) - voxel
        assert abs(error) < .1, f"Voxel {voxel} is drawn {error:+.2f} mm from its world position"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--screenshots", type=Path, help="Optional local directory for review images")
    args = parser.parse_args()
    check_plane_texture_registration()
    app = QApplication([])
    window = Window()
    window.show()
    try:
        window.load_head_model(args.model)
        wait_for_model(app, window)
        window.tabs.setCurrentIndex(2)
        for _ in range(5):
            pump(app)
        view = window.mesh_view
        assert len(view.actors) == len(window.head_model.surfaces)
        for surface in window.head_model.surfaces:
            actual = np.array(view.actors[surface.tag].GetBounds()).reshape(3, 2)
            np.testing.assert_allclose(actual[:, 0], surface.points.min(0), atol=1e-4)
            np.testing.assert_allclose(actual[:, 1], surface.points.max(0), atol=1e-4)
        tag = next(iter(view.actors))
        visible, opacity = view.checks[tag].isChecked(), view.sliders[tag].value()
        view.checks[tag].setChecked(not visible)
        assert bool(view.actors[tag].GetVisibility()) != visible
        view.checks[tag].setChecked(visible)
        view.sliders[tag].setValue(37)
        assert view.actors[tag].GetProperty().GetOpacity() == .37
        view.sliders[tag].setValue(opacity)
        camera = view.renderer.GetActiveCamera()
        before = np.array(camera.GetPosition())
        point = QPoint(view.canvas.width() // 2, view.canvas.height() // 2)
        QTest.mousePress(view.canvas, Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseMove(view.canvas, point + QPoint(60, 25), delay=20)
        QTest.mouseRelease(view.canvas, Qt.MouseButton.LeftButton, pos=point + QPoint(60, 25))
        pump(app)
        assert not np.allclose(camera.GetPosition(), before), "Mouse rotation did not move the camera"
        view.reset_camera()
        view.render()
        pump(app)
        pixels = capture(view.canvas.GetRenderWindow())
        height, width = pixels.shape[:2]
        center = pixels[height // 4:3 * height // 4, width // 4:3 * width // 4]
        assert np.ptp(center.astype(float), axis=(0, 1)).max() > 20, "No model geometry rendered in the viewport"
        if args.screenshots:
            args.screenshots.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.screenshots / "model-3d.png"))
        view.show_planes.setChecked(True)
        assert len(view.planes) == 3
        for axis, actor in enumerate(view.planes):
            corners = plane_geometry(window.volume, axis, view.indices[axis])
            all_corners = np.vstack((corners, corners[1] + corners[2] - corners[0]))
            actual = np.array(actor.GetBounds()).reshape(3, 2)
            np.testing.assert_allclose(actual[:, 0], all_corners.min(0), atol=1e-4)
            np.testing.assert_allclose(actual[:, 1], all_corners.max(0), atol=1e-4)
        slider = window.panels[0].slider
        slider.setValue(max(0, slider.value() - 1))
        assert view.indices[2] == slider.value()
        pump(app)
        if args.screenshots:
            window.grab().save(str(args.screenshots / "model-planes.png"))
        window.load_head_model(args.model)
        wait_for_model(app, window)
        window.tabs.setCurrentIndex(2)
        pump(app)
        assert view.actors, "Reopening lost the 3D scene"
        print("Native 3D check passed: plane texture registration, geometry, mouse rotation, visibility, opacity, linked MRI planes, and model reopening.", flush=True)
    finally:
        window.close()


if __name__ == "__main__":
    main()
