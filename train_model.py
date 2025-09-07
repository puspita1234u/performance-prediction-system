import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

DATA_PATH = "data/students.csv"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "student_model.joblib")

os.makedirs(MODEL_DIR, exist_ok=True)
df = pd.read_csv(DATA_PATH)

numeric_features = ["age","previous_marks","attendance_percent","study_hours_per_week","family_income", "assignment_score"]
categorical_features = ["gender","parental_education","internet_access","extra_classes"]

X = df[numeric_features + categorical_features]
y = df["passed"]

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
    ]
)

pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(n_estimators=200, random_state=42))
])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))
print("Confusion matrix:\n", confusion_matrix(y_test, y_pred))

joblib.dump(pipeline, MODEL_PATH)
print("Saved model to", MODEL_PATH)
