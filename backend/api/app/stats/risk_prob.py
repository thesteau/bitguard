def prob_to_risk(prob: float) -> str:
    if prob >= 0.6:
        return "very_high"
    elif prob >= 0.5:
        return "high"
    elif prob >= 0.1:
        return "mixed_signal"
    elif prob >= 0.01:
        return "low"
    else:
        return "very_low"
