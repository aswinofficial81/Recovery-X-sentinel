import { useEffect, useState, useMemo } from "react";
import {
    ShieldCheck,
    CheckCircle2,
    Clock,
    AlertCircle,
    RefreshCw,
    Search,
    CreditCard,
    Smartphone,
    MapPin,
    AlertTriangle,
    Check,
    IndianRupee,
} from "lucide-react";
import KPICard from "../components/KPICard";
import { getRecoveryActions } from "../services/api";

function Recovery() {
    const [actions, setActions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState("ALL");

    async function fetchActions() {
        try {
            setLoading(true);
            setError(null);
            const data = await getRecoveryActions();
            setActions(data.actions || []);
        } catch (err) {
            console.error("Failed to load recovery actions:", err);
            setError(err.message || "Unable to load recovery actions.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchActions();
    }, []);

    // Summary Statistics
    const stats = useMemo(() => {
        const total = actions.length;
        const success = actions.filter((a) => a.status === "SUCCESS").length;
        const pending = actions.filter(
            (a) => a.status === "EXECUTING" || a.status === "PENDING" || a.status === "APPROVED"
        ).length;
        const totalActualRecovered = actions
            .filter((a) => a.status === "SUCCESS")
            .reduce((sum, a) => sum + (Number(a.actual_recovery) || 0), 0);

        return {
            total,
            success,
            pending,
            totalActualRecovered,
        };
    }, [actions]);

    // Filtering & Search
    const filteredActions = useMemo(() => {
        return actions.filter((item) => {
            const matchesStatus =
                statusFilter === "ALL" ||
                (item.status || "").toUpperCase() === statusFilter;

            const q = searchQuery.trim().toLowerCase();
            if (!q) return matchesStatus;

            const matchesSearch =
                (item.transaction_id || "").toLowerCase().includes(q) ||
                (item.razorpay_order_id || "").toLowerCase().includes(q) ||
                (item.action_type || "").toLowerCase().includes(q) ||
                (item.payment_method || "").toLowerCase().includes(q) ||
                (item.status || "").toLowerCase().includes(q) ||
                (item.location || "").toLowerCase().includes(q) ||
                (item.failure_reason || "").toLowerCase().includes(q);

            return matchesStatus && matchesSearch;
        });
    }, [actions, statusFilter, searchQuery]);

    // Available statuses for filter pills
    const availableStatuses = useMemo(() => {
        const standard = ["SUCCESS", "EXECUTING", "PENDING", "FAILED", "BLOCKED"];
        const fromData = Array.from(
            new Set(actions.map((a) => (a.status || "").toUpperCase()).filter(Boolean))
        );
        // Union ensuring standard order first, then any extra
        return Array.from(new Set([...fromData, ...standard]));
    }, [actions]);

    return (
        <div className="recovery-page">
            {/* PAGE HEADER */}
            <div className="page-header">
                <div>
                    <h2>Recovery Actions</h2>
                    <p>
                        Track autonomous revenue recovery attempts and verified outcomes.
                    </p>
                </div>

                <div className="audit-header-actions">
                    <button
                        className="refresh-button"
                        onClick={fetchActions}
                        disabled={loading}
                        title="Refresh recovery actions"
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
                    title="Total Actions"
                    value={loading ? "..." : stats.total}
                    subtitle="Recovery attempts recorded"
                    icon={ShieldCheck}
                    variant="primary"
                />

                <KPICard
                    title="Successful Recoveries"
                    value={loading ? "..." : stats.success}
                    subtitle="Verified revenue recoveries"
                    icon={CheckCircle2}
                    variant="success"
                />

                <KPICard
                    title="Pending / Processing"
                    value={loading ? "..." : stats.pending}
                    subtitle="Awaiting user action or verification"
                    icon={Clock}
                    variant="warning"
                />

                <KPICard
                    title="Total Actual Recovered"
                    value={
                        loading
                            ? "..."
                            : `₹${stats.totalActualRecovered.toLocaleString("en-IN", {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                              })}`
                    }
                    subtitle="Confirmed in payment ledger"
                    icon={IndianRupee}
                    variant="success"
                />
            </section>

            {/* CONTROLS: SEARCH & STATUS FILTERS */}
            <div className="audit-controls">
                <div className="search-box">
                    <Search size={16} />
                    <input
                        type="text"
                        placeholder="Search by transaction, order, strategy, payment method..."
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
                        className={`filter-btn ${statusFilter === "ALL" ? "active" : ""}`}
                        onClick={() => setStatusFilter("ALL")}
                    >
                        All ({actions.length})
                    </button>
                    {availableStatuses.map((st) => {
                        const count = actions.filter(
                            (a) => (a.status || "").toUpperCase() === st
                        ).length;
                        if (count === 0 && st !== "ALL") return null;
                        return (
                            <button
                                key={st}
                                className={`filter-btn ${statusFilter === st ? "active" : ""}`}
                                onClick={() => setStatusFilter(st)}
                            >
                                {formatStatusLabel(st)} ({count})
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* MAIN CONTENT AREA */}
            {loading ? (
                <div className="page-state">
                    <RefreshCw size={24} className="spin" />
                    <span>Loading recovery actions...</span>
                </div>
            ) : error ? (
                <div className="page-state error">
                    <AlertCircle size={24} />
                    <span>Unable to load recovery actions: {error}</span>
                    <button className="retry-btn" onClick={fetchActions}>
                        Retry
                    </button>
                </div>
            ) : actions.length === 0 ? (
                <div className="page-state empty">
                    <ShieldCheck size={28} />
                    <span>No recovery actions recorded yet.</span>
                </div>
            ) : filteredActions.length === 0 ? (
                <div className="page-state empty">
                    <Search size={28} />
                    <span>No recovery actions match your filters.</span>
                    <button
                        className="retry-btn"
                        onClick={() => {
                            setSearchQuery("");
                            setStatusFilter("ALL");
                        }}
                    >
                        Reset filters
                    </button>
                </div>
            ) : (
                <div className="recovery-table-container">
                    <table className="recovery-table">
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>Strategy</th>
                                <th>Transaction</th>
                                <th>Payment Method</th>
                                <th style={{ textAlign: "right" }}>Expected Recovery</th>
                                <th style={{ textAlign: "right" }}>Actual Recovery</th>
                                <th>Razorpay Order</th>
                                <th>Attempt</th>
                                <th>Executed At</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredActions.map((action) => {
                                const isSuccess = action.status === "SUCCESS";
                                const isExecuting = action.status === "EXECUTING";
                                const isPending = action.status === "PENDING";
                                const isFailed = action.status === "FAILED";
                                const isBlocked = action.status === "BLOCKED";

                                const statusClass = isSuccess
                                    ? "status-success"
                                    : isExecuting
                                    ? "status-executing"
                                    : isPending
                                    ? "status-pending"
                                    : isFailed
                                    ? "status-failed"
                                    : isBlocked
                                    ? "status-blocked"
                                    : "status-default";

                                const actualAmount = Number(action.actual_recovery);
                                const expectedAmount = Number(action.expected_recovery);

                                return (
                                    <tr key={action.id} className={`recovery-row ${isSuccess ? "row-success" : ""}`}>
                                        {/* STATUS */}
                                        <td>
                                            <div className="table-status-cell">
                                                <span className={`status-pill ${statusClass}`}>
                                                    {action.status || "UNKNOWN"}
                                                </span>
                                                {isSuccess && (
                                                    <span className="verified-tag">
                                                        <Check size={11} />
                                                        Verified Recovery
                                                    </span>
                                                )}
                                            </div>
                                        </td>

                                        {/* STRATEGY */}
                                        <td>
                                            <span className="strategy-tag">
                                                {formatStrategyName(action.action_type)}
                                            </span>
                                        </td>

                                        {/* TRANSACTION */}
                                        <td>
                                            <div className="transaction-cell">
                                                <span className="monospace-text" title={action.transaction_id}>
                                                    {truncateId(action.transaction_id)}
                                                </span>
                                                {action.failure_reason && (
                                                    <small className="failure-reason-sub">
                                                        {action.failure_reason}
                                                    </small>
                                                )}
                                            </div>
                                        </td>

                                        {/* PAYMENT METHOD & CONTEXT */}
                                        <td>
                                            <div className="payment-method-cell">
                                                <span className="method-name">
                                                    {action.payment_method || "N/A"}
                                                </span>
                                                {(action.device || action.location) && (
                                                    <small className="context-sub">
                                                        {[action.device, action.location].filter(Boolean).join(" • ")}
                                                    </small>
                                                )}
                                            </div>
                                        </td>

                                        {/* EXPECTED RECOVERY */}
                                        <td className="amount-cell tabular">
                                            <span className="amount-expected">
                                                ₹{expectedAmount.toLocaleString("en-IN", {
                                                    minimumFractionDigits: 2,
                                                    maximumFractionDigits: 2,
                                                })}
                                            </span>
                                        </td>

                                        {/* ACTUAL RECOVERY */}
                                        <td className="amount-cell tabular">
                                            {isSuccess && actualAmount > 0 ? (
                                                <strong className="amount-actual-success" style={{ color: "var(--success-text)" }}>
                                                    ₹{actualAmount.toLocaleString("en-IN", {
                                                        minimumFractionDigits: 2,
                                                        maximumFractionDigits: 2,
                                                    })}
                                                </strong>
                                            ) : (
                                                <span className="amount-actual-zero" style={{ color: "var(--text-tertiary)" }}>
                                                    {actualAmount > 0
                                                        ? `₹${actualAmount.toLocaleString("en-IN", {
                                                              minimumFractionDigits: 2,
                                                          })}`
                                                        : "₹0.00"}
                                                </span>
                                            )}
                                        </td>

                                        {/* RAZORPAY ORDER */}
                                        <td>
                                            {action.razorpay_order_id ? (
                                                <span className="monospace-text order-id-text">
                                                    {action.razorpay_order_id}
                                                </span>
                                            ) : (
                                                <span className="empty-dash">—</span>
                                            )}
                                        </td>

                                        {/* ATTEMPT */}
                                        <td>
                                            <span className="attempt-pill">
                                                #{action.attempt_number || 1}
                                            </span>
                                        </td>

                                        {/* EXECUTED AT */}
                                        <td>
                                            <div className="timestamp-cell">
                                                <span>{formatTimestamp(action.executed_at || action.created_at)}</span>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

/* =========================================================================
   HELPERS & FORMATTERS
   ========================================================================= */

function formatTimestamp(isoString) {
    if (!isoString) return "—";
    try {
        const date = new Date(isoString);
        return new Intl.DateTimeFormat("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
        }).format(date);
    } catch {
        return String(isoString);
    }
}

function formatStrategyName(type) {
    if (!type) return "Strategy";
    return type
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatStatusLabel(status) {
    if (!status) return "Status";
    return status
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function truncateId(id) {
    if (!id) return "—";
    if (id.length <= 16) return id;
    return `${id.slice(0, 8)}...${id.slice(-6)}`;
}

export default Recovery;
