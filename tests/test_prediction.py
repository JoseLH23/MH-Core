from mh_core.engines.prediction_engine import PredictionEngine


def test_prediction_engine():
    engine = PredictionEngine()

    decision = {
        "best_opportunity": {
            "mh_score": 75
        }
    }

    patterns = {
        "opportunity_level": "HIGH"
    }

    learning_summary = {
        "average_mh_score": 60,
        "total_memories": 10
    }

    prediction = engine.predict(
        decision=decision,
        patterns=patterns,
        learning_summary=learning_summary
    )

    assert prediction["success_probability"] > 0
    assert prediction["recommendation"] in [
        "PRODUCIR",
        "PRODUCIR_CON_CUIDADO",
        "NO_PRIORIZAR"
    ]
    assert prediction["risk"] in ["LOW", "MEDIUM", "HIGH"]