from mh_core.factories.opportunity_factory import OpportunityFactory
from mh_core.engines.ranking_engine import RankingEngine


def analyze_opportunities(videos: list[dict]):
    opportunities = []

    for video in videos:
        opportunity = OpportunityFactory.from_youtube_video(video)
        opportunities.append(opportunity)

    ranked_opportunities = RankingEngine.rank(opportunities)

    return {
        "total_opportunities": len(ranked_opportunities),
        "best_opportunity": ranked_opportunities[0] if ranked_opportunities else None,
        "opportunities": ranked_opportunities
    }