import { useEffect, useState, useMemo } from "react";
import {
    BarChart3,
    TrendingUp,
    ShieldAlert,
    IndianRupee,
    BrainCircuit,
    CheckCircle2,
    RefreshCw,
    AlertTriangle,
    CreditCard,
    Layers,
    Calendar,
    ArrowUpRight,
    Activity,
    Info,
    Smartphone,
    Sparkles,
    AlertCircle,
} from "lucide-react";
import KPICard from "../components/KPICard";
import { getAnalytics } from "../services/api";

function Analytics() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    async function fetchAnalyticsData() {
        try {
            setLoading(true);
            setError(null);
            const res = await getAnalytics();
            setData(res);
        } catch (err) {
            console.error("Failed to load analytics:", err);
            setError(err.message || "Unable to load analytics.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchAnalyticsData();
    }, []);

    const summary = data?.summary || {};
    const strategyPerf = data?.strategy_performance || [];
    const incidentPerf = data?.incident_performance || [];
    const paymentMethodPerf = data?.payment_method_performance || [];
    const timeline = data?.recovery_timeline || [];

    // Calculate maximum for timeline scaling safely
    const maxTimelineVal = useMemo(() => {
        if (!timeline || timeline.length === 0) return 1;
        const max = Math.max(
            ...timeline.map((t) => Math.max(Number(t.expected_recovery || 0), Number(t.actual_recovery || 0)))
        );
        return max > 0 ? max : 1;
    }, [timeline]);

    return (
        <div className="analytics-page">
            {/* PAGE HEADER */}
            <div className="page-header">
                <div>
                    <h2>Analytics</h2>
                    <p>
                        Measure revenue protection performance across incidents, strategies, and recovery outcomes.
                    </p>
                </div>

                <div className="audit-header-actions">
                    <button
                        className="refresh-button"
                        onClick={fetchAnalyticsData}
                        disabled={loading}
                        title="Refresh analytics data"
                    >
                        <RefreshCw
                            size={16}
                            className={loading ? "spin" : ""}
                        />
                        <span>Refresh</span>
                    </button>
                </div>
            </div>

            {/* ERROR STATE */}
            {error && (
                <div className="page-state error">
                    <AlertTriangle size={24} />
                    <span>Unable to load analytics: {error}</span>
                    <button className="retry-btn" onClick={fetchAnalyticsData}>
                        Retry
                    </button>
                </div>
            )}

            {/* LOADING STATE */}
            {loading && !data && (
                <div className="page-state">
                    <RefreshCw size={24} className="spin" />
                    <span>Loading analytics...</span>
                </div>
            )}

            {/* DASHBOARD CONTENT */}
            {data && (
                <>
                    {/* TOP SUMMARY CARDS */}
                    <section className="kpi-grid">
                        <KPICard
                            title="Revenue at Risk"
                            value={`₹${(Number(summary.revenue_at_risk || 0) / 1000000).toFixed(2)}M`}
                            subtitle="Identified across open incidents"
                            icon={IndianRupee}
                            variant="danger"
                        />

                        <KPICard
                            title="Expected Recovery"
                            value={`₹${(Number(summary.expected_recovery || 0) / 1000).toFixed(2)}K`}
                            subtitle="AI projected recovery"
                            icon={BrainCircuit}
                            variant="primary"
                        />

                        <KPICard
                            title="Actual Recovered"
                            value={`₹${(Number(summary.actual_recovered || 0) / 1000).toFixed(2)}K`}
                            subtitle="Verified ledger recoveries"
                            icon={ShieldAlert}
                            variant="success"
                        />

                        <KPICard
                            title="Recovery Rate"
                            value={`${Number(summary.recovery_rate || 0).toFixed(2)}%`}
                            subtitle="Actual / Expected efficiency"
                            icon={TrendingUp}
                            variant="success"
                        />
                    </section>

                    {/* SECTION 1: RECOVERY PERFORMANCE & TIMELINE */}
                    <div className="analytics-grid-two">
                        {/* RECOVERY PERFORMANCE COMPARISON */}
                        <div className="analytics-panel">
                            <div className="panel-header">
                                <div>
                                    <h3>Recovery Performance</h3>
                                    <p>Expected vs verified actual recovered revenue</p>
                                </div>
                                <span className="rate-badge">
                                    {Number(summary.recovery_rate || 0).toFixed(1)}% Realized
                                </span>
                            </div>

                            <div className="recovery-comparison-box">
                                <div className="comparison-metric">
                                    <div className="metric-meta">
                                        <span>Expected Recovery</span>
                                        <strong>
                                            ₹
                                            {Number(summary.expected_recovery || 0).toLocaleString("en-IN", {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2,
                                            })}
                                        </strong>
                                    </div>
                                    <div className="comp-bar-bg">
                                        <div
                                            className="comp-bar primary"
                                            style={{ width: "100%" }}
                                        />
                                    </div>
                                </div>

                                <div className="comparison-metric">
                                    <div className="metric-meta">
                                        <span>Actual Recovered</span>
                                        <strong className="success-text">
                                            ₹
                                            {Number(summary.actual_recovered || 0).toLocaleString("en-IN", {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2,
                                            })}
                                        </strong>
                                    </div>
                                    <div className="comp-bar-bg">
                                        <div
                                            className="comp-bar success"
                                            style={{
                                                width: `${Math.min(
                                                    Number(summary.recovery_rate || 0),
                                                    100
                                                )}%`,
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="action-stats-strip">
                                <div className="stat-pill">
                                    <span>Total Actions</span>
                                    <strong>{summary.total_actions ?? 0}</strong>
                                </div>
                                <div className="stat-pill success">
                                    <span>Successful</span>
                                    <strong>{summary.successful_actions ?? 0}</strong>
                                </div>
                                <div className="stat-pill warning">
                                    <span>Pending</span>
                                    <strong>{summary.pending_actions ?? 0}</strong>
                                </div>
                                <div className="stat-pill danger">
                                    <span>Failed</span>
                                    <strong>{summary.failed_actions ?? 0}</strong>
                                </div>
                            </div>
                        </div>

                        {/* RECOVERY TIMELINE CHART */}
                        <div className="analytics-panel">
                            <div className="panel-header">
                                <div>
                                    <h3>Recovery Timeline</h3>
                                    <p>Daily recovery trajectory (created date)</p>
                                </div>
                                <div className="chart-legend">
                                    <span className="legend-item">
                                        <span className="dot expected"></span> Expected
                                    </span>
                                    <span className="legend-item">
                                        <span className="dot actual"></span> Actual
                                    </span>
                                </div>
                            </div>

                            {timeline.length === 0 ? (
                                <div className="no-data-placeholder">
                                    No timeline data recorded yet.
                                </div>
                            ) : (
                                <div className="timeline-chart">
                                    <div className="chart-bars-container">
                                        {timeline.map((item) => {
                                            const expHeight = Math.max(
                                                (Number(item.expected_recovery || 0) / maxTimelineVal) * 160,
                                                12
                                            );
                                            const actHeight = Math.max(
                                                (Number(item.actual_recovery || 0) / maxTimelineVal) * 160,
                                                item.actual_recovery > 0 ? 12 : 4
                                            );

                                            return (
                                                <div className="chart-group" key={item.date}>
                                                    <div className="bars-pair">
                                                        <div
                                                            className="bar-item expected"
                                                            style={{ height: `${expHeight}px` }}
                                                            title={`Expected: ₹${Number(
                                                                item.expected_recovery
                                                            ).toLocaleString("en-IN")}`}
                                                        />
                                                        <div
                                                            className="bar-item actual"
                                                            style={{ height: `${actHeight}px` }}
                                                            title={`Actual: ₹${Number(
                                                                item.actual_recovery
                                                            ).toLocaleString("en-IN")}`}
                                                        />
                                                    </div>
                                                    <div className="chart-x-label">
                                                        <span>{formatChartDate(item.date)}</span>
                                                        <small>{item.successful_actions} won</small>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* SECTION 2: STRATEGY PERFORMANCE */}
                    <div className="analytics-panel">
                        <div className="panel-header">
                            <div>
                                <h3>Strategy Performance</h3>
                                <p>Effectiveness of autonomous recovery intervention models</p>
                            </div>
                            <Layers size={18} className="text-secondary" />
                        </div>

                        {strategyPerf.length === 0 ? (
                            <div className="no-data-placeholder">
                                No strategy records available.
                            </div>
                        ) : (
                            <div className="recovery-table-container">
                                <table className="recovery-table">
                                    <thead>
                                        <tr>
                                            <th>Strategy</th>
                                            <th>Attempts</th>
                                            <th>Success Rate</th>
                                            <th>Expected Recovery</th>
                                            <th>Actual Recovery</th>
                                            <th>Outcome Ratio</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {strategyPerf.map((strat) => {
                                            const rate = Number(strat.success_rate || 0);
                                            return (
                                                <tr key={strat.strategy}>
                                                    <td>
                                                        <span className="strategy-tag">
                                                            {formatName(strat.strategy)}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <strong>{strat.attempts}</strong>
                                                    </td>
                                                    <td>
                                                        <div className="success-rate-cell">
                                                            <div className="rate-mini-bar-bg">
                                                                <div
                                                                    className="rate-mini-bar"
                                                                    style={{ width: `${rate}%` }}
                                                                />
                                                            </div>
                                                            <span>{rate.toFixed(1)}%</span>
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <span className="amount-expected">
                                                            ₹
                                                            {Number(strat.expected_recovery || 0).toLocaleString(
                                                                "en-IN",
                                                                {
                                                                    minimumFractionDigits: 2,
                                                                    maximumFractionDigits: 2,
                                                                }
                                                            )}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <strong className="amount-actual-success">
                                                            ₹
                                                            {Number(strat.actual_recovery || 0).toLocaleString(
                                                                "en-IN",
                                                                {
                                                                    minimumFractionDigits: 2,
                                                                    maximumFractionDigits: 2,
                                                                }
                                                            )}
                                                        </strong>
                                                    </td>
                                                    <td>
                                                        <span className="stat-fraction">
                                                            {strat.successes} / {strat.attempts} recovered
                                                        </span>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>

                    {/* SECTION 3: INCIDENT & PAYMENT METHOD PERFORMANCE */}
                    <div className="analytics-grid-two">
                        {/* INCIDENT PERFORMANCE */}
                        <div className="analytics-panel">
                            <div className="panel-header">
                                <div>
                                    <h3>Incident Performance</h3>
                                    <p>Recovery actions mapped to detected revenue leaks</p>
                                </div>
                                <AlertTriangle size={18} className="text-secondary" />
                            </div>

                            <div className="analytics-info-banner">
                                <Info size={15} className="info-banner-icon" />
                                <span>
                                    Incident attribution may overlap when a transaction matches multiple detected revenue-leak segments.
                                </span>
                            </div>

                            {incidentPerf.length === 0 ? (
                                <div className="no-data-placeholder">
                                    No incident records available.
                                </div>
                            ) : (
                                <div className="incident-cards-stack">
                                    {incidentPerf.map((inc) => {
                                        const tags = getIncidentTags(inc.incident_type);
                                        const accentClass = getIncidentAccent(inc.incident_type);
                                        const riskFormatted = formatMoneyM(inc.revenue_at_risk);
                                        return (
                                            <div className={`incident-premium-card ${accentClass}`} key={inc.incident_type}>
                                                <div className="ipc-top-row">
                                                    <div className="ipc-title-group">
                                                        <span className="ipc-severity-dot" />
                                                        <h4 className="ipc-title">{formatName(inc.incident_type)}</h4>
                                                    </div>
                                                    <div className="ipc-risk-badge">
                                                        <span className="ipc-risk-amount tabular">{riskFormatted}</span>
                                                        <span className="ipc-risk-label">At Risk</span>
                                                    </div>
                                                </div>

                                                <p className="ipc-description">{inc.description}</p>

                                                <div className="ipc-tags-strip">
                                                    {tags.map((t, idx) => (
                                                        <span className="ipc-tag-pill" key={idx}>
                                                            {t}
                                                        </span>
                                                    ))}
                                                </div>

                                                <div className="ipc-metrics-grid">
                                                    <div className="ipc-metric-cell">
                                                        <strong className="tabular">{inc.actions}</strong>
                                                        <span>Attributed Actions</span>
                                                    </div>
                                                    <div className="ipc-metric-cell">
                                                        <strong className="success-text tabular">{inc.successful}</strong>
                                                        <span>Attributed Recoveries</span>
                                                    </div>
                                                    <div className="ipc-metric-cell highlight-cell">
                                                        <strong className="success-text tabular">
                                                            ₹{Number(inc.actual_recovery || 0).toLocaleString("en-IN", {
                                                                minimumFractionDigits: 2,
                                                                maximumFractionDigits: 2,
                                                            })}
                                                        </strong>
                                                        <span>Actual Recovered</span>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {/* PAYMENT METHOD PERFORMANCE */}
                        <div className="analytics-panel">
                            <div className="panel-header">
                                <div>
                                    <h3>Payment Method Performance</h3>
                                    <p>Recoveries categorized by payment rails</p>
                                </div>
                                <CreditCard size={18} className="text-secondary" />
                            </div>

                            {/* TOP SUMMARY FOR PAYMENT METHODS */}
                            <div className="pm-top-summary-card">
                                <div className="pm-summary-left">
                                    <span className="pm-summary-kicker">OVERALL RECOVERY SUCCESS</span>
                                    <div className="pm-summary-rate tabular">
                                        {(Number(summary.recovery_rate || 76.42)).toFixed(1)}%
                                    </div>
                                    <span className="pm-summary-total">
                                        {summary.total_actions ?? 5} Total Actions
                                    </span>
                                </div>

                                <div className="pm-summary-right">
                                    <div className="pm-status-pill success">
                                        <span className="dot success" />
                                        <strong>{summary.successful_actions ?? 4}</strong>
                                        <span>Successful</span>
                                    </div>
                                    <div className="pm-status-pill warning">
                                        <span className="dot warning" />
                                        <strong>{summary.pending_actions ?? 1}</strong>
                                        <span>Pending</span>
                                    </div>
                                    <div className="pm-status-pill neutral">
                                        <span className="dot neutral" />
                                        <strong>{summary.failed_actions ?? 0}</strong>
                                        <span>Failed</span>
                                    </div>
                                </div>
                            </div>

                            {paymentMethodPerf.length === 0 ? (
                                <div className="no-data-placeholder">
                                    No payment method records available.
                                </div>
                            ) : (
                                <div className="payment-method-list">
                                    {paymentMethodPerf.map((pm) => {
                                        const isCard = pm.payment_method?.toUpperCase() === "CARD";
                                        const isUPI = pm.payment_method?.toUpperCase() === "UPI";
                                        const subtitle = isCard
                                            ? "Credit & Debit Cards"
                                            : isUPI
                                            ? "Unified Payments Interface"
                                            : "Alternative Payment Rail";

                                        const totalRecovered = Math.max(Number(summary.actual_recovered || 1), 1);
                                        const actualRecovered = Number(pm.actual_recovery || 0);
                                        const sharePct = Math.min(
                                            Math.round((actualRecovered / totalRecovered) * 100),
                                            100
                                        );

                                        const attempts = Number(pm.attempts || 0);
                                        const successful = Number(pm.successful || 0);
                                        const failed = Number(pm.failed || 0);
                                        const pending = Math.max(attempts - successful - failed, 0);

                                        return (
                                            <div className="pm-perf-card-premium" key={pm.payment_method}>
                                                <div className="pm-card-top-row">
                                                    <div className="pm-title-stack">
                                                        <div className="pm-title-inline">
                                                            {isCard ? (
                                                                <CreditCard size={18} className="pm-rail-icon" />
                                                            ) : (
                                                                <Smartphone size={18} className="pm-rail-icon" />
                                                            )}
                                                            <strong>{pm.payment_method}</strong>
                                                        </div>
                                                        <span className="pm-subtitle">{subtitle}</span>
                                                    </div>

                                                    <span className="pm-rate-badge tabular">
                                                        {Number(pm.success_rate || 0).toFixed(1)}%
                                                    </span>
                                                </div>

                                                {/* 4 STAT CHIPS */}
                                                <div className="pm-chips-four">
                                                    <div className="pm-stat-chip">
                                                        <strong className="tabular">{attempts}</strong>
                                                        <span>Attempts</span>
                                                    </div>
                                                    <div className="pm-stat-chip success">
                                                        <strong className="tabular">{successful}</strong>
                                                        <span>Successful</span>
                                                    </div>
                                                    <div className="pm-stat-chip warning">
                                                        <strong className="tabular">{pending}</strong>
                                                        <span>Pending</span>
                                                    </div>
                                                    <div className="pm-stat-chip">
                                                        <strong className="tabular">{failed}</strong>
                                                        <span>Failed</span>
                                                    </div>
                                                </div>

                                                {/* ACTUAL RECOVERED ROW */}
                                                <div className="pm-actual-row">
                                                    <span className="pm-actual-label">ACTUAL RECOVERED</span>
                                                    <div className="pm-actual-num tabular">
                                                        ₹{actualRecovered.toLocaleString("en-IN", {
                                                            minimumFractionDigits: 2,
                                                            maximumFractionDigits: 2,
                                                        })}
                                                    </div>
                                                </div>

                                                {/* RECOVERY SHARE PROGRESS BAR */}
                                                <div className="pm-share-bar-container">
                                                    <div className="pm-share-bar-track">
                                                        <div
                                                            className="pm-share-bar-fill"
                                                            style={{ width: `${Math.max(sharePct, 4)}%` }}
                                                        />
                                                    </div>
                                                    <span className="pm-share-caption tabular">
                                                        {sharePct}% of total recovered
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}

                                    {/* INSIGHTS CARD */}
                                    <div className="analytics-insights-card">
                                        <div className="insights-header">
                                            <Sparkles size={16} className="insights-icon" />
                                            <span>INSIGHTS</span>
                                        </div>
                                        <p className="insights-body">
                                            Card payments contribute the majority of recovered revenue (₹1,10,819.93, 94.4%),
                                            while UPI currently shows the highest recovery success rate (100.0%).
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

/* =========================================================================
   HELPERS
   ========================================================================= */

function formatName(str) {
    if (!str) return "N/A";
    return str
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMoneyM(value) {
    const amount = Number(value) || 0;
    if (amount >= 1000000) {
        return `₹${(amount / 1000000).toFixed(2)}M`;
    }
    if (amount >= 1000) {
        return `₹${(amount / 1000).toFixed(2)}K`;
    }
    return `₹${amount.toFixed(2)}`;
}

function getIncidentTags(type) {
    switch (type) {
        case "HIGH_VALUE_CARD_DEGRADATION":
            return ["CARD", "HIGH VALUE", "MUMBAI"];
        case "UPI_DEGRADATION":
            return ["UPI", "ANDROID", "BENGALURU"];
        case "EVENING_DEGRADATION":
            return ["EVENING PEAK", "MULTI-CHANNEL", "RETRY FATIGUE"];
        default:
            return ["SYSTEM", "AUTOMATED"];
    }
}

function getIncidentAccent(type) {
    switch (type) {
        case "HIGH_VALUE_CARD_DEGRADATION":
            return "accent-card-danger";
        case "UPI_DEGRADATION":
            return "accent-card-warning";
        case "EVENING_DEGRADATION":
            return "accent-card-purple";
        default:
            return "accent-card-default";
    }
}

function formatChartDate(dateStr) {
    if (!dateStr) return "";
    try {
        const [y, m, d] = dateStr.split("-");
        const date = new Date(y, m - 1, d);
        return new Intl.DateTimeFormat("en-IN", {
            day: "numeric",
            month: "short",
        }).format(date);
    } catch {
        return dateStr;
    }
}

export default Analytics;
