from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import Response

from app.services import telemetry_admission


class FakePipeline:
    def __init__(self, client: "FakeRedis") -> None:
        self.client = client
        self.commands: list[tuple[str, str, int | None]] = []

    def incr(self, key: str) -> "FakePipeline":
        self.commands.append(("incr", key, None))
        return self

    def expire(self, key: str, seconds: int) -> "FakePipeline":
        self.commands.append(("expire", key, seconds))
        return self

    async def execute(self) -> list[int | bool]:
        results: list[int | bool] = []
        for command, key, seconds in self.commands:
            if command == "incr":
                self.client.counters[key] = self.client.counters.get(key, 0) + 1
                results.append(self.client.counters[key])
            else:
                assert seconds is not None
                self.client.expirations[key] = seconds
                results.append(True)
        return results

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        return None


class FakeRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def pipeline(self, *, transaction: bool) -> FakePipeline:
        assert transaction is True
        return FakePipeline(self)

    async def aclose(self) -> None:
        return None


def test_two_anonymous_clients_keep_independent_120_per_video_budgets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_TELEMETRY_SECRET", "test-stable-telemetry-secret")
    monkeypatch.setenv("APP_ENV", "test")
    telemetry_admission._SEEN_MINT_WINDOWS.clear()

    fake = FakeRedis()
    video_id = uuid4()
    fixed_now = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)
    playback_session_id = uuid4()

    first_response = Response()
    token_a = telemetry_admission.ensure_session_token(first_response, None)

    async def first_write(token: str) -> None:
        await telemetry_admission.admit_playback_event(
            video_id=video_id,
            user_id=None,
            playback_session_id=playback_session_id,
            anonymous_session_token=token,
            now=fixed_now,
            redis_factory=lambda: fake,
        )

    asyncio.run(first_write(token_a))

    second_response = Response()
    token_b = telemetry_admission.ensure_session_token(second_response, None)
    asyncio.run(first_write(token_b))

    assert token_a != token_b

    async def consume_remaining_budget(token: str) -> None:
        for _ in range(telemetry_admission.MAX_EVENTS_PER_WINDOW - 1):
            telemetry_admission.ensure_session_token(Response(), token)
            await telemetry_admission.admit_playback_event(
                video_id=video_id,
                user_id=None,
                playback_session_id=uuid4(),
                anonymous_session_token=token,
                now=fixed_now,
                redis_factory=lambda: fake,
            )

    asyncio.run(consume_remaining_budget(token_a))
    asyncio.run(consume_remaining_budget(token_b))

    client_keys = [
        key
        for key in fake.counters
        if key.startswith(f"{telemetry_admission.ADMISSION_NAMESPACE}:anon-client:")
    ]
    assert len(client_keys) == 2
    assert sorted(fake.counters[key] for key in client_keys) == [120, 120]

    async def one_more(token: str) -> None:
        telemetry_admission.ensure_session_token(Response(), token)
        await telemetry_admission.admit_playback_event(
            video_id=video_id,
            user_id=None,
            playback_session_id=uuid4(),
            anonymous_session_token=token,
            now=fixed_now,
            redis_factory=lambda: fake,
        )

    with pytest.raises(telemetry_admission.TelemetryAdmissionLimitExceeded):
        asyncio.run(one_more(token_a))
    with pytest.raises(telemetry_admission.TelemetryAdmissionLimitExceeded):
        asyncio.run(one_more(token_b))

    assert sorted(fake.counters[key] for key in client_keys) == [121, 121]


def test_identity_mint_guard_is_separate_from_client_event_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_TELEMETRY_SECRET", "test-stable-telemetry-secret")
    monkeypatch.setenv("APP_ENV", "test")
    telemetry_admission._SEEN_MINT_WINDOWS.clear()

    fake = FakeRedis()
    video_id = uuid4()
    fixed_now = datetime(2026, 9, 8, 12, 1, 0, tzinfo=timezone.utc)

    accepted = 0
    for _ in range(150):
        token = telemetry_admission.ensure_session_token(Response(), None)
        try:
            asyncio.run(
                telemetry_admission.admit_playback_event(
                    video_id=video_id,
                    user_id=None,
                    playback_session_id=uuid4(),
                    anonymous_session_token=token,
                    now=fixed_now,
                    redis_factory=lambda: fake,
                )
            )
            accepted += 1
        except telemetry_admission.TelemetryAdmissionLimitExceeded:
            pass

    assert accepted == telemetry_admission.MAX_EVENTS_PER_WINDOW
    mint_keys = [key for key in fake.counters if key.startswith(telemetry_admission.IDENTITY_MINT_NAMESPACE)]
    assert len(mint_keys) == 1
    assert fake.counters[mint_keys[0]] == 149
    client_keys = [key for key in fake.counters if ":anon-client:" in key]
    assert len(client_keys) == 150
    assert all(fake.counters[key] == 1 for key in client_keys)
