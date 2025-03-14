import concurrent.futures
from utilities.openai_utils.process_prompt import answer_query_with_summarization
from DVoice.utilities.settings import SELECTED_MODEL
from typing import Dict, Any, List


def create_doc_summary(concatenated_data: Dict[str, Any], 
                       query: str, 
                       hard_compression: bool = True) -> List[Dict[str, Any]]:
    """
    Creates a summary for a collection of concatenated data by applying a summary query on each chunk 
    and summarizing the content.
 
    Args:
        concatenated_data (dict): A dictionary where keys are document titles and values are the content 
                              of the documents to be summarized. Each content is expected to be a 
                              list of data chunks.
        query (str): The query to be used for summarization.
        hard_compression (bool, optional): A flag indicating whether to apply hard compression (default is True).
    When Hard compression is True: It means we first summarize the chunks and then create a summary again out of the summarized
    chunks. When hard compression is False, we keep the chunks as is and then create a more detailed summary out of all chunks.
    
    Returns:
        list: A list of dictionaries, each containing:
            - "title": The title of the document.
            - "summary": The summary of the document.
            - "token_count_prompt": Token count for the prompt.
            - "token_count_completion": Token count for the completion.
            - "embeddings_count": Total token count across all chunks.
    """

    final_data_summary = []
    ## summarization at chunk level -  distilled content
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Prepare the futures
        futures = {executor.submit(answer_query_with_summarization, data, query, SELECTED_MODEL,
                                   summarization_at_chunk_level=hard_compression): \
                                   title for title, data in concatenated_data.items()}
        # Process the completed futures
        for future in concurrent.futures.as_completed(futures):
            title = futures[future]
            summary = future.result()
            token_sum = sum([int(element["n_tokens"]) for element in concatenated_data[title]])
            # if settings.DEBUG:
            #     print(f"got summary for {title}")
            final_data_summary.append({
                "title"                  : title,
                "summary"                : summary["text"],
                "token_count_prompt"     : summary["token_count_prompt"],
                "token_count_completion" : summary["token_count_completion"],
                "embeddings_count"       : token_sum,
            })
    
    return final_data_summary