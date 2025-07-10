from pydantic import BaseModel
from typing import Optional
class NewsArticle(BaseModel):
    title:str
    content:str
    htmlContent:str
    author:str
    source:Optional[str] = None
    
    