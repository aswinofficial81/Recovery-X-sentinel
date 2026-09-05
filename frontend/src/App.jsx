import { useEffect, useState } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  BrainCircuit,
  IndianRupee,
} from "lucide-react";

import Sidebar from "./components/Sidebar";
import KPICard from "./components/KPICard";
import ThemeToggle from "./components/ThemeToggle";
import Incidents from "./pages/Incidents";
import AuditTrail from "./pages/AuditTrail";
import Recovery from "./pages/Recovery";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";

import {
  getDashboard,
  getRecoveryMetrics,
  getRevenueLeaks,
} from "./services/api";

function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("recoverx-theme") || "dark";
  });

  const [dashboardData, setDashboardData] = useState(null);
  const [recoveryMetrics, setRecoveryMetrics] = useState(null);
  const [revenueLeaks, setRevenueLeaks] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activePage, setActivePage] = useState("dashboard");

  // Synchronize theme with document
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Load dashboard data from backend APIs
  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        const dashboard = await getDashboard();
        const recovery = await getRecoveryMetrics();
        const leaks = await getRevenueLeaks();

        setDashboardData(dashboard);
        setRecoveryMetrics(recovery);
        setRevenueLeaks(leaks.leaks || []);
      } catch (err) {
        console.error("Dashboard API error:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const recoveryRateVal = Number(recoveryMetrics?.recovery_rate || 0);
  const circumference = 2 * Math.PI * 50;
  const strokeDashoffset = circumference * (1 - Math.min(Math.max(recoveryRateVal, 0), 100) / 100);

  return (
    <div className="app-layout">
      <Sidebar
        incidentCount={dashboardData?.open_leaks ?? 0}
        activePage={activePage}
        setActivePage={setActivePage}
      />

      <div className="main-area">
        {/* TOP BAR */}
        <header className="topbar">
          <div>
            <h1>Revenue Intelligence</h1>
            <p>AI-powered revenue monitoring and recovery</p>
          </div>

          <div className="topbar-right">
            <div className="system-status">
              <span className="status-dot"></span>
              System Online
            </div>

            <ThemeToggle theme={theme} setTheme={setTheme} />
          </div>
        </header>

        {/* MAIN ROUTE CONTENT */}
        <main className="dashboard">
          {error && (
            <div className="api-error">
              Unable to load dashboard data: {error}
            </div>
          )}

          {activePage === "dashboard" && (
            <>
              {/* PAGE HEADER */}
              <div className="page-header">
                <div>
                  <h2>Revenue Overview</h2>
                  <p>Monitor revenue risk and autonomous recovery activity.</p>
                </div>

                <div className="live-indicator">
                  <span></span>
                  LIVE
                </div>
              </div>

              {/* TOP 4 KPI CARDS */}
              <section className="kpi-grid">
                <KPICard
                  title="Revenue at Risk"
                  value={
                    loading
                      ? "..."
                      : `₹${(
                          Number(dashboardData?.total_revenue_at_risk || 0) / 1000000
                        ).toFixed(2)}M`
                  }
                  subtitle="Across detected incidents"
                  icon={IndianRupee}
                  variant="danger"
                />

                <KPICard
                  title="Active Incidents"
                  value={
                    loading
                      ? "..."
                      : dashboardData?.open_leaks ?? 0
                  }
                  subtitle="Requires attention"
                  icon={AlertTriangle}
                  variant="warning"
                />

                <KPICard
                  title="Expected Recovery"
                  value={
                    loading
                      ? "..."
                      : `₹${(
                          Number(recoveryMetrics?.total_expected_recovery || 0) / 1000
                        ).toFixed(2)}K`
                  }
                  subtitle="Model prediction"
                  icon={BrainCircuit}
                  variant="primary"
                />

                <KPICard
                  title="Actual Recovered"
                  value={
                    loading
                      ? "..."
                      : `₹${(
                          Number(recoveryMetrics?.total_actual_recovery || 0) / 1000
                        ).toFixed(2)}K`
                  }
                  subtitle="Verified revenue"
                  icon={ShieldAlert}
                  variant="success"
                />
              </section>

              {/* MAIN DASHBOARD PANELS */}
              <section className="dashboard-grid">
                {/* REVENUE RISK MONITOR */}
                <div className="panel large-panel">
                  <div className="panel-header">
                    <div>
                      <h3>Revenue Risk Monitor</h3>
                      <p>Detected revenue deterioration by incident type</p>
                    </div>
                  </div>

                  <div className="risk-chart">
                    {revenueLeaks.length === 0 ? (
                      <div className="page-state empty">
                        <span>No revenue incidents detected.</span>
                      </div>
                    ) : (
                      revenueLeaks.map((leak) => {
                        const maxRisk = Math.max(
                          ...revenueLeaks.map(
                            (item) => Number(item.revenue_impact) || 0
                          )
                        );

                        const percentage =
                          maxRisk > 0
                            ? (Number(leak.revenue_impact) / maxRisk) * 100
                            : 0;

                        return (
                          <div className="risk-item" key={leak.id}>
                            <div className="risk-info">
                              <div>
                                <strong>
                                  {formatIncidentName(leak.leak_type)}
                                </strong>
                                <span>{leak.description}</span>
                              </div>

                              <strong className="risk-amount">
                                ₹{formatRisk(leak.revenue_impact)}
                              </strong>
                            </div>

                            <div className="risk-bar-background">
                              <div
                                className="risk-bar"
                                style={{ width: `${percentage}%` }}
                              />
                            </div>

                            <div className="risk-meta">
                              <span>
                                Confidence{" "}
                                {(Number(leak.confidence) * 100).toFixed(0)}%
                              </span>

                              <span className="open-label">
                                {leak.status}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* RECOVERY STATUS (Apple Circular Progress Ring) */}
                <div className="panel">
                  <div className="panel-header">
                    <div>
                      <h3>Recovery Rate</h3>
                      <p>Current autonomous recovery efficiency</p>
                    </div>
                  </div>

                  <div className="recovery-ring-container">
                    <div className="recovery-ring-wrapper">
                      <svg className="recovery-ring-svg" viewBox="0 0 120 120">
                        <circle
                          className="recovery-ring-bg"
                          cx="60"
                          cy="60"
                          r="50"
                          strokeWidth="8"
                          fill="none"
                        />
                        <circle
                          className="recovery-ring-fill"
                          cx="60"
                          cy="60"
                          r="50"
                          strokeWidth="8"
                          fill="none"
                          strokeDasharray={circumference}
                          strokeDashoffset={strokeDashoffset}
                        />
                      </svg>

                      <div className="recovery-ring-center">
                        <strong className="recovery-ring-percent">
                          {loading ? "..." : `${recoveryRateVal.toFixed(2)}%`}
                        </strong>
                        <span className="recovery-ring-label">Recovery Rate</span>
                      </div>
                    </div>

                    <div className="recovery-ring-footer">
                      <span>Actual / Expected</span>
                    </div>
                  </div>
                </div>
              </section>
            </>
          )}

          {activePage === "incidents" && <Incidents />}
          {activePage === "recovery" && <Recovery />}
          {activePage === "analytics" && <Analytics />}
          {activePage === "audit" && <AuditTrail />}
          {activePage === "settings" && (
            <Settings theme={theme} setTheme={setTheme} />
          )}
        </main>
      </div>
    </div>
  );
}

/* =========================
   HELPERS
========================= */

function formatIncidentName(type) {
  if (!type) {
    return "Unknown Incident";
  }

  return type
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatRisk(value) {
  const amount = Number(value) || 0;

  if (amount >= 1000000) {
    return `${(amount / 1000000).toFixed(2)}M`;
  }

  if (amount >= 1000) {
    return `${(amount / 1000).toFixed(2)}K`;
  }

  return amount.toFixed(2);
}

export default App;