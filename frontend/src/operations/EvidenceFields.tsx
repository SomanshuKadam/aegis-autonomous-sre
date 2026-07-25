import { formatLabel, formatTimestamp, formatValue } from "./incidentPresentation";

const PRIORITY_KEYS = [
  "diagnosis",
  "statement",
  "plausible_solution",
  "observation",
  "capacity",
  "saturated",
  "p95_latency_ms",
  "action_key",
  "outcome",
  "state",
  "expires_at",
  "trace_id",
  "source_trace_id",
];

const TIMESTAMP_KEYS = new Set([
  "occurred_at",
  "created_at",
  "updated_at",
  "decided_at",
  "expired_at",
  "expires_at",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isIdentifier(key: string) {
  return (
    key.endsWith("_id") ||
    key.endsWith("_hash") ||
    key.endsWith("_key") ||
    key === "fingerprint" ||
    key === "trace_id"
  );
}

function orderedEntries(values: Record<string, unknown>) {
  const entries = Object.entries(values).filter(([, value]) => value !== undefined);
  return entries.sort(([left], [right]) => {
    const leftIndex = PRIORITY_KEYS.indexOf(left);
    const rightIndex = PRIORITY_KEYS.indexOf(right);
    if (leftIndex === -1 && rightIndex === -1) return 0;
    if (leftIndex === -1) return 1;
    if (rightIndex === -1) return -1;
    return leftIndex - rightIndex;
  });
}

function FieldValue({ name, value }: { name: string; value: unknown }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="field-empty">None</span>;
    return (
      <ul className="field-list">
        {value.map((item, index) => (
          <li key={`${name}-${index}`}>
            {isRecord(item) ? <EvidenceFields values={item} nested /> : formatValue(item)}
          </li>
        ))}
      </ul>
    );
  }

  if (isRecord(value)) {
    if (Object.keys(value).length === 0) return <span className="field-empty">None</span>;
    return <EvidenceFields values={value} nested />;
  }

  if (TIMESTAMP_KEYS.has(name)) return <span>{formatTimestamp(value)}</span>;
  if (typeof value === "string" && /^https?:\/\//.test(value)) {
    return (
      <a href={value} target="_blank" rel="noopener noreferrer">
        Open link <span aria-hidden="true">↗</span>
      </a>
    );
  }

  return <span className={isIdentifier(name) ? "mono field-identifier" : undefined}>{formatValue(value)}</span>;
}

export function EvidenceFields({
  values,
  nested = false,
}: {
  values: Record<string, unknown>;
  nested?: boolean;
}) {
  const entries = orderedEntries(values);
  if (entries.length === 0) return <p className="muted">No values recorded.</p>;

  return (
    <dl className={nested ? "evidence-fields nested" : "evidence-fields"}>
      {entries.map(([name, value]) => (
        <div className="evidence-field" key={name}>
          <dt>{formatLabel(name)}</dt>
          <dd>
            <FieldValue name={name} value={value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
