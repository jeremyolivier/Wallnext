from pydantic import BaseModel


class Image(BaseModel):
    startdate: str  # YYYYMMDD
    urlbase: str  # e.g. "/th?id=OHR.GrizzlySwim_EN-US5133524829"
    title: str


class Archive(BaseModel):
    images: list[Image]
