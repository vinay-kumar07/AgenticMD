import os
from dotenv import load_dotenv
from typing import List
import numpy as np
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

def encode_data(data, chunk_size=None, chunk_overlap=None):
    """
    Encodes a data into a vector store using OpenAI embeddings.

    Args:
        data: The data to be encoded.
        chunk_size: The desired size of each text chunk.
        chunk_overlap: The amount of overlap between consecutive chunks.

    Returns:
        A FAISS vector store containing the encoded book content.
    """
    load_dotenv()
    os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')

    cleaned_texts = []
    for p in data:
        p = {
            "command": p["command"],
            "restriction": p["restriction"],
        }
        cleaned_texts.append(Document(page_content=str(p)))

    # cleaned_texts = [Document(page_content=str(p)) for p in data]
    vectorstore = FAISS.from_documents(cleaned_texts, OpenAIEmbeddings())
    return vectorstore