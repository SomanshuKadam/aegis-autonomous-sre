import { EvidenceFields } from "./EvidenceFields";
import { formatLabel, formatTimestamp, type PhaseViewModel } from "./incidentPresentation";

type IncidentPhaseCardProps = {
  phase: PhaseViewModel;
  expanded: boolean;
  onToggle: () => void;
};

export function IncidentPhaseCard({ phase, expanded, onToggle }: IncidentPhaseCardProps) {
  const triggerId = `${phase.id}-trigger`;
  const contentId = `${phase.id}-content`;

  return (
    <article className={`phase-card status-${phase.status}`}>
      <button
        className="phase-trigger"
        id={triggerId}
        type="button"
        aria-expanded={expanded}
        aria-controls={contentId}
        onClick={onToggle}
      >
        <span className="phase-status" aria-hidden="true" />
        <span className="phase-heading">
          <span className="phase-title-row">
            <strong>{phase.title}</strong>
            <span className="phase-status-label">{formatLabel(phase.status)}</span>
          </span>
          <span className="phase-summary">{phase.summary}</span>
          <span className="phase-time">{formatTimestamp(phase.occurredAt)}</span>
        </span>
        <span className="phase-chevron" aria-hidden="true">
          {expanded ? "−" : "+"}
        </span>
      </button>
      <div
        className="phase-content"
        id={contentId}
        role="region"
        aria-labelledby={triggerId}
        hidden={!expanded}
      >
        {phase.records.length === 0 ? (
          <p className="phase-empty">This phase has not been reached.</p>
        ) : (
          phase.records.map((record, index) => (
            <section className="phase-record" key={`${phase.id}-${record.title}-${index}`}>
              <h3>{record.title}</h3>
              <EvidenceFields values={record.values} />
            </section>
          ))
        )}
      </div>
    </article>
  );
}
