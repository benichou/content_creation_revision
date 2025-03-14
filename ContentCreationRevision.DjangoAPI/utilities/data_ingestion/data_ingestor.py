from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_text_splitters       import RecursiveCharacterTextSplitter
from langchain_community.embeddings import AzureOpenAIEmbeddings
from langchain_core.documents.base  import Document
from azure.identity         import DefaultAzureCredential
from utilities.doc_process  import analyze_txt, analyze_docx, analyze_pdf, analyze_pptx
from utilities.blob_storage import get_onboarding_file, get_all_blob_names
from django.conf            import settings
import os
import io
import time
from typing import Union

class DataIngestor():
    def __init__(self) -> None:
       
        self.vector_store   = None
        self.procesed_files = []
        
        # TODO: What do we do with logs?
        # if os.path.exists(os.path.join("logs","processed_files.txt")):
        #     with open(os.path.join("logs","processed_files.txt"), "r") as f:
        #             self.procesed_files = [fl.strip() for fl in f.readlines()]

        default_credential  = DefaultAzureCredential()
        self._token = default_credential.get_token(settings.COGNITIVE_SERVICES_URL)

        embedding_function = AzureOpenAIEmbeddings(
                    deployment     = settings.QUERY_MODEL_ID,
                    azure_endpoint = settings.API_BASE,
                    azure_ad_token = self._token.token,
                )

        self.vector_store_configs = dict()
        self.vector_store_configs["AZ_AI_SEARCH_ENDPOINT"]   = settings.AZ_AI_SEARCH_ENDPOINT
        self.vector_store_configs["AZ_AI_SEARCH_KEY"]        = None
        self.vector_store_configs["AZ_AI_SEARCH_INDEX_NAME"] = settings.AZ_AI_SEARCH_INDEX_NAME
        self.vector_store_configs["EMBEDDING_FUNCTION"]      = embedding_function
        self.vector_store_configs["VECTOR_STORE_TYPE"]       = settings.VECTOR_STORE_TYPE
        self.vector_store_configs["DEFAULT_CREDENTIAL"]      = default_credential

        self.chunking_config       = {"chunk_size" : settings.CHUNK_SIZE, "chunk_overlap" : settings.CHUNK_OVERLAP}
        self.txt_conversion_config = {"credentials": default_credential}

    def _convert_corpus_to_plain_text(self,  file: dict[str, Union[str, io.BytesIO]]) -> tuple[str, str]:
        if settings.DEBUG:
            print("starting", file["name"])
        
        file_name = file["name"]
        file_io   = file["byte_io"]

       

        if   ".pdf" in file_name:
            text = analyze_pdf(file_io, self.txt_conversion_config["credentials"])
        elif ".docx" in file_name:
            text = analyze_docx(file_io, self.txt_conversion_config["credentials"])
        elif ".txt"  in file_name:
            text = analyze_txt(file_io)
        elif ".ppt"  in file_name:
            text = analyze_pptx(file_io)

        return (text, {"source":file_name})
    
    def _convert_plain_text_to_chunks(self,txt_content: str, metadata: dict) -> list[Document]:
        doc = Document(page_content=txt_content,metadata=metadata)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size = self.chunking_config["chunk_size"], 
                                                       chunk_overlap = self.chunking_config["chunk_overlap"])
        docs = text_splitter.split_documents([doc])
        if settings.DEBUG:
            print(len(docs))
        return docs
    
    def _index_chunks(self, chunks) -> None:
        if self.vector_store_configs["VECTOR_STORE_TYPE"].lower() == "az ai search":
            if not self.vector_store:
                self.vector_store: AzureSearch = AzureSearch(
                    azure_search_endpoint = self.vector_store_configs["AZ_AI_SEARCH_ENDPOINT"],
                    azure_search_key      = self.vector_store_configs["AZ_AI_SEARCH_KEY"],
                    index_name            = self.vector_store_configs["AZ_AI_SEARCH_INDEX_NAME"],
                    embedding_function    = self.vector_store_configs["EMBEDDING_FUNCTION"]
                )
                if settings.DEBUG:
                    print(self.vector_store)
            
            self.vector_store.add_documents(chunks)
           
           
        else:
            raise Exception("Indexing not supported for vector store ", self.vector_store_type)
        
    

        
    def ingest_data(self) -> str:
        if settings.DEBUG:
            print("Ingesting Data")
    
        blob_file_names = get_all_blob_names(self._token)

        for file_name in blob_file_names:
            # Not processing PDF files for Project Orange
            if file_name.endswith(".pdf"):
                continue

            file = get_onboarding_file(file_name, self._token)
            page_content, metadata = self._convert_corpus_to_plain_text(file)
            chunks  = self._convert_plain_text_to_chunks(page_content, metadata)
            self._index_chunks(chunks)

        time.sleep(3)
        return "Data Ingestion Complete!"


