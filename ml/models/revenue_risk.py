import os
import sys
import pandas as pd
from sqlalchemy import text

# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../.."
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_MERCHANT_ID = "3efe1ed9-6767-47ca-9f2e-27bada51fb81"

# Incident segment definitions (standardized across recovery, analytics, leaks)
INCIDENT_SEGMENT_CONDITIONS = {
    "UPI_DEGRADATION": (
        "t.payment_method = 'UPI' AND t.location = 'Bengaluru' AND t.device = 'ANDROID'"
    ),
    "HIGH_VALUE_CARD_DEGRADATION": (
        "t.payment_method = 'CARD' AND t.location = 'Mumbai' AND t.amount >= 10000"
    ),
    "EVENING_DEGRADATION": (
        "EXTRACT(HOUR FROM t.transaction_time) >= 18 AND EXTRACT(HOUR FROM t.transaction_time) < 20"
    ),
}

DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "generated_transactions.csv"
)


# =========================================================
# LOAD CSV (OFFLINE / FALLBACK)
# =========================================================

def load_data():
    df = pd.read_csv(DATA_FILE)
    df["transaction_time"] = pd.to_datetime(df["transaction_time"])
    return df


def calculate_baseline(df):
    total_transactions = len(df)
    if total_transactions == 0:
        return 0.0
    successful_transactions = (df["status"] == "SUCCESS").sum()
    return float(successful_transactions / total_transactions)


def calculate_revenue_risk(df, incident_type, baseline_success_rate):
    """
    Offline DataFrame-based revenue risk calculation.
    """
    incident_df = df[df["incident_type"] == incident_type].copy()
    if len(incident_df) == 0:
        return None

    transaction_count = len(incident_df)
    successful_count = (incident_df["status"] == "SUCCESS").sum()
    failed_count = (incident_df["status"] == "FAILED").sum()
    actual_success_rate = successful_count / transaction_count if transaction_count > 0 else 0.0

    expected_successful_transactions = transaction_count * baseline_success_rate
    lost_transactions = max(0.0, expected_successful_transactions - successful_count)
    average_amount = incident_df["amount"].mean() if transaction_count > 0 else 0.0

    expected_revenue = expected_successful_transactions * average_amount
    actual_revenue = incident_df.loc[incident_df["status"] == "SUCCESS", "amount"].sum()
    revenue_at_risk = max(0.0, expected_revenue - actual_revenue)

    success_rate_drop = baseline_success_rate - actual_success_rate
    if success_rate_drop >= 0.20:
        severity = "CRITICAL"
    elif success_rate_drop >= 0.10:
        severity = "HIGH"
    elif success_rate_drop >= 0.05:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    confidence = min(0.99, 0.50 + (transaction_count / 1000) * 0.49) if transaction_count > 0 else 0.50

    return {
        "incident_type": incident_type,
        "transaction_count": int(transaction_count),
        "successful_transactions": int(successful_count),
        "failed_transactions": int(failed_count),
        "baseline_success_rate": round(baseline_success_rate * 100, 2),
        "actual_success_rate": round(actual_success_rate * 100, 2),
        "success_rate_drop": round(success_rate_drop * 100, 2),
        "expected_successful_transactions": round(expected_successful_transactions, 2),
        "lost_transactions": round(lost_transactions, 2),
        "average_transaction_amount": round(average_amount, 2),
        "expected_revenue": round(expected_revenue, 2),
        "actual_revenue": round(actual_revenue, 2),
        "gross_revenue_at_risk": round(revenue_at_risk, 2),
        "recovered_amount": 0.0,
        "revenue_at_risk": round(revenue_at_risk, 2),
        "severity": severity,
        "confidence": round(confidence, 2)
    }


# =========================================================
# DYNAMIC DATABASE-BACKED ENGINE
# =========================================================

