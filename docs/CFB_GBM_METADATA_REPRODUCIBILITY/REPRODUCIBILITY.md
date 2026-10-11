# CFB-GBM Version 4 metadata reproduction

Total labeled pairs: 379
Published-label mismatches: 0

| Pair | n | CR | PR | SD | PD | Mismatches |
|---|---:|---:|---:|---:|---:|---:|
| t0_to_t1 | 160 | 1 | 16 | 105 | 38 | 0 |
| t0_to_t2 | 112 | 0 | 18 | 64 | 30 | 0 |
| t1_to_t2 | 107 | 0 | 6 | 71 | 30 | 0 |

Categories were recalculated from the official Version 4 GTV volume columns using the thresholds in the CFB-GBM v2.0 paper. Output is aggregate-only; no patient IDs or patient-level result rows are written.

RANO categories are derived from the same GTV volumes being assessed. This audit reproduces published labels; it does not estimate independent diagnostic accuracy or clinical prediction performance.

Figure: ../figures/fig01_cfb_cohort_readiness.pdf (vector PDF), ../figures/fig01_cfb_cohort_readiness.svg (editable vector), and ../figures/fig01_cfb_cohort_readiness.png (360 dpi). Regenerate with scripts/plot_cfb_metadata.py using this directory's summary.json.
