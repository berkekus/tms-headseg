"""Project tissue schema and mappings from source label schemes."""

import numpy as np

BACKGROUND, SKIN, SKULL, CSF, GRAY_MATTER, WHITE_MATTER = range(6)
TISSUES = {SKIN: "skin", SKULL: "skull", CSF: "csf", GRAY_MATTER: "gray_matter", WHITE_MATTER: "white_matter"}

# Proposed in EXP-002 and not accepted; see Q-05. Blood (9) is CSF because MultiAxial labels
# intracranial blood, mostly dural sinuses, as CSF (EXP-002 evidence, 2026-11-03).
CHARM_TO_PROJECT = {
    0: BACKGROUND, 1: WHITE_MATTER, 2: GRAY_MATTER, 3: CSF, 4: SKULL, 5: SKIN, 6: CSF,
    7: SKULL, 8: SKULL, 9: CSF, 10: SKIN, 11: SKIN, 12: SKIN,
}


def _integer_values(labels):
    if labels.dtype.kind == "f" and np.any(labels != np.round(labels)):
        raise ValueError("Label maps must hold integer values.")
    return set(np.unique(labels).astype(np.int64).tolist())


def map_labels(labels, mapping):
    """Translate a source scheme; a value without a mapping stops processing."""
    values = _integer_values(labels)
    unknown = sorted(values - mapping.keys())
    if unknown:
        raise ValueError(f"Source labels {unknown} have no mapping.")
    lookup = np.zeros(max(values) + 1, np.uint8)
    for source, target in mapping.items():
        if source < len(lookup):
            lookup[source] = target
    return lookup[labels.astype(np.int64)]


def validate_project_labels(labels):
    unknown = sorted(_integer_values(labels) - {BACKGROUND, *TISSUES})
    if unknown:
        raise ValueError(f"Labels {unknown} are outside the project schema.")
    return labels.astype(np.uint8)
