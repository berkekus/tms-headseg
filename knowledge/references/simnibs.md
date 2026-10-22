---
type: Reference
title: SimNIBS Reference
description: Current baseline tools, documented entry points, and important example limitations.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: charm
  resource: https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html
  title: CHARM documentation
- id: release
  resource: https://github.com/simnibs/simnibs/releases/tag/v4.6.0
  title: SimNIBS 4.6.0 release
- id: mesh
  resource: https://simnibs.github.io/simnibs/build/html/documentation/command_line/meshmesh.html
  title: meshmesh documentation
- id: data
  resource: https://simnibs.github.io/simnibs/build/html/dataset.html
  title: Official example datasets
---

# SimNIBS Reference

Consulted on 2026-10-22. The inspected local installation directory is named 4.6; its runtime has not been verified here.

## Useful documented capabilities

- CHARM accepts T1 MRI, optionally with T2, and produces subject segmentation and a head mesh. T2 can improve skull reconstruction.[^charm]
- Version 4.6 includes an updated atlas, AI-based cortical surface reconstruction, and deep-learning initial registration. Treat old descriptions of the pipeline as version-specific.[^release]
- `meshmesh` creates a mesh from a label image. This establishes a documented meshing entry point, not compatibility with every external project format.[^mesh]
- Official sample data include Ernie. Inspect actual downloaded files: the supplied local example lacks the `label_prep/` directory used in the documentation's meshing example.[^data]

## Investigation boundary

Read source and documented interfaces before binary analysis. For this project, investigate label requirements, geometry, surface quality, and the runtime of stages that remain after segmentation replacement. Electric-field simulation is not needed for the initial modeling baseline.

## Related notes

[Ernie protocol](../experiments/ernie-baseline.md) · [Pipeline](../concepts/pipeline.md) · [Local observations](session-observations.md)

[^charm]: CHARM command-line documentation. [Open source](https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html).
[^release]: Official 4.6.0 release notes. [Open source](https://github.com/simnibs/simnibs/releases/tag/v4.6.0).
[^mesh]: Official meshmesh documentation. [Open source](https://simnibs.github.io/simnibs/build/html/documentation/command_line/meshmesh.html).
[^data]: Official datasets page; local file inventory is separately recorded in session observations. [Open source](https://simnibs.github.io/simnibs/build/html/dataset.html).