def calculate_dynamic_revenue_risk_from_db(merchant_id=None, db=None):
    """
    Computes dynamic revenue at risk for all known incident types directly
    from PostgreSQL transactions and accounts for verified recovery actions.
    """
    if merchant_id is None:
        merchant_id = DEFAULT_MERCHANT_ID

    close_db = False
    if db is None:
        from backend.app.database import SessionLocal
        db = SessionLocal()
        close_db = True

    try:
        # 1. Merchant Baseline Success Rate
        baseline_row = db.execute(text("""
            SELECT
                COUNT(*) AS total_transactions,
                COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_transactions
            FROM transactions
            WHERE merchant_id = :merchant_id
        """), {"merchant_id": merchant_id}).mappings().one()

        total_tx = baseline_row["total_transactions"]
        succ_tx = baseline_row["successful_transactions"]
        baseline_rate = (succ_tx / total_tx) if total_tx > 0 else 0.0

        results = {}

        for incident_type, condition in INCIDENT_SEGMENT_CONDITIONS.items():
            # Segment metrics
            seg_query = text(f"""
                SELECT
                    COUNT(*) AS count,
                    COUNT(*) FILTER (WHERE t.status = 'SUCCESS') AS successful_count,
                    COUNT(*) FILTER (WHERE t.status = 'FAILED') AS failed_count,
                    COALESCE(AVG(t.amount), 0) AS average_amount,
                    COALESCE(SUM(t.amount) FILTER (WHERE t.status = 'SUCCESS'), 0) AS actual_revenue,
                    COALESCE(SUM(t.amount) FILTER (WHERE t.status = 'FAILED'), 0) AS failed_revenue
                FROM transactions t
                WHERE t.merchant_id = :merchant_id
                  AND ({condition})
            """)
            seg_res = db.execute(seg_query, {"merchant_id": merchant_id}).mappings().one()

            seg_count = seg_res["count"]
            seg_succ = seg_res["successful_count"]
            seg_fail = seg_res["failed_count"]
            avg_amount = float(seg_res["average_amount"])
            actual_rev = float(seg_res["actual_revenue"])

            actual_rate = (seg_succ / seg_count) if seg_count > 0 else 0.0
            drop = baseline_rate - actual_rate
            expected_succ = seg_count * baseline_rate
            expected_rev = expected_succ * avg_amount
            gross_risk = max(0.0, expected_rev - actual_rev)

            # Severity
            if drop >= 0.20:
                severity = "CRITICAL"
            elif drop >= 0.10:
                severity = "HIGH"
            elif drop >= 0.05:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            confidence = min(0.99, 0.50 + (seg_count / 1000) * 0.49) if seg_count > 0 else 0.50

            # Verified recoveries for this segment
            rec_query = text(f"""
                SELECT COALESCE(SUM(ra.actual_recovery), 0) AS recovered_amount
                FROM recovery_actions ra
                JOIN transactions t ON t.id = ra.transaction_id
                WHERE t.merchant_id = :merchant_id
                  AND ra.status = 'SUCCESS'
                  AND ({condition})
            """)
            rec_res = db.execute(rec_query, {"merchant_id": merchant_id}).mappings().one()
            recovered_amount = float(rec_res["recovered_amount"] or 0.0)

            # Net remaining revenue at risk after recoveries
            net_risk = max(0.0, gross_risk - recovered_amount)

            results[incident_type] = {
                "incident_type": incident_type,
                "transaction_count": int(seg_count),
                "successful_transactions": int(seg_succ),
                "failed_transactions": int(seg_fail),
                "baseline_success_rate": round(baseline_rate * 100, 2),
                "actual_success_rate": round(actual_rate * 100, 2),
                "success_rate_drop": round(drop * 100, 2),
                "expected_successful_transactions": round(expected_succ, 2),
                "average_transaction_amount": round(avg_amount, 2),
                "expected_revenue": round(expected_rev, 2),
                "actual_revenue": round(actual_rev, 2),
                "gross_revenue_at_risk": round(gross_risk, 2),
                "recovered_amount": round(recovered_amount, 2),
                "revenue_at_risk": round(net_risk, 2),
                "severity": severity,
                "confidence": round(confidence, 2)
            }

        return {
            "baseline_success_rate": round(baseline_rate * 100, 2),
            "incidents": results
        }

    finally:
        if close_db:
            db.close()


