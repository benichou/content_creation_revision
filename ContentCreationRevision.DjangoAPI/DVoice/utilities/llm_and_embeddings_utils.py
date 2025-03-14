import sys, os
import io
import asyncio
import concurrent.futures
import tiktoken
import time
from openai import AzureOpenAI
from DVoice.utilities.settings import API_VERSION, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_MODEL
from DVoice.utilities.settings import AZURE_OPENAI_MODEL_NAME
from DVoice.utilities.settings import MAX_TOKEN_COMPLETION, TEMPERATURE
from django.conf               import settings
from langchain_openai import AzureChatOpenAI
import json
from pathlib import Path
import logging
from typing import List, Optional, Any, Dict, Tuple


# from dotenv import load_dotenv
# load_dotenv(dotenv_path="Deloitte.Ca.DBotBeta.DjangoAPI\\DVoice\\.env") ## to remove when we go to dev

## LOGGING CAPABILITIES

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
# Attach handler to the logger
logger.addHandler(handler)

def instantiate_azure_openai_client(TOKEN) -> AzureOpenAI:
    """
    Instantiates and returns an Azure OpenAI client using the provided authentication token.
 
    Args:
        TOKEN (it is a TokenCredential): An Azure authentication token obtained using 
                                 `ChainedTokenCredential` or another authentication method.
 
    Returns:
        AzureOpenAI: An instance of the Azure OpenAI client, configured with the 
                     specified API version, endpoint, and deployment model.
 
    Example:
        ```python
        from azure.identity import DefaultAzureCredential
        token_credential = DefaultAzureCredential()
        client = instantiate_azure_openai_client(token_credential)
        response =client.invoke("Who is the president of the USA now?") # note this is an AIMessage()
        ```
    """
    
    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT, 
        azure_ad_token = TOKEN.token,
        # api_key      =  os.environ["AZURE_OPENAI_API_KEY"],
        azure_deployment = AZURE_OPENAI_MODEL_NAME
    )
    
    print("✅Azure Open AI Client has been instantiated")
    
    return client

def instantiate_azure_openai_embedding_client(TOKEN) -> AzureOpenAI:
    """
    Instantiates and returns an Azure OpenAI client configured for embedding models.
 
    Args:
        TOKEN (TokenCredential): An Azure authentication token obtained using 
                                 `ChainedTokenCredential` or another authentication method.
 
    Returns:
        AzureOpenAI: An instance of the Azure OpenAI client, configured specifically for 
                     embedding model deployment.
 
    Example:
        ```python
        from azure.identity import DefaultAzureCredential ## use the chained method instead check views.py
        token_credential = DefaultAzureCredential()
        client = instantiate_azure_openai_embedding_client(token_credential)
        ## THEN YOU USE THIS CLIENT TO CREATE THE EMBEDDINGS YOU NEED
        ```
    """
    client = AzureOpenAI(
        api_version= settings.EMBEDDING_DEPLOYMENT_API_VERSION_DICTIONARY[settings.EMBEDDING_DEPLOYMENT_NAME], 
        azure_endpoint=AZURE_OPENAI_ENDPOINT, 
        azure_ad_token = TOKEN.token,
        azure_deployment = settings.EMBEDDING_DEPLOYMENT_NAME
    )
    
    print("Azure Open AI Client has been instantiated")
    
    return client



def instantiate_azure_chat_openai(TOKEN) -> AzureChatOpenAI:
    """
    Instantiates and returns an Azure Chat OpenAI client for conversational AI tasks.
 
    Args:
        TOKEN (TokenCredential): An Azure authentication token obtained using 
                                 `ChainedTokenCredential` or another authentication method.
 
    Returns:
        AzureChatOpenAI: An instance of the Azure Chat OpenAI client configured with the specified 
                         parameters.
 
    Example:
        ```python
        from azure.identity import DefaultAzureCredential ## use the chained method instead check views.py
        token_credential = DefaultAzureCredential()
        chat_model = instantiate_azure_chat_openai(token_credential)
        ```
    """
    model = AzureChatOpenAI(
            openai_api_version = API_VERSION,
            temperature        = TEMPERATURE,
            deployment_name    = AZURE_OPENAI_MODEL_NAME,
            azure_endpoint     = AZURE_OPENAI_ENDPOINT,
            azure_ad_token     = TOKEN.token, 
            # api_key      =  os.environ["AZURE_OPENAI_API_KEY"], ## will be removed by azure_ad_token when we go to dev
            max_tokens         = MAX_TOKEN_COMPLETION,
            model              = AZURE_OPENAI_MODEL
        )
    
    return model

