import { useState } from "react";
import {
    Palette,
    Store,
    Shield,
    Server,
    Check,
    AlertCircle,
    Info,
} from "lucide-react";

function Settings({ theme, setTheme }) {
    const [autoRecovery, setAutoRecovery] = useState(true);
    const [maxRetries, setMaxRetries] = useState(3);
    const [threshold, setThreshold] = useState("1000");

    const handleThemeChange = (newTheme) => {
        if (newTheme === "system") {
            const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
                ? "dark"
                : "light";
            setTheme(systemTheme);
            localStorage.removeItem("recoverx-theme");
        } else {
            setTheme(newTheme);
            localStorage.setItem("recoverx-theme", newTheme);
        }
    };

    return (
        <div className="settings-page">
            {/* PAGE HEADER */}
            <div className="page-header">
                <div>
                    <h2>Settings</h2>
                    <p>Configure interface appearance, recovery policies, and system preferences.</p>
                </div>
            </div>

            {/* APPEARANCE */}
            <div className="settings-group">
                <div className="settings-group-header">
                    <Palette size={18} />
                    <h3>Appearance</h3>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>Interface Theme</strong>
                        <span>Select how RecoverX Sentinel looks to match your environment</span>
                    </div>

                    <div className="theme-selector">
                        <button
                            className={`theme-opt-btn ${theme === "light" ? "active" : ""}`}
                            onClick={() => handleThemeChange("light")}
                        >
                            Light
                        </button>
                        <button
                            className={`theme-opt-btn ${theme === "dark" ? "active" : ""}`}
                            onClick={() => handleThemeChange("dark")}
                        >
                            Dark
                        </button>
                        <button
                            className="theme-opt-btn"
                            onClick={() => handleThemeChange("system")}
                        >
                            System
                        </button>
                    </div>
                </div>
            </div>

            {/* MERCHANT */}
            <div className="settings-group">
                <div className="settings-group-header">
                    <Store size={18} />
                    <h3>Merchant Account</h3>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>Merchant Status</strong>
                        <span>Verified commercial account operational</span>
                    </div>
                    <span className="status-indicator-pill active">
                        <span className="status-dot"></span> Active
                    </span>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>Revenue Protection</strong>
                        <span>Sentinel AI agent monitoring real-time transaction streams</span>
                    </div>
                    <span className="status-indicator-pill active">
                        <Check size={13} /> Enabled
                    </span>
                </div>
            </div>

            {/* RECOVERY POLICY */}
            <div className="settings-group">
                <div className="settings-group-header">
                    <Shield size={18} />
                    <h3>Recovery Policy</h3>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>Automatic Recovery</strong>
                        <span>Autonomously generate alternative payment links and smart retries</span>
                    </div>
                    <button
                        className={`theme-opt-btn ${autoRecovery ? "active" : ""}`}
                        onClick={() => setAutoRecovery(!autoRecovery)}
                    >
                        {autoRecovery ? "Enabled" : "Disabled"}
                    </button>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>Maximum Retry Attempts</strong>
                        <span>Upper threshold of autonomous recovery attempts per transaction</span>
                    </div>
                    <span className="table-mono">{maxRetries} Attempts</span>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>Recovery Threshold</strong>
                        <span>Minimum transaction amount for triggering autonomous intervention</span>
                    </div>
                    <span className="table-mono">₹{Number(threshold).toLocaleString("en-IN")}.00</span>
                </div>

                <div className="config-note">
                    <Info size={13} style={{ display: "inline", marginRight: "6px", verticalAlign: "middle" }} />
                    Note: Recovery policy rules shown above reflect baseline client configuration defaults.
                </div>
            </div>

            {/* SYSTEM STATUS */}
            <div className="settings-group">
                <div className="settings-group-header">
                    <Server size={18} />
                    <h3>System Diagnostics</h3>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>API Backend</strong>
                        <span>FastAPI intelligence engine on http://127.0.0.1:8000</span>
                    </div>
                    <span className="status-indicator-pill active">
                        <span className="status-dot"></span> Online
                    </span>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>Payment Gateway</strong>
                        <span>Razorpay API test mode environment</span>
                    </div>
                    <span className="status-indicator-pill test">
                        Test Mode Active
                    </span>
                </div>

                <div className="settings-row">
                    <div className="settings-row-info">
                        <strong>PostgreSQL Database</strong>
                        <span>Local transaction ledger & audit log repository</span>
                    </div>
                    <span className="status-indicator-pill active">
                        <Check size={13} /> Connected
                    </span>
                </div>
            </div>
        </div>
    );
}

export default Settings;
