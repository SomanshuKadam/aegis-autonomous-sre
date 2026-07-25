import { useEffect, useMemo, useState } from "react";
import { IncidentPhaseCard } from "./IncidentPhaseCard";
import {
  buildIncidentPhases,
  getDefaultExpandedPhase,
  type IncidentDetail,
} from "./incidentPresentation";

export function IncidentPhaseList({ incident }: { incident: IncidentDetail }) {
  const phases = useMemo(() => buildIncidentPhases(incident), [incident]);
  const defaultPhase = getDefaultExpandedPhase(phases);
  const [expandedPhase, setExpandedPhase] = useState<string>(defaultPhase);

  useEffect(() => {
    setExpandedPhase(defaultPhase);
  }, [defaultPhase, incident.incident_id]);

  return (
    <section className="phase-section" aria-labelledby="incident-lifecycle-title">
      <div className="section-heading">
        <div>
          <span className="section-label">Recovery lifecycle</span>
          <h2 id="incident-lifecycle-title">What happened</h2>
          <p>Open any phase to inspect its evidence and decisions.</p>
        </div>
      </div>
      <div className="phase-list">
        {phases.map((phase) => (
          <IncidentPhaseCard
            key={phase.id}
            phase={phase}
            expanded={expandedPhase === phase.id}
            onToggle={() =>
              setExpandedPhase((current) => (current === phase.id ? "" : phase.id))
            }
          />
        ))}
      </div>
    </section>
  );
}