def count_tokens(text: str, 
                 text_idx: int, 
                 model: str) -> tuple[int, int]:
    """
    Counts the number of tokens in the given text using the specified model's tokenizer.
 
    Args:
        text (str): The input text to tokenize and count tokens for.
        text_idx (int): An index identifier for the text (useful in tracking multiple texts).
        model (str): The model name whose tokenizer will be used, e.g., "gpt-3.5-turbo" or "gpt-4".
 
    Returns:
        tuple[int, int]: A tuple containing:
            - int: The number of tokens in the given text.
            - int: The provided text index (`text_idx`), returned for tracking purposes.
 
    Example:
        ```python
        token_count, index = count_tokens("Hello, world!", 1, "gpt-3.5-turbo")
        print(token_count, index)  # Example output: (4, 1)
        ```
    """
    # Choose the appropriate encoding for the specified model
    encoding = tiktoken.encoding_for_model(model)
    
    # Tokenize the text
    tokens = encoding.encode(text)
    
    # Return the number of tokens
    return len(tokens), text_idx

async def count_tokens_for_list_of_chunks(input_list: List[str]) -> List[int]:
    """
    Asynchronously counts the tokens for each chunk in a list of input data.
    Args:
        input_list (List[str]): A list of chunks, where each chunk of type str is processed
                                 The function processes each chunk by calling the count_tokens function.
    Returns:
        List[Any]: A list of responses, where each response is the result of the token count operation
                   and is sorted based on the index of the chunks.
    Notes:
        This function uses asyncio to concurrently process each chunk in the input list using run_in_executor.
    """
    start_time = time.time()
    loop = asyncio.get_event_loop() # start the async job
    tasks = []
    # Create asynchronous tasks to process each chunk
    for idx, chunk in enumerate(input_list):
        tasks.append(loop.run_in_executor(None, count_tokens, chunk,
                                                              idx,
                                                              AZURE_OPENAI_MODEL
                                            ))
    # Gather all the results concurrently
    responses = await asyncio.gather(*tasks)
    # Sort the responses by their respective indices
    ordered_responses = sorted(responses, key=lambda x: x[1])
    end_time = time.time()
    process_time = end_time - start_time
    # Print how long the token counting process took
    print(f"Counting Token on split markdown took {process_time} second(s)")

    return ordered_responses


