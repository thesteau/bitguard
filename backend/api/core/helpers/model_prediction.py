def predict_score(model, X_scaled):
    return int(((1 - model.predict_proba(X_scaled)[:, 1]) * 100).round().astype(int)[0])
