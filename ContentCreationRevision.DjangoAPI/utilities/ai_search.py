from langchain_community.vectorstores.azuresearch import AzureSearch
from azure.search.documents.indexes import SearchIndexClient
from langchain_openai import AzureOpenAIEmbeddings
from azure.identity import DefaultAzureCredential
from django.conf import settings

def ai_search_retrieve_docs(_token, query, top_k=3):

    embedding_function = AzureOpenAIEmbeddings(
                deployment     = settings.QUERY_MODEL_ID,
                azure_endpoint = settings.API_BASE,
                azure_ad_token = _token.token,
            )

    vector_store = AzureSearch(
                    azure_search_endpoint = settings.AZ_AI_SEARCH_ENDPOINT,
                    azure_search_key      = None,
                    index_name            = settings.AZ_AI_SEARCH_INDEX_NAME,
                    embedding_function    = embedding_function
                )
   
    # docs = vector_store.similarity_search(
    #     query=query,
    #     k=top_k,
    #     search_type=search_type,
    # )
    docs = vector_store.similarity_search_with_relevance_scores(
        query=query,
        k=top_k,
        score_threshold=settings.AI_SEARCH_THRESHOLD,
    )
    if settings.DEBUG:
        scores = [score for _,score in docs] 
        print("docs returned:", len(docs), "socres:", scores)
    return docs


def index_exists():   
       
        search_client = SearchIndexClient(
                            endpoint   =  settings.AZ_AI_SEARCH_ENDPOINT,
                            credential = DefaultAzureCredential()
                        )
     
        index_names = search_client.list_index_names()
        list_index = list(index_names)
        if settings.DEBUG:
            print(settings.AZ_AI_SEARCH_INDEX_NAME in list_index, list_index)


        if settings.AZ_AI_SEARCH_INDEX_NAME.strip() in list_index:
              return True
        return False
    