def generate_response_from_text_input(
    prompt: str,
    model_persona: str,
    text: str,
    client: Any,  # Assuming 'client' is an instance of a client for Azure OpenAI service
    azure_openai_model_name: str,
    response_format: Optional[str] = None, # note it should be a class if not None, not a str
    idx: Optional[int] = None
) -> tuple:
    """
    Call the Azure OpenAI service to extract insights from text based on a given prompt and model persona.
    Args:
        prompt (str): The prompt or question that will guide the model's response.
        model_persona (str): A string representing the model's persona, which can be used to instruct the model
                              on how to behave when responding.
        text (str): The input text from which the insights will be extracted or generated.
        client (Any): The Azure OpenAI client instance used to communicate with the Azure service, to conduct text generation
        azure_openai_model_name (str): The name of the Azure OpenAI model to be used for text completion.
        response_format (Optional[str], optional): The class type used for parsing the response. Defaults to None.
        idx (Optional[int], optional): An optional index to associate with the response. Defaults to None.
 
    Returns:
        tuple: A tuple containing the generated response and execution time. If idx is provided, the tuple will also include the index.
    Notes:
        The function interacts with the Azure OpenAI service, using either a default completion request or a custom 
        response format parsing, depending on whether `response_format` is provided.
    """
    
    start_time = time.time()
    # If no response format is specified, generate a standard response using chat completion
    if response_format is None:
        response = client.chat.completions.create(
            model=azure_openai_model_name,
            messages=[{
                "role": "system", 
                "content": model_persona
            }, {
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": f"{prompt}\n\n Here is the input text:\n {text}"
                }]
            }],
            max_tokens=MAX_TOKEN_COMPLETION,
            temperature=TEMPERATURE,
            top_p=1,
            n=1,)
    else:
        # If a response format is specified, use the chat completion with response format
        response =client.beta.chat.completions.parse(
            model=azure_openai_model_name,
            messages=[{
                "role": "system", 
                "content": model_persona
            }, {
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": f"{prompt}\n\n Here is the input text:\n {text}"
                }]
            }],
            max_tokens=MAX_TOKEN_COMPLETION,
            temperature=TEMPERATURE,
            top_p=1,
            n=1,
            response_format=response_format)
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Print generation result
    print("Response has been generated")
    # print(response)
    
    # Print time it takes to process extraction
    print(f"Extraction of insights from text in slide is: \
        Execution Time: {execution_time:.6f} seconds")
    # Return the response along with execution time, and optionally the index if provided
    if idx is not None:
        return response, execution_time, idx
    return response, execution_time



def save_tensor_from_blob_to_directory(
    bytesIO_input_file: io.BytesIO,  # Expecting a BytesIO object containing tensor data
    output_path: str,                # Path where the tensor will be saved
    tensor_name: str                 # Name of the tensor being saved, for logging purposes
) -> None:
    """
    Saves the tensor data from a BytesIO object to a specified file in a directory.
 
    Args:
        bytesIO_input_file (io.BytesIO): A BytesIO object containing the tensor data to be saved.
        output_path (str): The path (including filename) where the tensor should be saved in the directory
        tensor_name (str): The name of the tensor, used for logging purposes.
 
    Returns:
        None: This function does not return any value; it saves the tensor to the file system.
    Notes:
        - The function writes the content of the BytesIO object to the specified file path.
        - It uses a logger to indicate when the tensor is being saved successfully.
    """
    
    with open(output_path, "wb") as f:
        logger.info("✅Saving to file")
        f.write(bytesIO_input_file.getvalue())  # Extract bytes and write to file
    print(f"Saved tensor {tensor_name} at {output_path}")
    


def remove_any_previous_tensors_from_app_directory() -> None:
    """
    Removes previously stored tensor files from the application directory.
 
    This function checks if tensor files, defined in `DOCLING_LLM_DICT` (from DVoice.settings), exist in the local or Docker model path. 
    It deletes these files if they exist to clean up any previous tensors from the application directory.
 
    Args:
        None: This function does not require arguments. It uses settings from the `DVoice.utilities.settings` module.
 
    Returns:
        None: This function does not return any value. It performs file deletion as a side effect.
 
    Notes:
        - The function checks the appropriate model path based on the `DOCKER_MODE` setting.
        - If a tensor file exists, it is deleted; otherwise, a message is printed stating that the file does not exist.
    """
    from DVoice.utilities.settings import DOCLING_LLM_DICT, DOCLING_TRANSFORMER_MODEL_PATH_LOCAL
    from DVoice.utilities.settings import DOCKER_MODE, DOCLING_TRANSFORMER_MODEL_PATH_DOCKER
    # Determine the correct model path based on whether running in Docker mode or locally
    if DOCKER_MODE:
        DOCLING_TRANSFORMER_MODEL_PATH = DOCLING_TRANSFORMER_MODEL_PATH_DOCKER
    else:
        DOCLING_TRANSFORMER_MODEL_PATH = DOCLING_TRANSFORMER_MODEL_PATH_LOCAL
    # Loop through each tensor in the dictionary and attempt to remove it from the directory
    for tensor_name, llm_directory_path in DOCLING_LLM_DICT.items():
        # Define input and output filenames
        file_path = DOCLING_TRANSFORMER_MODEL_PATH + llm_directory_path + tensor_name
        try:
            # Check if the file exists before deleting
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"{file_path} deleted successfully.")
            else:
                print(f"{file_path} does not exist.")
        except Exception as e:
            print(f"Error removing {file_path} tensor because of {e}")
            
 # TODO: Let us have the model as setting in settings from django.config or settings
