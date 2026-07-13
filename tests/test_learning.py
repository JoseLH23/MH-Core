from mh_core.engines.learning_engine import LearningEngine


def test_learning_summary():
    engine = LearningEngine()

    summary = engine.summarize_learning()

    assert isinstance(summary, dict)

    assert "total_memories" in summary
    assert "average_mh_score" in summary
    assert "most_common_topics" in summary