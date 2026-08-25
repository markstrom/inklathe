from io import BytesIO
from time import sleep

import pytest
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
        script = client.get("/static/app.js")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert 'class="ascii-logo" aria-label="InkLathe"' in response.text
    assert 'id="theme-toggle"' in response.text
    assert 'id="favorite-preset"' in response.text
    assert 'id="save-favorite"' in response.text
    assert 'id="favorite-dialog"' in response.text
    assert 'data-tooltip="Compare with original (C)"' in response.text
    assert "Drop images" in response.text
    assert ">Process</button>" in response.text
    assert "Alt-click randomizes the treatment. New runs join the FIFO queue." in response.text
    assert "Generated fallbacks" not in response.text
    assert "Vintage mix" not in response.text
    assert '<option value="none">None</option>' in response.text
    assert '<option value="25">Subtle</option>' in response.text
    assert '<option value="50" selected>Worn</option>' in response.text
    assert '<option value="0">Clean</option>' not in response.text
    assert '<option value="none">Solid ink</option>' in response.text
    assert "Pattern placement" in response.text
    assert '<option value="1" selected>Centered</option>' in response.text
    assert '<option value="2">Mirrored</option>' in response.text
    assert '<option value="3">Offset crop</option>' in response.text
    assert "Wear seed" not in response.text
    assert 'id="next-variation"' not in response.text
    assert 'element.textContent = configured ? "Configured" : "Not configured";' in script.text
    assert 'type="range"' not in response.text
    assert "Alt-click to skip confirmation" in script.text
    assert "Remove ${source.file.name} from recent images?" in script.text
    assert 'const favoriteStorageKey = "inklathe-favorite-presets"' in script.text
    assert "function randomizePrintTreatment()" in script.text
    assert '"upscale",' in script.text
    assert '"seed",' in script.text


def test_http_basic_authentication_protects_app_and_api(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        auth_username="markstrom",
        auth_password="correct horse battery staple",
    )
    with TestClient(create_app(settings)) as client:
        denied = client.get("/")
        denied_api = client.get("/api/health")
        accepted = client.get("/", auth=("markstrom", "correct horse battery staple"))
        accepted_api = client.get(
            "/api/health", auth=("markstrom", "correct horse battery staple")
        )

    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == 'Basic realm="InkLathe", charset="UTF-8"'
    assert denied_api.status_code == 401
    assert accepted.status_code == 200
    assert accepted_api.json()["status"] == "ok"


def test_settings_reads_authentication_from_systemd_credentials(
    tmp_path, monkeypatch
) -> None:
    credentials = tmp_path / "credentials"
    credentials.mkdir()
    (credentials / "inklathe-auth-password").write_text(
        "server secret\n", encoding="utf-8"
    )
    monkeypatch.delenv("INKLATHE_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("INKLATHE_AUTH_PASSWORD_FILE", raising=False)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(credentials))
    monkeypatch.setenv("INKLATHE_DATA_DIR", str(tmp_path / "data"))

    settings = Settings.from_env()

    assert settings.auth_username == "inklathe"
    assert settings.auth_password == "server secret"


def test_job_round_trip(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={
                "background": "threshold",
                "upscale": "lanczos",
                "scale": 2,
                "texture": "scan-g306",
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
        assert job["settings"]["texture"] == "scan-g306"
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


def test_local_bitmap_textures_are_discovered(tmp_path) -> None:
    texture_dir = tmp_path / "textures"
    texture_dir.mkdir()
    Image.new("L", (80, 80), 255).save(texture_dir / "Grunge_306XL.jpg")
    Image.new("L", (80, 80), 127).save(
        texture_dir / "Texturelabs_Grunge_289XL.jpg"
    )
    Image.new("L", (80, 80), 127).save(
        texture_dir / "Texturelabs_Grunge_356XL.jpg"
    )
    settings = Settings(data_dir=tmp_path / "data", texture_dir=texture_dir)

    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health").json()
        response = client.post(
            "/api/jobs",
            files=[("files", ("logo.png", image_bytes(), "image/png"))],
            data={
                "upscale": "none",
                "grunge": 40,
                "texture": "scan-g306",
                "halftone": "halftone-g289",
            },
        )

    assert health["capabilities"]["bitmap_textures"] == [
        {
            "id": "scan-g306",
            "label": "Heavy screen ink",
            "category": "Screen print",
            "maximum_percent": 12.0,
            "kind": "scanned",
        }
    ]
    assert health["capabilities"]["halftones"] == [
        {
            "id": "halftone-g289",
            "label": "Black halftone floodcoat",
            "category": "Halftone",
            "kind": "scanned",
        }
    ]
    assert response.status_code == 202


def test_texture_catalog_supports_named_subfolders(tmp_path) -> None:
    texture_dir = tmp_path / "texture-library"
    wear_dir = texture_dir / "wear"
    halftone_dir = texture_dir / "halftone"
    wear_dir.mkdir(parents=True)
    halftone_dir.mkdir()
    Image.new("L", (80, 80), 255).save(wear_dir / "fibers.jpg")
    Image.new("L", (80, 80), 127).save(halftone_dir / "dots.jpg")
    (texture_dir / "textures.json").write_text(
        """{
          "version": 1,
          "textures": [
            {
              "id": "wear-fibers",
              "type": "wear",
              "file": "wear/fibers.jpg",
              "name": "Soft fabric fibers",
              "category": "Fabric",
              "maximum": 0.08
            },
            {
              "id": "halftone-dots",
              "type": "halftone",
              "file": "halftone/dots.jpg",
              "name": "Round print dots",
              "category": "Halftone",
              "invert": true
            }
          ]
        }""",
        encoding="utf-8",
    )
    settings = Settings(data_dir=tmp_path / "data", texture_dir=texture_dir)

    with TestClient(create_app(settings)) as client:
        capabilities = client.get("/api/health").json()["capabilities"]

    assert [item["label"] for item in capabilities["bitmap_textures"]] == [
        "Soft fabric fibers"
    ]
    assert [item["label"] for item in capabilities["halftones"]] == [
        "Round print dots"
    ]


def test_texture_catalog_rejects_parent_paths(tmp_path) -> None:
    texture_dir = tmp_path / "texture-library"
    texture_dir.mkdir()
    (texture_dir / "textures.json").write_text(
        """{
          "version": 1,
          "textures": [{
            "id": "unsafe",
            "type": "wear",
            "file": "../outside.jpg",
            "name": "Unsafe",
            "category": "Test",
            "maximum": 0.1
          }]
        }""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="safe relative file path"):
        create_app(Settings(data_dir=tmp_path / "data", texture_dir=texture_dir))


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
    texture_dir = tmp_path / "textures"
    texture_dir.mkdir()
    Image.new("L", (80, 80), 255).save(texture_dir / "Grunge_306XL.jpg")
    Image.new("L", (80, 80), 127).save(
        texture_dir / "Texturelabs_Grunge_289XL.jpg"
    )
    settings = Settings(data_dir=tmp_path / "data", texture_dir=texture_dir)
    with TestClient(create_app(settings)) as client:
        common_data = {
            "background": "threshold",
            "upscale": "lanczos",
            "scale": 2,
            "texture": "scan-g306",
            "halftone": "halftone-g289",
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

        cached_files = list((settings.data_dir / "cache").glob("*/*.png"))
        cached_inodes = {path: path.stat().st_ino for path in cached_files}
        assert len(cached_files) == 4

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
            "print-treatment",
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
