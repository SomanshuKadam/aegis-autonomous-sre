import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { ShopPage } from "./customer/ShopPage";
import { OverviewPage } from "./operations/OverviewPage";
import { IncidentListPage } from "./operations/IncidentListPage";
import { IncidentDetailPage } from "./operations/IncidentDetailPage";

function HomePage() {
  return <main className="page home-page">
    <section className="welcome-panel">
      <div><span className="section-label">Application reliability platform</span><h1>Operational clarity, from signal to recovery.</h1><p>Aegis brings service health, incident evidence, bounded remediation, and workload validation into one focused local console.</p><div className="button-row"><Link className="button primary" to="/ops">View operations</Link><Link className="button secondary" to="/shop">Open workload shop</Link></div></div>
      <div className="welcome-summary"><span className="status-dot" /> Local environment<div className="summary-value">Ready</div><p>Core services are available for demonstration.</p></div>
    </section>
    <section className="capability-grid"><article><span className="capability-number">01</span><h2>Unified visibility</h2><p>Review current health, workload activity, queue state, and incident history.</p></article><article><span className="capability-number">02</span><h2>Evidence-led decisions</h2><p>Keep every proposed action constrained by fresh evidence and explicit policy.</p></article><article><span className="capability-number">03</span><h2>Bounded recovery</h2><p>Demonstrate safe recovery for catalog, inventory, and order backlog scenarios.</p></article></section>
  </main>;
}

export default function App() {
  return <BrowserRouter><div className="app-shell"><header className="topbar"><Link className="brand" to="/"><span className="brand-mark">A</span><span><b>Aegis</b><small>Reliability Platform</small></span></Link><nav aria-label="Primary navigation"><NavLink to="/ops">Overview</NavLink><NavLink to="/ops/incidents">Incidents</NavLink><NavLink to="/shop">Workload Shop</NavLink></nav><div className="environment-badge"><span /> Local</div></header><Routes><Route path="/" element={<HomePage />} /><Route path="/shop" element={<ShopPage />} /><Route path="/ops" element={<OverviewPage />} /><Route path="/ops/incidents" element={<IncidentListPage />} /><Route path="/ops/incidents/:incidentId" element={<IncidentDetailPage />} /><Route path="*" element={<HomePage />} /></Routes></div></BrowserRouter>;
}
