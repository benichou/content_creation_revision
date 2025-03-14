from DVoice.utilities.llm_and_embeddings_utils import generate_response_from_text_input, instantiate_azure_openai_client
from DVoice.utilities.llm_and_embeddings_utils import instantiate_azure_openai_embedding_client, generate_embeddings_for_list_of_chunks
from DVoice.utilities.llm_and_embeddings_utils import generate_embeddings
from DVoice.prompt.prompt_repo import INPUT_QUERY_RETRIEVER_QA
from DVoice.prompt.model_persona_repo import MODEL_PERSONA_DIRECT_QA
from DVoice.utilities.settings import AZURE_OPENAI_MODEL_NAME, SELECTED_MODEL
# from utilities.chromadb import ChromaDBHandler
from utilities.openai_utils.process_prompt import _get_prompt_sections
from DVoice.prompt.prompt_actions import rewrite_query_core_action
from DVoice.utilities.llm_and_embeddings_utils import answer_query_from_retrieval_results
from collections import defaultdict
from typing import Dict, List, Any

def generate_dvoice_response_no_context(TOKEN,
                                        query: str,
                                        branding_requirements_message: str,
                                        target_language: str) -> str:
    """
    Generates a response to a query without context, based on branding requirements and the target language.
 
    Args:
        TOKEN (Azure Access Token): The authentication token to access the Azure OpenAI service.
        query (str): The query for which the response needs to be generated.
        branding_requirements_message (str): The branding guidelines that the content should adhere to.
        target_language (str): The target language for the response (e.g., "EN" for English, "FR" for French).
    
    Returns:
        response (str): The generated response content in the target language.
    """
    # Determine the language based on the target language code
    if target_language == "EN":
        language = "English"
    elif target_language == "FR":
        language = "French"

    # Instantiate the OpenAI client with the provided token
    client = instantiate_azure_openai_client(TOKEN)
    # Prepare the input task prompt by combining the branding requirements and the query
    input_task_prompt = branding_requirements_message + f" 8. and the content should be generated in {language}" \
                                                         + INPUT_QUERY_RETRIEVER_QA
    # Attempt to generate a response using the prompt
    try:
        response = generate_response_from_text_input(input_task_prompt,
                                                     MODEL_PERSONA_DIRECT_QA,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
        response = response[0].choices[0].message.content
    except Exception as e:
        # Log the initial error and attempt a second call
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(input_task_prompt,
                                                         MODEL_PERSONA_DIRECT_QA,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
            response = response[0].choices[0].message.content
        except Exception as e:
            # Log the failure and return a message indicating failure
            print(f"Complete failure error:{e}")
        
    print(f"Completed necessary list of files identification")

    return response

def conduct_retrieval_based_content_generation(TOKEN,
                                               concatenated_data: Dict[str, List[Any]],
                                               necessary_input_files: List[str],
                                               query_new: str,
                                               branding_requirements_message: str,
                                               language_of_output: Dict[str, str],
                                               chroma_db) -> str:
    """
    Conducts retrieval-based content generation by querying relevant documents, generating embeddings, and 
    creating content based on the retrieved sections, customized according to branding requirements.
 
    Args:
        TOKEN (Azure Access Token): The authentication token to access the Azure OpenAI service.
        concatenated_data (dict): A dictionary containing concatenated data with file titles as keys and lists of 
                               content (with embeddings) as values.
        necessary_input_files (list): A list of file names that should be included in the content generation.
        query_new (str): The new query for which the content needs to be generated.
        branding_requirements_message (str): The branding guidelines to apply when generating content.
        language_of_output (dict): A dictionary specifying the target language of the output content (e.g., {"language": ["EN"]}).
        chroma_db: A ChromaDB instance used to store and retrieve document embeddings.
 
    Returns:
        Generated Content (str): The generated content based on the query and retrieved document sections.
    
    Chroma DB dependency: For this retrieval process to really work and not error with the open source chroma 
    db we have please,
    keep the following packages with the listed versions here:
    - chroma-hnswlib==0.7.3
    - chromadb==0.4.18

    """
    import pandas as pd
    # Filter the concatenated data to only include necessary files
    filtered_concatenated_data = defaultdict(list, {k: concatenated_data[k] for k 
                                                    in necessary_input_files if k in concatenated_data})

    # Instantiate the embedding client using the provided authentication token
    embedding_client = instantiate_azure_openai_embedding_client(TOKEN)
    # Generate embeddings for the filtered concatenated data
    filtered_concatenated_data = generate_embeddings_for_list_of_chunks(embedding_client,
                                                                        filtered_concatenated_data)
    # Convert the filtered data into a pandas DataFrame (ChromaDB expects this format)                      
    df = pd.DataFrame()
    for key, list_of_dicts in filtered_concatenated_data.items():
        for record in list_of_dicts:
            df = df._append(record, ignore_index=True)
    ## df output is like below:
    ## >>> df.columns Index(['title', 'id', 'text', 'n_tokens', 'embedding'], dtype='object')
    ##                                         title  ...                                          embedding
    # 0   Oil and Gas_Spotlight article_ENs v1.docx  ...  [-0.004101620055735111, 0.006374916061758995, ...
    # 1  Economic outlook_FY25_Q1_EN_V2_EDR3 v3.pdf  ...  [0.02570480853319168, 0.023818789049983025, 0....
    # 2  Economic outlook_FY25_Q1_EN_V2_EDR3 v3.pdf  ...  [-0.002787482226267457, 0.011028803884983063, ...
    # 3  Economic outlook_FY25_Q1_EN_V2_EDR3 v3.pdf  ...  [-0.023517558351159096, 0.013963138684630394, ...
    # 4  Economic outlook_FY25_Q1_EN_V2_EDR3 v3.pdf  ...  [0.040555957704782486, -0.010706204921007156, ...
    # 5  Economic outlook_FY25_Q1_EN_V2_EDR3 v3.pdf  ...  [-0.014108720235526562, 0.028466932475566864, ...
    # 6  Economic outlook_FY25_Q1_EN_V2_EDR3 v3.pdf  ...  [0.033635213971138, -0.007610759232193232, 0.0...
    # 7  Economic outlook_FY25_Q1_EN_V2_EDR3 v3.pdf  ...  [-0.0050654630176723, 2.2156358681968413e-05, ...
    
    # Add the DataFrame to the ChromaDB for document retrieval
    chroma_db.add_document(df)
    # Rewrite the query for core action (possibly applying additional transformations or checks)
    core_query = rewrite_query_core_action(TOKEN, query_new)
    # Generate the embedding for the query
    query_embedding = generate_embeddings(embedding_client, core_query)
    # Retrieve the most relevant documents based on the query embedding
    retrieval_results = chroma_db.get_docs(query_embedding) ## get closest docs retrieval
    
    # Get the sections of the retrieved documents to be used in the prompt
    chosen_sections, titles, context_sections =_get_prompt_sections(retrieval_results, SELECTED_MODEL)
    # Generate content based on the retrieved sections and apply branding requirements
    generated_content = " \n\n " + answer_query_from_retrieval_results(core_query, 
                                                            chosen_sections,
                                                            branding_requirements_message,
                                                            language_of_output["language"][0], 
                                                            TOKEN)
    chroma_db.delete_collection()
    # Delete the collection from the ChromaDB (cleanup after retrieval)
    print("deleted collection for vector db chroma dab")
    return generated_content
            