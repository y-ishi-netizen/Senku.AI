import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import chromadb
import ollama
import hashlib
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

trusted = ["pubmed.ncbi.nlm.nih.gov",
"pnas.org",
"plos.org",
"arxiv.org",
"eurekalert.org",
"science.nasa.gov",
"usgs.gov",
"epa.gov",
"noaa.gov",
"cdc.gov",
"nih.gov",
"cern.ch",
"wikipedia.org"
]

class scraper_agent:

    def __init__(self, user_agent="senku.ai.bot/0.1 (contact me: senku.ai.bot@gmail.com)"):

        self.user_agent = user_agent
        self.robots_db = {}

    def url_agent(self, query: str) -> list[str]:       # I didnt want to manually search for 10 sites, it would take too long to load in 1000 documents.
        urls = []
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=30)# it has to be this big because of my filter restriction 
        for site in results:
            url = site["href"]

            hostname = urlparse(url).netloc

            trusted_url = any(hostname == dom or hostname.endswith("." + dom) for dom in trusted)
            checked_url = hostname.endswith((".gov", ".edu"))

            if trusted_url or checked_url:
                urls.append(url)

        return urls
    
    def robotstxt_check(self, urls: list[str], user_agent: str) -> list[str]: # I opted for the honest version, declaring myself instead of hiding because indentified bots get better access

        allowed_urls = []

        for url in urls:
            parts = urlparse(url)

            base_dom = f"{parts.scheme}://{parts.netloc}"
            robots_url = f"{base_dom}/robots.txt"

            if base_dom in self.robots_db:
                rfp = self.robots_db[base_dom]
            else:
                rfp = RobotFileParser()
                rfp.set_url(robots_url)
                try:
                    robots_response = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=10)
                    if robots_response.status_code == 404:
                        rfp.parse([])
                        self.robots_db[base_dom] = rfp
                    elif robots_response.status_code == 200:
                        rfp.parse(robots_response.text.splitlines())
                        self.robots_db[base_dom] = rfp
                    else:
                        self.robots_db[base_dom] = None
                        print(f"couldn't read robots.txt ({robots_response.status_code}): {robots_url}")
                except Exception as e :
                    self.robots_db[base_dom] = None
                    print(f"couldnt read{e}")

            if self.robots_db.get(base_dom) is None:
                print(f"couldnt read {robots_url}.")
                continue

            if rfp.can_fetch(user_agent, url):
                allowed_urls.append(url)
            else: 
                print(f"blocked by {robots_url}")

        return allowed_urls

    def get_website_info(self, url: str) -> str | None: 
        try:
            web_response = requests.get(url, headers={'User-Agent':self.user_agent}, timeout=10)

            if web_response.status_code != 200:
                print("the web server could not find the page you requested")
                return None
            else:
                print("Scrape sucessful")
                return web_response.text
        except Exception as e:
            print(f"An error occurred while fetching the webpage.{e}")
            return None

    def strip_text(self,html: str, url: str) -> dict | None: # I stripped the text so it dosent give random stuff filling up my db
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else ""

        if not title:
            title = url

        for script_or_style in soup(["script", "style", "nav", "header", "footer", "aside", "sup"]):
            script_or_style.decompose()

        content = soup.find('main') or soup.find('article') or soup.find('body') or soup.find(id="mw-content-text")
        if not content:
            print("An error occured: no content found")
            return None

        text = content.get_text(separator=' ', strip=True) if content else ""

        print("clean successful")
        return {
            "text": text,
            "source": url,
            "title": title
        }

    def chunk_text(self, text: str, chunk_size=512,overlap=100,) -> list[str]:  #I did this so I fall within embedding limit which is 512 for mxbai_embed_large.
        # I did a 100 character overlap (a standard 20%) so it dosent cut off in the middle of something important
        chunks = []
        start = 0
        while start < len(text):

            end = start + chunk_size

            chunk = text[start:end]

            chunks.append(chunk)

            start += (chunk_size - overlap)

            if end >= len(text):
                break
        return chunks
    def vectorize_chunk(self, chunks:list[str]) -> list[list[float]]:
        vectorized_chunks = []
        for chunk in chunks:
            vectorized_chunk = ollama.embed(
            model="mxbai-embed-large",      #chose this model becaue its the best for english
            input=chunk,
            )
            vectorized_chunks.append(vectorized_chunk['embeddings'][0])

        return vectorized_chunks
    def store_chunk(self, vectorized_chunks: list[list[float]], collection, title: str, source :str, chunks: list[str]) -> None:
        custom_id = hashlib.md5(source.encode()).hexdigest()[:10] # the id's have to be unique so i made the hashlib to mark the page and enumerate to mark the chunk, together they make a unique id number.
        ids = [f"doc_{custom_id}_{i}" for i, _ in enumerate(chunks)]

        metadatas = [{"title":title, "source":source, "customId":custom_id, "number":i}for i,_ in enumerate(chunks)]

        collection.upsert(
            documents = chunks,
            embeddings = vectorized_chunks,
            ids = ids,
            metadatas = metadatas
        )
    
class backend_of_senkuai:   
    def initialize_collection(self):  #create the vault or get it so i can store my chunks
        client = chromadb.PersistentClient(path="./my_ai_db")
        collection = client.get_or_create_collection(name="knowledge_db")
        return collection

    def collect_prompt (self, collection, prompt: str) ->tuple[str, list[dict]]:  
        query_result = ollama.embed(
            model="mxbai-embed-large",  
            input=prompt
        )
        query_vector = query_result['embeddings'][0] # I needed to vectorize my prompt so it can search for analogus vectors in my db

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=3
        )
        context = " ".join(results['documents'][0])

        return context, results['metadatas'][0]
    
    def _make_response(self, context: str, metadatas: list[dict], prompt: str) -> tuple[str | None, dict | None]:
        s_prompt = (
            f"Here is the scientific information: {context} "
            f"Use only this information, please answer the user's question: {prompt}"
            f"at the end of your message attach:{metadatas}"
        )
        
        url = "http://localhost:11434/api/generate"

        payload= {
            "model": "SENKU.AI",
            "prompt": s_prompt,
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            final_response = data["response"]
        except Exception as e:
            print(f"An error occurred while processing the request: {e}")
            return None, None
        return final_response, data