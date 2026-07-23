import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { ShopPage } from "./customer/ShopPage";
import { OverviewPage } from "./operations/OverviewPage";
import { IncidentListPage } from "./operations/IncidentListPage";
import { IncidentDetailPage } from "./operations/IncidentDetailPage";

function HomePage() {
  return <main className="home-page">
    <section className="home-hero">
      <p className="eyebrow">AEGIS · APPLICATION RELIABILITY</p>
      <h1>Make the next incident explain itself.</h1>
      <p className="lede">A local reliability console for observing application health, reviewing incident evidence, and running bounded recovery demonstrations.</p>
      <div className="hero-actions"><Link className="primary-action" to="/ops">Open operations</Link><Link className="secondary-action" to="/shop">Browse shop workload</Link></div>
    </section>
    <section className="home-cards" aria-label="Aegis capabilities">
      <article><span>01</span><h2>Observe</h2><p>Service health, workload activity, and incident state are visible in one place.</p></article>
      <article><span>02</span><h2>Decide</h2><p>Evidence and policy constrain every recovery proposal to a registered action.</p></article>
      <article><span>03</span><h2>Recover</h2><p>Catalog, inventory, and backlog scenarios have bounded verification and escalation paths.</p></article>
    </section>
  </main>;
}

export default function App() {
  return <BrowserRouter><header className="app-nav"><Link className="brand" to="/">AEGIS<span>•</span></Link><nav aria-label="Primary navigation"><NavLink to="/ops">Operations</NavLink><NavLink to="/ops/incidents">Incidents</NavLink><NavLink to="/shop">Workload shop</NavLink></nav><Link className="nav-status" to="/ops">Local stack</Link></header><Routes><Route path="/" element={<HomePage />} /><Route path="/shop" element={<ShopPage />} /><Route path="/ops" element={<OverviewPage />} /><Route path="/ops/incidents" element={<IncidentListPage />} /><Route path="/ops/incidents/:incidentId" element={<IncidentDetailPage />} /><Route path="*" element={<HomePage />} /></Routes></BrowserRouter>;
}
