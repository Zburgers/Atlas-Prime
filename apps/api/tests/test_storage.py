from app.services.storage import MinioProcessedHlsStorage


def test_processed_hls_storage_reads_processed_bucket(monkeypatch):
    calls = {}

    class FakeBody:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self):
            return b"#EXTM3U\n"

    class FakeClient:
        def get_object(self, *, Bucket, Key):
            calls["bucket"] = Bucket
            calls["key"] = Key
            return {
                "Body": FakeBody(),
                "ContentType": "application/vnd.apple.mpegurl",
                "ContentLength": 8,
                "ETag": '"etag"',
            }

    monkeypatch.setenv("MINIO_BUCKET_PROCESSED", "processed-test")
    monkeypatch.setattr("app.services.storage.boto3.client", lambda *args, **kwargs: FakeClient())

    result = MinioProcessedHlsStorage().get_hls_object(key="processed/video/hls/master.m3u8")

    assert calls == {"bucket": "processed-test", "key": "processed/video/hls/master.m3u8"}
    assert result.body == b"#EXTM3U\n"
