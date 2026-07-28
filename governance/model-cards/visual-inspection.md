# Model Card — Visual Inspection Baseline

## Identity

- Artifact: `cv_solar_champion.joblib`
- Method: HOG + LBP + statistics → calibrated LogisticRegression

## Intended use

Demonstrate a CPU-friendly, explainable inspection triage pipeline.

## Data

Synthetic textures resembling normal, hotspot, microcrack and soiling classes.
This is not a validated thermographic defect dataset.

## Validation

Stratified held-out textures, macro F1, balanced accuracy and calibration
evidence in `data/models/cv_metrics.json`.

## Limitations and security

It must not confirm electrical defects. Blur, adversarial patterns, cameras,
temperature and domain shift can invalidate results. The API limits type,
bytes, decoded pixels and does not retain uploads. Low-confidence results
require human review.
