"""ML-backed scoring engine.

Implements the ``ScoringEngine`` protocol from ``engine.py`` using 
scikit-learn's Isolation Forest algorithm for anomaly detection and financial scoring.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.config import settings
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.rules import DerivedMetrics, derive


class MLScoringEngine:
    """Uses Scikit-learn IsolationForest to derive a `DerivedMetrics` object."""

    def __init__(self):
        # We initialize an Isolation Forest model. 
        # In a real-world scenario, this would be loaded from a pre-trained model file.
        self.model = IsolationForest(
            n_estimators=100, 
            contamination=0.1, 
            random_state=42
        )
        self._is_fit = False

    def _fit_dummy_data(self):
        """Fit the model on some baseline synthetic data representing 'normal' users."""
        if self._is_fit:
            return
        
        # Synthetic baseline: [monthly_income, source_count, gig_count, bank_int, push_int]
        # Normal profiles: Income between 30k-150k, 1-3 sources, 1-2 gigs
        np.random.seed(42)
        normal_data = np.column_stack([
            np.random.normal(80000, 20000, 500), # Income
            np.random.randint(1, 4, 500),        # sources
            np.random.randint(0, 3, 500),        # gigs
            np.random.randint(0, 2, 500),        # bank
            np.random.randint(0, 2, 500)         # push
        ])
        
        # Add some anomalies
        anomalies = np.column_stack([
            np.random.normal(500000, 100000, 50), # Very high income
            np.random.randint(6, 10, 50),         # high sources
            np.random.randint(4, 7, 50),          # high gigs
            np.random.randint(0, 2, 50),
            np.random.randint(0, 2, 50)
        ])
        
        X_train = np.vstack([normal_data, anomalies])
        self.model.fit(X_train)
        self._is_fit = True

    async def compute(
        self,
        *,
        monthly_income: int,
        sources: list[str],
        gig_platforms: list[str],
        has_primary_bank: bool,
        permissions_push: bool,
    ) -> DerivedMetrics:
        # Fallback to rules if AI is entirely disabled
        if not settings.ai_enabled:
            return derive(
                monthly_income=monthly_income,
                sources=sources,
                gig_platforms=gig_platforms,
                has_primary_bank=has_primary_bank,
                permissions_push=permissions_push,
            )

        self._fit_dummy_data()

        # Create the feature vector for this user
        X_user = np.array([[
            monthly_income,
            len(sources),
            len(gig_platforms),
            int(has_primary_bank),
            int(permissions_push)
        ]])

        # IsolationForest decision_function returns an anomaly score 
        # (lower is more anomalous, typical range -0.5 to 0.5)
        raw_score = self.model.decision_function(X_user)[0]
        
        # Predict returns 1 for normal, -1 for anomaly
        is_anomaly = self.model.predict(X_user)[0] == -1

        # Normalize score to a 0-100 range for risk. 
        # If raw_score is high (normal), risk is low.
        # If raw_score is low (anomalous), risk is high.
        # Assuming raw_score is roughly between -0.3 and 0.3
        normalized_score = max(0, min(100, int((raw_score + 0.3) / 0.6 * 100)))
        risk = 100 - normalized_score
        
        # Generate baseline metrics using rules to fill the rest of the object
        base_metrics = derive(
            monthly_income=monthly_income,
            sources=sources,
            gig_platforms=gig_platforms,
            has_primary_bank=has_primary_bank,
            permissions_push=permissions_push,
        )
        
        # Override the dna_score and risk based on our ML model
        # Anomaly reduces DNA score and increases risk
        dna_score = base_metrics.dna_score
        if is_anomaly:
            dna_score = max(0, dna_score - 30) # Penalize anomalous profiles
        else:
            # Boost score slightly if very normal
            dna_score = min(100, dna_score + int(normalized_score * 0.1))

        return DerivedMetrics(
            monthly_income=base_metrics.monthly_income,
            clients=base_metrics.clients,
            sorted_clients=base_metrics.sorted_clients,
            top_client_share=base_metrics.top_client_share,
            herfindahl=base_metrics.herfindahl,
            diversification_index=base_metrics.diversification_index,
            stability=base_metrics.stability,
            discipline=base_metrics.discipline,
            growth=base_metrics.growth,
            savings=base_metrics.savings,
            diversification=base_metrics.diversification,
            risk=risk,
            dna_score=dna_score,
            income_quality=base_metrics.income_quality,
            cv=base_metrics.cv,
            yoy=base_metrics.yoy,
            late_payouts=base_metrics.late_payouts,
        )


def analyze_transactions(transactions: list[dict]) -> dict:
    """
    Process incoming financial transaction data, run it through an Isolation Forest model, 
    and return an anomaly score to identify unusual financial behavior.
    
    Expected format of transactions: 
    [{"amount": 1500.0, "direction": "credit", "category": "salary"}, ...]
    """
    if not transactions:
        return {"anomaly_score": 0, "is_anomalous": False, "risk_level": "low"}
        
    df = pd.DataFrame(transactions)
    
    # Feature engineering for transactions
    # E.g. convert direction to 1 (credit), -1 (debit)
    if "direction" in df.columns:
        df["dir_val"] = df["direction"].apply(lambda x: 1 if x == "credit" else -1)
    else:
        df["dir_val"] = 1
        
    df["amount_val"] = df["amount"].astype(float) * df["dir_val"]
    
    # Simple feature extraction per transaction: amount, direction
    X = df[["amount_val"]].values
    
    # Fit isolation forest
    # (In a real app, this would be pre-trained on global transactions)
    clf = IsolationForest(contamination=0.05, random_state=42)
    clf.fit(X)
    
    scores = clf.decision_function(X)
    predictions = clf.predict(X)
    
    # Aggregate to a single user-level score
    avg_score = float(np.mean(scores))
    anomalies_count = int(np.sum(predictions == -1))
    
    # Map score to a 0-100 anomaly scale where 100 is highly anomalous
    normalized_anomaly = max(0, min(100, int((0.5 - avg_score) * 100)))
    
    risk_level = "low"
    if normalized_anomaly > 70 or anomalies_count > len(transactions) * 0.1:
        risk_level = "high"
    elif normalized_anomaly > 40:
        risk_level = "medium"
        
    return {
        "anomaly_score": normalized_anomaly,
        "is_anomalous": risk_level == "high",
        "anomalous_transaction_count": anomalies_count,
        "risk_level": risk_level
    }
