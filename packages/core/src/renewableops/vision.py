"""Classical solar inspection benchmark using HOG, LBP and numeric features."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Literal, cast

import joblib
import numpy as np
from PIL import Image
from skimage.feature import hog, local_binary_pattern
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, StratifiedShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, LinearSVC

from .config import DEFAULT_SEED, MODEL_DIR

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

CV_LABELS = np.array(["normal", "microcrack", "hotspot", "soiling"])
ELPV_URL = "https://github.com/zae-bayern/elpv-dataset"
ELPV_LICENSE = "CC BY-NC-SA 4.0 (images); Apache-2.0 (loader)"


def extract_features(image: np.ndarray) -> np.ndarray:
    """Extract HOG, LBP and auditable intensity/gradient statistics."""

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
    normalized = grayscale.astype(np.float32) / 255.0
    centered = normalized - float(normalized.mean())
    standard_deviation = max(float(normalized.std()), 1e-8)
    gradient_y, gradient_x = np.gradient(normalized)
    gradient_magnitude = np.hypot(gradient_x, gradient_y)
    histogram, _ = np.histogram(grayscale, bins=32, range=(0, 256), density=False)
    probability = histogram / max(int(histogram.sum()), 1)
    nonzero = probability[probability > 0]
    statistics = np.array(
        [
            normalized.mean(),
            normalized.std(),
            np.percentile(normalized, 10),
            np.percentile(normalized, 50),
            np.percentile(normalized, 90),
            -np.sum(nonzero * np.log2(nonzero)),
            np.mean((centered / standard_deviation) ** 3),
            np.mean((centered / standard_deviation) ** 4) - 3,
            np.mean(gradient_magnitude > 0.12),
            np.mean(gradient_magnitude),
            np.mean(
                np.abs(
                    normalized
                    - np.asarray(
                        Image.fromarray(grayscale).resize((16, 16)).resize((64, 64))
                    )
                    / 255.0
                )
            ),
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


def _load_elpv() -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    try:
        from elpv_dataset.utils import load_dataset
    except ImportError as error:
        raise RuntimeError(
            "Install the `cv` extra (`uv sync --extra cv`) to train on ELPV."
        ) from error

    images, defect_probability, cell_type = load_dataset()
    labels = np.where(np.asarray(defect_probability) >= 0.5, "defective", "functional")
    package_file = __import__("elpv_dataset").__file__
    if package_file is None:
        raise RuntimeError("ELPV package location is unavailable")
    labels_path = Path(package_file).resolve().parent / "data" / "labels.csv"
    metadata: dict[str, object] = {
        "dataset": "ELPV",
        "dataset_url": ELPV_URL,
        "license": ELPV_LICENSE,
        "data_origin": "real public electroluminescence images",
        "images": int(len(images)),
        "annotation_hash": f"sha256:{hashlib.sha256(labels_path.read_bytes()).hexdigest()}",
        "task": "binary defective/functional at defect_probability >= 0.5",
        "control_variable": "mono/poly cell type",
        "group_split": "unavailable in distributed annotations; stratified type-aware split",
    }
    return np.asarray(images), labels, np.asarray(cell_type), metadata


def _load_synthetic(
    seed: int,
    samples_per_class: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    rng = np.random.default_rng(seed)
    images: list[np.ndarray] = []
    labels: list[str] = []
    groups: list[int] = []
    for class_index, label in enumerate(CV_LABELS):
        for sample in range(samples_per_class):
            images.append(_synthetic_image(str(label), rng))
            labels.append(str(label))
            groups.append(class_index * samples_per_class + sample // 5)
    metadata: dict[str, object] = {
        "dataset": "RenewableOps synthetic textures",
        "dataset_url": None,
        "license": "MIT",
        "data_origin": "synthetic texture benchmark",
        "images": len(images),
        "annotation_hash": hashlib.sha256(
            json.dumps(labels, separators=(",", ":")).encode()
        ).hexdigest(),
        "task": "four-class smoke benchmark",
        "control_variable": "deterministic texture group",
        "group_split": "GroupShuffleSplit by synthetic generation batch",
    }
    return np.asarray(images), np.asarray(labels), np.asarray(groups), metadata


def _cv_candidates(seed: int) -> dict[str, Any]:
    logistic = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=1.1,
                    max_iter=1_200,
                    class_weight="balanced",
                    random_state=seed,
                ),
            ),
        ]
    )
    linear_svc = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LinearSVC(
                    C=0.08,
                    class_weight="balanced",
                    dual="auto",
                    max_iter=8_000,
                    tol=1e-3,
                    random_state=seed,
                ),
            ),
        ]
    )
    return {
        "calibrated_logistic_regression": CalibratedClassifierCV(
            logistic,
            cv=3,
            method="sigmoid",
        ),
        "calibrated_linear_svc": CalibratedClassifierCV(
            linear_svc,
            cv=3,
            method="sigmoid",
        ),
        "rbf_svc": CalibratedClassifierCV(
            SVC(
                C=3.0,
                gamma="scale",
                class_weight="balanced",
                random_state=seed,
            ),
            cv=3,
            method="sigmoid",
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=140,
            max_depth=18,
            min_samples_leaf=2,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=1,
            random_state=seed,
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("scale", StandardScaler()),
                ("pca", PCA(n_components=48, whiten=True, random_state=seed)),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.08,
                        max_iter=120,
                        max_leaf_nodes=24,
                        l2_regularization=0.5,
                        random_state=seed,
                    ),
                ),
            ]
        ),
    }


def _expected_calibration_error(
    truth: np.ndarray,
    confidence: np.ndarray,
    predicted: np.ndarray,
    *,
    bins: int = 10,
) -> float:
    edges = np.linspace(0, 1, bins + 1)
    error = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (confidence > lower) & (confidence <= upper)
        if not mask.any():
            continue
        accuracy = float(np.mean(predicted[mask] == truth[mask]))
        error += float(np.mean(mask)) * abs(accuracy - float(np.mean(confidence[mask])))
    return error


def _classification_metrics(
    model: Any,
    features: np.ndarray,
    truth: np.ndarray,
) -> dict[str, object]:
    predicted = np.asarray(model.predict(features))
    probabilities = np.asarray(model.predict_proba(features))
    classes = np.asarray(model.classes_)
    precision, recall, class_f1, support = precision_recall_fscore_support(
        truth,
        predicted,
        labels=classes,
        zero_division=0,
    )
    confidence = probabilities.max(axis=1)
    result: dict[str, object] = {
        "accuracy": round(float(accuracy_score(truth, predicted)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(truth, predicted)), 4),
        "macro_f1": round(float(f1_score(truth, predicted, average="macro")), 4),
        "expected_calibration_error": round(
            _expected_calibration_error(truth, confidence, predicted),
            4,
        ),
        "confusion_matrix": confusion_matrix(truth, predicted, labels=classes).tolist(),
        "class_order": classes.tolist(),
        "per_class": {
            str(label): {
                "precision": round(float(precision[index]), 4),
                "recall": round(float(recall[index]), 4),
                "f1": round(float(class_f1[index]), 4),
                "support": int(support[index]),
            }
            for index, label in enumerate(classes)
        },
    }
    if len(classes) == 2:
        positive_index = int(np.where(classes == "defective")[0][0])
        binary_truth = (truth == "defective").astype(int)
        positive_probability = probabilities[:, positive_index]
        result.update(
            {
                "pr_auc": round(
                    float(average_precision_score(binary_truth, positive_probability)),
                    4,
                ),
                "roc_auc": round(
                    float(roc_auc_score(binary_truth, positive_probability)),
                    4,
                ),
                "brier_score": round(
                    float(brier_score_loss(binary_truth, positive_probability)),
                    4,
                ),
                "severe_defect_recall": round(
                    float(recall[positive_index]),
                    4,
                ),
            }
        )
    else:
        one_hot = np.column_stack([(truth == label).astype(int) for label in classes])
        result.update(
            {
                "pr_auc": round(
                    float(average_precision_score(one_hot, probabilities, average="macro")),
                    4,
                ),
                "roc_auc": round(
                    float(roc_auc_score(one_hot, probabilities, average="macro")),
                    4,
                ),
                "brier_score": round(float(np.mean((one_hot - probabilities) ** 2)), 4),
                "severe_defect_recall": None,
            }
        )
    return result


def train_cv_baseline(
    *,
    model_dir: Path = MODEL_DIR,
    seed: int = DEFAULT_SEED,
    samples_per_class: int = 55,
    dataset: Literal["auto", "elpv", "synthetic"] = "auto",
) -> dict[str, object]:
    """Train and select a classic CV model without using the held-out test."""

    if dataset in {"auto", "elpv"}:
        try:
            images, y, controls, metadata = _load_elpv()
        except RuntimeError:
            if dataset == "elpv":
                raise
            images, y, controls, metadata = _load_synthetic(seed, samples_per_class)
    else:
        images, y, controls, metadata = _load_synthetic(seed, samples_per_class)

    x = np.vstack([extract_features(image) for image in images])
    if metadata["dataset"] == "ELPV":
        strata = np.char.add(np.char.add(y.astype(str), ":"), controls.astype(str))
        first_split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
        development_index, test_index = next(first_split.split(x, strata))
        second_strata = strata[development_index]
        second_split = StratifiedShuffleSplit(
            n_splits=1,
            test_size=0.2,
            random_state=seed + 1,
        )
        train_relative, validation_relative = next(
            second_split.split(x[development_index], second_strata)
        )
        train_index = development_index[train_relative]
        validation_index = development_index[validation_relative]
    else:
        first_split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
        development_index, test_index = next(first_split.split(x, y, controls))
        second_split = GroupShuffleSplit(
            n_splits=1,
            test_size=0.2,
            random_state=seed + 1,
        )
        train_relative, validation_relative = next(
            second_split.split(
                x[development_index],
                y[development_index],
                controls[development_index],
            )
        )
        train_index = development_index[train_relative]
        validation_index = development_index[validation_relative]

    candidate_results: dict[str, dict[str, object]] = {}
    candidate_models = _cv_candidates(seed)
    for name, candidate in candidate_models.items():
        candidate.fit(x[train_index], y[train_index])
        candidate_results[name] = _classification_metrics(
            candidate,
            x[validation_index],
            y[validation_index],
        )
    champion_name = max(
        candidate_results,
        key=lambda name: cast(float, candidate_results[name]["macro_f1"]),
    )
    classifier = clone(candidate_models[champion_name])
    fit_index = np.concatenate([train_index, validation_index])
    classifier.fit(x[fit_index], y[fit_index])
    test_metrics = _classification_metrics(classifier, x[test_index], y[test_index])

    slice_metrics: dict[str, object] = {}
    if metadata["dataset"] == "ELPV":
        for cell_type in sorted(set(controls[test_index].tolist())):
            mask = controls[test_index] == cell_type
            slice_metrics[str(cell_type)] = _classification_metrics(
                classifier,
                x[test_index][mask],
                y[test_index][mask],
            )

    metrics: dict[str, object] = {
        **metadata,
        "model": f"HOG + LBP + statistics + {champion_name}",
        "champion": champion_name,
        "selection_metric": "validation macro F1",
        "test_used_for_selection": False,
        "feature_count": int(x.shape[1]),
        "train_images": int(len(train_index)),
        "validation_images": int(len(validation_index)),
        "test_images": int(len(test_index)),
        **test_metrics,
        "candidate_validation": candidate_results,
        "slices_by_cell_type": slice_metrics,
        "preprocessing": {
            "grayscale": True,
            "resize": [64, 64],
            "normalization": "statistics normalized to [0,1]; HOG L2-Hys",
            "augmentation_before_split": False,
        },
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": classifier,
        "model_name": champion_name,
        "model_version": "1.0.0",
        "classes": classifier.classes_.tolist(),
        "feature_extractor": "hog_lbp_statistics_v2",
        "dataset": metadata,
    }
    joblib.dump(artifact, model_dir / "cv_solar_champion.joblib", compress=3)
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
    artifact = joblib.load(model_dir / "cv_solar_champion.joblib")
    model = artifact["model"] if isinstance(artifact, dict) else artifact
    probabilities = model.predict_proba(extract_features(grayscale).reshape(1, -1))[0]
    classes = model.classes_
    best = int(np.argmax(probabilities))
    return {
        "status": "completed",
        "model_name": (
            artifact.get("model_name", "classic-cv")
            if isinstance(artifact, dict)
            else "classic-cv"
        ),
        "model_version": (
            artifact.get("model_version", "legacy") if isinstance(artifact, dict) else "legacy"
        ),
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
