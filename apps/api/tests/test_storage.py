from uuid import uuid4

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


def test_processed_hls_storage_deletes_only_the_video_prefix(monkeypatch):
    calls = []
    video_id = uuid4()

    class FakeClient:
        def list_objects_v2(self, **kwargs):
            calls.append(("list", kwargs))
            return {
                "Contents": [{"Key": f"processed/{video_id}/hls/master.m3u8"}, {"Key": f"processed/{video_id}/captions/en/track.vtt"}],
                "IsTruncated": False,
            }

        def delete_objects(self, **kwargs):
            calls.append(("delete", kwargs))
            return {"Deleted": kwargs["Delete"]["Objects"]}

    monkeypatch.setenv("MINIO_BUCKET_PROCESSED", "processed-test")
    monkeypatch.setattr("app.services.storage.boto3.client", lambda *args, **kwargs: FakeClient())

    deleted = MinioProcessedHlsStorage().delete_video_tree(video_id=video_id)

    assert deleted == 2
    assert calls == [
        ("list", {"Bucket": "processed-test", "Prefix": f"processed/{video_id}/"}),
        ("delete", {"Bucket": "processed-test", "Delete": {"Objects": [{"Key": f"processed/{video_id}/hls/master.m3u8"}, {"Key": f"processed/{video_id}/captions/en/track.vtt"}], "Quiet": True}}),
    ]
