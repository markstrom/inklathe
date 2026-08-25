from io import BytesIO
from time import sleep

from fastapi.testclient import TestClient
from PIL import Image

from inklathe.app import create_app
from inklathe.config import Settings
from inklathe.jobs import TIMESTAMP_EPOCH, _base62_timestamp


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), "white").save(output, "PNG")
    return output.getvalue()


def test_app_shell_is_english(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert "Drop images" in response.text
    assert ">Process</button>" in response.text
    assert '<option value="vintage-tee">Vintage tee</option>' in response.text


def test_job_round_trip(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={
                "background": "threshold",
                "upscale": "lanczos",
                "scale": 2,
                "texture": "scratches",
            },
        )
        assert response.status_code == 202
        job_id = response.json()["id"]
        for _ in range(50):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["state"] == "complete":
                break
            sleep(0.02)
        assert job["state"] == "complete"
        assert job["settings"]["texture"] == "scratches"
        result_name = job["files"][0]["name"]
        assert result_name.startswith("logo-")
        assert len(result_name.removesuffix(".png").rsplit("-", 1)[1]) == 5
        assert client.get(job["files"][0]["source"]).headers["content-type"] == "image/png"
        preview_response = client.get(job["files"][0]["preview"])
        assert preview_response.headers["content-type"] == "image/png"
        with Image.open(BytesIO(preview_response.content)) as preview:
            assert max(preview.size) <= 640
        assert client.get(job["files"][0]["download"]).headers["content-type"] == "image/png"
        assert client.get(job["archive"]).headers["content-type"] == "application/zip"


def test_result_can_be_deleted(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={"upscale": "none"},
        )
        job_id = response.json()["id"]
        for _ in range(50):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["state"] == "complete":
                break
            sleep(0.02)

        result = job["files"][0]
        assert client.delete(result["delete"]).status_code == 204
        assert client.get(result["download"]).status_code == 404
        assert client.get(result["preview"]).status_code == 404
        assert client.get(f"/api/jobs/{job_id}").json()["files"] == []


def test_processing_stages_are_reused_for_new_grunge(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        common_data = {
            "background": "threshold",
            "upscale": "lanczos",
            "scale": 2,
            "texture": "vintage-tee",
        }
        first_response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={**common_data, "grunge": 20},
        )
        first_job_id = first_response.json()["id"]
        for _ in range(50):
            first_job = client.get(f"/api/jobs/{first_job_id}").json()
            if first_job["state"] == "complete":
                break
            sleep(0.02)
        assert first_job["files"][0]["cache_hits"] == []

        cached_files = list((tmp_path / "cache").glob("*/*.png"))
        cached_inodes = {path: path.stat().st_ino for path in cached_files}
        assert len(cached_files) == 3

        second_response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={**common_data, "grunge": 60},
        )
        second_job_id = second_response.json()["id"]
        for _ in range(50):
            second_job = client.get(f"/api/jobs/{second_job_id}").json()
            if second_job["state"] == "complete":
                break
            sleep(0.02)

        assert second_job["files"][0]["cache_hits"] == [
            "normalized",
            "upscale",
            "background",
        ]
        assert {path: path.stat().st_ino for path in cached_files} == cached_inodes

        third_response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={**common_data, "background": "none", "grunge": 20},
        )
        third_job_id = third_response.json()["id"]
        for _ in range(50):
            third_job = client.get(f"/api/jobs/{third_job_id}").json()
            if third_job["state"] == "complete":
                break
            sleep(0.02)

        assert third_job["files"][0]["cache_hits"] == ["normalized", "upscale"]


def test_storage_limit_removes_old_jobs_before_current_job(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, max_data_bytes=1)
    with TestClient(create_app(settings)) as client:
        first_response = client.post(
            "/api/jobs",
            files=[("files", ("first.png", image_bytes(), "image/png"))],
            data={"upscale": "none"},
        )
        first_job_id = first_response.json()["id"]
        for _ in range(50):
            first_job = client.get(f"/api/jobs/{first_job_id}").json()
            if first_job["state"] == "complete":
                break
            sleep(0.02)

        second_response = client.post(
            "/api/jobs",
            files=[("files", ("second.png", image_bytes(), "image/png"))],
            data={"upscale": "none"},
        )
        second_job_id = second_response.json()["id"]
        for _ in range(50):
            second_job_response = client.get(f"/api/jobs/{second_job_id}")
            second_job = second_job_response.json()
            if second_job["state"] == "complete":
                break
            sleep(0.02)

        assert client.get(f"/api/jobs/{first_job_id}").status_code == 404
        assert client.get(f"/api/jobs/{second_job_id}").status_code == 200
        assert (tmp_path / "jobs" / second_job_id).exists()


def test_rejects_unconfigured_ai(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={"upscale": "ai"},
        )
        assert response.status_code == 409


def test_base62_timestamp_is_fixed_width_and_sortable() -> None:
    assert _base62_timestamp(TIMESTAMP_EPOCH) == "00000"
    assert _base62_timestamp(TIMESTAMP_EPOCH + 61) == "0000z"
    assert _base62_timestamp(TIMESTAMP_EPOCH + 62) == "00010"
    assert _base62_timestamp(TIMESTAMP_EPOCH + 1) < _base62_timestamp(TIMESTAMP_EPOCH + 2)
