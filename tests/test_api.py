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
        assert client.get(f"/api/jobs/{job_id}").json()["files"] == []


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
