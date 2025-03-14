import time
import asyncio
from collections import defaultdict
from DVoice.utilities.settings import CHUNK_SIZE, SELECTED_MODEL
from DVoice.utilities.llm_and_embeddings_utils import instantiate_azure_chat_openai, count_tokens_for_list_of_chunks
from DVoice.utilities.llm_structured_output import TextualClassificationOrNot

from DVoice.prompt.prompt_repo import CHUNK_CLASSIFICATION_PROMPT
from DVoice.prompt.model_persona_repo import MODEL_PERSONA_TEXT_VS_NOT_TEXT_CLASSIFICATION

from functools import partial
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.schema.prompt_template import format_document

from langchain_core.output_parsers import JsonOutputParser

from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from tqdm import tqdm
from typing import List, Tuple, Dict, Any


def chunk_into_cohesive_paragraphs(
    token_count_on_chunks: List[Tuple[int, int]], 
    chunks_list: List[str]
) -> List[str]:
    """
    Processes a list of text chunks and merges them into cohesive paragraphs while 
    preserving tabular data (aka tables) separately.
 
    This function takes a list of token counts mapped to chunk indices and merges the 
    chunks into larger, structured paragraphs. It ensures that tabular data (detected 
    by the presence of pipe characters '|') remains separate and is not merged with 
    regular paragraphs.
 
    Args:
        token_count_on_chunks (List[Tuple[int, int]]): 
            A list of tuples where each tuple contains:
            - The token count of a chunk (int).
            - The index of the chunk in the `chunks_list` (int).
        chunks_list (List[str]): 
            A list of text chunks to be processed.
 
    Returns:
        List[str]: A list of processed text chunks, where related paragraphs are merged 
                   together while tabular data remains in its own chunk.
 
    Notes:
        - If a chunk contains four or more '|' characters at the start or end, 
          it is classified as tabular data and stored separately.
        - Separate Chunks are merged//collated together until they reach `CHUNK_SIZE` (defined in DVoice.settings) tokens.
        - Processing time is logged at the end.
    """
    ## TODO: clean the local//dev code once we go to v1 release prod
    start_time =  time.time()
    last_chunk_idx = len(token_count_on_chunks) - 1 # Last chunk index
    chunk_count_cursor = 0 # Tracks token count within a chunk
    chunks_repo = [] # Stores the final merged chunks
    chunk = "" # Temporary storage for paragraph merging
    tabular_chunk = "" # Temporary storage for table data
    for token_count_analysis in token_count_on_chunks: # Unpack token count and index
        token_count, chunk_idx = token_count_analysis
        # token_count = token_count_analysis[0]
        # chunk_idx = token_count_analysis[1]
        # print(chunk_idx, chunks_list[chunk_idx], chunk_count_cursor)
        
        # Identify tabular data based on '|' character occurrence
        if "|" in chunks_list[chunk_idx][0:4] or "|" in chunks_list[chunk_idx][-4:]:
            count_of_bars = chunks_list[chunk_idx].count('|')
            if count_of_bars >= 4: # If there are 4+ bars, assume it's a table
                
                # Save the previous chunk before processing the table
                if chunk:
                    chunks_repo.append(chunk)
                    chunk_count_cursor = 0
                    chunk = ""
                # Store the table chunk separately
                tabular_chunk = chunks_list[chunk_idx]
                chunks_repo.append(tabular_chunk)
                # print("TABULAR")
                # print(tabular_chunk)
                tabular_chunk = "" # Reset after saving
                continue # do not process further since the whole table is its own chunk, get to a new chunk!
        
        # Merge//collate chunks while staying within CHUNK_SIZE and not at the last index
        if chunk_count_cursor < CHUNK_SIZE and chunk_idx != last_chunk_idx:
            # if chunk_idx >= 65:
            #     print(chunk_idx, chunks_list[chunk_idx], chunk_count_cursor, "CHECK")
            chunk += '\n\n' + chunks_list[chunk_idx] ## mesh collate with previous chunks. If no previous chunks, you are just adding the fiirst chunk
            chunk_count_cursor += token_count ## add count to chunk count cursor
        # If chunk size exceeds limit, store it and start a new one
        elif chunk_count_cursor >= CHUNK_SIZE and chunk_idx < last_chunk_idx: #make sure not to add the last bit that has already been added
            chunk += '\n\n' + chunks_list[chunk_idx]
            # if chunk_idx >= 65:
            #     print(chunk_idx, chunks_list[chunk_idx], chunk_count_cursor, "CHECK 1")
            # print("ADD THIS")
            # print(chunk)
            chunks_repo.append(chunk) # Save completed chunk
            chunk_count_cursor = 0 # Reset counter
            chunk = "" # Reset for the next chunk
        
        # Handle the last chunk separately to ensure it's stored
        if chunk_idx == last_chunk_idx:
            # print(chunk)
            # if chunks_list[chunk_idx] not in chunks_repo[-1]:
            chunk += '\n\n' + chunks_list[chunk_idx]
            # print("ADD THIS LAST")
            # print(chunk)
            chunks_repo.append(chunk)

    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Overall Chunking Processing is {processing_time} second(s)")
    
    return chunks_repo


