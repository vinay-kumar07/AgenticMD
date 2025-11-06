from encode import encode_data
import json
import ast

class LAMMPSQueryRAG:
    def __init__(self):
        with open("data/LAMMPSData/lammps_data.json", "r") as f:
            lammps_data = json.load(f)
        self.chunks_vector_store = encode_data(lammps_data)

    def query_rag_lammps(self, command: str):
        chunks_query_retriever = self.chunks_vector_store.as_retriever(search_kwargs={"k": 1})
        query = f"What are the restriction and description for {command} command"
        docs = chunks_query_retriever.invoke(query)
        context = [doc.page_content for doc in docs]
        ctx = ast.literal_eval(context[0])
        return ctx['restriction']