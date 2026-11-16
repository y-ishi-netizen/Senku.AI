import streamlit as st
import scraper


@st.cache_resource
def getCollection():
    backend = scraper.backend_of_senkuai()
    return backend.initialize_collection(), backend

collection, backend = getCollection()


st.title("CONSTRUCT-00: SENKU.AI")
st.write("Welcome proxy.")

prompt = st.chat_input("whats your question: ")

if prompt:
    st.chat_message("user").write(prompt)

    context, results = backend.collect_prompt(collection, prompt)   

    finalResponse, data = backend.make_response(context, results, prompt)

    if not finalResponse:
        st.error("Error returning response")

    st.chat_message("assistant").write(finalResponse)

    
