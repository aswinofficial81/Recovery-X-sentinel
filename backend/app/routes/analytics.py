from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.auth import get_current_merchant
from ml.models.revenue_risk import calculate_all_revenue_risks

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"]
)


@router.get("")
def get_analytics(
    merchant: dict = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    merchant_id = merchant["id"]

    # 1. Dynamic Incident Risks & Summary Metrics
    try:
        dynamic_risks = calculate_all_revenue_risks(merchant_id=merchant_id, db=db)
        incident_metrics = dynamic_risks.get("incidents", {})
        revenue_at_risk = sum(
            float(inc.get("revenue_at_risk", 0.0))
            for inc in incident_metrics.values()
        )
    except Exception as e:
        print(f"[ANALYTICS] Dynamic risk calculation fallback: {e}", flush=True)
        incident_metrics = {}
        leak_res = db.execute(text("""
            SELECT COALESCE(SUM(revenue_impact), 0) AS revenue_at_risk
            FROM revenue_leaks
            WHERE merchant_id = :merchant_id AND status = 'OPEN';
        """), {"merchant_id": merchant_id}).mappings().one()
        revenue_at_risk = float(leak_res["revenue_at_risk"] or 0)

    recovery_res = db.execute(text("""
        SELECT
            COUNT(*) AS total_actions,
            COUNT(*) FILTER (WHERE ra.status = 'SUCCESS') AS successful_actions,
            COUNT(*) FILTER (WHERE ra.status = 'FAILED') AS failed_actions,
            COUNT(*) FILTER (WHERE ra.status = 'BLOCKED') AS blocked_actions,
            COUNT(*) FILTER (WHERE ra.status IN ('PENDING', 'APPROVED', 'EXECUTING')) AS pending_actions,
            COALESCE(SUM(ra.expected_recovery), 0) AS total_expected_recovery,
            COALESCE(SUM(ra.actual_recovery) FILTER (WHERE ra.status = 'SUCCESS'), 0) AS total_actual_recovery
        FROM recovery_actions ra
        JOIN transactions t ON t.id = ra.transaction_id
        WHERE t.merchant_id = :merchant_id;
    """), {"merchant_id": merchant_id}).mappings().one()

    total_actions = int(recovery_res["total_actions"])
    successful_actions = int(recovery_res["successful_actions"])
    failed_actions = int(recovery_res["failed_actions"])
    pending_actions = int(recovery_res["pending_actions"])
    blocked_actions = int(recovery_res["blocked_actions"])
    expected_recovery = float(recovery_res["total_expected_recovery"] or 0)
    actual_recovered = float(recovery_res["total_actual_recovery"] or 0)
    recovery_rate = (
        (actual_recovered / expected_recovery * 100)
        if expected_recovery > 0
        else 0.0
    )

    summary = {
        "revenue_at_risk": round(revenue_at_risk, 2),
        "expected_recovery": round(expected_recovery, 2),
        "actual_recovered": round(actual_recovered, 2),
        "recovery_rate": round(recovery_rate, 2),
        "total_actions": total_actions,
        "successful_actions": successful_actions,
        "failed_actions": failed_actions,
        "pending_actions": pending_actions,
        "blocked_actions": blocked_actions
    }

    # 2. Strategy Performance
    strat_rows = db.execute(text("""
        SELECT
            ra.action_type AS strategy,
            COUNT(*) AS attempts,
            COUNT(*) FILTER (WHERE ra.status = 'SUCCESS') AS successes,
            COALESCE(SUM(ra.expected_recovery), 0) AS expected_recovery,
            COALESCE(SUM(ra.actual_recovery) FILTER (WHERE ra.status = 'SUCCESS'), 0) AS actual_recovery
        FROM recovery_actions ra
        JOIN transactions t ON t.id = ra.transaction_id
        WHERE t.merchant_id = :merchant_id
        GROUP BY ra.action_type;
    """), {"merchant_id": merchant_id}).mappings().all()

    strategy_performance = []
    for s in strat_rows:
        attempts = int(s["attempts"])
        successes = int(s["successes"])
        rate = (successes / attempts * 100) if attempts > 0 else 0.0
        strategy_performance.append({
            "strategy": s["strategy"],
            "attempts": attempts,
            "successes": successes,
            "success_rate": round(rate, 2),
            "expected_recovery": round(float(s["expected_recovery"] or 0), 2),
            "actual_recovery": round(float(s["actual_recovery"] or 0), 2)
        })

    # 3. Incident Performance
    leaks = db.execute(text("""
        SELECT leak_type, description, revenue_impact
        FROM revenue_leaks
        WHERE merchant_id = :merchant_id
        ORDER BY revenue_impact DESC;
    """), {"merchant_id": merchant_id}).mappings().all()

    tx_rows = db.execute(text("""
        SELECT
            ra.status,
            ra.expected_recovery,
            ra.actual_recovery,
            t.amount,
            t.payment_method,
            t.device,
            t.location,
            t.transaction_time
        FROM recovery_actions ra
        JOIN transactions t ON t.id = ra.transaction_id
        WHERE t.merchant_id = :merchant_id;
    """), {"merchant_id": merchant_id}).mappings().all()

    incident_performance = []
    for l in leaks:
        l_type = l["leak_type"]
        matching_actions = []
        for tx in tx_rows:
            time_hour = tx["transaction_time"].hour if tx["transaction_time"] else None
            matched = False
            if (
                l_type == "HIGH_VALUE_CARD_DEGRADATION"
                and tx["payment_method"] == "CARD"
                and tx["device"] == "IOS"
                and tx["location"] == "Mumbai"
                and float(tx["amount"]) >= 10000
            ):
                matched = True
            elif (
                l_type == "UPI_DEGRADATION"
                and tx["payment_method"] == "UPI"
                and tx["device"] == "ANDROID"
                and tx["location"] == "Bengaluru"
            ):
                matched = True
            elif (
                l_type == "EVENING_DEGRADATION"
                and time_hour is not None
                and 18 <= time_hour < 20
            ):
                matched = True

            if matched:
                matching_actions.append(tx)

        acts = len(matching_actions)
        succ = len([a for a in matching_actions if a["status"] == "SUCCESS"])
        act_rec = sum(
            float(a["actual_recovery"] or 0)
            for a in matching_actions
            if a["status"] == "SUCCESS"
        )

        dyn_incident = incident_metrics.get(l_type)
        dyn_risk = float(dyn_incident["revenue_at_risk"]) if dyn_incident else float(l["revenue_impact"] or 0)

        incident_performance.append({
            "incident_type": l_type,
            "description": l["description"],
            "revenue_at_risk": round(dyn_risk, 2),
            "actions": acts,
            "successful": succ,
            "actual_recovery": round(act_rec, 2)
        })

    # 4. Payment Method Performance
    pm_rows = db.execute(text("""
        SELECT
            t.payment_method,
            COUNT(*) AS attempts,
            COUNT(*) FILTER (WHERE ra.status = 'SUCCESS') AS successful,
            COALESCE(SUM(ra.expected_recovery), 0) AS expected_recovery,
            COALESCE(SUM(ra.actual_recovery) FILTER (WHERE ra.status = 'SUCCESS'), 0) AS actual_recovery
        FROM recovery_actions ra
        JOIN transactions t ON t.id = ra.transaction_id
        WHERE t.merchant_id = :merchant_id
        GROUP BY t.payment_method;
    """), {"merchant_id": merchant_id}).mappings().all()

    payment_method_performance = []
    for pm in pm_rows:
        attempts = int(pm["attempts"])
        succ = int(pm["successful"])
        rate = (succ / attempts * 100) if attempts > 0 else 0.0
        payment_method_performance.append({
            "payment_method": pm["payment_method"],
            "attempts": attempts,
            "successful": succ,
            "success_rate": round(rate, 2),
            "expected_recovery": round(float(pm["expected_recovery"] or 0), 2),
            "actual_recovery": round(float(pm["actual_recovery"] or 0), 2)
        })

    # 5. Recovery Timeline (Scoped to merchant)
    timeline_rows = db.execute(text("""
        SELECT
            DATE(ra.executed_at) AS rec_date,
            COALESCE(SUM(ra.actual_recovery) FILTER (WHERE ra.status = 'SUCCESS'), 0) AS daily_recovered,
            COUNT(*) FILTER (WHERE ra.status = 'SUCCESS') AS successful_actions
        FROM recovery_actions ra
        JOIN transactions t ON t.id = ra.transaction_id
        WHERE ra.executed_at IS NOT NULL
          AND t.merchant_id = :merchant_id
        GROUP BY DATE(ra.executed_at)
        ORDER BY rec_date ASC;
    """), {"merchant_id": merchant_id}).mappings().all()

    recovery_timeline = []
    cumulative = 0.0
    for r in timeline_rows:
        daily = float(r["daily_recovered"] or 0)
        cumulative += daily
        recovery_timeline.append({
            "date": r["rec_date"].isoformat() if r["rec_date"] else None,
            "daily_recovered": round(daily, 2),
            "cumulative_recovered": round(cumulative, 2),
            "successful_actions": int(r["successful_actions"])
        })

    return {
        "merchant": {
            "id": merchant["id"],
            "name": merchant["name"]
        },
        "summary": summary,
        "strategy_performance": strategy_performance,
        "incident_performance": incident_performance,
        "payment_method_performance": payment_method_performance,
        "recovery_timeline": recovery_timeline
    }
