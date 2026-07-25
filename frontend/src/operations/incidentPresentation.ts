export type TimelineEvent = {
  event_id: string;
  stage: string;
  type: string;
  outcome: string;
  summary: string;
  occurred_at: string;
};

export type SignozLink = {
  url: string | null;
  reason: string | null;
};

export type IncidentDetail = {
  incident_id: string;
  category: string;
  state: string;
  created_at?: string;
  updated_at?: string;
  source?: string;
  fingerprint?: string;
  trace_id?: string;
  alert_count?: number;
  escalation_reason?: string;
  target?: Record<string, unknown>;
  timeline: TimelineEvent[];
  evidence: Record<string, unknown>[];
  hypotheses: Record<string, unknown>[];
  proposals: Record<string, unknown>[];
  policy_decisions: Record<string, unknown>[];
  approvals: Record<string, unknown>[];
  executions: Record<string, unknown>[];
  verifications: Record<string, unknown>[];
  rollbacks: Record<string, unknown>[];
  notifications: Record<string, unknown>[];
  agent_runs: Record<string, unknown>[];
  signoz: Record<string, SignozLink>;
};

export type PhaseStatus =
  | "complete"
  | "current"
  | "warning"
  | "failed"
  | "pending"
  | "not-reached";

export type PhaseViewModel = {
  id: "detected" | "investigated" | "decision" | "remediation" | "verification";
  title: string;
  status: PhaseStatus;
  summary: string;
  occurredAt: string | null;
  records: Array<{ title: string; values: Record<string, unknown> }>;
};

const ACTIVE_INVESTIGATION_STATES = new Set([
  "DETECTED",
  "VALIDATING",
  "ENRICHING",
  "INVESTIGATING",
]);

const TERMINAL_WARNING_STATES = new Set(["BLOCKED", "ESCALATED", "ROLLED_BACK"]);
const TERMINAL_FAILURE_STATES = new Set(["FAILED"]);

function latest(values: Record<string, unknown>[]) {
  return values.at(-1);
}

function timestampOf(value: Record<string, unknown> | undefined): string | null {
  if (!value) return null;
  for (const key of ["occurred_at", "decided_at", "expired_at", "created_at", "updated_at"]) {
    if (typeof value[key] === "string") return value[key];
  }
  return null;
}

function recordTitle(prefix: string, value: Record<string, unknown>, index: number) {
  const type = typeof value.type === "string" ? formatLabel(value.type) : "";
  const attempt = typeof value.attempt === "number" ? ` attempt ${value.attempt}` : "";
  return type ? `${prefix}: ${type}${attempt}` : `${prefix}${attempt || ` ${index + 1}`}`;
}

function incidentIdentity(incident: IncidentDetail): Record<string, unknown> {
  return {
    category: incident.category,
    state: incident.state,
    source: incident.source,
    target: incident.target,
    alert_count: incident.alert_count,
    trace_id: incident.trace_id,
    incident_id: incident.incident_id,
    created_at: incident.created_at,
  };
}

function investigationRecords(incident: IncidentDetail) {
  const records: PhaseViewModel["records"] = [];
  const agentRun = latest(incident.agent_runs);
  if (agentRun) records.push({ title: "Codex diagnosis", values: agentRun });
  incident.evidence.forEach((value, index) => {
    records.push({ title: recordTitle("Evidence", value, index), values: value });
  });
  incident.hypotheses.forEach((value, index) => {
    records.push({ title: recordTitle("Hypothesis", value, index), values: value });
  });
  return records;
}

function decisionRecords(incident: IncidentDetail) {
  return [
    ...incident.proposals.map((values, index) => ({
      title: recordTitle("Bounded proposal", values, index),
      values,
    })),
    ...incident.policy_decisions.map((values, index) => ({
      title: recordTitle("Policy decision", values, index),
      values,
    })),
    ...incident.approvals.map((values, index) => ({
      title: recordTitle("Approval", values, index),
      values,
    })),
  ];
}

function remediationRecords(incident: IncidentDetail) {
  return [
    ...incident.executions.map((values, index) => ({
      title: recordTitle("Execution", values, index),
      values,
    })),
    ...incident.rollbacks.map((values, index) => ({
      title: recordTitle("Rollback", values, index),
      values,
    })),
  ];
}

function verificationRecords(incident: IncidentDetail) {
  const records = incident.verifications.map((values, index) => ({
    title: recordTitle("Verification", values, index),
    values,
  }));
  const finalNotification = latest(incident.notifications);
  if (finalNotification) {
    records.push({ title: "Final notification", values: finalNotification });
  }
  return records;
}

function investigatedStatus(incident: IncidentDetail): PhaseStatus {
  if (incident.agent_runs.length || incident.hypotheses.length) return "complete";
  if (ACTIVE_INVESTIGATION_STATES.has(incident.state)) return "current";
  return "not-reached";
}

function decisionStatus(incident: IncidentDetail): PhaseStatus {
  const approval = latest(incident.approvals);
  const approvalState = String(approval?.state ?? "");
  if (incident.state === "APPROVAL_REQUIRED" || approvalState === "PENDING") return "current";
  if (approvalState === "EXPIRED" || approvalState === "REJECTED") return "warning";
  if (approvalState === "APPROVED") return "complete";
  const policyOutcome = String(latest(incident.policy_decisions)?.outcome ?? "");
  if (policyOutcome === "BLOCKED") return "warning";
  if (policyOutcome) return "complete";
  return incident.proposals.length ? "pending" : "not-reached";
}

