"""Surface files that declare their frame, and helpers for the model metadata record.

3D Slicer reads `SPACE=RAS` from an STL header or a PLY comment, and assumes LPS without it.
"""

import hashlib
import struct

import numpy as np

from .surfaces import enclosed_volume, is_closed

SCHEMA = "tms-headseg-model/1"
FRAME_TAG = "SPACE=RAS UNITS=mm"

_STL_HEADER_BYTES = 80
_STL_FACET = np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_stl(path, mesh):
    """Binary STL, which stores float32 coordinates and one normal per triangle."""
    triangles = mesh.vertices[mesh.faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    facets = np.zeros(len(triangles), _STL_FACET)
    facets["normal"] = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
    facets["vertices"] = triangles
    with open(path, "wb") as file:
        file.write(FRAME_TAG.encode("ascii").ljust(_STL_HEADER_BYTES))
        file.write(struct.pack("<I", len(facets)))
        facets.tofile(file)


def read_stl_header(path):
    with open(path, "rb") as file:
        return file.read(_STL_HEADER_BYTES).decode("ascii", errors="replace")


def write_ply(path, mesh):
    """Binary PLY, which keeps shared vertices and so the surface connectivity."""
    header = ("ply\nformat binary_little_endian 1.0\n"
              f"comment {FRAME_TAG}\n"
              f"element vertex {len(mesh.vertices)}\n"
              "property float x\nproperty float y\nproperty float z\n"
              f"element face {len(mesh.faces)}\n"
              "property list uchar int vertex_indices\nend_header\n")
    faces = np.zeros(len(mesh.faces), [("count", "u1"), ("indices", "<i4", 3)])
    faces["count"] = 3
    faces["indices"] = mesh.faces
    with open(path, "wb") as file:
        file.write(header.encode("ascii"))
        mesh.vertices.astype("<f4").tofile(file)
        faces.tofile(file)


def read_ply_header(path):
    with open(path, "rb") as file:
        return file.read(4096).split(b"end_header")[0].decode("ascii", errors="replace")


WRITERS = {"stl": write_stl, "ply": write_ply}
HEADER_READERS = {".stl": read_stl_header, ".ply": read_ply_header}


def describe_surface(path, mesh):
    return {"file": path.name, "sha256": sha256(path), "vertices": len(mesh.vertices),
            "triangles": len(mesh.faces), "closed": is_closed(mesh),
            "volume_ml": enclosed_volume(mesh) / 1000,
            "bounds_mm": {"min": mesh.vertices.min(axis=0).tolist(), "max": mesh.vertices.max(axis=0).tolist()}}
