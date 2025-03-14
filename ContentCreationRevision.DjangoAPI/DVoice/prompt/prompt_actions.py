from DVoice.prompt.model_persona_repo import MODEL_PERSONA_ADDITIONAL_INSTRUCTION_CATEGORIZATION, MODEL_PERSONA_TEXT_REVISION
from DVoice.prompt.model_persona_repo import MODEL_PERSONA_TRANSLATOR, MODEL_PERSONA_FILE_SELECTOR, MODEL_PERSONA_TEXT_VS_NOT_TEXT_CLASSIFICATION
from DVoice.prompt.model_persona_repo import MODEL_PERSONA_LANGUAGE_IDENTIFIER, MODEL_PERSONA_QUERY_BREAKDOWN, MODEL_PERSONA_QUERY_CLASSIFIER
from DVoice.prompt.model_persona_repo import MODEL_PERSONA_FILE_NAME_DETERMINATION
from DVoice.prompt.prompt_repo import ADDITIONAL_INSTRUCTION_CATEGORIZATION_PROMPT, INPUT_LANGUAGE_CLASSIFICATION_PROMPT 
from DVoice.prompt.prompt_repo import INPUT_TRANSLATION_PROMPT, INPUT_QUERY_BREAKDOWN_PROMPT, INPUT_QUERY_REWRITER_PROMPT 
from DVoice.prompt.prompt_repo import INPUT_NUMBER_OF_OUTPUT_TO_GENERATE_PROMPT, INPUT_BILL_96_COMPLIANCE_IDENTIFIER_PROMPT
from DVoice.prompt.prompt_repo import INPUT_QUERY_REWRITER_CORE_ACTION_PROMPT, COMPARE_ORIGINAL_VS_NEW_TEXT_PROMPT
from DVoice.prompt.prompt_repo import INPUT_QUERY_FILE_NAME, INPUT_TRANSLATION_PARAMETER_PROMPT
from DVoice.prompt.prompt_repo import INPUT_QUERY_INTENT_CLASSIFICATION_PROMPT, generate_prompt_files_identifier_for_retrieval_task
from DVoice.utilities.settings import AZURE_OPENAI_MODEL_NAME
from DVoice.utilities.llm_and_embeddings_utils import generate_response_from_text_input, instantiate_azure_openai_client
from DVoice.utilities.llm_structured_output import PromptCategorizationParser, LanguageCategorization 
from DVoice.utilities.llm_structured_output import BrokenDownQueries, Bill96Compliance, NumberOfOutputFiles, QueryIntent, ListFiles
import ast, json # for structured output parsing into python memory
import asyncio
import time
from typing import Any, Dict, Optional, List

def determine_additional_insturctions_intent(manual_input_text: str, 
                                             TOKEN) -> dict:
    """
    Determines the intent behind additional instructions provided in a manual input text.
 
    This function:
      - Uses Azure OpenAI to classify the provided text into predefined instruction categories.
      - Attempts to parse the response into a structured dictionary format.
      - Retries once in case of an initial failure.
 
    Args:
        manual_input_text (str): The user-provided instruction text for categorization.
        TOKEN (Azure Access Token): Authentication token for Azure OpenAI API.
 
    Returns:
        dict: A structured dictionary representing the categorized intent of the input text.
 
    Notes:
        - Uses `generate_response_from_text_input` to process text via Azure OpenAI.
        - Attempts to parse the response using `ast.literal_eval` to gather the structured output properly
        - Implements a retry mechanism in case of failures.
    """
    
    client = instantiate_azure_openai_client(TOKEN) # Initialize Azure OpenAI client
    try:
        response = generate_response_from_text_input(ADDITIONAL_INSTRUCTION_CATEGORIZATION_PROMPT,
                                                     MODEL_PERSONA_ADDITIONAL_INSTRUCTION_CATEGORIZATION,
                                                     manual_input_text, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=PromptCategorizationParser)
        # Extract and parse response content
        prompt_categorization = ast.literal_eval(response[0].choices[0].message.content)
    except Exception as e:
        # Retry once in case of failure
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(ADDITIONAL_INSTRUCTION_CATEGORIZATION_PROMPT,
                                                         MODEL_PERSONA_ADDITIONAL_INSTRUCTION_CATEGORIZATION,
                                                         manual_input_text, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=PromptCategorizationParser)
            # Extract and parse response content
            prompt_categorization = ast.literal_eval(response[0].choices[0].message.content)
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
        
    print(f"Completed Prompt categorization of the additional instructions")
    
    return prompt_categorization

