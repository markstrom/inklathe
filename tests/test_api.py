from io import BytesIO
from time import sleep

from fastapi.testclient import TestClient
from PIL import Image

from inklathe.app import create_app
from inklathe.config import Settings


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), "white").save(output, "PNG")
    return output.getvalue()


def test_job_round_trip(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={"background": "threshold", "upscale": "lanczos", "scale": 2},
        )
        assert response.status_code == 202
        job_id = response.json()["id"]
        for _ in range(50):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["state"] == "complete":
                break
            sleep(0.02)
        assert job["state"] == "complete"
        assert client.get(job["files"][0]["download"]).headers["content-type"] == "image/png"
        assert client.get(job["archive"]).headers["content-type"] == "application/zip"


def test_rejects_unconfigured_ai(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={"upscale": "ai"},
        )
        assert response.status_code == 409
