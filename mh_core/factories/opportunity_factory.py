from mh_core.models.opportunity import Opportunity


class OpportunityFactory:
    @staticmethod
    def from_youtube_video(video: dict) -> Opportunity:
        return Opportunity(
            title=video.get("title", ""),
            channel=video.get("channel", ""),
            views=video.get("views", 0),
            views_per_day=video.get("views_per_day", 0),
            source="youtube",
            url=video.get("url", ""),
            score=video.get("score", 0),
        )