def generate_embeddings(client: Any, 
                        text: str, 
                        model: str = "text-embedding-3-small") -> Any: ## model = "deployment_name"
    """
    Generates embeddings for the provided text using the specified model.
 
    This function communicates with an embedding service (e.g., OpenAI API) to generate embeddings 
    from the given input text. If an error occurs due to a rate limit or other issue, the function 
    will retry up to three times with a 60-second delay between attempts.
 
    Args:
        client (Any): The client object used to interact with the embedding service.
                      It is assumed to have an `embeddings.create()` method for generating embeddings.
                      Note: The client is the client generated by AzureOpenAI class in the one of the methods above
        text (str): The input text for which embeddings are to be generated.
        model (str, optional): The model name to be used for generating embeddings. 
                               Defaults to "text-embedding-3-small". TODO: we will have to sync it with django settings since embeddings evolve over time
 
    Returns:
        Any: The embeddings generated from the input text. The return type depends on the client 
             and API, typically an array or a tensor. Note: Note an embedding is a tensor of floats
    Notes:
        - The function retries up to three times if it encounters an error during the embedding generation.
        - A 60-second delay is applied between each retry in case of rate-limiting errors (e.g., TPM limits).
    """
    try:
        # Try to generate embeddings using the provided model
        embeddings = client.embeddings.create(input = [text], model=model).data[0].embedding
    except Exception as e:
        print(f"Error {e} identified - let us do it one more time")
        time.sleep(60) ## in case of of TPM limit error
        try:
            # If an error occurs, retry after a 60-second wait (e.g., due to TPM limit)
            embeddings = client.embeddings.create(input = [text], model=model).data[0].embedding
        except Exception as e:
            # Retry again after another 60-second delay if the error persists
            print(f"Error {e} identified - let us do it one more time")
            time.sleep(60) ## let us wait another one more final minute
            try:
               embeddings = client.embeddings.create(input = [text], model=model).data[0].embedding
            except:
                # If all retries fail, log the error and return None
                print(f"Error {e} identified")
                embeddings = None

    return embeddings

def process_split(client: Any, 
                  split: Dict[str, str], 
                  index: int) -> Tuple[int, Any]:
    """
    Processes a split of text and generates its embedding using the provided client.
 
    This function uses an external service (e.g., Azure OpenAI) to generate an embedding for a given
    split of text. The function returns the index of the split along with the generated embedding.
 
    Args:
        client (Any): The client object used to interact with the embedding service. 
                      This client must have a method to generate embeddings (e.g., `generate_embeddings`).
        split (Dict[str, str]): A dictionary containing the text split, where the key "text" holds 
                                 the text that needs to be embedded.
        index (int): The index of the split in a larger list of text splits.
 
    Returns:
        Tuple[int, Any]: A tuple containing the index of the split and its corresponding embedding.
                         The embedding can be any data structure returned by the external embedding service.
 
    Notes:
        - This function calls `generate_embeddings` to generate the embedding for the split's text.
    """
    embedding = generate_embeddings(client, split["text"])
    return index ,embedding



