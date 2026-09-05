from agent.llm_client import ask_llm
from ml.models.strategy_ranking import rank_strategies
from ml.models.policy_engine import evaluate_policy
from ml.models.recovery_executor import execute_recovery


def analyze_recovery(
    transaction: dict,
    incident_type: str,
    revenue_at_risk: float,
    execute: bool = False
):
    """
    RecoverX Sentinel decision pipeline:

    1. ML ranks recovery strategies
    2. LLM explains the ML decision
    3. Policy engine validates the recommended strategy

    The LLM never has authority to bypass policy.
    """

    # ---------------------------------------------------------
    # STEP 1: Make sure incident type is available to ML
    # ---------------------------------------------------------

    transaction["incident_type"] = incident_type

    # ---------------------------------------------------------
    # STEP 2: ML strategy ranking
    # ---------------------------------------------------------

    rankings = rank_strategies(transaction)

    if not rankings:
        raise ValueError(
            "ML strategy ranking returned no strategies"
        )

    best_strategy = rankings[0]
    print(
        f"[ANALYZE] ML ranking completed: recommended={best_strategy['strategy']} (prob={best_strategy['recovery_probability']})",
        flush=True
    )

    strategy_summary = []

    for result in rankings:
        strategy_summary.append({
            "rank": result["rank"],
            "strategy": result["strategy"],
            "recovery_probability": round(
                result["recovery_probability"],
                4
            ),
            "expected_recovery": round(
                result["expected_recovery"],
                2
            )
        })

    # ---------------------------------------------------------
    # STEP 3: LLM analysis
    # ---------------------------------------------------------

    safe_transaction = {
        "transaction_id": transaction.get("transaction_id"),
        "merchant_id": transaction.get("merchant_id"),
        "customer_id": transaction.get("customer_id"),
        "amount": transaction.get("amount"),
        "currency": transaction.get("currency"),
        "payment_method": transaction.get("payment_method"),
        "status": transaction.get("status"),
        "failure_reason": transaction.get("failure_reason"),
        "device": transaction.get("device"),
        "location": transaction.get("location"),
        "retry_count": transaction.get("retry_count", 0)
    }

    prompt = f"""
Analyze this revenue recovery incident.

Transaction:
{safe_transaction}

Incident type:
{incident_type}

Revenue at risk:
₹{revenue_at_risk:.2f}

ML Strategy Rankings:
{strategy_summary}

The ML model ranks:

Recommended strategy:
{best_strategy["strategy"]}

Recovery probability:
{best_strategy["recovery_probability"] * 100:.2f}%

Expected recovery:
₹{best_strategy["expected_recovery"]:.2f}

Provide:

1. Root cause explanation
2. Explanation of why the ML-ranked strategy is appropriate
3. Comparison with the other available strategy
4. Expected recovery reasoning
5. Risks or limitations

Important rules:

- Only use facts provided in the transaction.
- Clearly distinguish facts from possible explanations.
- Do not invent a specific bank, gateway, issuer, or failure cause.
- Do not claim money has been recovered.
- Expected recovery is only a prediction.
- Do not bypass policy restrictions.
- The deterministic policy engine has final authority.
"""

    print("[ANALYZE] LLM analysis started", flush=True)
    llm_result = ask_llm(prompt)
    print(
        f"[ANALYZE] LLM analysis completed (fallback_used={llm_result.get('fallback_used')})",
        flush=True
    )

    # ---------------------------------------------------------
    # STEP 4: POLICY ENGINE
    # ---------------------------------------------------------

    policy_result = evaluate_policy(
        transaction,
        best_strategy["strategy"]
    )
    print(
        f"[ANALYZE] policy evaluation completed: decision={policy_result.get('decision')}",
        flush=True
    )

    
    execution_result = None

    if execute:
        transaction["expected_recovery"] = best_strategy[
            "expected_recovery"
        ]

        execution_result = execute_recovery(
            transaction,
            best_strategy["strategy"]
        )

    # ---------------------------------------------------------
    # STEP 5: Final result
    # ---------------------------------------------------------

    return {
        "incident_type": incident_type,
        "revenue_at_risk": revenue_at_risk,

        "ml_decision": {
            "recommended_strategy": best_strategy["strategy"],
            "recovery_probability": best_strategy[
                "recovery_probability"
            ],
            "expected_recovery": best_strategy[
                "expected_recovery"
            ],
            "rankings": strategy_summary
        },

        "llm": llm_result,

        "policy": policy_result,

        "execution": execution_result
    }