def determine_clean_intent(prompt_categorization: Dict[str, Any]) -> Dict[str, bool]:
    """
    Determines whether style modification is required based on the given prompt categorization.
 
    This function:
      - Checks if the "style_modification" key in `prompt_categorization` is `False` (boolean or string).
      - Returns a dictionary with `"style_modification": False` if no modification is needed.
      - Returns a dictionary with `"style_modification": True` if modification is required.
 
    Args:
        prompt_categorization (Dict[str, Any]): A dictionary containing categorization details,
            specifically a "style_modification" key that can be:
            - A boolean (`True` or `False`)
            - A string (`"True"`, `"TRUE"`, `"False"`, `"FALSE"`)
 
    Returns:
        Dict[str, bool]: A dictionary containing the cleaned style modification intent.
 
    Example:
        >>> determine_clean_intent({"style_modification": "True"})
        {'style_modification': True}
 
        >>> determine_clean_intent({"style_modification": False})
        {'style_modification': False}
 
    Notes:
        - This function ensures that "True"/"False" string values are converted to actual booleans.
        - If the value is already a boolean, it is returned as-is.
    """
    if prompt_categorization["style_modification"] is False:
        style_modification = False
        return {"style_modification":style_modification}
    elif prompt_categorization["style_modification"] in ["False", "FALSE"]:
        style_modification = False
        return {"style_modification":style_modification}
    if prompt_categorization["style_modification"]:
        style_modification = True
        return {"style_modification":style_modification}
    elif prompt_categorization["style_modification"] in ["True", "TRUE"]:
        style_modification = True
        return {"style_modification":style_modification}
    
def determine_input_language(query: str, 
                             TOKEN) -> Dict[str, str]:
    """
    Determines the language of the given input text using an Azure OpenAI model.
 
    This function:
      - Sends the input `query` to an Azure OpenAI model for language identification.
      - Parses the model's response to extract the detected language.
      - Handles potential errors by retrying once if an initial failure occurs.
      - Returns a structured dictionary containing the language classification.
 
    Args:
        query (str): The input text for which the language needs to be determined.
        TOKEN (Azur Access Token): Authentication token for accessing the Azure OpenAI API.
 
    Returns:
        Dict[str, str]: A dictionary containing the language classification result, the key is a string and the value is a string
 
    Example:
        >>> determine_input_language("Bonjour, comment ça va?", "your_token_here")
        {'language': 'French'}
 
        >>> determine_input_language("Hello, how are you?", "your_token_here")
        {'language': 'English'}
 
    Notes:
        - The function uses `instantiate_azure_openai_client(TOKEN)` to set up the API client.
        - `generate_response_from_text_input(...)` is called with a predefined prompt for language classification.
        - If an error occurs in the first attempt, the function retries once before failing.
    """
    # Instantiate the Azure OpenAI client 
    client = instantiate_azure_openai_client(TOKEN)
    try:
        # Attempt to classify the language of the input query
        response = generate_response_from_text_input(INPUT_LANGUAGE_CLASSIFICATION_PROMPT,
                                                     MODEL_PERSONA_LANGUAGE_IDENTIFIER,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=LanguageCategorization)
        prompt_categorization = ast.literal_eval(response[0].choices[0].message.content)
    except Exception as e:
        print(f"Initial error {e}")
        # Retry once in case of failure
        try:
            response = generate_response_from_text_input(INPUT_LANGUAGE_CLASSIFICATION_PROMPT,
                                                         MODEL_PERSONA_LANGUAGE_IDENTIFIER,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=LanguageCategorization)
            prompt_categorization = ast.literal_eval(response[0].choices[0].message.content)
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
            return {} # Return an empty dictionary in case of complete failure
    
    print(f"Completed input language determination")

    return prompt_categorization


