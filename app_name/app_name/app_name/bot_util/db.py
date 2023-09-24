import os
from langchain.document_loaders import (
    NotebookLoader, #ipynb
    TextLoader, # py
    UnstructuredMarkdownLoader, #md
)
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma


class VectorDB:
    db = None
    _retriever = None

    persist_dir: str
    data_dir: str
    collection_name: str
    load_dict: dict

    def __init__(self, persist_dir: str, data_dir: str, collection_name: str, db_type=Chroma):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.data_dir = data_dir
        self.db = db_type
        self.load_dict = {
            "txt": TextLoader,
            "md": UnstructuredMarkdownLoader,
            "ipynb": NotebookLoader,
        }

    def upload_embedding_from_file(self, file_path):
        loader = self.load_dict.get(file_path.split(".")[-1])
        if loader is None:
            raise ValueError("Not supported file type")
        documents = loader(file_path).load()

        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)
        print(docs, end='\n\n\n')

        chroma = Chroma.from_documents(
            docs,
            OpenAIEmbeddings(),
            collection_name=self.collection_name,
            persist_directory=self.persist_dir,
        )


        self.db = chroma
        self._retriever = chroma.as_retriever()
        print('db success')

    def load_data(self):
        failed_upload_files = []

        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith(".txt"):   # or file.endswith(".md") or file.endswith(".ipynb"):
                    file_path = os.path.join(root, file)

                    try:
                        self.upload_embedding_from_file(file_path)
                        print("SUCCESS: ", file_path)
                    except Exception as e:
                        print("FAILED: ", file_path + f"by({e})")
                        failed_upload_files.append(file_path)

    def query(self, query: str, use_retriever: bool = False) -> list[str]:
        if use_retriever:
            docs = self._retriever.get_relevant_documents(query)
        else:
            docs = self.db.similarity_search(query)

        str_docs = [doc.page_content for doc in docs]
        return str_docs

