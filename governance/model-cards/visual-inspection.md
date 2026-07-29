# Model Card — Visual Inspection Baseline

## Identity

- Artifact: `cv_solar_champion.joblib`
- Method: HOG + LBP + statistics → calibrated RBF SVC

## Intended use

Demonstrate a CPU-friendly inspection triage pipeline with mandatory human
review for low-confidence or consequential decisions.

## Data

ELPV: 2.624 public 300×300 electroluminescence images from 44 photovoltaic
modules. The task is binary defective/functional at defect probability ≥ 0,5;
cell type mono/poly is retained for slice evaluation. Image license:
CC BY-NC-SA 4.0; loader: Apache-2.0.

## Validation

Type-aware stratified train/validation/test split with 525 untouched test
images. Five candidates are selected by validation macro F1. The final RBF SVC
records balanced accuracy 0,7337, macro F1 0,7467, PR-AUC 0,7354, ROC-AUC
0,8254, calibration, confusion matrix and mono/poly slices in
`data/models/cv_metrics.json`.

## Limitations and security

It must not confirm electrical defects. ELPV is not thermal imagery and its
license does not allow unrestricted commercial reuse. Blur, adversarial
patterns, cameras, temperature, class imbalance and domain shift can invalidate
results. The API limits MIME, bytes and decoded pixels, does not retain uploads
and records review separately without automatic retraining.