def translate_query_to_desired_language(TOKEN, 
                                        query: str, 
                                        target_language: str = "English") -> Optional[str]:
    """
    Translates a given query into the desired target language using an Azure OpenAI model.
 
    This function:
      - Sends the input `query` to an Azure OpenAI model with a translation prompt.
      - Attempts to translate the input text into the specified `target_language`.
      - Retries once if an error occurs during the initial request.
      - Returns the translated text if successful, otherwise returns `None`.
 
    Args:
        TOKEN (Azure Access Token): Authentication token for accessing the Azure OpenAI API.
        query (str): The input text to be translated.
        target_language (str, optional): The language to translate the text into. Defaults to "English".
 
    Returns:
        Optional[str]: The translated text if successful, otherwise `None`.
 
    Example:
        >>> translate_query_to_desired_language("your_token_here", "Bonjour, comment ça va?", "English")
        'Hello, how are you?'
 
        >>> translate_query_to_desired_language("your_token_here", "你好，你怎么样？", "French") (Niho ma, ni shi she ma)
        'Bonjour, comment allez-vous ?'
 
    Notes:
        - The function uses `instantiate_azure_openai_client(TOKEN)` to create an API client.
        - If the first attempt fails, it retries once before returning `None`.
        - Uses a predefined prompt (`INPUT_TRANSLATION_PROMPT`) for language translation.
    """
    # Instantiate the Azure OpenAI clien
    client = instantiate_azure_openai_client(TOKEN)
    # Construct translation instruction for the model
    target_lang_for_prompt = f" to {target_language}"
    try:
        # Attempt translation
        response = generate_response_from_text_input(INPUT_TRANSLATION_PROMPT + target_lang_for_prompt,
                                                     MODEL_PERSONA_LANGUAGE_IDENTIFIER,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
    except Exception as e:
        print(f"Initial error {e}")
        # Retry once in case of failure
        try:
            response = generate_response_from_text_input(INPUT_TRANSLATION_PROMPT + target_lang_for_prompt,
                                                         MODEL_PERSONA_LANGUAGE_IDENTIFIER,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
            return None # Return None in case of complete failure

    print(f"Completed query translation to {target_language}")

    return response[0].choices[0].message.content

async def translate_query_parameter_to_english(query: str, client: Any) -> str:
    """
    Translates a given query parameter into English using an Azure OpenAI model.
 
    This function:
      - Sends the input `query` to an Azure OpenAI model for translation into English.
      - Uses `asyncio.to_thread` to execute the translation in a non-blocking manner.
      - Retries once if an error occurs during the initial request.
      - Returns the translated text if successful.
 
    Args:
        query (str): The input query to be translated.
        client (Any): The Azure OpenAI client instance used for API calls.
 
    Returns:
        str: The translated parameter (from the query argument) in English.
 
    Example:
    >>> await translate_query_parameter_to_english("Article de journal quotidien", client)
        'Daily Newspaper Article'
 
    Notes:
        - Uses a predefined prompt (`INPUT_TRANSLATION_PARAMETER_PROMPT`) for translation.
        - Retries once if the first attempt fails.
        - Runs `generate_response_from_text_input` asynchronously to avoid blocking execution.
    """
    try:
        # Attempt to translate query using Azure OpenAI model
        response = await asyncio.to_thread(generate_response_from_text_input,
                                           INPUT_TRANSLATION_PARAMETER_PROMPT,
                                           MODEL_PERSONA_LANGUAGE_IDENTIFIER,
                                           query, 
                                           client, 
                                           AZURE_OPENAI_MODEL_NAME,
                                           response_format=None)
    except Exception as e:
        print(f"Initial error {e}")
        # Retry once in case of failure
        try:
            response = await asyncio.to_thread(generate_response_from_text_input,
                                           INPUT_TRANSLATION_PARAMETER_PROMPT,
                                           MODEL_PERSONA_LANGUAGE_IDENTIFIER,
                                           query, 
                                           client, 
                                           AZURE_OPENAI_MODEL_NAME,
                                           response_format=None)
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
            return ""  # Return an empty string in case of failure
        
    print(f"Completed query translation to english of the parameters")

    return response[0].choices[0].message.content

async def process_parameter_translation(list_parameters: List[str], TOKEN) -> List[str]:
    """
    Processes the translation of a list of query parameters into English in parallel.
 
    This function:
      - Instantiates an Azure OpenAI client using the provided `TOKEN`.
      - Creates asynchronous translation tasks for each parameter in `list_parameters`.
      - Uses `asyncio.gather` to execute all translations concurrently for efficiency.
      - Measures and prints the total processing time.
      - Returns the list of translated parameters.
 
    Args:
        list_parameters (List[str]): A list of query parameters to be translated.
        TOKEN (Azure Access Token): The authentication token used to instantiate the Azure OpenAI client.
 
    Returns:
        List[str]: A list of translated query parameters.
 
    Example:
        >>> await process_parameter_translation([Concis", "Essai Philosophique"], TOKEN)
        Returns: ['Concise', 'Philosophical Essay']
 
    Notes:
        - This function improves efficiency by running translations in parallel.
        - `asyncio.gather` ensures all tasks are executed concurrently.
    """
    start = time.time()
    # Instantiate Azure OpenAI client
    client = instantiate_azure_openai_client(TOKEN)
    # Create async tasks for each parameter to be translated to English
    tasks = [translate_query_parameter_to_english(param, client) for param in list_parameters] ## parallelization
    # Execute tasks concurrently and collect results
    results = await asyncio.gather(*tasks)
    
    end = time.time()
    process_time = end - start
    print(f"Processing the translation in parallel of the different parameters took {process_time} seconds")
 
    return results


def break_down_query_to_multiple_query_output(TOKEN: Any, query: str) -> Dict[str, List[str]]:
    """
    Breaks down a given query into multiple outputs for further processing.
 
    This function sends the provided `query` to an Azure OpenAI client for breakdown into smaller parts, based on a predefined prompt.
    It handles errors by retrying the request in case of failure. The function returns the breakdown of the query as a dictionary, parsed from the response.
 
    Args:
        TOKEN (Azure Access Token): The authentication token to instantiate the Azure OpenAI client.
        query (str): The input query to be broken down.
 
    Returns:
        Dict[str, List[str]]: A dictionary containing the breakdown of the query where the key is 'query_breakdown' abd 
        the value is a list of strings. Each string is sub component of the broken down query
 
    Example:
    >>> query="Create a social media post in French and summarize the content about the Trade negotiations"
    >>> query_output = break_down_query_to_multiple_query_output(TOKEN, query)
    >>> print(query_output)
        {'query_breakdown': ['Create a social media post in French', 'Summarize the content about the Trade negotiations']}
 
    Notes:
        - The function retries the request in case of an exception to ensure robustness.
        - `response_format=BrokenDownQueries` ensures the response is structured as expected for query breakdown.
    """
    client = instantiate_azure_openai_client(TOKEN) # Initialize the Azure OpenAI client with the provided TOKEN
    try:
        response = generate_response_from_text_input(INPUT_QUERY_BREAKDOWN_PROMPT,
                                                     MODEL_PERSONA_QUERY_BREAKDOWN,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=BrokenDownQueries)
        query_breakdown = ast.literal_eval(response[0].choices[0].message.content) # Parse the response into a dictionary
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(INPUT_QUERY_BREAKDOWN_PROMPT,
                                                         MODEL_PERSONA_QUERY_BREAKDOWN,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=BrokenDownQueries) # Retry and parse response again
            query_breakdown = ast.literal_eval(response[0].choices[0].message.content)
        except Exception as e:
            print(f"Complete failure breaking down query with error {e}")
            return {'query_breakdown': []} ## Like returning None
        
    print(f"Completed query breakdown")

    return query_breakdown

def rewrite_query(TOKEN: Any, query: str) -> str:
    """
    Rewrites the provided query using an Azure OpenAI model.
 
    This function sends the given query to the Azure OpenAI service for rewriting based on a predefined prompt. 
    If an error occurs during the first attempt, it retries the process. 
    The function returns the rewritten version of the query.
 
    Args:
        TOKEN (Azure Access Token): The authentication token used to instantiate the Azure OpenAI client.
        query (str): The query that needs to be rewritten.
 
    Returns:
        str: The rewritten version of the input query.
 
    Example:
    >>> rewritten_query = rewrite_query(TOKEN, "How can I improve my coding skills?")
    >>> print(rewritten_query)
        "What are some ways to enhance my programming abilities?"
 
    Notes:
        - The function retries the request if the initial attempt fails to ensure robustness.
        - `response_format=None` specifies that no special response format is needed.
    """
    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(INPUT_QUERY_REWRITER_PROMPT,
                                                     MODEL_PERSONA_TEXT_REVISION,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(INPUT_QUERY_REWRITER_PROMPT,
                                                         MODEL_PERSONA_TEXT_REVISION,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
        except Exception as e:
            print(f"Complete failure error:{e}")
        
    print(f"Completed Query Rewriting")

    return response[0].choices[0].message.content

def rewrite_query_core_action(TOKEN: Any, 
                              query: str) -> str:
    """
    Rewrites the provided query based on a core action prompt using an Azure OpenAI model.
 
    This function sends the given query to the Azure OpenAI service for rewriting based on a specific prompt for core actions. 
    If the first attempt fails, the function retries. 
    The function returns the rewritten query.
 
    Args:
        TOKEN (Azure Access Token): The authentication token used to instantiate the Azure OpenAI client.
        query (str): The query that needs to be rewritten.
 
    Returns:
        str: The rewritten version of the input query.
 
    Example:
    >>> rewritten_query = rewrite_query_core_action(TOKEN, "How do I optimize my code?")
    >>> print(rewritten_query)
            "What are the best practices for improving code performance?"
    
    Notes:
        - The function retries the request if the initial attempt fails, ensuring robustness.
        - `response_format=None` specifies that no special response format is needed.
    """
    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(INPUT_QUERY_REWRITER_CORE_ACTION_PROMPT,
                                                     MODEL_PERSONA_TEXT_REVISION,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(INPUT_QUERY_REWRITER_CORE_ACTION_PROMPT,
                                                         MODEL_PERSONA_TEXT_REVISION,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
        except Exception as e:
            print(f"Complete failure error:{e}")
        
    print(f"Completed Query Rewriting")

    return response[0].choices[0].message.content


def identify_bill_96_compliance(TOKEN: Any, 
                                query: str) -> Dict[str, bool]:
    """
    Identifies whether a given query complies with Bill 96 requirements.
 
    This function sends the provided query to an Azure OpenAI model for compliance checking with Bill 96. 
    It retries the operation if the initial request fails. The function returns the identified Bill 96 requirements.
 
    Args:
        TOKEN (Azure Access Token): The authentication token to instantiate the Azure OpenAI client. 
        query (str): The query to be checked for compliance with Bill 96.
 
    Returns:
        Dict[str, bool]: A dictionary identifiying whether there needs to be bill 96 compliance: 
        Returns: {'bill_96_compliance' : True} or {'bill_96_compliance' : False}
 
    Example:
    >>> compliance_info = identify_bill_96_compliance(TOKEN, "Please create a document that adheres to bill 96 compliance requirements")
    >>> print(compliance_info)
            {'bill_96_compliance' : True}
 
    Notes:
        - The function retries the request if the initial attempt fails to ensure reliability.
        - `response_format=Bill96Compliance` specifies that the response is expected to include compliance details in a structured format.
    """
    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(INPUT_BILL_96_COMPLIANCE_IDENTIFIER_PROMPT,
                                                     MODEL_PERSONA_TEXT_REVISION,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=Bill96Compliance)
        bill96_requirements = json.loads(response[0].choices[0].message.content)
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(INPUT_BILL_96_COMPLIANCE_IDENTIFIER_PROMPT,
                                                         MODEL_PERSONA_TEXT_REVISION,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=Bill96Compliance)
            bill96_requirements = json.loads(response[0].choices[0].message.content)
        except Exception as e:
            print(f"Complete failure error:{e}")
        
    print(f"Completed Bill96 requirements identification")

    return bill96_requirements

def identify_number_output_files(TOKEN, 
                                 query: str) -> Dict[str, bool]:
    """
    Identifies the number of output files to generate based on the provided query.
 
    This function sends the query to an Azure OpenAI model to determine how many output files need to be generated. 
    In particular, does the master query to be assessed need (True or False) one or more than one otput file
    It retries the request if the initial attempt fails, and returns the result indicating whether only one output file is required.
 
    Args:
        TOKEN (Azure Access Token): The authentication token to instantiate the Azure OpenAI client. 
        query (str): The query whose result will determine the number of output files to be generated.
 
    Returns:
        Dict[str, bool]: A dictionary containing information about the number of output files to generate.
        Returns either {'only_one_file': True} or {'only_one_file': False}
        Very rarely, the LLM can make mistakes and output {'only_one_file': 'True'} or {'only_one_file': 'TRUE'} (Same for False)
        Example:
    >>> result = identify_number_output_files(TOKEN, "How many output files should be generated?")
    >>> print(result)
            {'only_one_file': True}
 
    Notes:
        - The function retries the request if the initial attempt fails to ensure reliability.
        - `response_format=NumberOfOutputFiles` specifies that the response is expected to include the number of output files.
    """
    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(INPUT_NUMBER_OF_OUTPUT_TO_GENERATE_PROMPT,
                                                     MODEL_PERSONA_TEXT_REVISION,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=NumberOfOutputFiles)
        only_one_file_indicator = json.loads(response[0].choices[0].message.content)
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(INPUT_NUMBER_OF_OUTPUT_TO_GENERATE_PROMPT,
                                                         MODEL_PERSONA_TEXT_REVISION,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=NumberOfOutputFiles)
            only_one_file_indicator = json.loads(response[0].choices[0].message.content)
        except Exception as e:
            print(f"Complete failure error:{e}")
        
    print(f"Completed number output files identification")

    return only_one_file_indicator


def determine_query_intended_task(TOKEN: Any, query: str) -> Dict[str, bool]:
    """
    Determines the intended task for a given query, such as `retrieval`, `summarization`, or `rewriting`.
 
    This function sends the provided query to an Azure OpenAI model to classify the query's intent 
    (e.g., whether it is a `retrieval` task, `summarization` task, or `rewriting` task). It retries the request 
    if the initial attempt fails, ensuring reliable task identification.
 
    Args:
        TOKEN (Azure Access Token): The authentication token to instantiate the Azure OpenAI client. 
        query (str): The query whose intended task (retrieval, summarization, rewriting, etc.) needs to be determined.
 
    Returns:
        Dict[str, bool]: A dictionary identifiying whether it is `summarization`, `rewriting` or `retrieval`
        Returns: {'summarization': boolean, 'rewriting': boolean, 'retrieval': boolean}
    Example:
    >>> result = determine_query_intended_task(TOKEN, "Summarize this text for me.")
    >>> print(result)
        {'summarization': True, 'rewriting': False, 'retrieval': False}
 
    Notes:
        - The function retries the request in case of an error to enhance reliability.
        - The response is parsed to identify the specific task intended by the query in a dictionary
 
    """
    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(INPUT_QUERY_INTENT_CLASSIFICATION_PROMPT,
                                                     MODEL_PERSONA_QUERY_CLASSIFIER,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=QueryIntent)
        # Parse the response to determine the query's intended task
        query_intent_determinaton = json.loads(response[0].choices[0].message.content)
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(INPUT_QUERY_INTENT_CLASSIFICATION_PROMPT,
                                                         MODEL_PERSONA_QUERY_CLASSIFIER,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=QueryIntent)
            # Parse the response again after retry
            query_intent_determinaton = json.loads(response[0].choices[0].message.content)
        except Exception as e:
            print(f"Complete failure error:{e}")
        
    print(f"Completed Task Identification")

    return query_intent_determinaton


def determine_necessary_files(TOKEN: Any, 
                              file_summaries: List[Dict[str, str]], 
                              user_query: str, 
                              task_type: str) -> List[str]:
    """
    Determines the necessary files for a specific task based on file summaries and the user's query.
 
    This function generates a prompt using the provided file summaries, user query, and task type, 
    then uses an Azure OpenAI model to retrieve a list of files that are necessary to fulfill the task. That list of files,
    is retrieved from the list of summaries (dictionaries) for each file
 
    It retries the request if the initial attempt to identify the files fails.
 
    Args:
        TOKEN (Azure Access Token): The authentication token for accessing the Azure OpenAI client.
        file_summaries (List[Dict[str, str]]): A list of summaries of available files that may be relevant to the task.
        user_query (str): The user's query that will help guide the file selection process.
        task_type (str): The type of task (e.g., retrieval, summarization) to help determine which files are necessary.
 
    Returns:
        List[str]: A list of file identifiers (e.g., filenames, URLs, or file paths) that are deemed necessary for the task.
 
    Example:
    >>> file_summaries = ["title"                  : "Canadian Economy Trends.docx",
                          "summary"                : " # The Canadian Economy Trends \n\n ## ...",
                        "token_count_prompt"     : 500,
                        "token_count_completion" : 754,
                        "embeddings_count"       : None,
                    }, {...}, {...}..]
    >>> user_query = "Please create an executive summary about the Canadian economy trends"
    >>> task_type = "summarization"
    >>> result = determine_necessary_files(TOKEN, file_summaries, user_query, task_type)
    >>> print(result)
            ['Canadian Economy Trends.docx'] ## note it can also be multiple files to 
            cater to a single user query especially when the user wants a 
            combined executive summary out of several files
 
    Notes:
        - The function uses retries in case of failure when determining the necessary files.
        - The list of necessary files is parsed from the model's response by using structured output with the ListFiles
          class
    """

    prompt_message, query = generate_prompt_files_identifier_for_retrieval_task(file_summaries, user_query, task_type)

    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(prompt_message,
                                                     MODEL_PERSONA_FILE_SELECTOR,
                                                     query, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=ListFiles)
        list_of_files = json.loads(response[0].choices[0].message.content)
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(prompt_message,
                                                         MODEL_PERSONA_FILE_SELECTOR,
                                                         query, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=ListFiles)
            list_of_files = json.loads(response[0].choices[0].message.content)
        except Exception as e:
            print(f"Complete failure error:{e}")
        
    print(f"Completed necessary list of files identification")

    return list_of_files

def translate_identical_alternative_language(TOKEN, 
                                             content_to_translate: str, 
                                             target_language: str) -> str:
    """
    Translates the provided content to a target language (English or French) using Azure OpenAI services.
 
    This function checks the specified target language, constructs the appropriate prompt, 
    and then translates the provided content into the target language.
    It is meant to be used for complete and identical translation of the final output into the other
      official canadian language (could be expanded
    to any other languages covered by the LLM in the future)
 
    If the initial translation attempt fails, the function retries the request.
 
    Args:
        TOKEN (Azure Access Token): The authentication token used to access the Azure OpenAI client.
        content_to_translate (str): The content to be translated.
        target_language (str): The target language for translation ("EN" for English, "FR" for French).
 
    Returns:
        str: The identical content but translated to the target language
 
    Example:
    >>> translated_text = translate_identical_alternative_language(TOKEN, <Final Output about the Canadian Economic Trends in English>, "FR")
    >>> print(translated_text)
            <Translated Output about the Canadian Economic Trends in French>
 
    Notes:
        - This function only supports translation between French and English for now
        - The function handles retries in case of a failure during the translation process.
    """
    # Determine the language based on the provided target_language code
    if target_language == "EN":
        language = "English"
    elif target_language == "FR":
        language = "French"
    else:
        raise ValueError("Unsupported target language. Only 'EN' and 'FR' are supported.")
    client = instantiate_azure_openai_client(TOKEN)
    # Construct the input task prompt based on the target language
    input_task_prompt = INPUT_TRANSLATION_PROMPT + f" {language}"
    try:
        response = generate_response_from_text_input(input_task_prompt,
                                                     MODEL_PERSONA_TRANSLATOR,
                                                     content_to_translate, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
        translated_content = response[0].choices[0].message.content
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(input_task_prompt,
                                                         MODEL_PERSONA_TRANSLATOR,
                                                         content_to_translate, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
            translated_content = response[0].choices[0].message.content
        except Exception as e:
            # Log the failure if the retry also fails
            print(f"Complete failure error:{e}")
        
    print(f"Completed necessary list of files identification")

    return translated_content

def determine_query_task_type_pairs(TOKEN, 
                                    rewritten_query: str, 
                                    list_of_tasks_to_complete: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Determines the task type pairs for each query in the provided list based on the analysis of the rewritten query.
 
    This function iterates through each task in the provided list of tasks, performs an intent analysis
    on the rewritten query, and maps each query to its corresponding task type(s).
 
    Args:
        TOKEN (Any): The authentication token used to access the Azure OpenAI client.
        rewritten_query (str): The query whose intent is to be analyzed.
        list_of_tasks_to_complete (Dict[str, List[str]]): A dictionary wherethe only and sole (always) key is `query_breakdown`
                                                        and the sole value is  
                                                        the list of sub queries coming from the broken down master query.
 
    Returns:
        Dict[str, List[str]]: A dictionary where the keys are the sub queries and the values are lists of 1 unique task type
                               that the query is mapped to based on its intent analysis either `summarization`, `rewriting`,
                               or `retrieval`
 
    Example:
    >>> task_pairs = determine_query_task_type_pairs(TOKEN, "What are the results?", {'query_breakdown': 
                                                                                ['Create a social media post in French', 
                                                                                'Summarize the content about the Trade negotiations']})
    >>> print(task_pairs)
        {"Create a social media post in French": ["retrieval"], 
        "Summarize the content about the Trade negotiations": ["summarization"]}
 
    Notes:
        - The function relies on the `determine_query_intended_task` function to analyze the intent of the query.
    """
    query_task_pairs = {}
    # Iterate over each task and its associated queries
    for _, tasks in list_of_tasks_to_complete.items():
        for query in tasks:
            # Perform intent analysis for the rewritten query
            intent_analysis = determine_query_intended_task(TOKEN, rewritten_query)
            # Determine the task type(s) from the intent analysis
            task_type = [key for key, value in intent_analysis.items() if value is True]
            # Map the query to its determined task type(s)
            query_task_pairs[query] = task_type
    
    # Return the dictionary containing query-task type pairs
    return query_task_pairs

def compare_original_vs_revised_text(original_text: str, revised_text: str, TOKEN) -> str:
    """
    Compares the original text with the revised text and provides an explanation of the revision.
 
    This function takes the original and revised versions of a text and sends them to a language model 
    for comparison. It returns an explanation of the changes between the original and revised texts.
 
    Args:
        original_text (str): The original text before revision.
        revised_text (str): The revised version of the text.
        TOKEN (Azure Access Token): The authentication token used to instantiate the Azure OpenAI client.
 
    Returns:
        str: The explanation of the revision as generated by the language model.
 
    Example:
    >>> explanation = compare_original_vs_revised_text("Hello world.", "Hello, world my man!", TOKEN)
    >>> print(explanation)
            "The revised text adds a comma after 'Hello', to give gravitas and 'my man' to make it more relatable"
 
    Notes:
        - The function relies on the `generate_response_from_text_input` method for generating the revision explanation.
        - In case of failure, the function retries the request once before raising an error.
    """
    texts_for_comparison = f"The 'Original' text is: {original_text} and the 'Revised' text os {revised_text}"
    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(COMPARE_ORIGINAL_VS_NEW_TEXT_PROMPT,
                                                     MODEL_PERSONA_TEXT_VS_NOT_TEXT_CLASSIFICATION,
                                                     texts_for_comparison, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
        revision_explanation = response[0].choices[0].message.content
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(COMPARE_ORIGINAL_VS_NEW_TEXT_PROMPT,
                                                         MODEL_PERSONA_TEXT_VS_NOT_TEXT_CLASSIFICATION,
                                                         texts_for_comparison, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
            revision_explanation = response[0].choices[0].message.content
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
        
    print(f"Completed Prompt categorization of the additional instructions")
    
    return revision_explanation

def determine_file_output_user_friendly_name(query: str, 
                                             language: str, 
                                             TOKEN) -> str:
    """
    Determines a user-friendly file name based on the given query and language.
 
    This function takes an input query, determines the language (either French or English), 
    and uses an AI model to generate a user-friendly file name based on the original query.

    Used only in DVoice Creation
 
    Args:
        query (str): The original query for which a user-friendly file name needs to be generated.
        language (str): The language in which the file name should be generated ('FR' for French or 'EN' for English).
        TOKEN (Azure Access Token): The authentication token used to instantiate the Azure OpenAI client.
 
    Returns:
        str: A user-friendly file name generated by the AI model based on the input query and language.
 
    Example:
    >>> user_friendly_name = determine_file_output_user_friendly_name("Retrieve data on sales figures", "EN", TOKEN)
    >>> print(user_friendly_name)
        "Sales_Figures_Data_Files"
 
    Notes:
        - The function defaults to 'French' if the language is 'FR', otherwise defaults to 'English'.
        - The function retries the request once in case of failure before raising an error.
    """
    # Determine the language to use for generating the file name
    language = "French" if language == "FR" else "English"
    # Prepare the query for generating the user-friendly file name
    query_to_find_file_name = f"The 'original' query is {query} and please create the file name in {language}"
    client = instantiate_azure_openai_client(TOKEN)
    try:
        # Generate the response from the model to determine the user-friendly file name
        response = generate_response_from_text_input(INPUT_QUERY_FILE_NAME,
                                                     MODEL_PERSONA_FILE_NAME_DETERMINATION,
                                                     query_to_find_file_name, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
        user_friendly_name = response[0].choices[0].message.content
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(INPUT_QUERY_FILE_NAME,
                                                         MODEL_PERSONA_FILE_NAME_DETERMINATION,
                                                         query_to_find_file_name, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
            user_friendly_name = response[0].choices[0].message.content
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
        
    print(f"Completed Prompt categorization of the additional instructions")
    
    return user_friendly_name