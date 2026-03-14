"""
Explainability Module (SHAP / LIME Integration)

Provides functions to explain the predictions of classical machine learning models
(like XGBoost, LightGBM, RandomForest) to understand feature importance and rationale.
"""
import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List

try:
    import shap
except ImportError:
    shap = None

logger = logging.getLogger(__name__)

def generate_shap_explanation(model, X_train: np.ndarray, feature_names: List[str], X_instance: np.ndarray = None) -> Dict[str, Any]:
    """
    Generates SHAP values for a given model to explain overall feature importance 
    or a specific prediction instance.
    """
    if shap is None:
        logger.warning("SHAP is not installed. Returning fallback feature importance.")
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            sorted_idx = np.argsort(importances)[::-1]
            return {
                "top_features": [feature_names[i] for i in sorted_idx[:10]],
                "importances": [float(importances[i]) for i in sorted_idx[:10]],
                "method": "native_feature_importances"
            }
        return {"error": "SHAP not installed and model lacks native feature_importances_"}

    try:
        # Create a TreeExplainer for tree-based models (RF, XGBoost, LGBM)
        explainer = shap.TreeExplainer(model)
        
        if X_instance is not None:
            # Explain a specific prediction
            shap_values = explainer.shap_values(X_instance)
            # If binary classification, SHAP might return a list of arrays (one per class)
            if isinstance(shap_values, list):
                shap_values = shap_values[1] # Focus on positive class
            
            # Extract top contributing features for this instance
            vals = shap_values[0] if len(shap_values.shape) > 1 else shap_values
            sorted_idx = np.argsort(np.abs(vals))[::-1]
            
            return {
                "instance_explanation": True,
                "top_features": [feature_names[i] for i in sorted_idx[:10]],
                "shap_values": [float(vals[i]) for i in sorted_idx[:10]],
                "method": "shap_tree_explainer"
            }
        else:
            # Global feature importance across the dataset
            # Use a sample to speed up computation
            X_sample = X_train[:min(1000, len(X_train))]
            shap_values = explainer.shap_values(X_sample)
            
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
                
            # Calculate mean absolute SHAP values for global importance
            mean_shap = np.abs(shap_values).mean(axis=0)
            sorted_idx = np.argsort(mean_shap)[::-1]
            
            return {
                "instance_explanation": False,
                "top_features": [feature_names[i] for i in sorted_idx[:15]],
                "mean_shap_values": [float(mean_shap[i]) for i in sorted_idx[:15]],
                "method": "shap_global_importance"
            }
            
    except Exception as e:
        logger.error(f"Error generating SHAP explanation: {e}")
        return {"error": str(e)}

def get_lime_explanation(model, X_train: np.ndarray, feature_names: List[str], X_instance: np.ndarray):
    """
    Placeholder for LIME integration. LIME is particularly useful for explaining 
    individual predictions in a model-agnostic way.
    """
    # LIME implementation would go here (requires lime package)
    pass
