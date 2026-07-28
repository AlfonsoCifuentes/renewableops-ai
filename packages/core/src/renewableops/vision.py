"""Classical solar inspection baseline using HOG/LBP-style numeric features."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import joblib
import numpy as np
from PIL import Image
from skimage.feature import hog, local_binary_pattern
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import DEFAULT_SEED, MODEL_DIR

CV_LABELS = np.array(["normal", "microcrack", "hotspot", "soiling"])


def extract_features(image: np.ndarray) -> np.ndarray:
    """Extract HOG, LBP histogram and robust intensity statistics."""

    grayscale = np.asarray(Image.fromarray(image).convert("L").resize((64, 64)))
    hog_vector = hog(
        grayscale,
        orientations=9,
        pixels_per_cell=(8, 8),
        cells_per_block=(2, 2),
        block_norm="L2-Hys",
    )
    lbp = local_binary_pattern(  # type: ignore[no-untyped-call]
        grayscale, P=8, R=1, method="uniform"
    )
    hist, _ = np.histogram(lbp, bins=np.arange(11), range=(0, 10), density=True)
    statistics = np.array(
        [
            grayscale.mean(),
            grayscale.std(),
            np.percentile(grayscale, 10),
            np.percentile(grayscale, 50),
            np.percentile(grayscale, 90),
        ]
    )
    return np.concatenate([hog_vector, hist, statistics]).astype(np.float32)


def _synthetic_image(label: str, rng: np.random.Generator, size: int = 64) -> np.ndarray:
    grid_y, grid_x = np.mgrid[0:size, 0:size]
    base = 112 + 22 * np.sin(grid_x / 5) + rng.normal(0, 6, (size, size))
    if label == "microcrack":
        diagonal = np.abs(grid_y - (0.65 * grid_x + rng.integers(5, 18))) < 1.4
        base[diagonal] = 28
    elif label == "hotspot":
        cx, cy = rng.integers(18, 46, 2)
        radius = (grid_x - cx) ** 2 + (grid_y - cy) ** 2
        base += 105 * np.exp(-radius / 75)
    elif label == "soiling":
        base *= 0.66 + 0.08 * np.sin(grid_y / 9)
    return cast(np.ndarray, np.clip(base, 0, 255).astype(np.uint8))


def train_cv_baseline(
    *, model_dir: Path = MODEL_DIR, seed: int = DEFAULT_SEED, samples_per_class: int = 55
) -> dict[str, float | int | str]:
    """Train a deterministic classic CV smoke model on explicitly synthetic textures."""

    rng = np.random.default_rng(seed)
    features: list[np.ndarray] = []
    labels: list[str] = []
    groups: list[int] = []
    for class_index, label in enumerate(CV_LABELS):
        for sample in range(samples_per_class):
            features.append(extract_features(_synthetic_image(str(label), rng)))
            labels.append(str(label))
            groups.append(class_index * samples_per_class + sample // 5)
    x = np.vstack(features)
    y = np.asarray(labels)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.22, random_state=seed)
    train_index, test_index = next(splitter.split(x, y, groups))
    base = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=1.1,
                    max_iter=900,
                    class_weight="balanced",
                    random_state=seed,
                ),
            ),
        ]
    )
    classifier = CalibratedClassifierCV(base, cv=3, method="sigmoid")
    classifier.fit(x[train_index], y[train_index])
    prediction = classifier.predict(x[test_index])
    metrics: dict[str, float | int | str] = {
        "model": "HOG + LBP + calibrated logistic regression",
        "accuracy": round(float(accuracy_score(y[test_index], prediction)), 4),
        "macro_f1": round(float(f1_score(y[test_index], prediction, average="macro")), 4),
        "train_images": int(len(train_index)),
        "test_images": int(len(test_index)),
        "data_origin": "synthetic texture benchmark",
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(classifier, model_dir / "cv_solar_champion.joblib", compress=3)
    (model_dir / "cv_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def inspect_image(image: np.ndarray, *, model_dir: Path = MODEL_DIR) -> dict[str, object]:
    """Run bounded inference and return calibrated probabilities plus quality evidence."""

    grayscale = np.asarray(Image.fromarray(image).convert("L").resize((64, 64)))
    contrast = float(grayscale.std())
    if contrast < 5:
        return {
            "status": "review_required",
            "reason": "Image contrast is too low for reliable inference",
            "quality_score": round(contrast / 5, 3),
        }
    model = joblib.load(model_dir / "cv_solar_champion.joblib")
    probabilities = model.predict_proba(extract_features(grayscale).reshape(1, -1))[0]
    classes = model.classes_
    best = int(np.argmax(probabilities))
    return {
        "status": "completed",
        "prediction": str(classes[best]),
        "confidence": round(float(probabilities[best]), 4),
        "quality_score": round(min(1.0, contrast / 32), 3),
        "probabilities": {
            str(label): round(float(value), 4)
            for label, value in zip(classes, probabilities, strict=True)
        },
        "explanation": "HOG edge orientation, LBP texture and intensity statistics",
        "is_synthetic_model": True,
    }
