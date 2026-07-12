from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AnalyticsTotals(BaseModel):
    impressions: int
    views: int
    watch_time_seconds: Decimal


class AnalyticsDailyPoint(AnalyticsTotals):
    date: date


class AnalyticsTopVideo(AnalyticsTotals):
    video_id: UUID
    title: str


class StudioAnalyticsResponse(BaseModel):
    date_from: date
    date_to: date
    totals: AnalyticsTotals
    daily: list[AnalyticsDailyPoint]
    top_videos: list[AnalyticsTopVideo]


class AnalyticsRebuildResponse(BaseModel):
    date_from: date
    date_to: date
    video_metric_rows: int
    creator_metric_rows: int
