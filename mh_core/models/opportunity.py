from pydantic import BaseModel


class Opportunity(BaseModel):
    title: str
    channel: str
    views: int = 0
    views_per_day: float = 0
    source: str = "youtube"
    url: str = ""
    score: float = 0