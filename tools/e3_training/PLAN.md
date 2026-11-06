# Dataset003 E3 notebook adaptation

User authorized updating the notebook for the supplied E3 package on 2026-11-06.
The previous sampler-only source/notebook copy is backed up outside Git under
`training-runs/e3-sampler-only-superseded-60r2wsu9/`.

## Design

Use actual `handoff_e3.zip`, Dataset003_E3Face, 90 train entries / 67 source people
and 16 validation people. Keep physical IXI copies and standard uniform nnU-Net
sampling; remove the obsolete custom loader. Standard loss handles ignore label 6.
Use the E2 environment and architecture/patch plan, changing only dataset_name to 3.
Keep fresh initialization, seed 42, four augmentation workers and 5/100 epoch runs.

Reuse E2 archive/grid/RAS helpers in a private module adapter, avoiding changes to
E2. Add E3 manifest, copy, source-person and exact ignore-mask checks. Freeze source
bytes and RAS decoded values/coordinates, rather than platform-dependent gzip bytes.
Persist a distinct Dataset003 experiment ID and require the GPU pilot before the
fresh main run. Keep all flags off and require exact validation identities.

## Work

- [x] Back up previous local preparation and write Dataset003 regression tests;
  observe failures on the old dataset, path and command.
- [x] Add E3 data adapter, fixed contract and Dataset003 plans; retain immutable
  source archive and physical-copy checks.
- [x] Replace custom sampler with standard 5/100-epoch trainers and test ignore
  loss invariance, zero gradients, six output channels and CPU weight updates.
- [x] Update the standalone notebook for correct upload paths, SHA sidecar,
  source/RAS audit, Dataset003 commands, pilot gate and separate result directory.
- [x] Audit/convert the real data and test nnU-Net preprocessing of GU002/IXI037.
- [x] Complete final notebook/regression/standalone checks, stage the revised
  portable notebook and update canonical knowledge with verified results.

No automatic paid training, Workbench E3 integration, inference postprocessing,
commit or push is included. The live Colab GPU pilot remains the remote run gate.