def chunk_classification(
    file_chunks_repo: Dict[str, List[str]], 
    TOKEN, # the actual Access token object generated by calling the Azure method for Access token generation
) -> Dict[str, List[Document]]:
    """
    Classifies chunks of text as either textual or non-textual (e.g., images, tables).
 
    This function processes a dictionary of file paths and their associated chunks, 
    applies a language model to classify each chunk, and returns a dictionary mapping 
    file paths to classified Langchain `Document` objects.
 
    Args:
        file_chunks_repo (Dict[str, List[str]]): 
            A dictionary where keys are file paths, and values are lists of text chunks.
        TOKEN (Azure Access Token): 
            The API token required for authentication with the Azure OpenAI service.
 
    Returns:
        Dict[str, List[Document]]: 
            A dictionary where each file path maps to a list of Langchain `Document` 
            objects with classification metadata (`classification_type` key).
 
    Notes:
        - Uses Langchain to structure the text chunks into `Document` objects.
        - Runs classification in parallel using a Langchain pipe//`chain-based` approach.
        - Handles exceptions to retry classification in case of failures.
    """
    start_time = time.time()
    # Initialize the model and JSON parser
    model = instantiate_azure_chat_openai(TOKEN)
    parser = JsonOutputParser(pydantic_object=TextualClassificationOrNot)
    # Prepare classification prompt
    classification_query = "\n\n" + MODEL_PERSONA_TEXT_VS_NOT_TEXT_CLASSIFICATION + "\n\n" + CHUNK_CLASSIFICATION_PROMPT
    classification_prompt = PromptTemplate(template=f"{classification_query}")
    # Prepare the prompt that will use the page content for classification
    document_content_transfer_prompt = PromptTemplate(template="{page_content}")
    transfer_docs_to_prompt = PromptTemplate.from_template("Classify whether the input is textual or not :\n\n{context} ")
    partial_format_document = partial(format_document, prompt=document_content_transfer_prompt)
    
    # Create Langchain `Document` objects for each file and its chunks
    doc_repos = {}
    for file_path, list_of_chunks in file_chunks_repo.items():
        docs = []
        for chk_idx, chk in enumerate(list_of_chunks):
            docs.append(
                Document(
                page_content=chk,
                metadata={"source": file_path, "chunk_id": chk_idx,
                          "classification_type" : dict()},
            ))
        doc_repos[file_path] = docs

    # Define the classification chain    
    map_classify_chain = (
        {"context":partial_format_document}
        | transfer_docs_to_prompt + classification_prompt
        | model
        | parser
                )
    # Wrapper chain to retain original `Document` metadata while adding classification type
    map_classify_as_doc_chain = (RunnableParallel({"doc": RunnablePassthrough(), "content": map_classify_chain}) 
                                 ## Run the classification in parallel here
        |               (lambda x: Document(page_content=str(x["doc"].page_content), 
                                            metadata={"source": x["doc"].metadata["source"],
                                            "classification_type":x["content"]})) 
                        # previousline: save for each Langchain Document a new langchain document that has 
                        # the classification type added with structured json
    ).with_config(run_name="Classify (return doc)")
    # The final full classification chain
    map_classify = (map_classify_as_doc_chain.map()).with_config(run_name="Classification of chunks")
    
    # Process each file's chunks through the classification pipeline
    ## TODO: need to parallelize below code for faster inference
    file_chunks_classification_repo = {}
    for file_path, docs in tqdm(doc_repos.items()):
        try: 
            response =  map_classify.invoke(
                docs,
                config={"max_concurrency": 5}
            )
        except Exception as e:
            print(f"Initial error with {e}")
            try:
               response =  map_classify.invoke(
                docs,
                config={"max_concurrency": 5}
            )
            except Exception as e:
                 print(f"Failure classifying chunks with {e}")
        
        file_chunks_classification_repo[file_path] = response
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Classification of the chunks between text vs not text (images and tables) has taken {processing_time} \
            second(s)")
    
    return file_chunks_classification_repo


