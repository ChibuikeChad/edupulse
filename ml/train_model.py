import os

import joblib
import matplotlib
matplotlib.use("Agg")  # save charts to a file, no pop-up window
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(HERE, "students.csv"))

FEATURES = ["attendance", "assignment", "test"]
X = df[FEATURES]
y = df["failed"]

# Hold back 25% of students the model never sees during training
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

model = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

pred = model.predict(X_test)
proba = model.predict_proba(X_test)[:, 1]  # probability of failing

print("=== Random Forest (tested on unseen students) ===")
print(f"Accuracy: {accuracy_score(y_test, pred):.1%}")
print(f"AUC:      {roc_auc_score(y_test, proba):.3f}")
print("Confusion matrix [rows = actual, columns = predicted] (0 = passed, 1 = failed):")
print(confusion_matrix(y_test, pred))
print(classification_report(y_test, pred, target_names=["passed", "failed"]))

# Compare with our rule-based formula on the same unseen students
rule_risk = 100 - (
    0.40 * X_test["attendance"] + 0.33 * X_test["assignment"] + 0.27 * X_test["test"]
)
print("=== Rule-based formula, same students ===")
print(f"AUC:      {roc_auc_score(y_test, rule_risk):.3f}")

# Which factors matter most to the model?
importances = pd.Series(model.feature_importances_, index=FEATURES).sort_values()
print("\nFeature importances:")
print(importances.sort_values(ascending=False).round(3))

plt.figure(figsize=(6, 3))
importances.plot(kind="barh", color="#2F5D50")
plt.xlabel("Importance")
plt.title("What the model relies on to predict failure")
plt.tight_layout()
plt.savefig(os.path.join(HERE, "feature_importance.png"), dpi=150)

joblib.dump(model, os.path.join(HERE, "model.joblib"))
print("\nSaved model.joblib and feature_importance.png")