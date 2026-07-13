import os
import csv
import math
import requests
from pathlib import Path
from datetime import datetime, timezone
from mh_core.config import (
    YOUTUBE_SEARCH_QUERIES,
    YOUTUBE_MAX_RESULTS_PER_QUERY,
    YOUTUBE_REGION_CODE,
    YOUTUBE_RELEVANCE_LANGUAGE
)
from mh_core.utils.logger import logger
from mh_core.utils.retry import reintentar_con_backoff


class YouTubeResearchEngine:
    def __init__(self):
        self.api_key = os.environ.get("YOUTUBE_API_KEY")

    def research(self, project):
        if not self.api_key:
            logger.warning("YouTubeResearchEngine: no se encontró YOUTUBE_API_KEY. Usando tema normal.")
            return None

        logger.info("YouTubeResearchEngine: investigando YouTube con datos reales...")
        all_items = []

        for query in YOUTUBE_SEARCH_QUERIES:
            try:
                ids = self._search_video_ids(query)
                if ids:
                    all_items.extend(self._get_video_details(ids, query))
            except Exception as e:
                logger.warning(f"YouTubeResearchEngine: falló búsqueda '{query}': {e}")

        if not all_items:
            logger.warning("YouTubeResearchEngine: YouTube no devolvió resultados útiles.")
            return None

        ranked = sorted(all_items, key=lambda x: x["score"], reverse=True)
        report_path = Path(project) / "youtube_research_report.csv"
        summary_path = Path(project) / "youtube_research_summary.txt"
        self._save_csv(report_path, ranked)
        summary_path.write_text(self._summary_text(ranked[:10]), encoding="utf-8")

        top = ranked[0]
        logger.info(
            "YouTubeResearchEngine: mejor oportunidad detectada — "
            f"tema='{top['query']}' | título='{top['title']}' | canal='{top['channel']}' | "
            f"vistas={top['views']} | vistas/día={top['views_per_day']:.0f} | "
            f"score={top['score']:.2f} | reporte={report_path}"
        )

        return {

            "topic": self._topic_from_winner(top),
            "winner": top,
            "top_videos": ranked[:10],
            "report_path": str(report_path)
        }

    def _search_video_ids(self, query):
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": YOUTUBE_MAX_RESULTS_PER_QUERY,
            "order": "relevance",
            "regionCode": YOUTUBE_REGION_CODE,
            "relevanceLanguage": YOUTUBE_RELEVANCE_LANGUAGE,
            "key": self.api_key,
        }
        def _pedir():
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                raise RuntimeError(f"429 Too Many Requests: {resp.text[:200]}")
            return resp

        r = reintentar_con_backoff(_pedir, nombre=f"YouTube search('{query}')")
        data = r.json()
        if r.status_code != 200:
            raise RuntimeError(data)
        return [item.get("id", {}).get("videoId") for item in data.get("items", []) if item.get("id", {}).get("videoId")]

    def _get_video_details(self, video_ids, query):
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }
        def _pedir():
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                raise RuntimeError(f"429 Too Many Requests: {resp.text[:200]}")
            return resp

        r = reintentar_con_backoff(_pedir, nombre="YouTube video details")
        data = r.json()
        if r.status_code != 200:
            raise RuntimeError(data)

        out = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            published = snippet.get("publishedAt", "")
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0)) if "likeCount" in stats else 0
            comments = int(stats.get("commentCount", 0)) if "commentCount" in stats else 0
            age_days = self._age_days(published)
            views_per_day = views / max(age_days, 1)
            engagement = likes + comments * 2
            engagement_rate = engagement / max(views, 1)
            score = self._score(views, views_per_day, engagement_rate, age_days, title)
            out.append({
                "query": query,
                "video_id": item.get("id", ""),
                "title": title,
                "channel": channel,
                "published_at": published,
                "age_days": age_days,
                "views": views,
                "likes": likes,
                "comments": comments,
                "views_per_day": views_per_day,
                "engagement_rate": engagement_rate,
                "score": score,
                "url": f"https://www.youtube.com/watch?v={item.get('id', '')}"
            })
        return out

    def _age_days(self, published_at):
        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return max((now - dt).total_seconds() / 86400, 0.1)
        except Exception:
            return 999

    def _score(self, views, views_per_day, engagement_rate, age_days, title):
        growth = math.log10(views_per_day + 10) * 35
        volume = math.log10(views + 10) * 12
        engagement = min(engagement_rate * 1000, 30)
        freshness_bonus = 20 if age_days <= 7 else 10 if age_days <= 30 else 3 if age_days <= 90 else 0
        hook_bonus = self._hook_bonus(title)
        return growth + volume + engagement + freshness_bonus + hook_bonus

    def _hook_bonus(self, title):
        t = title.lower()
        patterns = ["por qué", "cómo", "nadie", "esto", "secreto", "verdad", "descubrieron", "no sabías", "misterio", "cerebro", "inteligencia artificial", "ia"]
        return sum(3 for p in patterns if p in t)

    def _topic_from_winner(self, winner):
        return (
            f"{winner['query']}: inspirado en el patrón viral '{winner['title']}'. "
            "Crea un video original, no copies el contenido, solo usa el tema general y el tipo de curiosidad."
        )

    def _save_csv(self, path, rows):
        fields = ["score", "query", "title", "channel", "views", "views_per_day", "likes", "comments", "engagement_rate", "age_days", "published_at", "url"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fields})

    def _summary_text(self, rows):
        lines = ["MINDHIGH YOUTUBE RESEARCH SUMMARY", ""]
        for i, row in enumerate(rows, 1):
            lines += [
                f"{i}. {row['title']}",
                f"   Query: {row['query']}",
                f"   Canal: {row['channel']}",
                f"   Vistas: {row['views']}",
                f"   Vistas/día: {row['views_per_day']:.0f}",
                f"   Score: {row['score']:.2f}",
                f"   URL: {row['url']}",
                ""
            ]
        return "\n".join(lines)
