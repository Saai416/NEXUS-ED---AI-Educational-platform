from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
import requests

import streamlit as st

client = OpenAI()
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

import requests
import nltk
from bs4 import BeautifulSoup
nltk.download('punkt')
nltk.download('punkt_tab')
pinecone_key=os.getenv("PINECONE_KEY", "")
pinecone_host=os.getenv("PINECONE_HOST", "https://rag-index-xfor3af.svc.aped-4627-b74a.pinecone.io")
from pinecone.grpc import PineconeGRPC as pinecone
pc = pinecone(api_key=pinecone_key)
index = pc.Index(host=pinecone_host)
def get_content_preprocessed(url):
    response = requests.get(url)
    print(response.content)
    soup = BeautifulSoup(response.content, 'html.parser')
    sentences = nltk.sent_tokenize(soup.get_text())
    return sentences
def upsertVector(vector, namespace):
    def chunks(iterable, batch_size=100):
        it = iter(iterable)
        chunk = tuple(itertools.islice(it, batch_size))
        while chunk:
            yield chunk
            chunk = tuple(itertools.islice(it, batch_size))
    for ids_vectors_chunk in chunks(vector, batch_size=100):
        index.upsert(vectors=ids_vectors_chunk, namespace=namespace)  
text_name=st.text_input("Name of your content")
input_method = st.radio("Choose input method", ["URL", "Manual Text"])

if input_method == "URL":
    url=st.text_input("Enter the url of your content")
else:
    manual_text = st.text_area("Enter your content")

if st.button("Process Content"):
    if input_method == "URL":
        sentences = get_content_preprocessed(url)
    else:
        sentences = nltk.sent_tokenize(manual_text)
    response = client.embeddings.create(
    input=sentences,
    model="text-embedding-ada-002"
    )
    response_data = response.data
    import uuid

    pinecone_vectors = []

    for sentence, embedding in zip(sentences, response.data):
     pinecone_vectors.append({
        'id': str(uuid.uuid4()),
        'values': embedding.embedding,
        'metadata': {
            'text': sentence
        }
     })

    import itertools
    upsertVector(vector=pinecone_vectors, namespace=text_name)

query = st.text_input("Ask your Qrueries related to the content given by you") # Changed to st.text_input
if 'answer' not in st.session_state:
    st.session_state.answer = None
if st.button("Ask for Answer"):

    vectorResult = index.query(
        namespace=text_name,
        vector=client.embeddings.create(input=query, model="text-embedding-ada-002").data[0].embedding,
        top_k=3,
        include_values=False,
        include_metadata=True
        )
    result=[]
    for item in vectorResult.matches:
        result.append(item['metadata']['text'])

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": "You are an story teller assistant.With the User question and The list of answer generated create an easily understandable answer in less than 50 words.\n\n Userquery : {} \n\n Referance_content : {} \n\n Answer : ".format(query,result)
            }
           ]
        )
    st.session_state.answer = completion.choices[0].message.content 
if st.session_state.answer: 
    with st.container():
        st.write("Answer")
        st.write(st.session_state.answer)



            
