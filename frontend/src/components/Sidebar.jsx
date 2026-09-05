import {
    LayoutDashboard,
    AlertTriangle,
    ShieldCheck,
    BarChart3,
    FileClock,
    Settings,
} from "lucide-react";

function Sidebar({
    incidentCount = 0,
    activePage,
    setActivePage,
}) {
    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="logo-mark">RX</div>
                <div>
                    <h2>RecoverX</h2>
                    <span>Sentinel</span>
                </div>
            </div>

            <nav className="sidebar-nav">
                <p className="nav-label">MONITORING</p>

                <button
                    className={`nav-item ${activePage === "dashboard" ? "active" : ""}`}
                    onClick={() => setActivePage("dashboard")}
                >
                    <LayoutDashboard size={18} />
                    <span>Dashboard</span>
                </button>

                <button
                    className={`nav-item ${activePage === "incidents" ? "active" : ""}`}
                    onClick={() => setActivePage("incidents")}
                >
                    <AlertTriangle size={18} />
                    <span>Incidents</span>
                    {incidentCount > 0 && (
                        <span className="nav-count">{incidentCount}</span>
                    )}
                </button>

                <p className="nav-label">RECOVERY</p>

                <button
                    className={`nav-item ${activePage === "recovery" ? "active" : ""}`}
                    onClick={() => setActivePage("recovery")}
                >
                    <ShieldCheck size={18} />
                    <span>Recovery</span>
                </button>

                <button
                    className={`nav-item ${activePage === "analytics" ? "active" : ""}`}
                    onClick={() => setActivePage("analytics")}
                >
                    <BarChart3 size={18} />
                    <span>Analytics</span>
                </button>

                <p className="nav-label">SYSTEM</p>

                <button
                    className={`nav-item ${activePage === "audit" ? "active" : ""}`}
                    onClick={() => setActivePage("audit")}
                >
                    <FileClock size={18} />
                    <span>Audit Trail</span>
                </button>

                <button
                    className={`nav-item ${activePage === "settings" ? "active" : ""}`}
                    onClick={() => setActivePage("settings")}
                >
                    <Settings size={18} />
                    <span>Settings</span>
                </button>
            </nav>

            <div className="sidebar-footer">
                <div className="merchant-status">
                    <span className="status-dot"></span>
                    <div>
                        <strong>Merchant Active</strong>
                        <small>Revenue protection enabled</small>
                    </div>
                </div>
            </div>
        </aside>
    );
}

export default Sidebar;