import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from schema import NewsArticle
from db import articles_collection
url = "https://timesofindia.indiatimes.com/business/india-business/are-you-making-digital-payments-npci-shares-5-key-tips-for-safe-upi-use-heres-how-to-avoid-getting-scammed/articleshow/122364617.cms"


def insertArticle (article:NewsArticle):
    existing = articles_collection.find_one({
        "title":article.title
    })
    if(existing):
        print("Already present")
    else:
        articles_collection.insert_one(article.model_dump())
        print("article added")   

def pageProcessor(url) :
  
   
    try:
        result = requests.get(url)
        doc = BeautifulSoup(result.text,"html.parser")
        title = doc.find("h1").text
        target_div = doc.find("div", class_="_s30J")
        content = ''.join(
         t if isinstance(t, NavigableString) else t.get_text(strip=True) if t.name == 'li' else ''
         for t in target_div.contents
        ).strip()
        htmlContent = target_div.decode_contents()
        author = doc.find("div", class_="xf8Pm byline").text
        source = "TOI"
        article =  NewsArticle(
        title=str(title),
        content=str(content),
        htmlContent=str(htmlContent),
        author=str(author),
        source=source
         )
        insertArticle(article)
    
        return article

    except:
        print("Skipping Error")


pageProcessor(url)


url_main = "https://timesofindia.indiatimes.com/business"

result = requests.get(url_main)
doc = BeautifulSoup(result.text,"html.parser")

a_tag = doc.find_all("a")
hrefs = [a.get('href') for a in a_tag if a.get('href')]
print(len(hrefs))
# hrefs_to_process = hrefs[500:]


for url in hrefs:
    pageProcessor(url)