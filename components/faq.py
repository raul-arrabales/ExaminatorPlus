import streamlit as st


def faq():
    st.markdown(
        """
# FAQ
## How does Examinator Plus (EP) work?
When you upload course documents, they will be divided into smaller chunks 
and stored in a special type of database called a vector index 
that allows for semantic search and retrieval.

When you ask EP to generate exam questions for a given topic it will search through the
document chunks and find the most relevant ones using the vector index.
Then, it will use an LLM to generate the questions based on a prompt.
"""
    )