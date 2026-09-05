import { useEffect, useState, useCallback } from "react";
import {
    AlertTriangle,
    BrainCircuit,
    ShieldCheck,
    ExternalLink,
    CheckCircle2,
    Check,
    RefreshCw,
    Layers,
    ChevronDown,
    ChevronUp,
    Copy,
} from "lucide-react";

import {
    getRevenueLeaks,
    getIncidentTransactions,
    analyzeRecovery,
    executeRecovery,
    getRecoveryConfig,
} from "../services/api";

import AIIncidentReport from "../components/AIIncidentReport";

function formatIncidentName(type) {
    if (!type) return "Unknown Incident";
    return type
        .replaceAll("_", " ")
        .toLowerCase()
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatMoney(value) {
    const amount = Number(value) || 0;
    if (amount >= 1000000) {
        return `₹${(amount / 1000000).toFixed(2)}M`;
    }
    if (amount >= 1000) {
        return `₹${(amount / 1000).toFixed(2)}K`;
    }
    return `₹${amount.toFixed(2)}`;
}

function formatSegmentChips(segment) {
    if (!segment) return "GENERAL";
    return Object.values(segment)
        .map((v) => String(v).toUpperCase())
        .join(" · ");
}

export default function Incidents() {
    const [incidents, setIncidents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Dynamic queue of failed transactions per incident: { [incidentId]: [tx1, tx2, ...] }
    const [incidentQueues, setIncidentQueues] = useState({});
    const [queueLoading, setQueueLoading] = useState({});

    // Analysis results keyed by transactionId: { [txId]: { transaction, analysis, execution, error, executionError } }
    const [analysisResults, setAnalysisResults] = useState({});
    const [analyzingTxId, setAnalyzingTxId] = useState(null);
    const [executingTxId, setExecutingTxId] = useState(null);

    // Expanded transaction for viewing AI report: transactionId | null
    const [expandedTxId, setExpandedTxId] = useState(null);
    const [copiedTxId, setCopiedTxId] = useState(null);

    // Fetch transactions queue for an incident
    const loadQueueForIncident = useCallback(async (incident) => {
        const incId = incident.id;
        try {
            setQueueLoading((prev) => ({ ...prev, [incId]: true }));
            const res = await getIncidentTransactions(incident.leak_type, 10);
            const transactions = res?.transactions || [];
            setIncidentQueues((prev) => ({
                ...prev,
                [incId]: transactions,
            }));
        } catch (err) {
            console.error(`Failed to load queue for incident ${incident.leak_type}:`, err);
        } finally {
            setQueueLoading((prev) => ({ ...prev, [incId]: false }));
        }
    }, []);

    // Initial load: fetch revenue incidents and their transaction queues
    useEffect(() => {
        let isMounted = true;

        async function loadIncidentsAndQueues() {
            try {
                const result = await getRevenueLeaks();
                const leaks = result.leaks || [];
                if (!isMounted) return;
                setIncidents(leaks);

                // Dynamically fetch failed transactions for each incident
                for (const inc of leaks) {
                    try {
                        const txRes = await getIncidentTransactions(inc.leak_type, 10);
                        if (isMounted && txRes?.transactions) {
                            setIncidentQueues((prev) => ({
                                ...prev,
                                [inc.id]: txRes.transactions,
                            }));
                        }
                    } catch (e) {
                        console.error("Failed to load queue for", inc.leak_type, e);
                    }
                }
            } catch (err) {
                console.error(err);
                if (isMounted) setError(err.message);
            } finally {
                if (isMounted) setLoading(false);
            }
        }

        loadIncidentsAndQueues();
        return () => {
            isMounted = false;
        };
    }, []);

    // Copy transaction ID to clipboard
    const copyToClipboard = (text) => {
        navigator.clipboard?.writeText(text);
        setCopiedTxId(text);
        setTimeout(() => setCopiedTxId(null), 2000);
    };

    // Update transaction recovery status in queue state
    const updateTxInQueue = (incidentId, txId, patch) => {
        setIncidentQueues((prev) => {
            const list = prev[incidentId] || [];
            return {
                ...prev,
                [incidentId]: list.map((tx) => (tx.id === txId ? { ...tx, ...patch } : tx)),
            };
        });
    };

    // Analyze specific transaction
    async function handleAnalyzeTx(incident, tx) {
        const txId = tx.id || tx.transaction_id;
        try {
            setAnalyzingTxId(txId);
            setAnalysisResults((prev) => ({
                ...prev,
                [txId]: {
                    ...prev[txId],
                    error: null,
                },
            }));

            const response = await analyzeRecovery(txId);
            const initialExecution = response?.existing_recovery || null;

            setAnalysisResults((prev) => ({
                ...prev,
                [txId]: {
                    transaction: response.transaction || tx,
                    analysis: response.analysis,
                    execution: initialExecution,
                    error: null,
                },
            }));

            // Auto-expand the analyzed transaction report
            setExpandedTxId(txId);

            // Synchronize queue item status if backend returned existing recovery
            if (initialExecution?.status) {
                const rawStatus = initialExecution.status.toUpperCase();
                const orderId = initialExecution.razorpay_order_id || initialExecution.order_id;
                const actualRecovery =
                    initialExecution.recovered_amount ?? initialExecution.actual_recovery ?? 0;

                updateTxInQueue(incident.id, txId, {
                    recovery_status: rawStatus,
                    razorpay_order_id: orderId,
                    actual_recovery: actualRecovery,
                });
            }
        } catch (err) {
            console.error("Analysis failed:", err);
            setAnalysisResults((prev) => ({
                ...prev,
                [txId]: {
                    transaction: tx,
                    error: err.message,
                },
            }));
            setExpandedTxId(txId);
        } finally {
            setAnalyzingTxId(null);
        }
    }

    // Execute Recovery for specific transaction
    async function handleExecuteTx(incident, tx) {
        const txId = tx.id || tx.transaction_id;
        try {
            setExecutingTxId(txId);
            const currentResult = analysisResults[txId];
            const analysisData = currentResult?.analysis?.analysis || currentResult?.analysis;
            const mlDecision = analysisData?.ml_decision;
            const strategy = mlDecision?.recommended_strategy || "Alternative Payment";

            const executionResponse = await executeRecovery(txId, strategy);

            setAnalysisResults((prev) => ({
                ...prev,
                [txId]: {
                    ...prev[txId],
                    execution: executionResponse,
                    executionError: null,
                },
            }));

            const rawStatus = (
                executionResponse?.status ||
                executionResponse?.recovery?.status ||
                "ORDER_CREATED"
            ).toUpperCase();

            const orderId =
                executionResponse?.razorpay_order_id ||
                executionResponse?.recovery?.razorpay_order_id ||
                executionResponse?.order_id;

            const actualRecovery =
                executionResponse?.recovered_amount ??
                executionResponse?.recovery?.recovered_amount ??
                executionResponse?.actual_recovery ??
                executionResponse?.recovery?.actual_recovery ??
                0;

            updateTxInQueue(incident.id, txId, {
                recovery_status: rawStatus,
                razorpay_order_id: orderId,
                actual_recovery: actualRecovery,
            });
        } catch (err) {
            console.error("Execution failed:", err);
            setAnalysisResults((prev) => ({
                ...prev,
                [txId]: {
                    ...prev[txId],
                    executionError: err.message,
                },
            }));
        } finally {
            setExecutingTxId(null);
        }
    }

    // Open Razorpay Checkout for a transaction with an active order
    const openCheckout = async (tx, orderId, amount) => {
        const transactionId = tx.id || tx.transaction_id;
        const finalAmount = Number(amount || tx.amount || 0);
        let keyId = import.meta.env.VITE_RAZORPAY_KEY_ID;
        if (!keyId) {
            try {
                const config = await getRecoveryConfig();
                keyId = config?.razorpay_key_id;
            } catch (err) {
                console.warn("Could not load recovery config:", err);
            }
        }
        const keyParam = keyId ? `&key_id=${encodeURIComponent(keyId)}` : "";
        const paymentUrl = `http://localhost:5500/test_payment.html?order_id=${encodeURIComponent(
            orderId
        )}&transaction_id=${encodeURIComponent(transactionId)}&amount=${encodeURIComponent(
            finalAmount
        )}${keyParam}`;
        window.open(paymentUrl, "_blank");
    };



    if (loading) {
        return (
            <div className="page-state">
                <BrainCircuit size={28} className="spin" />
                <span>Loading revenue intelligence stream...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="page-state error">
                <AlertTriangle size={28} />
                <span>Failed to load incidents: {error}</span>
            </div>
        );
    }

    return (
        <div className="incidents-page">
            {/* PAGE HEADER */}
            <div className="page-header">
                <div>
                    <h2>Revenue Incidents</h2>
                    <p>AI-detected revenue degradation and active recovery triggers</p>
                </div>

                <div className="incident-count">
                    <AlertTriangle size={15} />
                    <span>{incidents.length} Active Events</span>
                </div>
            </div>

            {/* INCIDENT GRID */}
            <div className="incident-grid">
                {incidents.map((incident) => {
                    const queue = incidentQueues[incident.id] || [];
                    const isQueueLoading = queueLoading[incident.id];

                    return (
                        <div className="incident-card" key={incident.id}>
                            {/* INCIDENT HEADER */}
                            <div className="incident-card-header">
                                <div className="incident-tags-row">
                                    <span className="segment-chip">
                                        {formatSegmentChips(incident.segment)}
                                    </span>
                                    <span className="open-label">{incident.status}</span>
                                </div>
                            </div>

                            {/* TITLE & DESCRIPTION */}
                            <h3>{formatIncidentName(incident.leak_type)}</h3>
                            <p className="incident-description">{incident.description}</p>

                            {/* METRICS STRIP */}
                            <div className="incident-metrics-strip">
                                <div>
                                    <span>REVENUE AT RISK</span>
                                    <strong className="risk-value tabular">
                                        {formatMoney(incident.revenue_impact)}
                                    </strong>
                                </div>
                                <div>
                                    <span>CONFIDENCE</span>
                                    <strong className="tabular">
                                        {(Number(incident.confidence) * 100).toFixed(0)}%
                                    </strong>
                                </div>
                                <div>
                                    <span>DETECTION VECTOR</span>
                                    <strong>
                                        {incident.segment?.payment_method
                                            ? String(incident.segment.payment_method).toUpperCase()
                                            : "MULTI-CHANNEL"}
                                    </strong>
                                </div>
                            </div>

                            {/* AFFECTED TRANSACTIONS / RECOVERY QUEUE SECTION */}
                            <div className="recovery-queue-container">
                                <div className="queue-header">
                                    <div className="queue-title-wrap">
                                        <Layers size={16} className="queue-icon" />
                                        <h4>Affected Transactions (Recovery Queue)</h4>
                                        <span className="queue-badge">
                                            {queue.length} Active Candidates
                                        </span>
                                    </div>
                                    <button
                                        className="queue-refresh-btn"
                                        onClick={() => loadQueueForIncident(incident)}
                                        disabled={isQueueLoading}
                                        title="Refresh live failed transactions from PostgreSQL"
                                    >
                                        <RefreshCw
                                            size={13}
                                            className={isQueueLoading ? "spin" : ""}
                                        />
                                        <span>Refresh</span>
                                    </button>
                                </div>

                                {isQueueLoading && queue.length === 0 ? (
                                    <div className="queue-loading">
                                        <RefreshCw size={18} className="spin" />
                                        <span>Querying PostgreSQL transaction pool...</span>
                                    </div>
                                ) : queue.length === 0 ? (
                                    <div className="queue-empty">
                                        <span>No failed transactions found matching this incident criteria.</span>
                                    </div>
                                ) : (
                                    <div className="queue-table-wrapper">
                                        <table className="queue-table">
                                            <thead>
                                                <tr>
                                                    <th>Transaction ID</th>
                                                    <th>Amount</th>
                                                    <th>Method & Device</th>
                                                    <th>Failure Reason</th>
                                                    <th>Location</th>
                                                    <th>Attempt</th>
                                                    <th>Status</th>
                                                    <th style={{ textAlign: "right" }}>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {queue.map((tx) => {
                                                    const txId = tx.id;
                                                    const isAnalyzed = Boolean(analysisResults[txId]);
                                                    const isCurrentlyAnalyzing = analyzingTxId === txId;
                                                    const isExpanded = expandedTxId === txId;

                                                    const result = analysisResults[txId];
                                                    const execution = result?.execution;
                                                    const rawStatus = (
                                                        execution?.status ||
                                                        execution?.recovery?.status ||
                                                        tx.recovery_status ||
                                                        "READY"
                                                    ).toUpperCase();

                                                    const isRecovered =
                                                        rawStatus === "SUCCESS" ||
                                                        rawStatus === "RECOVERED";
                                                    const isOrderCreated =
                                                        rawStatus === "ORDER_CREATED" ||
                                                        rawStatus === "EXECUTING";
                                                    const isBlocked = rawStatus === "BLOCKED";
                                                    const isFailed = rawStatus === "FAILED";

                                                    const orderId =
                                                        execution?.razorpay_order_id ||
                                                        execution?.recovery?.razorpay_order_id ||
                                                        execution?.order_id ||
                                                        tx.razorpay_order_id;

                                                    const actualRecovery =
                                                        execution?.recovered_amount ??
                                                        execution?.recovery?.recovered_amount ??
                                                        execution?.actual_recovery ??
                                                        execution?.recovery?.actual_recovery ??
                                                        tx.actual_recovery ??
                                                        0;

                                                    return (
                                                        <tr
                                                            key={txId}
                                                            className={isExpanded ? "row-expanded" : ""}
                                                        >
                                                            {/* TRANSACTION ID */}
                                                            <td>
                                                                <div className="tx-id-cell">
                                                                    <span
                                                                        className="tx-id-code"
                                                                        title={txId}
                                                                    >
                                                                        {txId.slice(0, 8)}...
                                                                        {txId.slice(-4)}
                                                                    </span>
                                                                    <button
                                                                        className="tx-copy-btn"
                                                                        onClick={() =>
                                                                            copyToClipboard(txId)
                                                                        }
                                                                        title="Copy full transaction ID"
                                                                    >
                                                                        {copiedTxId === txId ? (
                                                                            <Check
                                                                                size={12}
                                                                                className="copied"
                                                                            />
                                                                        ) : (
                                                                            <Copy size={12} />
                                                                        )}
                                                                    </button>
                                                                </div>
                                                            </td>

                                                            {/* AMOUNT */}
                                                            <td>
                                                                <span className="tx-amount tabular">
                                                                    ₹
                                                                    {Number(tx.amount).toLocaleString(
                                                                        "en-IN",
                                                                        {
                                                                            minimumFractionDigits: 2,
                                                                            maximumFractionDigits: 2,
                                                                        }
                                                                    )}
                                                                </span>
                                                            </td>

                                                            {/* METHOD & DEVICE */}
                                                            <td>
                                                                <span className="tx-method-chip">
                                                                    {tx.payment_method} ·{" "}
                                                                    {tx.device || "WEB"}
                                                                </span>
                                                            </td>

                                                            {/* FAILURE REASON */}
                                                            <td>
                                                                <span className="tx-failure-badge">
                                                                    {tx.failure_reason || "Declined"}
                                                                </span>
                                                            </td>

                                                            {/* LOCATION */}
                                                            <td>
                                                                <span className="tx-meta-text">
                                                                    {tx.location || "Online"}
                                                                </span>
                                                            </td>

                                                            {/* ATTEMPT */}
                                                            <td>
                                                                <span className="tx-attempt-pill">
                                                                    #{tx.attempt || 1}
                                                                </span>
                                                            </td>

                                                            {/* RECOVERY STATUS */}
                                                            <td>
                                                                {isRecovered ? (
                                                                    <span className="status-pill status-success">
                                                                        <CheckCircle2 size={12} />
                                                                        <span>Recovered</span>
                                                                    </span>
                                                                ) : isOrderCreated ? (
                                                                    <span className="status-pill status-executing">
                                                                        <span>Order Created</span>
                                                                    </span>
                                                                ) : isBlocked ? (
                                                                    <span className="status-pill status-blocked">
                                                                        <span>Blocked</span>
                                                                    </span>
                                                                ) : isFailed ? (
                                                                    <span className="status-pill status-failed">
                                                                        <span>Failed</span>
                                                                    </span>
                                                                ) : (
                                                                    <span className="status-pill status-ready">
                                                                        <span>Ready</span>
                                                                    </span>
                                                                )}
                                                            </td>

                                                            {/* ACTIONS */}
                                                            <td style={{ textAlign: "right" }}>
                                                                <div className="tx-action-group">
                                                                    {/* ANALYZE BUTTON */}
                                                                    <button
                                                                        className={`tx-btn ${
                                                                            isAnalyzed
                                                                                ? "tx-btn-secondary"
                                                                                : "tx-btn-primary"
                                                                        }`}
                                                                        onClick={() => {
                                                                            if (isAnalyzed) {
                                                                                setExpandedTxId(
                                                                                    isExpanded
                                                                                        ? null
                                                                                        : txId
                                                                                );
                                                                            } else {
                                                                                handleAnalyzeTx(
                                                                                    incident,
                                                                                    tx
                                                                                );
                                                                            }
                                                                        }}
                                                                        disabled={isCurrentlyAnalyzing}
                                                                    >
                                                                        <BrainCircuit
                                                                            size={13}
                                                                            className={
                                                                                isCurrentlyAnalyzing
                                                                                    ? "spin"
                                                                                    : ""
                                                                            }
                                                                        />
                                                                        <span>
                                                                            {isCurrentlyAnalyzing
                                                                                ? "Analyzing..."
                                                                                : isAnalyzed
                                                                                ? isExpanded
                                                                                    ? "Hide Report"
                                                                                    : "View Report"
                                                                                : "Analyze"}
                                                                        </span>
                                                                        {isAnalyzed &&
                                                                            (isExpanded ? (
                                                                                <ChevronUp size={12} />
                                                                            ) : (
                                                                                <ChevronDown
                                                                                    size={12}
                                                                                />
                                                                            ))}
                                                                    </button>

                                                                    {/* CHECKOUT BUTTON (IF ORDER READY) */}
                                                                    {isOrderCreated && orderId && !isRecovered && (
                                                                        <button
                                                                            className="tx-btn tx-btn-checkout"
                                                                            onClick={() =>
                                                                                openCheckout(
                                                                                    tx,
                                                                                    orderId,
                                                                                    tx.amount
                                                                                )
                                                                            }
                                                                            title="Open Razorpay Checkout Simulation"
                                                                        >
                                                                            <span>Checkout</span>
                                                                            <ExternalLink size={12} />
                                                                        </button>
                                                                    )}

                                                                    {/* RECOVERED CONFIRMATION BADGE */}
                                                                    {isRecovered && (
                                                                        <span className="tx-recovered-badge tabular">
                                                                            <Check size={12} />
                                                                            <span>
                                                                                ₹
                                                                                {Number(
                                                                                    actualRecovery ||
                                                                                        tx.amount
                                                                                ).toLocaleString(
                                                                                    "en-IN",
                                                                                    {
                                                                                        maximumFractionDigits: 0,
                                                                                    }
                                                                                )}
                                                                            </span>
                                                                        </span>
                                                                    )}
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

                            {/* INLINE AI REPORT EXPANSION (FOR EXPANDED TRANSACTION) */}
                            {expandedTxId &&
                                queue.some((t) => t.id === expandedTxId) &&
                                (() => {
                                    const activeTx = queue.find((t) => t.id === expandedTxId);
                                    const res = analysisResults[expandedTxId];
                                    if (!res) return null;

                                    if (res.error) {
                                        return (
                                            <div className="analysis-result">
                                                <div className="api-error">
                                                    <span>Analysis Error: {res.error}</span>
                                                </div>
                                            </div>
                                        );
                                    }

                                    const analysisData =
                                        res.analysis?.analysis || res.analysis;
                                    const txData = res.transaction || activeTx;
                                    const mlDecision = analysisData?.ml_decision;
                                    const policy = analysisData?.policy;
                                    const llm = analysisData?.llm;

                                    const execution = res.execution;
                                    const rawStatus = (
                                        execution?.status ||
                                        execution?.recovery?.status ||
                                        activeTx.recovery_status ||
                                        ""
                                    ).toUpperCase();

                                    const isSuccess =
                                        rawStatus === "SUCCESS" || rawStatus === "RECOVERED";
                                    const isOrderCreated =
                                        rawStatus === "ORDER_CREATED" ||
                                        rawStatus === "EXECUTING";
                                    const isExecuting = executingTxId === expandedTxId;

                                    const orderId =
                                        execution?.razorpay_order_id ||
                                        execution?.recovery?.razorpay_order_id ||
                                        execution?.order_id ||
                                        activeTx.razorpay_order_id;

                                    const recoveredAmount =
                                        execution?.recovered_amount ??
                                        execution?.recovery?.recovered_amount ??
                                        execution?.actual_recovery ??
                                        execution?.recovery?.actual_recovery ??
                                        txData?.amount ??
                                        0;

                                    return (
                                        <div className="analysis-result active-expanded-report">
                                            <div className="expanded-report-header">
                                                <div className="expanded-report-title">
                                                    <BrainCircuit size={16} />
                                                    <span>
                                                        AI DIAGNOSTIC REPORT · {expandedTxId}
                                                    </span>
                                                </div>
                                                <button
                                                    className="expanded-close-btn"
                                                    onClick={() => setExpandedTxId(null)}
                                                >
                                                    Close Report
                                                </button>
                                            </div>

                                            <div className="ai-report-presentation-box">
                                                <AIIncidentReport
                                                    transaction={txData}
                                                    mlDecision={mlDecision}
                                                    llm={llm}
                                                    policy={policy}
                                                />

                                                {/* EXECUTE RECOVERY BUTTON */}
                                                {policy?.decision === "ALLOW" &&
                                                    !isSuccess &&
                                                    !isOrderCreated && (
                                                        <div style={{ marginTop: "18px" }}>
                                                            <button
                                                                className="execute-recovery-btn"
                                                                onClick={() =>
                                                                    handleExecuteTx(
                                                                        incident,
                                                                        activeTx
                                                                    )
                                                                }
                                                                disabled={isExecuting}
                                                            >
                                                                <ShieldCheck size={16} />
                                                                <span>
                                                                    {isExecuting
                                                                        ? "Generating Razorpay Order..."
                                                                        : "Execute Recovery Action"}
                                                                </span>
                                                            </button>
                                                        </div>
                                                    )}

                                                {/* ORDER CREATED SECTION */}
                                                {isOrderCreated && orderId && !isSuccess && (
                                                    <div className="order-created-section">
                                                        <div className="order-info">
                                                            <strong>
                                                                RECOVERY PAYMENT ORDER READY
                                                            </strong>
                                                            <span className="tabular">
                                                                ORDER_CREATED · {orderId}
                                                            </span>
                                                        </div>
                                                        <button
                                                            className="checkout-button"
                                                            onClick={() =>
                                                                openCheckout(
                                                                    activeTx,
                                                                    orderId,
                                                                    activeTx.amount
                                                                )
                                                            }
                                                        >
                                                            <span>Open Razorpay Checkout</span>
                                                            <ExternalLink size={14} />
                                                        </button>
                                                    </div>
                                                )}

                                                {/* RECOVERY VERIFIED BADGE */}
                                                {isSuccess && (
                                                    <div className="recovery-verified-badge">
                                                        <div className="verified-checkmark-icon">
                                                            <CheckCircle2 size={24} />
                                                        </div>
                                                        <span className="verified-title">
                                                            RECOVERY VERIFIED
                                                        </span>
                                                        <div className="verified-amount-hero tabular">
                                                            ₹
                                                            {Number(
                                                                recoveredAmount
                                                            ).toLocaleString("en-IN", {
                                                                minimumFractionDigits: 2,
                                                                maximumFractionDigits: 2,
                                                            })}
                                                        </div>
                                                        <span className="verified-meta-caption">
                                                            Revenue successfully recovered · Verified
                                                            payment
                                                        </span>
                                                    </div>
                                                )}

                                                {/* EXECUTION ERROR */}
                                                {res.executionError && (
                                                    <div
                                                        className="api-error"
                                                        style={{ marginTop: "16px" }}
                                                    >
                                                        {res.executionError}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })()}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}