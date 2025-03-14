import os
from pathlib import Path
import ast
from DVoice.parsing.file_parsing import parse_files, extract_markdown_from_parsed_output
from DVoice.utilities.llm_and_embeddings_utils import generate_response_from_text_input, instantiate_azure_openai_client
from DVoice.prompt.model_persona_repo import MODEL_PERSONA_TEXT_SUMMARIZATION, MODEL_PERSONA_TEXT_EXTRACTION
from DVoice.prompt.prompt_repo import GUIDELINE_SUMMARIZATION_PROMPT, GUIDELINE_EXTRACTION_PROMPT
from DVoice.utilities.settings import AZURE_OPENAI_MODEL_NAME

from typing import Dict, Any

def create_guidelines(guideline_markdown_extract_repo: Dict[str, str]) -> Dict[str, str]:
    """
    Process a repository of markdown guidelines and extract summaries for each document.
 
    This function iterates through a collection of markdown documents, identifies the file,
    and applies either a specific manual extraction method or a summarization method to generate
    guideline summaries. The summaries are stored in a repository and returned.
 
    Args:
        guideline_markdown_extract_repo (Dict[str, str]): A dictionary where the keys are the file paths of the guidelines,
                                                         and the values are the markdown content for each respective guideline.
 
    Returns:
        Dict[str, str]: A dictionary containing the filenames (without extension) as keys and their corresponding summarized
                        guidelines as values.
    """
    guideline_summaries_repo = {}
    for file_path, guideline_markdown_text in guideline_markdown_extract_repo.items():
        if Path(file_path).stem == "Content Voice_2021_Param4_Editorial Style Guide":
            print("The markdown guideline has been crafted manually for now otherwise it is way too long")
            guideline_summaries, execution_time = generate_response_from_text_input(GUIDELINE_EXTRACTION_PROMPT,
                                                                                    MODEL_PERSONA_TEXT_EXTRACTION, 
                                                                                    guideline_markdown_text, 
                                                                                    client, 
                                                                                    AZURE_OPENAI_MODEL_NAME, 
                                                                                    response_format=None, 
                                                                                    )
        else:
            guideline_summaries, execution_time = generate_response_from_text_input(GUIDELINE_SUMMARIZATION_PROMPT,
                                                                                    MODEL_PERSONA_TEXT_SUMMARIZATION, 
                                                                                    guideline_markdown_text, 
                                                                                    client, 
                                                                                    AZURE_OPENAI_MODEL_NAME, 
                                                                                    response_format=None, 
                                                                                    )
        guideline = guideline_summaries.choices[0].message.content
        guideline_summaries_repo[Path(file_path).stem] = guideline
        print(f"Captured Guideline Summary for {Path(file_path).stem} in {execution_time} seconds")
    
    return guideline_summaries_repo

def save_markdown_summaries(summary_repo: Dict[str, str]) -> None:
    """
    Save the summarized markdown guidelines to specified file paths.
 
    This function iterates through the provided dictionary of summarized markdown guidelines, 
    creates the necessary directories if they do not exist, and writes the guidelines to 
    individual markdown files. The files are saved with a specific naming convention 
    based on the original guideline file names.
 
    Args:
        summary_repo (Dict[str, str]): A dictionary where the keys are the filenames of the guidelines
                                       and the values are the corresponding summarized markdown content.
    Returns:
        None: This function does not return any value. It saves the summarized markdown content
              to files in the specified directory.
    """
    guideline_prefix = "Content Voice_2021_"
    for file_name, markdown_guideline in summary_repo.items():
        md_path = Path(os.getcwd() + f"DVoiceDjangoAPI\\DVoice\\guidelines\\summary_guidelines\\")
        os.makedirs(md_path, exist_ok=True)
        with open(str(md_path) + f"\\DVoice_summary_guideline_{file_name.split(guideline_prefix)[1]}.md", "w", encoding="utf-8") as markdown_file:
            markdown_file.write(markdown_guideline)

            print(f"File DVoice_summary_guideline_{file_name.split(guideline_prefix)[1]} has been saved in {md_path}")
    

if __name__ == "__main__":
    
    client = instantiate_azure_openai_client()
    ## TODO: refactor to make sure the new guideline will be saved in blob
    conv_results, number_of_files = parse_files("DVoiceDjangoAPI\\DVoice\\guidelines\\guideline_files\\guidelines") 
    guideline_markdown_extract_repo = extract_markdown_from_parsed_output(conv_results, number_of_files)
    guideline_summaries_repo = create_guidelines(guideline_markdown_extract_repo)
    save_markdown_summaries(guideline_summaries_repo)