from mh_core.engines.scoring_engine import ScoringEngine


def test_calculate_video_score():
    engine = ScoringEngine()

    video = {
        "views": 100000,
        "views_per_day": 50000,
        "likes": 5000,
        "age_days": 2
    }

    score = engine.calculate_video_score(video)

    assert isinstance(score, float)
    assert score > 0
    assert score <= 100