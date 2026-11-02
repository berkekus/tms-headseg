"""Asymmetric synthetic head defined in RAS millimetres, for geometry checks only."""

import numpy as np

from .frames import voxel_to_world

NOSE = np.array([0., 96., -10.])
LEFT_EAR = np.array([-76., 0., 0.])
RIGHT_VENTRICLE = np.array([8., 0., 5.])


def _inside(points, center, radii):
    return (((points - np.asarray(center)) / np.asarray(radii)) ** 2).sum(axis=1) <= 1


def phantom_labels(shape, affine):
    """Sample project labels on any grid, so every orientation holds the same anatomy."""
    points = voxel_to_world(affine, np.indices(shape).reshape(3, -1).T)
    labels = np.zeros(len(points), np.uint8)
    labels[_inside(points, (0, 0, 0), (70, 85, 90))] = 1
    labels[_inside(points, (0, 88, -10), (10, 14, 16))] = 1
    labels[_inside(points, (-72, 0, 0), (8, 12, 18))] = 1
    labels[_inside(points, (0, 0, 0), (64, 79, 84))] = 2
    labels[_inside(points, (0, 0, 0), (60, 75, 80))] = 3
    labels[_inside(points, (0, 0, 0), (57, 72, 77))] = 4
    labels[_inside(points, (0, 0, 0), (48, 62, 66))] = 5
    labels[_inside(points, RIGHT_VENTRICLE, (6, 18, 8))] = 3
    return labels.reshape(shape)
