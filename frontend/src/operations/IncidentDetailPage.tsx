import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { IncidentPhaseList } from "./IncidentPhaseList";
import {
  buildIncidentPhases,
  type IncidentDetail,
} from "./incidentPresentation";
import { SignozLinks } from "./SignozLinks";
import { TechnicalDetails } from "./TechnicalDetails";

function outcomeCopy(incident: IncidentDetail, latestSummary: string) {
  if (incident.state === "RESOLVED") {
    return {
      label: "Recovery verified",
      title: "The incident is resolved",
      detail: latestSummary,
      tone: "success",
    };
  }
  if (incident.state === "APPROVAL_REQUIRED") {
    return {
      label: "Operator action",
      title: "Approval is required",
      detail: latestSummary,
      tone: "attention",
    };
  }
  if (incident.state === "ESCALATED") {
    return {
      label: "Safely stopped",
      title: "The incident was escalated",
      detail: latestSummary,
      tone: "warning",
    };
  }
  if (incident.state === "BLOCKED") {
    return {
      label: "Safely stopped",
      title: "Remediation is blocked",
      detail: latestSummary,
      tone: "warning",
    };
  }
  if (incident.state === "FAILED") {
    return {
      label: "Attention required",
      title: "Recovery did not complete",
      detail: latestSummary,
      tone: "danger",
    };
  }
  return {
    label: "In progress",
    title: "Aegis is investigating",
    detail: latestSummary,
    tone: "neutral",
  };
}

export function IncidentDetailPage() {
  const { incidentId = "" } = useParams();
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<IncidentDetail>(`/operations/incidents/${incidentId}`)
      .then(setIncident)
      .catch((reason: Error) => setError(reason.message));
  }, [incidentId]);

  const phases = useMemo(() => (incident ? buildIncidentPhases(incident) : []), [incident]);

  if (error) {
    return (
      <main className="page">
        <div className="notice error">{error}</div>
      </main>
    );
  }
  if (!incident) {
    return (
      <main className="page">
        <div className="empty-state">Loading incident record...</div>
      </main>
    );
  }

  const latestPhase =
    [...phases].reverse().find((phase) => phase.status !== "not-reached") ?? phases[0];
  const outcome = outcomeCopy(incident, latestPhase?.summary ?? "Incident record loaded");

  return (
    <main className="page incident-detail-page">
      <Link className="back-link" to="/ops/incidents">
        <span aria-hidden="true">←</span> Back to incidents
      </Link>
      <div className="page-heading incident-heading">
        <div>
          <span className="section-label">Incident detail</span>
          <h1>{incident.category.replaceAll("_", " ")}</h1>
          <p className="mono">{incident.incident_id}</p>
        </div>
        <span className="state-pill large">{incident.state.replaceAll("_", " ")}</span>
      </div>

      <section className="detail-layout">
        <div className="detail-main">
          <section className={`operator-outcome tone-${outcome.tone}`}>
            <span className="outcome-label">{outcome.label}</span>
            <h2>{outcome.title}</h2>
            <p>{outcome.detail}</p>
          </section>
          <IncidentPhaseList incident={incident} />
          <TechnicalDetails incident={incident} />
        </div>

        <aside>
          <section className="panel detail-card incident-summary">
            <h2>Incident summary</h2>
            <dl>
              <div>
                <dt>Category</dt>
                <dd>{incident.category.replaceAll("_", " ")}</dd>
              </div>
              <div>
                <dt>Current state</dt>
                <dd>{incident.state.replaceAll("_", " ")}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>
                  {incident.created_at
                    ? new Date(incident.created_at).toLocaleString()
                    : "Not recorded"}
                </dd>
              </div>
              <div>
                <dt>Trace ID</dt>
                <dd className="mono identifier-wrap">{incident.trace_id ?? "Not recorded"}</dd>
              </div>
            </dl>
          </section>
          <SignozLinks links={incident.signoz} />
        </aside>
      </section>
    </main>
  );
}
