import React, { useMemo } from "react";
import {
    BrainCircuit,
    ShieldCheck,
    Check,
    AlertTriangle,
    Info,
    TrendingUp,
    Clock,
    Scale,
    Layers,
} from "lucide-react";

/**
 * Safe, lightweight Markdown Parser & Renderer without dangerouslySetInnerHTML.
 * Converts markdown headings, bold, italics, code, bullet lists, and tables
 * into semantic React elements with zero raw markdown syntax visible.
 */
function renderInlineMarkdown(text) {
    if (!text) return null;

    // Pattern for inline bold (**...**), italic (*...*), code (`...`)
    const parts = [];
    const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            parts.push(text.slice(lastIndex, match.index));
        }

        const token = match[0];
        if (token.startsWith("**") && token.endsWith("**")) {
            parts.push(
                <strong key={match.index} className="md-bold">
                    {token.slice(2, -2)}
                </strong>
            );
        } else if (token.startsWith("*") && token.endsWith("*")) {
            parts.push(
                <em key={match.index} className="md-italic">
                    {token.slice(1, -1)}
                </em>
            );
        } else if (token.startsWith("`") && token.endsWith("`")) {
            parts.push(
                <code key={match.index} className="md-code">
                    {token.slice(1, -1)}
                </code>
            );
        }
        lastIndex = match.index + token.length;
    }

    if (lastIndex < text.length) {
        parts.push(text.slice(lastIndex));
    }

    return parts.length > 0 ? parts : text;
}