def answer_query_from_retrieval_results(
    query: str,
    chosen_sections: List[str],
    branding_requirements_message: str,
    language_of_output: str,
    TOKEN,
) -> str:
    """
    Answers a query based on retrieved sections and other parameters using the Azure OpenAI API.
 
    This function generates a response to the provided query by utilizing retrieved content sections, 
    branding requirements, and language specifications. It communicates with an external service (Azure OpenAI) 
    to generate the response, retrying if any errors occur during the generation process.
 
    Args:
        query (str): The query that needs to be answered.
        chosen_sections (List[str]): A list of content sections that were retrieved to answer the query.
        branding_requirements_message (str): A string message specifying the branding requirements for the output.
        language_of_output (str): The desired language for the response. It can be "EN" for English or "FR" for French.
        TOKEN (Access token object generated by Azure - not a string): The token used for authentication when accessing the Azure OpenAI client.
 
    Returns:
        Any: The generated output (a string output for now, maybe JSON later), which contains the answer to the query.
 
    Notes:
        - The function uses the Azure OpenAI client to generate a response to the query based on the provided sections.
        - If the output language is specified as "EN", the language will be set to English; if "FR", it will be set to French.
        - The function handles retries in case of errors during the initial response generation.
    """

    from utilities.openai_utils.prompt import header
    from DVoice.prompt.prompt_repo import INPUT_QUERY_RETRIEVER_QA
    from DVoice.prompt.model_persona_repo import MODEL_PERSONA_QA_RETRIEVER
    # Instantiate the Azure OpenAI client with the provided TOKEN
    client = instantiate_azure_openai_client(TOKEN)
    # Determine the language for the output based on the provided 'language_of_output'
    if language_of_output == "EN":
        language = "English"
    elif language_of_output == "FR":
        language = "French"
    # Construct the prompt message that will be used in the response generation
    prompt_message =  header + f"**\n Given the following content retrieved by your colleague that seemed to best\
                                    answer the question: \n{chosen_sections}" \
                             + branding_requirements_message + f"and 8. The language of the content should be solely in {language}"\
                             + INPUT_QUERY_RETRIEVER_QA 
    try:
        # Generate a response from the input text
        response = generate_response_from_text_input(prompt_message,
                                                     MODEL_PERSONA_QA_RETRIEVER,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
        generated_output = response[0].choices[0].message.content
    except Exception as e:
        # Handle the first exception and retry the response generation
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(prompt_message,
                                                         MODEL_PERSONA_QA_RETRIEVER,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
            generated_output = response[0].choices[0].message.content
        except Exception as e:
            # Handle the second exception if the error persists
            print(f"Complete failure error:{e}")
        
    print("DVoice Creation Retrieval Completed")

    return generated_output

def generate_embeddings_for_list_of_chunks(
    embedding_client: Any, # the azure open ai client for embedding generation
    lists_of_chunks: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates embeddings for a list of text chunks using a specified embedding client.
 
    This function processes each chunk of text from the input list of chunks, computes embeddings 
    for each chunk using the provided embedding client, and then stores the embeddings in the original 
    list of chunks. It uses multithreading (via ThreadPoolExecutor) to process chunks concurrently.
 
    Args:
        embedding_client (Any): The client used to generate embeddings. It should have a method to 
                                 generate embeddings, such as `generate_embeddings`.
        lists_of_chunks (Dict[str, List[Dict[str, Any]]]): A dictionary where keys are document identifiers 
                                                           and values are lists of chunks of text. 
                                                           Each chunk is represented as a dictionary 
                                                           containing text and other metadata.
 
    Returns:
        Dict[str, List[Dict[str, Any]]]: The input dictionary with the embeddings added to each chunk.
 
    Notes:
        - The function processes each document (list of chunks) sequentially.
        - Multithreading is used to process each chunk concurrently (in each separate document) for faster embedding generation.
        - The embeddings are added directly to the `embedding` key in each chunk's dictionary.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Start processing each document (list of chunks) sequentially
        for key, list_of_chunks in lists_of_chunks.items(): ## processing one document at a time for now
            # Create a list of futures to process each chunk concurrently
            futures = [executor.submit(process_split,embedding_client, split, index) for index, split in enumerate(list_of_chunks)]
            # Wait for each future to complete and assign the embedding to the chunk
            for future in concurrent.futures.as_completed(futures):
                index, embedding = future.result()
                lists_of_chunks[key][index]["embedding"] = embedding
        print("All Embeddings for the necessary input files required for to cover the retrieval process are created")
    
    # Return the updated lists of chunks (we just updated the original list of chunks by adding an additional key-value pair) with embeddings
    return lists_of_chunks