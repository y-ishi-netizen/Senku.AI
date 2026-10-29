import scraper
import logging
import time

logging.basicConfig(level=logging.INFO)#i want my logs to show up

query = input("What type of information would you like to store?: ")

wpoopy = scraper.scraper_agent()

poopy = wpoopy.url_agent(query)

allowed_urls = wpoopy.robotstxt_check(poopy, wpoopy.user_agent)

for url in allowed_urls:
    
    try:
        web_response = wpoopy.get_website_info(url)
        stripped_text = wpoopy.strip_text(web_response, url)
        if not stripped_text:
            print(f"No text found for {url}.")
            continue
        text = (stripped_text.get("text"))
        title = (stripped_text.get("title"))

        #print(len(text), title)
    except Exception as e:
        logging.exception(f"error occured while processing {url}")# i wanna keep track of errors
        print(f"Something went wrong: {e}")
    finally:
        time.sleep(1)# i want to be curtious to other peoples servers

    chunks = wpoopy.chunk_text(text)

    vectorized_chunks = wpoopy.vectorize_chunk(chunks)

    


