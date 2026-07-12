"use client";

import { Show, SignInButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  apiRequest,
  type ContentReport,
  type ContentReportListResponse,
  type ModerationActionName,
  type ModerationActionResult,
} from "../../components/video-api";
import { formatDate } from "../../components/status-ui";

const ACTIONS: ModerationActionName[] = ["remove", "limit", "restore"];

export default function AdminReportsPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [reports, setReports] = useState<ContentReport[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    if (!isSignedIn) {
      setReports([]);
      setTotal(0);
      setLoading(false);
      return;
    }
    try {
      const token = await getToken();
      const response = await apiRequest<ContentReportListResponse>("/admin/reports?state=open", { token });
      setReports(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load moderation reports.");
      setReports([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn]);

  useEffect(() => {
    if (isLoaded) {
      queueMicrotask(() => void loadReports());
    }
  }, [isLoaded, loadReports]);

  const applyAction = async (reportId: string, action: ModerationActionName) => {
    setBusyId(reportId);
    setError(null);
    try {
      const token = await getToken();
      const result = await apiRequest<ModerationActionResult>(`/admin/reports/${reportId}/actions`, {
        token,
        method: "POST",
        body: { action },
      });
      setReports((current) => current.filter((report) => report.id !== result.report.id));
      setTotal((current) => Math.max(0, current - 1));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to apply moderation action.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="adminStack">
      <section className="surface" aria-labelledby="reports-heading">
        <div className="sectionHeader">
          <div>
            <p className="eyebrow">Admin</p>
            <h1 id="reports-heading">Content reports</h1>
            <p className="muted">Open reports requiring a moderation decision.</p>
          </div>
          <div className="actionRow">
            <Link className="secondaryLink" href="/admin">
              Operations
            </Link>
            <button className="secondaryButton" type="button" onClick={() => void loadReports()} disabled={loading || !isSignedIn}>
              Refresh
            </button>
          </div>
        </div>

        <Show when="signed-out">
          <div className="notice">
            <p>Sign in with an administrator account to review reports.</p>
            <SignInButton mode="modal">
              <button type="button">Sign in</button>
            </SignInButton>
          </div>
        </Show>

        {error ? <p className="errorText">{error}</p> : null}
        {loading ? <p className="muted">Loading reports...</p> : null}
        {!loading && !error && reports.length === 0 ? <p className="muted">No open reports.</p> : null}
        {reports.length > 0 ? <p className="metaLine">{total} open report{total === 1 ? "" : "s"}</p> : null}

        <div className="adminList" role="list">
          {reports.map((report) => (
            <article className="adminListItem" key={report.id} role="listitem">
              <div>
                <h2>{report.target_type === "video" ? "Video report" : "Comment report"}</h2>
                <p className="metaLine">{formatDate(report.created_at)} · {report.target_id}</p>
                <p><strong>{report.reason}</strong></p>
                {report.details ? <p className="muted">{report.details}</p> : null}
              </div>
              <div className="adminActions" aria-label={`Actions for report ${report.id}`}>
                {ACTIONS.map((action) => (
                  <button
                    className={action === "remove" ? "dangerButton" : "secondaryButton"}
                    disabled={busyId === report.id}
                    key={action}
                    onClick={() => void applyAction(report.id, action)}
                    type="button"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
