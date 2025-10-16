import sys
# sys.path.append('RAG_TECHNIQUES')



import os
import sys
from dotenv import load_dotenv
from langchain.docstore.document import Document

from typing import List
# from rank_bm25 import BM25Okapi
import numpy as np


# Original path append replaced for Colab compatibility
from RAG_TECHNIQUES.helper_functions import *
from RAG_TECHNIQUES.evaluation.evalute_rag import *

# Load environment variables from a .env file
load_dotenv()

# Set the OpenAI API key environment variable
os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')

def encode_data(data):
    """
    Encodes a PDF book into a vector store using OpenAI embeddings.

    Args:
        path: The path to the PDF file.
        chunk_size: The desired size of each text chunk.
        chunk_overlap: The amount of overlap between consecutive chunks.

    Returns:
        A FAISS vector store containing the encoded book content.
    """
    cleaned_texts = [Document(page_content=str(p)) for p in data]

    # Create embeddings (Tested with OpenAI and Amazon Bedrock)
    embeddings = get_langchain_embedding_provider(EmbeddingProvider.OPENAI)
    
    # Create vector store
    vectorstore = FAISS.from_documents(cleaned_texts, embeddings)

    return vectorstore