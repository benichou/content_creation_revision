from DVoice.prompt.model_persona_repo import MODEL_PERSONA_LAYOUT_REVISION
from DVoice.prompt.prompt_repo import MANUAL_INPUT_PROMPT
from DVoice.utilities.settings import AZURE_OPENAI_MODEL_NAME
from DVoice.utilities.chunking import chunk_documents_cohesively
from DVoice.utilities.llm_and_embeddings_utils import generate_response_from_text_input, instantiate_azure_openai_client
from DVoice.utilities.llm_structured_output import ManualInputParser
import asyncio
import ast
from typing import Dict, List, Any
import time

async def generate_response_async(chunk: str, client: Any) -> str:
    """
    Asynchronously generates a response for a given text chunk using Azure OpenAI.
 
    This function takes a chunk of text and asynchronously calls the Azure OpenAI model to process the chunk in markdown
    format.
    It handles errors and retries the request if an initial failure occurs. The response is parsed to extract
    the relevant information.
 
    Args:
        chunk (str): The text chunk to process in markdown format and generate a response for.
        client (Azure Open AI Client): The Azure OpenAI client used to interact with the model.
 
    Returns:
        str: The parsed response from the model, specifically structured output with the ManualInputParser class.
        Returns {'parsed_manual_input': "This is the parsed content my friend"}
 
    Example:
    >>> response = await generate_response_async("Some text to process", client)
    >>> print(response)
            {'parsed_manual_input': "# This is the parsed content my friend"}
 
    Notes:
        - The function uses `asyncio.to_thread` to run the blocking I/O operations asynchronously.
        - The function retries the operation if an exception occurs, with a 60-second delay before retrying.
    """
    try:
        response = await asyncio.to_thread(generate_response_from_text_input,
            MANUAL_INPUT_PROMPT,
            MODEL_PERSONA_LAYOUT_REVISION,
            chunk,
            client,
            AZURE_OPENAI_MODEL_NAME,
            response_format=ManualInputParser
        )
    except Exception as e:
        print(f"Initial error {e}")
        time.sleep(60) # in case the error was due to the TPM being reached previously in the try statement
        try:
            response = await asyncio.to_thread(generate_response_from_text_input,
                MANUAL_INPUT_PROMPT,
                MODEL_PERSONA_LAYOUT_REVISION,
                chunk,
                client,
                AZURE_OPENAI_MODEL_NAME,
                response_format=ManualInputParser
            )
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
            return ""  # Return empty string to avoid breaking the sequence
    parsed_output = ast.literal_eval(response[0].choices[0].message.content)
    
    return parsed_output["parsed_manual_input"]

async def process_chunks_parallel(chuncked_documents_pre_layout: Dict[str, List[str]], client: Any) -> str:
    """
    Processes chunks of documents in parallel while preserving the original order.
 
    This function processes a dictionary of chunked documents asynchronously, where each document is represented
    by a list of text chunks. It creates async tasks for each chunk, processes them concurrently, and concatenates the results
    while maintaining the order of the chunks.
 
    Args:
        chuncked_documents_pre_layout (Dict[str, List[str]]): A dictionary where the keys are document identifiers
            (e.g., file names) and the values are lists of text chunks to process.
        client (Azure Open AI Client): The Azure OpenAI client used to interact with the model for generating responses.
 
    Returns:
        str: The markdown formatted concatenated output from processing all the chunks, in the original order.
 
    Example:
    >>> output = await process_chunks_parallel({"file1": ["chunk1", "chunk2"]}, client)
    >>> print(output)
            "## Chunk 1 ### Chunk 2"
 
    Notes:
        - The function processes chunks in parallel using `asyncio.gather()` to execute the tasks concurrently.
        - The time it takes to process the chunks is measured and printed for performance monitoring.
    """
    start = time.time()
    markdown_output = ""
 
    for key, list_chunk in chuncked_documents_pre_layout.items():
        print(f"Processing file: {key}")
        # Create async tasks for each chunk
        tasks = [generate_response_async(chunk, client) for chunk in list_chunk] ## parallelization
        # Execute tasks concurrently and collect results
        results = await asyncio.gather(*tasks)
        # Join results in order and append to markdown_output
        markdown_output += "".join(results)
    
    end = time.time()
    process_time = end - start
    print(f"processing the chunks in parallel took {process_time}")
 
    return markdown_output


def parse_manual_input(manual_input_text: str, TOKEN) -> Dict[str, str]:
    """
    Parses the manual input text, processes it in chunks, and generates a markdown output.
 
    This function takes raw manual input text, splits it into chunks, processes them in parallel, 
    and then generates a markdown file with the processed content. The markdown file is stored 
    in a dictionary with a sample file path as the key.
 
    Args:
        manual_input_text (str): The raw text input provided by the user, which will be parsed and processed.
        TOKEN (Azure Access Token): The authentication token used to instantiate the Azure OpenAI client.
 
    Returns:
        Dict[str, str]: A dictionary containing the generated markdown output, with a sample file path as the key.
 
    Example:
    >>> manual_input = "This is some user input"
    >>> repo = parse_manual_input(manual_input, TOKEN)
    >>> print(repo)
            {"C:\\random_file_path\\to\\manual_input_inserted_by_user.md": "## Formatted in Markdown This is some user input"}
    """
    chuncked_documents_pre_layout = chunk_documents_cohesively({"raw_content":manual_input_text})
    markdown_output = ""
    manual_input_repo = {}
    client = instantiate_azure_openai_client(TOKEN)
    ## parallel processing of the chunks
    markdown_output = asyncio.run(process_chunks_parallel(chuncked_documents_pre_layout, client))
        
    manual_input_repo["C:\\random_file_path\\to\\manual_input_inserted_by_user.md"] = markdown_output 
    print(f"The following Markdown output has been generated from the manual input inserted \
          in the front end by the user")
    
    return manual_input_repo
    
    
    