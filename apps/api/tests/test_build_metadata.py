from app.core import config


def test_build_metadata_defaults_to_unknown(monkeypatch):
    monkeypatch.delenv("ATLAS_BUILD_SHA", raising=False)
    monkeypatch.delenv("ATLAS_BUILD_TIME", raising=False)

    assert config.build_sha() == "unknown"
    assert config.build_time() == "unknown"


def test_build_metadata_reads_environment_overrides(monkeypatch):
    monkeypatch.setenv("ATLAS_BUILD_SHA", "abc123")
    monkeypatch.setenv("ATLAS_BUILD_TIME", "2026-08-24T12:00:00Z")

    assert config.build_sha() == "abc123"
    assert config.build_time() == "2026-08-24T12:00:00Z"
