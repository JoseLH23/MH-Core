from mh_core.models.opportunity import Opportunity
from mh_core.engines.scoring_engine import ScoringEngine


class RankingEngine:

    @staticmethod
    def rank(opportunities: list[Opportunity]) -> list[Opportunity]:
        return sorted(
            opportunities,
            key=lambda opportunity: opportunity.score,
            reverse=True
        )

    def rank_videos(self, videos: list[dict]) -> list[dict]:
        scoring_engine = ScoringEngine()
        scored_videos = scoring_engine.score_videos(videos)

        ranked = sorted(
            scored_videos,
            key=lambda video: video.get("mh_score", 0),
            reverse=True
        )

        for index, video in enumerate(ranked, start=1):
            mh_score = video.get("mh_score", 0)

            video["rank"] = index
            video["opportunity_score"] = mh_score

            if mh_score >= 70:
                video["priority"] = "HIGH"
            elif mh_score >= 40:
                video["priority"] = "MEDIUM"
            else:
                video["priority"] = "LOW"

        return ranked