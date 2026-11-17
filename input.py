import scraper
import logging
import time

logging.basicConfig(level=logging.INFO)#i want my logs to show up

backend = scraper.backend_of_senkuai()

collection = backend.initialize_collection()

query = input("What type of information would you like to store?: ")

scraper = scraper.scraper_agent()

url = scraper.url_agent(query)

allowed_urls = scraper.robotstxt_check(url, scraper.user_agent)

for url in allowed_urls:
    
    try:
        web_response = scraper.get_website_info(url)
        stripped_text = scraper.strip_text(web_response, url)
        if not stripped_text:
            print(f"No text found for {url}.")
            continue
        text = (stripped_text.get("text"))
        title = (stripped_text.get("title"))
        source = (stripped_text.get("source"))

        #print(len(text), title)
    except Exception as e:
        logging.exception(f"error occured while processing {url}")# i wanna keep track of errors
        print(f"Something went wrong: {e}")
    finally:
        time.sleep(1)# i want to be curtious to other peoples servers

        chunks = scraper.chunk_text(text)

        vectorized_chunks = scraper.vectorize_chunk(chunks)

        store_yo_chunks = scraper.store_chunk(vectorized_chunks, collection, title, source, chunks)

        print(collection.count())

    


