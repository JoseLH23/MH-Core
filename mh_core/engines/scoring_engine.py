class ScoringEngine:

    def calculate_video_score(self, video: dict) -> float:
        views = video.get("views", 0)
        views_per_day = video.get("views_per_day", 0)
        likes = video.get("likes", 0)
        age_days = video.get("age_days", 1)

        if age_days <= 0:
            age_days = 1

        growth_score = min(views_per_day / 1000, 40)
        views_score = min(views / 100000, 25)
        engagement_score = min((likes / max(views, 1)) * 1000, 15)
        freshness_score = max(0, 10 - (age_days / 30))
        stability_score = 10

        final_score = (
            growth_score +
            views_score +
            engagement_score +
            freshness_score +
            stability_score
        )

        return round(final_score, 2)

    def score_videos(self, videos: list[dict]) -> list[dict]:
        scored_videos = []

        for video in videos:
            video["mh_score"] = self.calculate_video_score(video)
            scored_videos.append(video)

        return scored_videos
    