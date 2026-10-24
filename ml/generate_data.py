import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N = 600  # number of past students

# Hidden "ability" the model never sees directly (0 to 1, most students fairly able)
ability = rng.beta(4, 2, N)


def observed(spread):
    """What we can measure: ability plus noise, as a percentage."""
    return np.clip(ability + rng.normal(0, spread, N), 0.05, 1.0) * 100


attendance = observed(0.12)
assignment = observed(0.12)
test = observed(0.10)

# Final exam outcome: driven by ability plus luck, NOT by our risk formula
exam_mark = ability * 100 + rng.normal(0, 10, N)
failed = (exam_mark < 50).astype(int)

df = pd.DataFrame({
    "attendance": attendance.round(1),
    "assignment": assignment.round(1),
    "test": test.round(1),
    "failed": failed,
})

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.csv")
df.to_csv(out, index=False)
print(f"Saved {len(df)} rows to {out}")
print(f"Failure rate: {failed.mean():.1%}")