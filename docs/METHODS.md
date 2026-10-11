# Methods notes

## Measurement convention

The protocol distinguishes expert-provided values, algorithm-derived values and segmentation spread. The CLI does not estimate tumor boundaries from an MRI. It consumes a curated manifest so source-specific label values, coordinate conventions and lesion inclusion can be independently validated first.

For each method and visit, retain the original 3D mask and document: source sequence, native/registered space, affine/voxel spacing, segmentation labels, enhancing-region mapping, lesion-selection rule, and any registration or resampling. Calculate volume only in physical units using voxel geometry. A 2D SPD derived from a mask is an algorithmic proxy until its slice, calipers and lesion selection are validated against the source expert measurement.

The `imaging-audit` command uses the released native CT1 mask for each method and its own enhancing label: DeepBraTumIA label 1; HD-GLIO-AUTO label 2. The DeepBraTumIA mapping was checked against the included per-visit `Enhancing_Core` volume JSON. It multiplies enhancing voxels by the absolute determinant of the affine's spatial 3×3 matrix to obtain mm³, then compares the mask grid with CT1. Earlier results using label 2 for both methods are superseded. These are data-integrity and volume summaries, not RANO SPD and not independent validation of either segmenter. Any inferential use requires spatial/label review and a frozen measurement protocol.

## Deferral scores

- `threshold_margin_fraction`: normalized distance from the current measurement to the nearest active decision threshold; lower margin means higher risk score. The analysis score is `1 / (1 + margin)`, bounded to (0, 1] for finite non-negative margins.
- `segmentation_spread_fraction`: spread across frozen per-method SPD measurements divided by a pre-specified scale; larger spread means higher risk score.

Version the normalization formula and threshold definition. A score is not a probability unless calibration is demonstrated on held-out patients.

## Statistical units

The patient is the independent sampling unit. The project reports visit-level curves with patient-clustered resampling. A patient with many visits must not dominate by being treated as many independent participants. Show both patient and visit counts.

## Current implementation boundary

`response.py` implements transparent threshold calculations only. Full RANO assessment also depends on protocol-specific factors such as timing, confirmatory imaging, non-target/new lesions, treatment context, neurologic status and corticosteroids. These fields must be explicitly available and implemented before a full automated RANO claim is made.