def get_incident_revenue_risk(incident_type, merchant_id=None, db=None):
    """
    Get dynamic revenue at risk for a specific incident type.
    Falls back gracefully if database is unavailable or incident is NORMAL.
    """
    if incident_type not in INCIDENT_SEGMENT_CONDITIONS:
        return None

    try:
        data = calculate_dynamic_revenue_risk_from_db(merchant_id=merchant_id, db=db)
        return data["incidents"].get(incident_type)
    except Exception as e:
        print(f"[REVENUE_RISK] DB calculation fallback for {incident_type}: {e}", flush=True)
        try:
            df = load_data()
            baseline = calculate_baseline(df)
            return calculate_revenue_risk(df, incident_type, baseline)
        except Exception as inner_e:
            print(f"[REVENUE_RISK] Offline fallback failed: {inner_e}", flush=True)
            return None


def calculate_all_revenue_risks(merchant_id=None, db=None):
    """
    Get dynamic revenue risk calculation for all incidents.
    """
    try:
        return calculate_dynamic_revenue_risk_from_db(merchant_id=merchant_id, db=db)
    except Exception as e:
        print(f"[REVENUE_RISK] DB calculation error, falling back to dataset: {e}", flush=True)
        df = load_data()
        baseline = calculate_baseline(df)
        incidents = {}
        for inc_type in INCIDENT_SEGMENT_CONDITIONS.keys():
            res = calculate_revenue_risk(df, inc_type, baseline)
            if res:
                incidents[inc_type] = res
        return {
            "baseline_success_rate": round(baseline * 100, 2),
            "incidents": incidents
        }


def analyze_all_incidents():
    """
    Legacy helper function maintained for backwards compatibility.
    """
    res = calculate_all_revenue_risks()
    baseline = res["baseline_success_rate"] / 100.0
    results_list = list(res["incidents"].values())
    return baseline, results_list


# =========================================================
# MAIN / CLI
# =========================================================

if __name__ == "__main__":
    print("\n========================================")
    print("       REVENUE AT RISK ENGINE (DYNAMIC)")
    print("========================================")

    res = calculate_all_revenue_risks()
    baseline = res["baseline_success_rate"]
    incidents = res["incidents"]

    print(f"\nMerchant baseline success rate: {baseline:.2f}%\n")

    total_gross = 0.0
    total_recovered = 0.0
    total_net = 0.0

    for itype, result in incidents.items():
        print("----------------------------------------")
        print(f"Incident: {result['incident_type']}")
        print(f"Transactions: {result['transaction_count']:,}")
        print(f"Success rate: {result['actual_success_rate']:.2f}% (Baseline: {result['baseline_success_rate']:.2f}%)")
        print(f"Gross revenue at risk: Rs {result.get('gross_revenue_at_risk', result['revenue_at_risk']):,.2f}")
        print(f"Verified recovered:    Rs {result.get('recovered_amount', 0.0):,.2f}")
        print(f"Net revenue at risk:   Rs {result['revenue_at_risk']:,.2f}")
        print(f"Severity: {result['severity']}, Confidence: {result['confidence']:.2f}")

        total_gross += result.get("gross_revenue_at_risk", result["revenue_at_risk"])
        total_recovered += result.get("recovered_amount", 0.0)
        total_net += result["revenue_at_risk"]

    print("\n========================================")
    print(f"TOTAL GROSS RISK: Rs {total_gross:,.2f}")
    print(f"TOTAL RECOVERED:  Rs {total_recovered:,.2f}")
    print(f"TOTAL NET RISK:   Rs {total_net:,.2f}")
    print("========================================\n")