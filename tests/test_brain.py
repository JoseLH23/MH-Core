from mh_core.brain.brain_engine import MHBrain


def test_brain_report():
    brain = MHBrain()

    decision = {
        "best_opportunity": {
            "title": "Video prueba",
            "channel": "Canal prueba",
            "mh_score": 80
        }
    }

    prediction = {
        "success_probability": 85,
        "confidence": "MEDIUM",
        "risk": "LOW",
        "recommendation": "PRODUCIR"
    }

    patterns = {
        "opportunity_level": "HIGH",
        "title_patterns": {
            "question_titles": 1,
            "emotional_titles": 1
        }
    }

    learning_summary = {
        "total_memories": 10
    }

    report = brain.generate_report(
        topic="prueba",
        decision=decision,
        prediction=prediction,
        patterns=patterns,
        learning_summary=learning_summary
    )

    assert "executive_summary" in report
    assert "reasoning" in report
    assert "recommended_actions" in report