def chunk_documents_cohesively(markdown_extract_repo: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Splits markdown documents into cohesive chunks while preserving logical paragraph structures.
 
    This function processes a dictionary where each file path maps to a markdown string.
    It removes excessive newlines, splits the text into chunks, counts tokens in each chunk,
    and then organizes them into cohesive paragraphs.
 
    Args:
        markdown_extract_repo (Dict[str, str]): 
            A dictionary where keys are file paths (string), and values are extracted markdown text (string).
 
    Returns:
        Dict[str, List[str]]: 
            A dictionary where each file path (string) maps to a list of cohesive text chunks (list of strings).
 
    Notes:
        - Cleans excessive newlines to ensure well-structured chunks.
        - Uses token counting to determine chunk boundaries.
        - Handles markdown structures like paragraphs and tables very effectively.
    """
    start_time = time.time()
    
    cohesive_chunks_repo = {}
    for file_path, markdown in markdown_extract_repo.items():
        # Clean excessive newlines to normalize paragraph separation
        markdown = markdown.replace("\n\n\n\n\n", "\n\n")
        markdown = markdown.replace("\n\n\n\n", "\n\n")
        markdown = markdown.replace("\n\n\n", "\n\n")
        markdown = markdown.replace("\n\n \n\n", "\n\n")
        # markdown = markdown.replace("\n\n", "\n\n ") ## added to make sure we delineate well between distinct paragraphs and tables
        # markdown = markdown.replace("\n\n", " \n\n") ## added to make sure we delineate well between distinct paragraphs and tables
        
        # Split into chunks based on newlines first, fallback to space if necessary
        chunks_list = markdown.split("\n\n") # Split by paragraph-level separation
        if len(chunks_list) == 1: # if the chunk is actually only one (big or small does not matter) paragraph of text
            chunks_list = markdown.split("\n") # Try line-by-line separation
        if len(chunks_list) == 1: # if the chunk is actually a list of sentences without any line or paragraph spaces, then split at word level, very rare, never has been used so far
            chunks_list = markdown.split(" ") # Fallback to word-level splitting
        
        # Count tokens in each chunk asynchronously
        token_count_on_chunks = asyncio.run(count_tokens_for_list_of_chunks(chunks_list))
        # Chunk into cohesive paragraphs based on token count and inherent text characteristics
        chunks_repo = chunk_into_cohesive_paragraphs(token_count_on_chunks, chunks_list)
        cohesive_chunks_repo[file_path] = chunks_repo
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Cohesive chunking of the document took {processing_time} second(s)")
    
    return cohesive_chunks_repo

def prepare_list_chunks_and_metadata(dictionary_of_file_chunks: Dict[str, List[str]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Processes a dictionary of file chunks and prepares metadata for each chunk.
 
    This function takes a dictionary where each file name maps to a list of text chunks.
    It generates metadata including:
      - Title (file name)
      - Unique ID (combining file name and chunk index)
      - Text content of the chunk
      - Token count using a selected model
      - Placeholder for embedding (initially set to None)
 
    Args:
        dictionary_of_file_chunks (Dict[str, List[str]]): 
            A dictionary where keys are file names and values are lists of extracted text chunks.
 
    Returns:
        Dict[str, List[Dict[str, Any]]]: 
            A dictionary mapping file names to lists of chunk metadata dictionaries.
 
    Notes:
        - Uses `get_token_count` to compute token sizes for each chunk.
        - Each chunk is stored with a unique identifier.
        - Uses `defaultdict` to organize data by file title.
    """
    from utilities.openai_utils.process_prompt import get_token_count
    data = []        
    index = 0 # initialize index that serves to create part of the id
    for file_name, chunk_list in dictionary_of_file_chunks.items():
        for j, split in enumerate(chunk_list):
            chunk_token_size = get_token_count(split, SELECTED_MODEL) ## need to have the correct import statement
            data.append({
                "title"    : file_name, # file name reference
                "id"       : f"{file_name}|{index}{j}",  # Unique identifier for each chunk
                "text"     : split, # Chunked content
                'n_tokens' : chunk_token_size, # Token count
                "embedding": None, # Placeholder for embedding
            })
    
    # Organize chunks by file title
    concatenated_data = defaultdict(list)

    for document in data:
        concatenated_data[document["title"]].append(document)
    
    return concatenated_data
