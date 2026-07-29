from renewableops.model_evidence import build_model_verification


def test_model_artifacts_execute_smoke_inference():
    report = build_model_verification()

    assert report["status"] == "passed"
    assert len(report["artifacts"]) == 2
    assert {item["technology"] for item in report["artifacts"]} == {"solar", "wind"}
    assert all(item["smoke_inference"]["status"] == "passed" for item in report["artifacts"])
    assert all(item["sha256"].startswith("sha256:") for item in report["artifacts"])