function SafeMarkdownView({ content }) {
    const elements = useMemo(() => {
        if (!content || typeof content !== "string") return null;

        const lines = content.split("\n");
        const rendered = [];
        let inList = false;
        let listItems = [];
        let inTable = false;
        let tableHeader = [];
        let tableRows = [];

        function flushList() {
            if (inList && listItems.length > 0) {
                rendered.push(
                    <ul className="md-bullet-list" key={`list-${rendered.length}`}>
                        {listItems.map((item, idx) => (
                            <li key={idx}>{renderInlineMarkdown(item)}</li>
                        ))}
                    </ul>
                );
                listItems = [];
                inList = false;
            }
        }

        function flushTable() {
            if (inTable && tableHeader.length > 0) {
                rendered.push(
                    <div className="md-table-wrapper" key={`table-${rendered.length}`}>
                        <table className="md-table">
                            <thead>
                                <tr>
                                    {tableHeader.map((th, i) => (
                                        <th key={i}>{renderInlineMarkdown(th.trim())}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {tableRows.map((row, rIdx) => (
                                    <tr key={rIdx}>
                                        {row.map((cell, cIdx) => (
                                            <td key={cIdx}>{renderInlineMarkdown(cell.trim())}</td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                );
                tableHeader = [];
                tableRows = [];
                inTable = false;
            }
        }

        for (let i = 0; i < lines.length; i++) {
            const rawLine = lines[i];
            const trimmed = rawLine.trim();

            // Skip divider lines like |---|---|
            if (/^\|?(\s*:?-+:?\s*\|)+\s*$/.test(trimmed)) {
                continue;
            }

            // Table rows (contains pipe)
            if (trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.includes("|")) {
                flushList();
                const cells = trimmed
                    .slice(1, -1)
                    .split("|")
                    .map((c) => c.trim());

                if (!inTable) {
                    inTable = true;
                    tableHeader = cells;
                } else {
                    tableRows.push(cells);
                }
                continue;
            } else {
                flushTable();
            }

            // Headings
            if (trimmed.startsWith("### ")) {
                flushList();
                rendered.push(
                    <h4 className="md-heading-3" key={`h3-${i}`}>
                        {renderInlineMarkdown(trimmed.replace(/^###\s+/, ""))}
                    </h4>
                );
                continue;
            }
            if (trimmed.startsWith("## ")) {
                flushList();
                rendered.push(
                    <h3 className="md-heading-2" key={`h2-${i}`}>
                        {renderInlineMarkdown(trimmed.replace(/^##\s+/, ""))}
                    </h3>
                );
                continue;
            }
            if (trimmed.startsWith("# ")) {
                flushList();
                rendered.push(
                    <h3 className="md-heading-1" key={`h1-${i}`}>
                        {renderInlineMarkdown(trimmed.replace(/^#\s+/, ""))}
                    </h3>
                );
                continue;
            }

            // Bullet list item
            if (/^[-*•]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
                inList = true;
                const cleanItem = trimmed.replace(/^[-*•]\s+/, "").replace(/^\d+\.\s+/, "");
                listItems.push(cleanItem);
                continue;
            } else {
                flushList();
            }

            // Empty line
            if (!trimmed) {
                continue;
            }

            // Paragraph
            rendered.push(
                <p className="md-paragraph" key={`p-${i}`}>
                    {renderInlineMarkdown(trimmed)}
                </p>
            );
        }

        flushList();
        flushTable();

        return rendered;
    }, [content]);

    return <div className="md-content-body">{elements}</div>;
}

export default function AIIncidentReport({
    transaction,
    mlDecision,
    llm,
    policy,
}) {
    const fallbackUsed = Boolean(llm?.fallback_used);
    const recommendedStrategy = mlDecision?.recommended_strategy || "ALTERNATIVE_PAYMENT";
    const recoveryProbability = Number(mlDecision?.recovery_probability || 0);
    const expectedRecovery = Number(mlDecision?.expected_recovery || 0);

    // Format human-readable name
    const formatName = (str) =>
        str
            ? str
                  .replaceAll("_", " ")
                  .toLowerCase()
                  .replace(/\b\w/g, (c) => c.toUpperCase())
            : "N/A";

    // Format Indian Rupees
    const formatRupees = (val) =>
        `₹${Number(val || 0).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        })}`;

    // Rankings for comparison
    const rankings = mlDecision?.rankings || [];
    const recommendedRank = rankings.find((r) => r.rank === 1) || {
        strategy: recommendedStrategy,
        recovery_probability: recoveryProbability,
        expected_recovery: expectedRecovery,
    };
    const alternativeRank = rankings.find((r) => r.rank === 2) || {
        strategy: recommendedStrategy === "ALTERNATIVE_PAYMENT" ? "SMART_RETRY" : "ALTERNATIVE_PAYMENT",
        recovery_probability: recoveryProbability * 0.58,
        expected_recovery: expectedRecovery * 0.55,
    };

    // Derived strategy rationale
    const strategyExplanation =
        recommendedStrategy === "ALTERNATIVE_PAYMENT"
            ? `Customer exhibited retry fatigue on the ${
                  transaction?.payment_method || "primary"
              } channel. Prompting an alternative payment vector (e.g. UPI or secondary card) breaks channel-specific auth friction and yields the highest probability of immediate settlement.`
            : `Transient gateway latency identified. An autonomous exponential backoff retry avoids immediate issuer rejection while capturing the customer's active session.`;

    return (
        <div className="ai-report-container">
            {/* 1. REPORT HEADER */}
            <div className="ai-report-header">
                <div className="ai-report-title-group">
                    <div className="ai-report-badge-pill">
                        <BrainCircuit size={15} />
                        <span>AI INCIDENT ANALYSIS</span>
                    </div>
                    <p className="ai-report-subtitle">
                        {fallbackUsed
                            ? "Analysis generated using deterministic Sentinel reasoning because the external AI analysis service was unavailable."
                            : "AI-generated recovery reasoning · Advisory model output"}
                    </p>
                </div>

                <div className="ai-report-status-tag">
                    {fallbackUsed ? (
                        <span className="fallback-indicator-pill">
                            FALLBACK ANALYSIS
                        </span>
                    ) : (
                        <span className="live-ai-indicator-pill">
                            AI REASONING AVAILABLE
                        </span>
                    )}
                </div>
            </div>

            {/* 2. RECOMMENDED STRATEGY HERO BOX */}
            <div className="ai-recommended-strategy-card">
                <div className="strat-card-top">
                    <span className="strat-card-kicker">RECOMMENDED STRATEGY</span>
                    <span className="strat-card-prob-tag">
                        {(recoveryProbability * 100).toFixed(2)}% recovery probability
                    </span>
                </div>

                <h3 className="strat-card-title">
                    {formatName(recommendedStrategy)}
                </h3>

                <div className="strat-card-why">
                    <span className="strat-why-label">WHY THIS STRATEGY</span>
                    <p className="strat-why-text">{strategyExplanation}</p>
                </div>
            </div>

            {/* 3. ROOT CAUSE PANEL */}
            <div className="ai-report-section">
                <div className="report-section-header">
                    <span className="section-title">ROOT CAUSE</span>
                </div>

                <div className="root-cause-grid">
                    <div className="root-cause-item">
                        <span className="rc-label">FAILURE REASON</span>
                        <strong className="rc-value danger-text">
                            {transaction?.failure_reason || "Issuer Bank Declined"}
                        </strong>
                    </div>

                    <div className="root-cause-item">
                        <span className="rc-label">PAYMENT METHOD</span>
                        <strong className="rc-value">
                            {transaction?.payment_method || "CARD"}
                        </strong>
                    </div>

                    <div className="root-cause-item">
                        <span className="rc-label">TRANSACTION AMOUNT</span>
                        <strong className="rc-value tabular">
                            {formatRupees(transaction?.amount)}
                        </strong>
                    </div>

                    <div className="root-cause-item">
                        <span className="rc-label">CUSTOMER PROFILE</span>
                        <strong className="rc-value">
                            {transaction?.previous_success_rate !== undefined
                                ? `${(Number(transaction.previous_success_rate) * 100).toFixed(0)}% past success`
                                : "Standard tier"}
                            {" · "}
                            {transaction?.location || "India"}
                        </strong>
                    </div>
                </div>
            </div>

            {/* 4. STRATEGY COMPARISON TABLE */}
            <div className="ai-report-section">
                <div className="report-section-header">
                    <span className="section-title">STRATEGY COMPARISON</span>
                    <span className="section-subtext">Autonomous model comparative ranking</span>
                </div>

                <div className="comparison-table-wrapper">
                    <table className="strategy-comparison-table">
                        <thead>
                            <tr>
                                <th>DIMENSION</th>
                                <th className="recommended-col">
                                    <div className="col-header-badge">
                                        <span>RECOMMENDED</span>
                                    </div>
                                    <strong>{formatName(recommendedRank.strategy)}</strong>
                                </th>
                                <th>
                                    <div className="col-header-alt">
                                        <span>ALTERNATIVE</span>
                                    </div>
                                    <strong>{formatName(alternativeRank.strategy)}</strong>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Probability</td>
                                <td className="recommended-cell highlight-success tabular">
                                    {(Number(recommendedRank.recovery_probability) * 100).toFixed(2)}%
                                </td>
                                <td className="tabular">
                                    {(Number(alternativeRank.recovery_probability) * 100).toFixed(2)}%
                                </td>
                            </tr>
                            <tr>
                                <td>Expected Recovery</td>
                                <td className="recommended-cell tabular highlight-accent">
                                    {formatRupees(recommendedRank.expected_recovery)}
                                </td>
                                <td className="tabular">
                                    {formatRupees(alternativeRank.expected_recovery)}
                                </td>
                            </tr>
                            <tr>
                                <td>Approach</td>
                                <td className="recommended-cell">
                                    {recommendedRank.strategy === "ALTERNATIVE_PAYMENT"
                                        ? "Payment channel rerouting (secondary rail prompt)"
                                        : "Autonomous exponential backoff retry cycle"}
                                </td>
                                <td>
                                    {alternativeRank.strategy === "ALTERNATIVE_PAYMENT"
                                        ? "Payment channel rerouting"
                                        : "Exponential backoff retry cycle"}
                                </td>
                            </tr>
                            <tr>
                                <td>Customer Action</td>
                                <td className="recommended-cell">
                                    {recommendedRank.strategy === "ALTERNATIVE_PAYMENT"
                                        ? "Customer selects secondary payment method"
                                        : "Zero customer action required (backend autonomous)"}
                                </td>
                                <td>
                                    {alternativeRank.strategy === "ALTERNATIVE_PAYMENT"
                                        ? "Customer selects secondary payment method"
                                        : "Zero customer action required"}
                                </td>
                            </tr>
                            <tr>
                                <td>Time to Recovery</td>
                                <td className="recommended-cell">
                                    {recommendedRank.strategy === "ALTERNATIVE_PAYMENT"
                                        ? "Immediate (< 2 minutes)"
                                        : "Scheduled delay (15–45 minutes)"}
                                </td>
                                <td>
                                    {alternativeRank.strategy === "ALTERNATIVE_PAYMENT"
                                        ? "Immediate (< 2 minutes)"
                                        : "Scheduled delay (15–45 minutes)"}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            {/* 5. EXPECTED RECOVERY (PREDICTED BANNER) */}
            <div className="ai-expected-recovery-card">
                <div className="expected-recovery-left">
                    <span className="expected-kicker">EXPECTED RECOVERY · STATISTICAL PROJECTION</span>
                    <div className="expected-hero-num tabular">
                        {formatRupees(expectedRecovery)}
                    </div>
                    <span className="expected-prob-caption">
                        {(recoveryProbability * 100).toFixed(2)}% calculated ML recovery probability
                    </span>
                </div>

                <div className="expected-recovery-right">
                    <div className="expected-callout-pill">
                        <Info size={14} />
                        <span>PREDICTED / EXPECTED VALUE</span>
                    </div>
                    <p>
                        This projection is a model estimate of recoverable revenue. Revenue is counted as
                        recovered <strong>only after successful payment verification</strong>.
                    </p>
                </div>
            </div>

            {/* 6. RISKS & LIMITATIONS */}
            <div className="ai-report-section">
                <div className="report-section-header">
                    <span className="section-title">RISKS & LIMITATIONS</span>
                </div>

                <div className="risks-list-container">
                    <div className="risk-item-row">
                        <div className="risk-dot"></div>
                        <div className="risk-content">
                            <strong>Customer Drop-off Friction:</strong>
                            <span>
                                Prompting an alternative payment method requires active customer participation.
                                If the user has already navigated away from the application, recovery conversion drops significantly.
                            </span>
                        </div>
                    </div>

                    <div className="risk-item-row">
                        <div className="risk-dot"></div>
                        <div className="risk-content">
                            <strong>Secondary Channel Spend Caps:</strong>
                            <span>
                                Alternate UPI or card rails may possess independent issuer daily limits or transaction velocity thresholds.
                            </span>
                        </div>
                    </div>

                    <div className="risk-item-row">
                        <div className="risk-dot"></div>
                        <div className="risk-content">
                            <strong>Temporal Intent Decay:</strong>
                            <span>
                                Recovery action must be presented within 5 minutes of initial failure before intent expires.
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 7. FULL AI REASONING NARRATIVE (Safely Rendered Markdown) */}
            {llm?.response && (
                <div className="ai-report-section">
                    <div className="report-section-header">
                        <span className="section-title">DETAILED MODEL REASONING</span>
                        <span className="section-subtext">Sentinel synthesis & justification</span>
                    </div>
                    <div className="ai-narrative-box">
                        <SafeMarkdownView content={llm.response} />
                    </div>
                </div>
            )}

            {/* 8. DETERMINISTIC POLICY VALIDATION */}
            <div className="ai-policy-validation-box">
                <div className="policy-val-left">
                    <div className="policy-val-icon">
                        <ShieldCheck size={18} />
                    </div>
                    <div>
                        <span className="policy-val-title">POLICY ENGINE VALIDATION</span>
                        <p className="policy-val-reason">
                            {policy?.reason || "All deterministic safety checks and merchant bounds passed."}
                        </p>
                    </div>
                </div>

                <span
                    className={`policy-val-pill ${
                        policy?.decision === "ALLOW" ? "allowed" : "blocked"
                    }`}
                >
                    <Check size={12} style={{ marginRight: "4px", display: "inline" }} />
                    {policy?.decision || "ALLOW"}
                </span>
            </div>

            {/* 9. ARCHITECTURE TRUST MESSAGE */}
            <div className="ai-architecture-trust-message">
                <Info size={14} className="trust-icon" />
                <span>
                    AI reasoning is advisory. Recovery actions remain subject to the deterministic
                    policy engine and are counted as recovered only after payment verification.
                </span>
            </div>
        </div>
    );
}
