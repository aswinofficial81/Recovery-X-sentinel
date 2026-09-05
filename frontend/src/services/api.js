const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";


async function fetchAPI(endpoint) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
    }

    return response.json();
}

export async function getDashboard() {
    return fetchAPI("/api/dashboard");
}

export async function getRevenueLeaks() {
    return fetchAPI("/api/revenue-leaks");
}

export async function getRecoveryMetrics() {
    return fetchAPI("/api/recovery/metrics");
}

export async function getIncidentTransaction(incidentType) {
    const response = await fetch(
        `${API_BASE_URL}/api/recovery/incident/${encodeURIComponent(
            incidentType
        )}/transaction`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to find transaction: ${response.status}`
        );
    }

    return response.json();
}

export async function getIncidentTransactions(incidentType, limit = 20) {
    const response = await fetch(
        `${API_BASE_URL}/api/recovery/incident/${encodeURIComponent(
            incidentType
        )}/transactions?limit=${limit}`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to fetch incident transactions: ${response.status}`
        );
    }

    return response.json();
}

export async function analyzeRecovery(transactionId, timeoutMs = 15000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/recovery/analyze/${transactionId}`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                signal: controller.signal,
            }
        );

        if (!response.ok) {
            throw new Error(
                `Recovery analysis failed: ${response.status}`
            );
        }

        return await response.json();
    } catch (err) {
        if (err.name === "AbortError") {
            throw new Error("Analysis request timed out after 15 seconds. Please retry.");
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
    }
}

export async function executeRecovery(transactionId, strategy) {
    const response = await fetch(
        `${API_BASE_URL}/api/recovery/execute/${transactionId}?strategy=${encodeURIComponent(
            strategy
        )}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        }
    );

    if (!response.ok) {
        throw new Error(
            `Recovery execution failed: ${response.status}`
        );
    }

    return response.json();
}

export async function getAuditLogs() {
    return fetchAPI("/api/audit-logs");
}

export async function getRecoveryActions() {
    return fetchAPI("/api/recovery/actions");
}

export async function getAnalytics() {
    return fetchAPI("/api/analytics");
}