function remediationStatus(incident: IncidentDetail): PhaseStatus {
  const executionState = String(latest(incident.executions)?.state ?? "");
  if (executionState === "FAILED") return "failed";
  if (["SUCCEEDED", "NOOP"].includes(executionState)) return "complete";
  if (executionState || ["EXECUTING", "REMEDIATING"].includes(incident.state)) return "current";
  if (TERMINAL_WARNING_STATES.has(incident.state)) return "warning";
  return "not-reached";
}

function verificationStatus(incident: IncidentDetail): PhaseStatus {
  const outcome = String(latest(incident.verifications)?.outcome ?? "");
  if (outcome === "VERIFIED" || incident.state === "RESOLVED") return "complete";
  if (outcome && outcome !== "PENDING") return "failed";
  if (TERMINAL_FAILURE_STATES.has(incident.state)) return "failed";
  if (TERMINAL_WARNING_STATES.has(incident.state)) return "warning";
  if (["VERIFYING", "VERIFICATION"].includes(incident.state)) return "current";
  return "not-reached";
}

function investigatedSummary(incident: IncidentDetail) {
  const run = latest(incident.agent_runs);
  const hypothesis = latest(incident.hypotheses);
  return String(
    run?.diagnosis ??
      hypothesis?.statement ??
      (incident.evidence.length
        ? `${incident.evidence.length} evidence record${incident.evidence.length === 1 ? "" : "s"} collected`
        : "Investigation has not started"),
  );
}

function decisionSummary(incident: IncidentDetail) {
  const approval = latest(incident.approvals);
  const state = String(approval?.state ?? "");
  if (state === "PENDING") return "Operator approval is required before remediation";
  if (state === "APPROVED") return "The bounded remediation was approved";
  if (state === "EXPIRED") return "Approval expired without changing the system";
  if (state === "REJECTED") return "The proposed remediation was rejected";
  const policy = latest(incident.policy_decisions);
  return String(policy?.reason ?? policy?.outcome ?? "No policy decision has been recorded");
}

function remediationSummary(incident: IncidentDetail) {
  const execution = latest(incident.executions);
  if (execution) {
    const action = latest(incident.proposals)?.action_key;
    return `${String(action ?? "Bounded action")} ${String(execution.state ?? "completed").toLowerCase()}`;
  }
  if (TERMINAL_WARNING_STATES.has(incident.state)) {
    return "Aegis stopped safely without executing a system change";
  }
  return "No remediation has been executed";
}

function verificationSummary(incident: IncidentDetail) {
  const verification = latest(incident.verifications);
  if (verification) {
    if (verification.outcome === "VERIFIED") return "Recovery was verified with fresh business behavior";
    return `Verification finished with ${String(verification.outcome).toLowerCase()}`;
  }
  if (incident.state === "ESCALATED") return "Incident was escalated without a system change";
  if (incident.state === "BLOCKED") return "Aegis stopped because safe remediation could not proceed";
  return "Verification has not been reached";
}

export function buildIncidentPhases(incident: IncidentDetail): PhaseViewModel[] {
  const accepted = incident.timeline.find(
    (event) => event.stage === "DETECTED" && event.outcome === "accepted",
  );
  const agentRun = latest(incident.agent_runs);
  const hypothesis = latest(incident.hypotheses);
  const approval = latest(incident.approvals);
  const policy = latest(incident.policy_decisions);
  const execution = latest(incident.executions);
  const rollback = latest(incident.rollbacks);
  const verification = latest(incident.verifications);

  return [
    {
      id: "detected",
      title: "Detected",
      status: "complete",
      summary: accepted?.summary ?? "Alert accepted and incident created",
      occurredAt: accepted?.occurred_at ?? incident.created_at ?? null,
      records: [{ title: "Incident signal", values: incidentIdentity(incident) }],
    },
    {
      id: "investigated",
      title: "Investigated",
      status: investigatedStatus(incident),
      summary: investigatedSummary(incident),
      occurredAt: timestampOf(agentRun ?? hypothesis ?? latest(incident.evidence)),
      records: investigationRecords(incident),
    },
    {
      id: "decision",
      title: "Decision",
      status: decisionStatus(incident),
      summary: decisionSummary(incident),
      occurredAt: timestampOf(approval ?? policy ?? latest(incident.proposals)),
      records: decisionRecords(incident),
    },
    {
      id: "remediation",
      title: "Remediation",
      status: remediationStatus(incident),
      summary: remediationSummary(incident),
      occurredAt: timestampOf(rollback ?? execution),
      records: remediationRecords(incident),
    },
    {
      id: "verification",
      title: "Verification",
      status: verificationStatus(incident),
      summary: verificationSummary(incident),
      occurredAt: timestampOf(verification ?? latest(incident.notifications)),
      records: verificationRecords(incident),
    },
  ];
}

export function getDefaultExpandedPhase(phases: PhaseViewModel[]) {
  return (
    [...phases]
      .reverse()
      .find((phase) => ["current", "warning", "failed", "complete"].includes(phase.status))?.id ??
    phases[0]?.id ??
    ""
  );
}

export function formatLabel(value: string) {
  const words = value.replaceAll("_", " ").replaceAll("-", " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Value";
}

export function formatTimestamp(value: unknown) {
  if (typeof value !== "string" || !value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not recorded";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.map(formatValue).join("; ") : "None";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}
