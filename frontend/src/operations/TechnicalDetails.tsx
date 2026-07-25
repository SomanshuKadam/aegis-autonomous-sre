import type { IncidentDetail } from "./incidentPresentation";

type AuditGroup = {
  title: string;
  values: Record<string, unknown>[];
};

export function TechnicalDetails({ incident }: { incident: IncidentDetail }) {
  const groups: AuditGroup[] = [
    { title: "Lifecycle events", values: incident.timeline },
    { title: "Evidence", values: incident.evidence },
    { title: "Hypotheses", values: incident.hypotheses },
    { title: "Proposals", values: incident.proposals },
    { title: "Policy decisions", values: incident.policy_decisions },
    { title: "Approvals", values: incident.approvals },
    { title: "Executions", values: incident.executions },
    { title: "Verifications", values: incident.verifications },
    { title: "Rollbacks", values: incident.rollbacks },
    { title: "Notifications", values: incident.notifications },
  ];

  return (
    <details className="panel technical-details">
      <summary>
        <span>
          <strong>Technical details</strong>
          <small>Complete append-only audit data and raw records</small>
        </span>
        <span className="technical-chevron" aria-hidden="true">+</span>
      </summary>
      <div className="technical-groups">
        {groups.map((group) => (
          <details className="audit-group" key={group.title}>
            <summary className="audit-summary">
              <span>{group.title}</span>
              <span>{group.values.length}</span>
            </summary>
            {group.values.length === 0 ? (
              <p className="audit-empty">No records.</p>
            ) : (
              <pre className="audit-json">{JSON.stringify(group.values, null, 2)}</pre>
            )}
          </details>
        ))}
      </div>
    </details>
  );
}
