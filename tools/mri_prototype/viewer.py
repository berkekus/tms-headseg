"""Three world-aligned slice views with physical aspect ratio and label colors."""

import colorsys

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from volume import slice_data


def label_color(label):
    rgb = colorsys.hsv_to_rgb((int(label) * .61803398875) % 1, .65, .95)
    return tuple(round(channel * 255) for channel in rgb)


def render_slice(volume, labels, axis, index, level, width, opacity, colors=None):
    plane = slice_data(volume.data, axis, index)
    gray = np.clip((plane - (level - width / 2)) / max(width, .001), 0, 1)
    rgb = np.repeat((gray * 255).astype(np.uint8)[..., None], 3, axis=2)
    if labels is not None and opacity > 0:
        ids = slice_data(labels, axis, index)
        for label in np.unique(ids[ids > 0]):
            mask = ids == label
            color = (colors or {}).get(int(label), label_color(label))
            rgb[mask] = rgb[mask] * (1 - opacity) + np.array(color) * opacity
    rgb = np.ascontiguousarray(rgb)
    return QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0],
                  QImage.Format.Format_RGB888).copy()


class Canvas(QWidget):
    def __init__(self, directions):
        super().__init__()
        self.image = None
        self.aspect = 1.
        self.directions = directions
        self.empty_message = "Open a T1 MRI to inspect slices"
        self.setMinimumSize(180, 220)
        self.setAccessibleName("MRI slice; orientation markers at image edges")

    def set_empty_message(self, message):
        self.empty_message = message
        self.setAccessibleDescription(message)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101c21"))
        painter.setPen(QColor("#98aeb7"))
        if self.image is None:
            painter.drawText(self.rect().adjusted(18, 18, -18, -18),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.empty_message)
            return
        area = self.rect().adjusted(26, 26, -26, -26)
        width = min(area.width(), area.height() * self.aspect)
        height = width / self.aspect
        target = QRectF(area.center().x() - width / 2, area.center().y() - height / 2, width, height)
        painter.drawImage(target, self.image)
        left, right, top, bottom = self.directions
        painter.setPen(QColor("#d9e8e9"))
        painter.drawText(7, self.height() // 2, left)
        painter.drawText(self.width() - 18, self.height() // 2, right)
        painter.drawText(self.width() // 2, 19, top)
        painter.drawText(self.width() // 2, self.height() - 9, bottom)


class SlicePanel(QFrame):
    def __init__(self, title, axis, directions):
        super().__init__()
        self.axis = axis
        self.volume = None
        self.labels = None
        self.colors = {}
        self.level, self.width, self.opacity = 0., 1., .4
        self.setObjectName("slicePanel")
        layout = QVBoxLayout(self)
        heading = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("planeTitle")
        heading.addWidget(label)
        self.position = QLabel("—")
        self.position.setAlignment(Qt.AlignmentFlag.AlignRight)
        heading.addWidget(self.position)
        layout.addLayout(heading)
        self.canvas = Canvas(directions)
        layout.addWidget(self.canvas, 1)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setAccessibleName(f"{title} slice")
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.refresh)
        layout.addWidget(self.slider)

    def set_volume(self, volume):
        self.volume = volume
        self.labels = None
        self.colors = {}
        self.slider.setEnabled(volume is not None)
        if volume is not None:
            self.level, self.width = volume.window
            self.slider.setRange(0, volume.data.shape[self.axis] - 1)
            self.slider.setValue(volume.data.shape[self.axis] // 2)
        self.refresh()

    def refresh(self):
        if self.volume is None:
            self.canvas.image = None
            self.position.setText("—")
        else:
            index = self.slider.value()
            self.canvas.image = render_slice(self.volume, self.labels, self.axis, index,
                                             self.level, self.width, self.opacity, self.colors)
            axes = [axis for axis in range(3) if axis != self.axis]
            spacing = np.diag(self.volume.image.affine)[:3]
            shape = self.volume.data.shape
            self.canvas.aspect = shape[axes[0]] * spacing[axes[0]] / (shape[axes[1]] * spacing[axes[1]])
            coordinate = self.volume.image.affine[self.axis, self.axis] * index + self.volume.image.affine[self.axis, 3]
            self.position.setText(f"{index + 1}/{shape[self.axis]} · {coordinate:.1f} mm")
            self.canvas.setAccessibleDescription(self.position.text())
        self.canvas.update()
