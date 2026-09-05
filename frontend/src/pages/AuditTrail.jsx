import { useEffect, useState, useMemo } from "react";
import {
    FileClock,
    CheckCircle2,
    Zap,
    ShieldAlert,
    ShieldCheck,
    AlertTriangle,
    RefreshCw,
    BrainCircuit,
    Search,
    ChevronDown,
    ChevronUp,
    Hash,
    User,
    Calendar,
    ArrowUpRight,
} from "lucide-react";
import KPICard from "../components/KPICard";
import { getAuditLogs } from "../services/api";

function AuditTrail() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filterType, setFilterType] = useState("ALL");
    const [searchQuery, setSearchQuery] = useState("");
    const [expandedLogs, setExpandedLogs] = useState({});

    async function fetchLogs() {
        try {
            setLoading(true);
            setError(null);
            const data = await getAuditLogs();
            setLogs(data.logs || []);
        } catch (err) {
            console.error("Failed to load audit trail:", err);
            setError(err.message || "Unable to load audit trail.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchLogs();
    }, []);

    // Summary statistics
    const stats = useMemo(() => {
        const total = logs.length;
        const recoveryEvents = logs.filter(
            (l) => l.event_type === "RECOVERY_EXECUTED"
        ).length;
        const verificationEvents = logs.filter(
            (l) => l.event_type === "RECOVERY_VERIFIED"
        ).length;
        const latestTime = logs[0]?.created_at
            ? formatTimestamp(logs[0].created_at)
            : "No activity";

        return {
            total,
            recoveryEvents,
            verificationEvents,
            latestTime,
        };
    }, [logs]);

    // Filter and search
    const filteredLogs = useMemo(() => {
        return logs.filter((log) => {
            const matchesFilter =
                filterType === "ALL" ||
                log.event_type === filterType;

            const q = searchQuery.trim().toLowerCase();
            if (!q) return matchesFilter;

            const matchesSearch =
                (log.event_type || "").toLowerCase().includes(q) ||
                (log.actor || "").toLowerCase().includes(q) ||
                (log.transaction_id || "").toLowerCase().includes(q) ||
                (log.details?.razorpay_order_id || "").toLowerCase().includes(q) ||
                (log.details?.strategy || "").toLowerCase().includes(q);

            return matchesFilter && matchesSearch;
        });
    }, [logs, filterType, searchQuery]);

    function toggleExpand(id) {
        setExpandedLogs((prev) => ({
            ...prev,
            [id]: !prev[id],
        }));
    }

    // Available event types for filter dropdown
    const availableTypes = useMemo(() => {
        const types = new Set(logs.map((l) => l.event_type).filter(Boolean));
        return Array.from(types);
    }, [logs]);

    return (
        <div className="audit-trail-page">
            {/* PAGE HEADER */}
            <div className="page-header">
                <div>
                    <h2>Audit Trail</h2>
                    <p>
                        Complete history of revenue protection decisions and actions.
                    </p>
                </div>

                <div className="audit-header-actions">
                    <button
                        className="refresh-button"
                        onClick={fetchLogs}
                        disabled={loading}
                        title="Refresh audit logs"
                    >
                        <RefreshCw
                            size={16}
                            className={loading ? "spin" : ""}
                        />
                        <span>Refresh</span>
                    </button>
                </div>
            </div>

            {/* TOP SUMMARY CARDS */}
            <section className="kpi-grid">
                <KPICard
                    title="Total Events"
                    value={loading ? "..." : stats.total}
                    subtitle="Recorded audit trail entries"
                    icon={FileClock}
                    variant="primary"
                />

                <KPICard
                    title="Recovery Executions"
                    value={loading ? "..." : stats.recoveryEvents}
                    subtitle="Autonomous execution triggers"
                    icon={Zap}
                    variant="warning"
                />

                <KPICard
                    title="Verification Events"
                    value={loading ? "..." : stats.verificationEvents}
                    subtitle="Confirmed recovered payments"
                    icon={CheckCircle2}
                    variant="success"
                />

                <KPICard
                    title="Latest Activity"
                    value={
                        loading
                            ? "..."
                            : logs[0]
                            ? formatTimeAgo(logs[0].created_at)
                            : "None"
                    }
                    subtitle={stats.latestTime}
                    icon={Calendar}
                    variant="default"
                />
            </section>

            {/* CONTROLS: SEARCH & FILTER */}
            <div className="audit-controls">
                <div className="search-box">
                    <Search size={16} />
                    <input
                        type="text"
                        placeholder="Search by transaction ID, order ID, actor, strategy..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    {searchQuery && (
                        <button
                            className="clear-search"
                            onClick={() => setSearchQuery("")}
                        >
                            ✕
                        </button>
                    )}
                </div>

                <div className="filter-group">
                    <button
                        className={`filter-btn ${filterType === "ALL" ? "active" : ""}`}
                        onClick={() => setFilterType("ALL")}
                    >
                        All ({logs.length})
                    </button>
                    {availableTypes.map((type) => (
                        <button
                            key={type}
                            className={`filter-btn ${filterType === type ? "active" : ""}`}
                            onClick={() => setFilterType(type)}
                        >
                            {formatEventTypeLabel(type)}
                        </button>
                    ))}
                </div>
            </div>

            {/* MAIN CONTENT AREA */}
            {loading ? (
                <div className="page-state">
                    <RefreshCw size={24} className="spin" />
                    <span>Loading audit trail...</span>
                </div>
            ) : error ? (
                <div className="page-state error">
                    <AlertTriangle size={24} />
                    <span>Unable to load audit trail: {error}</span>
                    <button className="retry-btn" onClick={fetchLogs}>
                        Retry
                    </button>
                </div>
            ) : filteredLogs.length === 0 ? (
                <div className="page-state empty">
                    <FileClock size={28} />
                    <span>
                        {searchQuery || filterType !== "ALL"
                            ? "No matching audit events found."
                            : "No audit events recorded yet."}
                    </span>
                    {(searchQuery || filterType !== "ALL") && (
                        <button
                            className="retry-btn"
                            onClick={() => {
                                setSearchQuery("");
                                setFilterType("ALL");
                            }}
                        >
                            Reset filters
                        </button>
                    )}
                </div>
            ) : (
                <div className="audit-timeline">
                    {filteredLogs.map((log) => {
                        const isExpanded = !!expandedLogs[log.id];
                        const details = log.details || {};
                        const visual = getEventVisual(log.event_type, details);
                        const Icon = visual.icon;

                        // Extracted values
                        const recoveredAmount =
                            details.amount_paid ??
                            details.recovered_amount ??
                            details.actual_recovery;
                        const expectedAmount = details.expected_recovery;
                        const originalAmount = details.amount;
                        const orderId = details.razorpay_order_id;
                        const status = details.new_status || details.status;
                        const strategy = details.strategy;
                        const policyDecision = details.policy_decision;

                        return (
                            <div
                                key={log.id}
                                className={`audit-card audit-card-${visual.variant}`}
                            >
                                {/* CARD TOP ROW */}
                                <div className="audit-card-header">
                                    <div className="audit-type-group">
                                        <div className={`audit-icon-wrapper ${visual.variant}`}>
                                            <Icon size={18} />
                                        </div>
                                        <div>
                                            <div className="audit-title-row">
                                                <strong className="audit-event-title">
                                                    {formatEventTypeLabel(log.event_type)}
                                                </strong>
                                                <span className={`audit-badge badge-${visual.variant}`}>
                                                    {log.event_type}
                                                </span>
                                                {status && (
                                                    <span className={`status-pill status-${String(status).toLowerCase()}`}>
                                                        {status}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="audit-summary-desc">
                                                {visual.description(details)}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="audit-timestamp-block">
                                        <span className="audit-date">
                                            {formatTimestamp(log.created_at)}
                                        </span>
                                        <span className="audit-ago">
                                            {formatTimeAgo(log.created_at)}
                                        </span>
                                    </div>
                                </div>

                                {/* META ROW: Transaction, Actor */}
                                <div className="audit-meta-row">
                                    {log.transaction_id && (
                                        <div className="meta-item">
                                            <Hash size={13} />
                                            <span>Transaction:</span>
                                            <strong className="monospace-text">
                                                {log.transaction_id}
                                            </strong>
                                        </div>
                                    )}

                                    <div className="meta-item">
                                        <User size={13} />
                                        <span>Actor:</span>
                                        <strong>{log.actor || "system"}</strong>
                                    </div>

                                    {strategy && (
                                        <div className="meta-item">
                                            <span>Strategy:</span>
                                            <span className="strategy-tag">
                                                {strategy.replace(/_/g, " ")}
                                            </span>
                                        </div>
                                    )}

                                    {policyDecision && (
                                        <div className="meta-item">
                                            <span>Policy:</span>
                                            <span
                                                className={`policy-pill ${
                                                    policyDecision === "ALLOW"
                                                        ? "allowed"
                                                        : "blocked"
                                                }`}
                                            >
                                                {policyDecision}
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {/* HIGHLIGHTED FINANCIAL/ORDER DETAILS */}
                                {(recoveredAmount !== undefined ||
                                    expectedAmount !== undefined ||
                                    originalAmount !== undefined ||
                                    orderId) && (
                                    <div className="audit-details-highlight">
                                        {recoveredAmount !== undefined &&
                                            recoveredAmount !== null && (
                                                <div className="highlight-cell success">
                                                    <span>Recovered Amount</span>
                                                    <strong>
                                                        ₹
                                                        {Number(recoveredAmount).toLocaleString(
                                                            "en-IN",
                                                            {
                                                                minimumFractionDigits: 2,
                                                                maximumFractionDigits: 2,
                                                            }
                                                        )}
                                                    </strong>
                                                </div>
                                            )}

                                        {expectedAmount !== undefined &&
                                            expectedAmount !== null && (
                                                <div className="highlight-cell primary">
                                                    <span>Expected Recovery</span>
                                                    <strong>
                                                        ₹
                                                        {Number(expectedAmount).toLocaleString(
                                                            "en-IN",
                                                            {
                                                                minimumFractionDigits: 2,
                                                                maximumFractionDigits: 2,
                                                            }
                                                        )}
                                                    </strong>
                                                </div>
                                            )}

                                        {originalAmount !== undefined &&
                                            originalAmount !== null &&
                                            recoveredAmount === undefined && (
                                                <div className="highlight-cell default">
                                                    <span>Impact Amount</span>
                                                    <strong>
                                                        ₹
                                                        {Number(originalAmount).toLocaleString(
                                                            "en-IN",
                                                            {
                                                                minimumFractionDigits: 2,
                                                                maximumFractionDigits: 2,
                                                            }
                                                        )}
                                                    </strong>
                                                </div>
                                            )}

                                        {orderId && (
                                            <div className="highlight-cell order">
                                                <span>Razorpay Order</span>
                                                <strong className="monospace-text">
                                                    {orderId}
                                                </strong>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* COLLAPSIBLE RAW JSON SECTION */}
                                {Object.keys(details).length > 0 && (
                                    <div className="audit-json-section">
                                        <button
                                            className="toggle-json-btn"
                                            onClick={() => toggleExpand(log.id)}
                                        >
                                            <span>
                                                {isExpanded
                                                    ? "Hide Full Event Details"
                                                    : "View Raw Event Details"}
                                            </span>
                                            {isExpanded ? (
                                                <ChevronUp size={14} />
                                            ) : (
                                                <ChevronDown size={14} />
                                            )}
                                        </button>

                                        {isExpanded && (
                                            <pre className="audit-json-pre">
                                                {JSON.stringify(details, null, 2)}
                                            </pre>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

/* =========================================================================
   HELPERS & FORMATTERS
   ========================================================================= */

function formatTimestamp(isoString) {
    if (!isoString) return "N/A";
    try {
        const date = new Date(isoString);
        const day = new Intl.DateTimeFormat("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
        }).format(date);
        const time = new Intl.DateTimeFormat("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
        }).format(date);
        return `${day} · ${time}`;
    } catch {
        return String(isoString);
    }
}

function formatTimeAgo(isoString) {
    if (!isoString) return "N/A";
    try {
        const diff = Date.now() - new Date(isoString).getTime();
        const seconds = Math.floor(diff / 1000);
        if (seconds < 60) return "Just now";
        const mins = Math.floor(seconds / 60);
        if (mins < 60) return `${mins}m ago`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    } catch {
        return "Recent";
    }
}

function formatEventTypeLabel(type) {
    if (!type) return "Event";
    return type
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getEventVisual(eventType, details = {}) {
    switch (eventType) {
        case "RECOVERY_VERIFIED":
            return {
                icon: CheckCircle2,
                variant: "success",
                description: (d) =>
                    d.amount_paid
                        ? `Recovery payment verified and recorded for ₹${Number(d.amount_paid).toLocaleString("en-IN")}.`
                        : "Recovery payment verified successfully by autonomous system.",
            };

        case "RECOVERY_EXECUTED":
            return {
                icon: Zap,
                variant: "warning",
                description: (d) =>
                    d.message ||
                    (d.strategy
                        ? `Autonomous recovery initiated using strategy ${d.strategy}.`
                        : "Recovery action executed."),
            };

        case "POLICY_BLOCKED":
            return {
                icon: ShieldAlert,
                variant: "danger",
                description: (d) =>
                    d.reason || "Recovery execution was blocked by safety policy.",
            };

        case "POLICY_APPROVED":
            return {
                icon: ShieldCheck,
                variant: "success",
                description: () => "Recovery execution approved by policy engine.",
            };

        case "INCIDENT_DETECTED":
            return {
                icon: AlertTriangle,
                variant: "warning",
                description: (d) =>
                    d.description || "Revenue leak incident detected.",
            };

        case "ANALYSIS_COMPLETED":
            return {
                icon: BrainCircuit,
                variant: "accent",
                description: () => "AI recovery model analysis and strategy ranking completed.",
            };

        default:
            return {
                icon: FileClock,
                variant: "default",
                description: () => "System event logged.",
            };
    }
}

export default AuditTrail;
