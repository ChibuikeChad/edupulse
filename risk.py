from db import get_db

# Original plan: attendance 30, assignments 25, tests 20.
# Engagement and historical data don't exist in our database, so we
# scale those three weights up to add to 100%.
WEIGHTS = {"attendance": 0.40, "assignment": 0.33, "test": 0.27}


def level_for(score):
    if score <= 30:
        return "low"
    if score <= 60:
        return "moderate"
    return "high"


def compute_risk(rows):
    """rows: score records with kind, score, max_score for ONE enrollment."""
    factors = {}
    for kind in WEIGHTS:
        got = sum(r["score"] for r in rows if r["kind"] == kind)
        out_of = sum(r["max_score"] for r in rows if r["kind"] == kind)
        if out_of > 0:
            factors[kind] = round(got / out_of * 100, 1)  # percentage

    if not factors:
        return None  # no scores yet, so nothing to assess

    # If a factor has no data, share its weight among the others
    total_weight = sum(WEIGHTS[k] for k in factors)
    performance = sum(factors[k] * WEIGHTS[k] for k in factors) / total_weight
    risk = round(100 - performance, 1)

    return {
        "risk_score": risk,
        "level": level_for(risk),
        "factors": factors,
        "weakest": min(factors, key=factors.get),
    }


def recompute_all():
    conn = get_db()
    conn.execute("DELETE FROM risk_assessments")
    count = 0
    for e in conn.execute("SELECT id FROM enrollments").fetchall():
        rows = conn.execute(
            "SELECT kind, score, max_score FROM scores WHERE enrollment_id = ?", (e["id"],)
        ).fetchall()
        result = compute_risk(rows)
        if result:
            conn.execute(
                "INSERT INTO risk_assessments (enrollment_id, risk_score, level) VALUES (?,?,?)",
                (e["id"], result["risk_score"], result["level"]),
            )
            count += 1
    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    n = recompute_all()
    print(f"Assessed {n} enrollments.")
    conn = get_db()
    for r in conn.execute("SELECT level, COUNT(*) AS n FROM risk_assessments GROUP BY level"):
        print(f"  {r['level']}: {r['n']}")
    conn.close()