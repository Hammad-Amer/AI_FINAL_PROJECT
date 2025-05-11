import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
import os


INPUT_CSV  = "combined_data.csv"
OUTPUT_CSV = "normalized_telemetry_data.csv"
SCALER_FILE = "models/feature_pipeline.pkl"
os.makedirs(os.path.dirname(SCALER_FILE), exist_ok=True)

df = pd.read_csv(INPUT_CSV)

TARGETS = ['steer', 'accel', 'brake']
FEATURES = [c for c in df.columns if c not in TARGETS + ['time']]

X = df[FEATURES].copy()
y = df[TARGETS].copy()

bounded      = ['track' + str(i) for i in range(19)] \
             + ['opponent' + str(i) + '_dist' for i in range(1,6)] \
             + ['focusLeft','focusCenter','focusRight']

robust_feats = ['wheelSpinFL','wheelSpinFR','wheelSpinRL','wheelSpinRR']

standard_feats = [f for f in FEATURES if f not in bounded + robust_feats]

preprocessor = ColumnTransformer(transformers=[
    ("impute_and_minmax", Pipeline([
         ('imputer', SimpleImputer(strategy='mean')),
         ('scaler',  MinMaxScaler(feature_range=(0,1)))
     ]), bounded),
    ("impute_and_robust", Pipeline([
         ('imputer', SimpleImputer(strategy='mean')),
         ('scaler',  RobustScaler())
     ]), robust_feats),
    ("impute_and_standard", Pipeline([
         ('imputer', SimpleImputer(strategy='mean')),
         ('scaler',  StandardScaler())
     ]), standard_feats),
], remainder='drop', verbose=True)

X_processed = preprocessor.fit_transform(X)

X_norm = pd.DataFrame(X_processed, columns=bounded + robust_feats + standard_feats)
df_out = pd.concat([X_norm, y.reset_index(drop=True)], axis=1)

df_out.to_csv(OUTPUT_CSV, index=False)
joblib.dump(preprocessor, SCALER_FILE)

print(f" Saved normalized data to {OUTPUT_CSV}")
print(f" Saved preprocessing pipeline to {SCALER_FILE}")
