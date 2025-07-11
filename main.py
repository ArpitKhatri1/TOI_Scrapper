import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from schema import NewsArticle
from db import articles_collection, new_articles_collection
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import time
from config import GOOGLE_API_KEY

url = "https://timesofindia.indiatimes.com/india/earthquake-tremors-felt-in-delhi/articleshow/122390891.cms"


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


url_main = "https://timesofindia.indiatimes.com"

result = requests.get(url_main)
doc = BeautifulSoup(result.text,"html.parser")

a_tag = doc.find_all("a")
hrefs = [a.get('href') for a in a_tag if a.get('href')][100:]
print(len(hrefs))


count = 0
for url in hrefs:
    pageProcessor(url)
    count = count +1
    print(count,flush=True)
    


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    
)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a personalized, bias-aware news companion that delivers trending and niche updates tailored to the user's interests, attention span, and emotional bandwidth. You will have 100 articles passed at one time. Mention the TOPIC TAG (INDIA, WORLD, BUSINESS, TECHNOLOGY, ENTERTAINMENT, SPORTS, SCIENCE, HEALTH), MOOD TAG (POSITIVE, NEGATIVE, NEUTRAL, ENTERTAINMENT) and BIAS TAG (LEFT (Emphasizes equity, welfare, rights, anti-corporate sentiment), RIGHT (Emphasizes nationalism, free markets, law and order, tradition), CENTRE (balanced or factual)). Mention these three tags as three space separated words in all uppercase in ENGLISH as the output, separated by newline for each news article. OUTPUT FORMAT: 'ARTICLE n: TOPIC MOOD BIAS'. Your response should have nothing else in it."),
        ("human", "{news}")
    ]
)
chain = prompt | llm

def get_missing_articles():
    # Get all titles from the new collection
    existing_titles = set(doc["title"] for doc in new_articles_collection.find({}, {"title": 1}))
    
    # Get all articles not in the new collection
    missing_articles = list(articles_collection.find({
        "title": {"$nin": list(existing_titles)}
    }))
    
    return missing_articles


missing = get_missing_articles()
print(len(missing))





def parse_and_insert_articles(news):
    import time
    descriptions = ""
    
    for i, article in enumerate(news):
        if article.get("content"):
            descriptions += f"Article {i+1}\n{article['content']}\n"

    try:
        result = chain.invoke({"news": descriptions})
    except Exception as e:
        print("Waiting for Gemini limit reset...")
        time.sleep(60)
        print("Trying again...")
        result = chain.invoke({"news": descriptions})
    
    print("Gemini part successful")
    print(result.content)

    result.content = str(result.content)  
    lines = result.content.strip().split("\n")

    for i, line in enumerate(lines):
        tokens = line.strip().split()
        if len(tokens) < 3:
            print(f"Skipping article {i+1}, not enough tags: {line}")
            continue
        try:
            topic, mood, bias = tokens[-3:]
            news[i]["topic"] = topic
            news[i]["mood"] = mood
            news[i]["bias"] = bias
        except Exception as e:
            print(f"Something went wrong for article number {i+1}")
            print(e)

   
    articles = new_articles_collection

  
    filtered_news = []
    for article in news:
        if not article.get("title"):
            continue
        exists = articles.find_one({"title": article["title"]})
        if exists:
            print(f"Article with title '{article['title']}' already exists. Skipping.")
        else:
            filtered_news.append(article)

    if not filtered_news:
        print("No new articles to insert.")
        return

    try:
        articles.insert_many(filtered_news)
    except Exception as e:
        print("MongoDB insert failed:")
        print(e)
        print(f"This batch of {len(filtered_news)} articles was NOT inserted")
        return

    print(f"Inserted {len(filtered_news)} new articles into MongoDB")


def chunked(iterable, size):
    
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


print(f"Total missing articles: {len(missing)}")


for batch_num, batch in enumerate(chunked(missing, 100), start=1):
    print(f"\n🚀 Processing batch {batch_num} with {len(batch)} articles...")
    parse_and_insert_articles(batch)





# semantic search part 

def embed_articles(test_article):
    try:
        text_to_embed = f"Title : {test_article.get("title")} Content: {test_article.get("content")}"
        # print(text_to_embed)
        vector = embeddings.embed_query(text_to_embed)
        # print(len(vector))

        new_articles_collection.update_one({
            "_id":test_article.get("_id")
        },{
            "$set":{"embedding":vector}
        })
        print("embedding inserted successfully")
    except Exception as e:
        print(e)
        time.sleep(60)
        print("retrying")
        text_to_embed = f"Title : {test_article.get("title")} Content: {test_article.get("content")}"
        # print(text_to_embed)
        vector = embeddings.embed_query(text_to_embed)
        # print(len(vector))

        new_articles_collection.update_one({
            "_id":test_article.get("_id")
        },{
            "$set":{"embedding":vector}
        })
        print("embedding inserted successfully")
        
        
        
missing_embedding_articles = list(new_articles_collection.find({
    "embedding": { "$exists": False }
}))

print(f"Total articles without 'embedding': {len(missing_embedding_articles)}")


embed_count = 0
for missing_embedding_article in missing_embedding_articles:
    embed_articles(missing_embedding_article)
    embed_count = embed_count + 1
    print(embed_count)

