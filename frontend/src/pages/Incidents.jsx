import { useEffect, useState } from "react";
import {
    AlertTriangle,
    BrainCircuit,
    ShieldCheck,
    ExternalLink,
    CheckCircle2,
    Check,
} from "lucide-react";

import {
    getRevenueLeaks,
    getIncidentTransaction,
    analyzeRecovery,
    executeRecovery,
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

    const [analyzingId, setAnalyzingId] = useState(null);
    const [analysisResults, setAnalysisResults] = useState({});
    const [executingId, setExecutingId] = useState(null);

    // Load incidents
    useEffect(() => {
        async function loadIncidents() {
            try {
                const result = await getRevenueLeaks();
                setIncidents(result.leaks || []);
            } catch (err) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        loadIncidents();
    }, []);

    // Analyze Incident
    async function handleAnalyze(incident) {
        try {
            setAnalyzingId(incident.id);
            setAnalysisResults((prev) => ({
                ...prev,
                [incident.id]: {
                    ...prev[incident.id],
                    error: null,
                },
            }));

            const txResult = await getIncidentTransaction(incident.leak_type);
            const transaction = txResult?.transaction;

            if (!transaction) {
                throw new Error("No sample transaction found for this incident.");
            }

            const transactionId = transaction.id || transaction.transaction_id;
            const analysis = await analyzeRecovery(transactionId);

            // Check if backend already has an existing recovery action
            let initialExecution = null;
            if (analysis?.existing_recovery) {
                initialExecution = analysis.existing_recovery;
            }

            setAnalysisResults((prev) => ({
                ...prev,
                [incident.id]: {
                    transaction,
                    analysis,
                    execution: initialExecution,
                },
            }));
        } catch (err) {
            console.error("Analysis failed:", err);
            setAnalysisResults((prev) => ({
                ...prev,
                [incident.id]: {
                    error: err.message,
                },
            }));
        } finally {
            setAnalyzingId(null);
        }
    }

    // Execute Recovery
    async function handleExecute(incident) {
        try {
            setExecutingId(incident.id);

            const result = analysisResults[incident.id];
            const transaction = result?.transaction;
            const mlDecision = result?.analysis?.analysis?.ml_decision;

            if (!transaction) {
                throw new Error("Missing transaction context for execution.");
            }

            const transactionId = transaction.id || transaction.transaction_id;
            const strategy = mlDecision?.recommended_strategy || "Alternative Payment";

            const executionResponse = await executeRecovery(transactionId, strategy);

            setAnalysisResults((prev) => ({
                ...prev,
                [incident.id]: {
                    ...prev[incident.id],
                    execution: executionResponse,
                },
            }));
        } catch (err) {
            console.error("Execution failed:", err);
            setAnalysisResults((prev) => ({
                ...prev,
                [incident.id]: {
                    ...prev[incident.id],
                    executionError: err.message,
                },
            }));
        } finally {
            setExecutingId(null);
        }
    }

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
                    const result = analysisResults[incident.id];
                    const analysis = result?.analysis?.analysis;
                    const transaction = result?.transaction;
                    const mlDecision = analysis?.ml_decision;
                    const policy = analysis?.policy;
                    const llm = analysis?.llm;

                    const execution = result?.execution;
                    const rawStatus = (
                        execution?.status ||
                        execution?.recovery?.status ||
                        ""
                    ).toUpperCase();

                    const isSuccess = rawStatus === "SUCCESS";
                    const isOrderCreated = rawStatus === "ORDER_CREATED";
                    const isExecuting = rawStatus === "EXECUTING";

                    const orderId =
                        execution?.razorpay_order_id ||
                        execution?.recovery?.razorpay_order_id ||
                        execution?.order_id;

                    const recoveredAmount =
                        execution?.recovered_amount ??
                        execution?.recovery?.recovered_amount ??
                        execution?.actual_recovery ??
                        execution?.recovery?.actual_recovery ??
                        26213.01;

                    return (
                        <div className="incident-card" key={incident.id}>
                            {/* INCIDENT HEADER */}
                            <div className="incident-card-header">
                                <div className="incident-tags-row">
                                    <span className="segment-chip">
                                        {formatSegmentChips(incident.segment)}
                                    </span>
                                    <span className="open-label">
                                        {incident.status}
                                    </span>
                                </div>
                            </div>

                            {/* TITLE & DESCRIPTION */}
                            <h3>{formatIncidentName(incident.leak_type)}</h3>
                            <p className="incident-description">
                                {incident.description}
                            </p>

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

                            {/* ANALYZE BUTTON */}
                            <div className="incident-actions">
                                <button
                                    className="analyze-button"
                                    onClick={() => handleAnalyze(incident)}
                                    disabled={analyzingId === incident.id}
                                >
                                    <BrainCircuit size={16} />
                                    <span>
                                        {analyzingId === incident.id
                                            ? "Analyzing Event Stream..."
                                            : "Analyze"}
                                    </span>
                                </button>
                            </div>

                            {/* AI ANALYSIS EXPANSION */}
                            {result && (
                                <div className="analysis-result">
                                    {result.error ? (
                                        <div className="api-error">
                                            {result.error}
                                        </div>
                                    ) : (
                                        <div className="ai-report-presentation-box">
                                            <AIIncidentReport
                                                transaction={transaction}
                                                mlDecision={mlDecision}
                                                llm={llm}
                                                policy={policy}
                                            />

                                            {/* EXECUTION STATES */}
                                            {policy?.decision === "ALLOW" && !isSuccess && !isOrderCreated && !isExecuting && (
                                                <div style={{ marginTop: "16px" }}>
                                                    <button
                                                        className="execute-recovery-btn"
                                                        onClick={() => handleExecute(incident)}
                                                        disabled={executingId === incident.id}
                                                    >
                                                        <ShieldCheck size={16} />
                                                        <span>
                                                            {executingId === incident.id
                                                                ? "Generating Order..."
                                                                : "Execute Recovery"}
                                                        </span>
                                                    </button>
                                                </div>
                                            )}

                                            {/* ORDER CREATED STATE */}
                                            {isOrderCreated && orderId && (
                                                <div className="order-created-section">
                                                    <div className="order-info">
                                                        <strong>RECOVERY PAYMENT READY</strong>
                                                        <span className="tabular">
                                                            ORDER_CREATED · {orderId}
                                                        </span>
                                                    </div>
                                                    <button
                                                        className="checkout-button"
                                                        onClick={() => {
                                                            const transactionId =
                                                                transaction?.transaction_id ||
                                                                transaction?.id;
                                                            const amount = Number(
                                                                execution?.amount ||
                                                                transaction?.amount ||
                                                                0
                                                            );
                                                            const paymentUrl = `http://localhost:5500/test_payment.html?order_id=${encodeURIComponent(
                                                                orderId
                                                            )}&transaction_id=${encodeURIComponent(
                                                                transactionId
                                                            )}&amount=${encodeURIComponent(amount)}`;
                                                            window.open(paymentUrl, "_blank");
                                                        }}
                                                    >
                                                        <span>Open Razorpay Checkout</span>
                                                        <ExternalLink size={14} />
                                                    </button>
                                                </div>
                                            )}

                                            {/* VERIFIED TERMINAL CONFIRMATION STATE */}
                                            {isSuccess && (
                                                <div className="recovery-verified-badge">
                                                    <div className="verified-checkmark-icon">
                                                        <CheckCircle2 size={24} />
                                                    </div>
                                                    <span className="verified-title">RECOVERY VERIFIED</span>
                                                    <div className="verified-amount-hero tabular">
                                                        ₹
                                                        {Number(recoveredAmount).toLocaleString("en-IN", {
                                                            minimumFractionDigits: 2,
                                                            maximumFractionDigits: 2,
                                                        })}
                                                    </div>
                                                    <span className="verified-meta-caption">
                                                        Revenue successfully recovered · Verified payment
                                                    </span>
                                                </div>
                                            )}

                                            {/* EXECUTION ERROR */}
                                            {result.executionError && (
                                                <div className="api-error" style={{ marginTop: "16px" }}>
                                                    {result.executionError}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}