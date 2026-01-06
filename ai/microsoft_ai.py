# Microsoft Azure AI Simulation Layer

def login_risk_score(attempts, ip_reuse):
    score = 10
    if attempts >= 3:
        score += 40
    if ip_reuse:
        score += 30
    return min(score, 100)


def vote_anomaly_score(votes_per_min):
    if votes_per_min > 5:
        return 85
    elif votes_per_min > 3:
        return 60
    return 15