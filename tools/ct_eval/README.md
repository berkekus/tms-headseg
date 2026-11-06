# CT skull evaluation (plan F8)

`ct_skull.py` scores a predicted skull against bone seen on CT. The CT must be on the same voxel grid as the MR the prediction came from, as in SynthRAD2023 (D15), where each brain MR is already registered to its CT. The reference comes from the CT, not from charm or any MR segmenter, so E2, E3 and charm are scored against the same independent reference.

CT data is evaluation data only. It never enters training.

## Reference and score

1. **Reference.** CT above 300 HU (`BONE_HU`), 1-voxel gaps closed, isolated parts below 1 mL dropped.
2. **Signal only.** Only voxels where the MR has signal are scored (`prepare_e2.outside_acquisition`). The CT often extends below the MR field of view, and defacing removes MR signal.
3. **Regions.**
   - **Calvaria (main score):** the top 70 mm of the skull, which holds the TMS targets.
   - **Field:** everything with signal, including the skull base, face and vertebrae.
4. **Metrics:** Dice, mean symmetric surface distance (`assd_mm`) and its 95th percentile (`hd95_mm`). Surface points are taken from the full masks, so the region's cut planes add no false surface.

```powershell
python tools\ct_eval\ct_skull.py --ct ct.nii.gz --mr mr.nii.gz --pred prediction.nii.gz --json e2.json
python tools\ct_eval\ct_skull.py --ct ct.nii.gz --mr mr.nii.gz --pred m2m_X\final_tissues.nii.gz --charm --json charm.json
```

`--charm` reads charm labels 4, 7 and 8 as skull. All three files are reoriented to RAS and must share one affine.

## D15 headers

D15 files set only the qform (sform code 0). nibabel and E2 read the qform. charm refuses files whose qform and sform differ, so charm inputs are copies with sform = qform. The voxels and the affine are unchanged.

## Pilot (2026-11-06, K1 desktop)

Cases: one per center (1BA001, 1BB002, 1BC001), extracted to `tms-data\ct_eval_D15_pilot_20261106`.

**Alignment check:** In every case the CT bone outline lay on the dark skull band of the T1. Center B's MR is contrast-enhanced.

**E2 (`results_e2_L4_20261105`) against CT, calvaria:**

| Case | Dice (300 HU) | ASSD (mm) | HD95 (mm) | E2 / CT volume |
| --- | --- | --- | --- | --- |
| 1BA001 | 0.813 | 1.21 | 2.00 | 156 / 215 mL |
| 1BB002 | 0.828 | 1.16 | 2.83 | 225 / 254 mL |
| 1BC001 | 0.834 | 1.03 | 2.24 | 199 / 233 mL |

**What the pilot shows:**
- E2 draws the skull about one voxel thinner than CT, losing bone at both the inner and outer edges.
- At 200, 300 and 400 HU, the calvaria Dice moves by at most 0.06, rising with the threshold. The order of the cases changes, so every comparison should use the same threshold.
- 1BA001 has an intracranial calcification larger than 1 mL near a lesion, which the reference counts as bone.

These are three cases, not a result.

## Tests

```bash
cd tools/ct_eval && python -m unittest -v
```
