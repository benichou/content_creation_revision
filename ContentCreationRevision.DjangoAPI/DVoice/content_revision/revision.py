import time
import asyncio
from pathlib import Path
# from DVoice.utilities.settings import AZURE_OPENAI_MODEL_NAME
# from DVoice.utilities.llms_utils import generate_response_from_text_input
from DVoice.utilities.llm_and_embeddings_utils import instantiate_azure_chat_openai
from DVoice.utilities.llm_structured_output import LayoutParser
from DVoice.utilities.llm_structured_output import Guideline1Parser, Guideline2Parser, Guideline3Parser, Guideline4Parser
from DVoice.utilities.llm_structured_output import GuidelinesWithAdditionalUserInstructionsParser

from DVoice.prompt.prompt_repo import OUTPUT_AFTER_LAYOUT_REVISION_PROMPT
from DVoice.prompt.prompt_repo import GUIDELINE_LAYOUT_REVISION_PROMPT, GUIDELINE_WRITING_PRINCIPLES_PROMPT
from DVoice.prompt.prompt_repo import OUTPUT_AFTER_FIRST_REVISION_PROMPT, GUIDELINE_REFERRING_TO_Content_PROMPT
from DVoice.prompt.prompt_repo import OUTPUT_AFTER_SECOND_REVISION_PROMPT, GUIDELINE_REFERRING_TO_EFFECTIVE_WRITING_PROMPT
from DVoice.prompt.prompt_repo import OUTPUT_AFTER_THIRD_REVISION_PROMPT, OUTPUT_AFTER_FOURTH_REVISION_PROMPT
from DVoice.prompt.prompt_repo import OUTPUT_AFTER_FIFTH_REVISION_PROMPT
from DVoice.prompt.prompt_repo import  GUIDELINE_REFERRING_TO_EDITORIAL_STYLE_GUIDE_PROMPT
from DVoice.prompt.model_persona_repo import MODEL_PERSONA_LAYOUT_REVISION, MODEL_PERSONA_APPLICATION_OF_GUIDELINES
from DVoice.prompt.prompt_actions import compare_original_vs_revised_text
from functools import partial
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.schema.prompt_template import format_document
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
# from langchain.schema import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser

from typing import Dict, List, Any, Tuple, Callable, Optional

def define_revise_chunk_layout_chain(TOKEN):
    """
    Defines a LangChain processing chain to revise the layout of document chunks using an LLM.
 
    This function prepares a chain that takes in chunks of document content, applies a classification
    and revision prompt using an LLM, and returns structured output in a revised format. The process 
    involves:
        - Initializing the LLM with the provided authentication token.
        - Setting up a JSON parser to enforce structured output.
        - Formatting document content into LangChain's `PromptTemplate`.
        - Constructing a processing chain to classify and revise layout content.
        - Wrapping the output in a `Document` object to preserve metadata.
 
    Args:
        TOKEN (Azure Access Token): Authentication token for the Azure OpenAI model.
 
    Returns:
        map_revise_layout_chain: A LangChain `Runnable` object representing the async revision chain.
    Notes:
        - This function only defines the processing chain. The chain must be invoked separately.
        - The output will include the revised chunk (in the metadata) while retaining original metadata.
    """
    start_time = time.time()
    # prepare the model and parser
    model = instantiate_azure_chat_openai(TOKEN)
    parser = JsonOutputParser(pydantic_object=LayoutParser)
    # prepare the classifcation prompt with model classification persona and classifcation prompt
    revision_query = "\n\n" + MODEL_PERSONA_LAYOUT_REVISION + "\n\n" + GUIDELINE_LAYOUT_REVISION_PROMPT
    revision_prompt = PromptTemplate(template=f"{revision_query}")
    # prepare the prompt that will use the page content and assess it for classification into text or not 
    ## we really transfer the page content, here a chunk, into the Langchain Prompt Template so it is in the LLM context 
    document_content_transfer_prompt = PromptTemplate(template="- page_content: '{page_content}'") 
    transfer_docs_to_prompt = PromptTemplate.from_template("Given the following markdown text input :\n\n{context}, please")
    # we transfer the chunk//page content, only keep page content thanks to the langchain format_document method
    ## and then thanks to partial, we only keep the page content as a string that is later transfer to context
    ## in the {"context": partial_format_document} loc
    partial_format_document = partial(format_document, prompt=document_content_transfer_prompt) ## only take page_content
    ## output prompt
    ### we specifically tell what we expect as output to direct the llm to really output an output that fits with
    ### the intended output, as per expected by the json structured output parser
    ### Note: We could not emphasize this more, the output prompt has proved very useful to force the llm to 100%
    ### output the correct structured output format (format not actual value)
    output_query = "\n\n" + OUTPUT_AFTER_LAYOUT_REVISION_PROMPT
    output_prompt = PromptTemplate(template= f"{output_query}")
    ## Prepare the Langchain chain to ensure the proper context and structured output are put in place
    map_revise_layout_chain = (
        {"context": partial_format_document} # the actual chunk is put in there for classification
        | transfer_docs_to_prompt + revision_prompt + output_prompt # context and prompt prep
        | model ## llm
        | parser ## the parser for structured output: note it is not mandatory and does not always have to be a json parser
                ) 
    # A wrapper chain to keep the original Document metadata
    ## The Runnable Paralle and Runnable Passthrough ensure the parallel processing
    map_revise_layout_as_doc_chain = (RunnableParallel({"doc": RunnablePassthrough(), "content": map_revise_layout_chain}) 
                                 ## Run the guideline revision in parallel here with the map_revise_layout_chain
                                # | (lambda x: x["content"]) # please keep this very specific line (on the left), it can be useful for you to understand the actual output from the chain #  for debugging only 
                                  |(lambda x: Document(page_content=str(x["doc"].page_content), 
                                            metadata={"source": x["doc"].metadata["source"],
                                                      "chunk_id": x["doc"].metadata["chunk_id"],
                                                      "revised_chunk":x["content"]})) 
                        # previousline: save for each Langchain Document, from the x output generated by lambda 
                        # a new langchain document that has the original chunk in page content (non revised)
                        # and in metadata:
                        # the source (filename), 
                        # chunk id (to keep track of the particular order, just in case)
                        # and the revised chunk (it really just the chunk//page_content with the llm having applied the revisions)

    ).with_config(run_name="Revise Chunk Layout (return doc)") # you can give it any run name but keep it cohesive with the chain
    # The final full classification chain
    map_revise_layout_chain = (map_revise_layout_as_doc_chain.map()).with_config(run_name="Revision of chunks layout async")
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Initialization of the revise chunk layout chain took {processing_time} second(s)")
    
    ## please note we just defined the chain for now, nothing has been run, we need to `invoke` (how we activate the llm) 
    # it to run the revision
    return map_revise_layout_chain 

def process_chunks_for_layout_revision(file_chunks_doc: Dict[str, List[str]]) -> Dict[str, List[Document]]:
    """
    Processes document (string) chunks for layout revision by converting them into LangChain `Document` objects.
    This function takes a dictionary of file paths mapped to lists of text chunks, structures them 
    into `Document` objects with metadata, and returns a dictionary mapping each file path to its 
    corresponding list of `Document` objects.
    
    Args:
        file_chunks_doc (Dict[str, List[str]]): A dictionary where keys are file paths (str) and 
        values are lists of document text chunks (List[str]).
 
    Returns:
        doc_repos (Dict[str, List[Document]]): A dictionary mapping file paths to lists of LangChain `Document` objects,
                                   where each `Document` includes:
                                   - `page_content`: The text content of the chunk (the actual string content).
                                   - `metadata["source"]`: The original file path.
                                   - `metadata["chunk_id"]`: The chunk's index in the document (to keep track of 'chronological order' in the document).
                                   - `metadata["revised_chunk"]`: Initially an empty string that eventually stores the revised string chunk: THIS IS REALLY WHERE WE
                                   STORE THE ACTUAL REVISION OUTPUT WORK!!
 
    Notes:
        - This function only structures the data for later processing; it does not modify or revise the chunks.
        - The metadata field `revised_chunk` is initialized as an empty string for later updates in the next revision method
    """
    ## TODO LOW PRIORITY: TO BE REFACTORED WITH THE PROCESS_CHUNKS_FOR_LAYOUT_REVISION METHOD
    start_time = time.time()
    
    doc_repos = {}
    # Iterate through each file and its list of text chunks
    for file_path, list_of_chunks in file_chunks_doc.items():
        docs = []
        for chk_idx, chk in enumerate(list_of_chunks):
            docs.append(
                Document(
                page_content=chk,
                metadata={"source": file_path, # Store original file path
                          "chunk_id": chk_idx, # Track chunk index
                          "revised_chunk" : ""}, # Placeholder for future revisions
            ))
        doc_repos[file_path] = docs # Store processed documents under their respective file paths
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Processing of the document chunks took {processing_time} second(s)")
    
    return doc_repos

async def apply_chunk_layout_revision(file_chunks_repo: Dict[str, List[str]], TOKEN) -> List[Any]:
    """
    Asynchronously applies chunk layout revision to a repository of document chunks.
    What we really do is that we focus on revising the layout into something "that make sense" and in markdown compliant
    format
 
    This function processes document chunks into `Document` objects, initializes a revision chain, 
    and applies the revision chain asynchronously to each document.
 
    Args:
        file_chunks_repo (Dict[str, List[str]]): A dictionary where keys are file paths (str) and 
                                                 values are lists of text chunks (List[str]) 
                                                 representing document content.
        TOKEN (Azure Access Token): Authentication token or configuration object used to access the language model.
 
    Returns:
        responses (List[Langchain Documents]): A list of Langchain Document responses from the layout revision process, containing the revised 
                   document chunks for each processed file with the original chunk and associated metadata
        [Document(page_content= "The Canadian Economy Trends ...", metadata={source="Canadian Economy Trends.docx", 
                                                                        chunk_id="1",
                                                                        revised_chunk="## The Most Important Canadian 
                                                                                        Economic Trends ..."}), 
        Document(page_content= " The USA Impact on  ...", metadata={source="Canadian Economy Trends.docx", 
                                                                        chunk_id="2",
                                                                        revised_chunk="### Evaluation of the 
                                                                         the USA Impact on ..."}),
        ...,
        Document(page_content= " Print this Document with Recycled Paper", metadata={source="VERY_LARGE_IFRS_FILE.pdf", 
                                                                        chunk_id="55",
                                                                        revised_chunk="Print this Document with Recycled Paper"}),
        ....]
 
    Notes:
        - Uses asyncio for concurrent execution to improve performance.
        - The function first structures the input data into LangChain `Document` objects.
        - Processing is parallelized using `asyncio.gather()` with `loop.run_in_executor()`.
        - The number of processed files is used to calculate per-file processing time.
    """
    start_time = time.time()
    # Convert file chunks into LangChain `Document` objects
    doc_repos = process_chunks_for_layout_revision(file_chunks_repo)
    number_files = len(list(doc_repos.keys()))
    # Define the layout revision chain
    map_revise_layout_chain = define_revise_chunk_layout_chain(TOKEN)
    # Create an event loop and prepare tasks for asynchronous execution
    loop = asyncio.get_event_loop()
    tasks = []
    for file_path, docs in doc_repos.items():
        print(f"##File: {Path(file_path).stem} LAYOUT REVISION ASYNC ##")
        tasks.append(loop.run_in_executor(None, apply_lcel_chain_to_single_doc, file_path, 
                                                                                map_revise_layout_chain,
                                                                                docs
                                                                                ))
    # Run all tasks concurrently and collect responses
    responses = await asyncio.gather(*tasks)
    
    ## for debugging
    # file_chunks_revised_layout_repo = {}
    # for file_path, docs in tqdm(doc_repos.items()):
        
    #     response =  map_revise_layout_chain.invoke(
    #         docs,
    #         config={"max_concurrency": 5}
    #     )
    #     file_chunks_revised_layout_repo[file_path] = response
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Revision of the layout of the chunks has taken {processing_time} \
            second(s) or {processing_time/number_files} second(s) per files")
    
    return responses

def reconstruct_revised_layout_chunk_into_file(chunk_revised_layout_output_raw: List[Tuple[str, List[Any]]]) -> Dict[str, str]:
    """
    Reconstructs revised document chunks into full files while maintaining their original order.
 
    This function takes a list of tuples containing file paths and lists of revised document chunks.
    It orders the chunks based on their original position (chunk ID) and reconstructs the full document 
    by concatenating the revised content.
 
    Args:
        chunk_revised_layout_output_raw (List[Tuple[str, List[Any]]]): 
            A list of tuples where:
            - The first element (str) is the file path.
            - The second element (List[Any]) is a list of langchain documents that store the original and 
                revised chunks with the associated metadata.
 
    Returns:
        reconstructed_revised_file_repo (Dict[str, str]): A dictionary where keys are file paths (str) and values are reconstructed 
                        document content (str) with revised layout.
 
    Notes:
        - Chunks are sorted in ascending order using the `chunk_id` to preserve original document structure - used to be extra safe.
        - The reconstructed document replaces unwanted tokens such as "- page_content" and excessive new lines.
        - Processing time is logged for performance analysis.
    """
    start_time = time.time()
    reconstructed_revised_file_repo = {}
    for revised_chunks_output in chunk_revised_layout_output_raw:
        file_path = revised_chunks_output[0]
        list_of_revised_chunks = revised_chunks_output[1]
        ## order chunks with ascending order to ensure we re-build the chunks into the doc from begining to end...
        ## in its original order
        ordered_list_of_revised_chunks = sorted(list_of_revised_chunks, key=lambda doc: doc.metadata["chunk_id"])
         
        # Initialize reconstructed file content if not already present
        if file_path not in reconstructed_revised_file_repo:
            reconstructed_revised_file_repo[file_path] = ""
        # Concatenate revised chunks while cleaning unnecessary formatting
        for revised_chunk in ordered_list_of_revised_chunks:
            
            reconstructed_revised_file_repo[file_path] += '\n\n ' + revised_chunk.metadata["revised_chunk"]["text_with_revised_layout"].\
                                                                        replace("- page_content", "").replace("```", "").replace("\n\n\n\n", "\n\n")
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Reconstruction of the file from the chunks with revised layout took {processing_time} second(s)")
    
    return reconstructed_revised_file_repo

def initialize_revision_parsers() -> List[JsonOutputParser]:
    """
    Initializes and returns a list of JSON output parsers for different guideline revisions, for the purpose of strucured
    output that can more easily pass the revisions sequentially )sequential chains in the parallel runnable (async process).
    Structured output is indeed very important to support sequential chaining in the parallel/async process, otherwise
    we cannot pass easily different output in a sequential (where n depends on n-1) manner.
 
    This function creates five instances of `JsonOutputParser`, each associated with a specific 
    guideline parser class. These parsers are used to process structured guideline revisions.
 
    Returns:
        List[JsonOutputParser]: A list containing initialized (json) parser instances for various guideline formats.
        Returns [Json Structured Output Parser Class 1, ..., Json Structured Output Parser Class 5]
    Notes:
        - The function tracks and logs the initialization time for performance monitoring.
        - Each parser is instantiated with a corresponding Pydantic object for structured parsing.
    """
    start_time = time.time()
    # Initialize parsers for different guideline types
    parser_1 = JsonOutputParser(pydantic_object=Guideline1Parser) ## for guideline 1
    parser_2 = JsonOutputParser(pydantic_object=Guideline2Parser) ## for guideline 2
    parser_3 = JsonOutputParser(pydantic_object=Guideline3Parser) ## for guideline 3
    parser_4 = JsonOutputParser(pydantic_object=Guideline4Parser) ## for guideline 4
    parser_5 = JsonOutputParser(pydantic_object=GuidelinesWithAdditionalUserInstructionsParser) ## Optional Guidelines (when user adds additional instructions for revision in the UX)
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Initialization of the parsers took {processing_time} second(s)")
    
    return [parser_1, parser_2, parser_3, parser_4, parser_5] ## list of parsers

def generate_revision_prompts(additional_instructions: str) -> List[PromptTemplate]:
    """
    Generates a list of revision prompts based on predefined guidelines and additional user instructions.
 
    This function constructs multiple revision prompts using predefined guideline templates 
    and an optional user-provided instruction set. The prompts are formatted as Langchain `PromptTemplate` 
    instances to be used in language model processing.
 
    Args:
        additional_instructions (str): Custom style guideline instructions provided by the user, but note they can also be empty!
 
    Returns:
        List[PromptTemplate]: A list of five Langchain `PromptTemplate` objects that can be used to apply revisions by the LLMs
                            , each corresponding to 
                              a different and static guideline for text revision. 
                            
                            Some Context:
                              Note we were provided 4 guidelines for the revision guideline stored here:
                             - Content.Ca.DBotBeta.DjangoAPI\DVoice\guidelines\guideline_files\guidelines
                             That is why we have 4 baseline parsers. 

                             Also Note the above static guidelines have been provided
                              by Content Marketing and these guidelines are handled here:
                              Content.Ca.DBotBeta.DjangoAPI\DVoice\guidelines\creating_actionable_guideline_summary_for_prompt\guideline_prompt_creation.py
                              and stored there: 
                              - Content.Ca.DBotBeta.DjangoAPI\DVoice\guidelines\summary_guidelines
 
    Notes:
        - The function tracks and logs the time taken to generate the prompts.
        - The fifth prompt incorporates additional user-defined instructions for custom revisions.
    """
    ## REVISION PROMPTS
    ## prepare the application of guideline prompts with model revision persona and the different guideline prompts
    # first guideline
    
    start_time = time.time()

    first_revision_query = "\n\n" + MODEL_PERSONA_APPLICATION_OF_GUIDELINES + "\n\n" + GUIDELINE_WRITING_PRINCIPLES_PROMPT
    first_revision_prompt = PromptTemplate(template=f"{first_revision_query}")
    # second guideline
    second_revision_query = "\n\n" + MODEL_PERSONA_APPLICATION_OF_GUIDELINES + "\n\n" + GUIDELINE_REFERRING_TO_Content_PROMPT
    second_revision_prompt = PromptTemplate(template=f"{second_revision_query}")
    # third guideline 
    third_revision_query = "\n\n" + MODEL_PERSONA_APPLICATION_OF_GUIDELINES + "\n\n" + GUIDELINE_REFERRING_TO_EFFECTIVE_WRITING_PROMPT
    third_revision_prompt = PromptTemplate(template=f"{third_revision_query}")
    # fourth guideline
    fourth_revision_query = "\n\n" + MODEL_PERSONA_APPLICATION_OF_GUIDELINES + "\n\n" + GUIDELINE_REFERRING_TO_EDITORIAL_STYLE_GUIDE_PROMPT
    fourth_revision_prompt = PromptTemplate(template=f"{fourth_revision_query}")
    # optional additional instructions guideline given by the user
    fifth_revision_query = "\n\n" + MODEL_PERSONA_APPLICATION_OF_GUIDELINES + "\n\n" + "AND"+\
                                                                            " as a final guide style revision"+\
                                                                            " please apply the following style"+\
                                                                            " guideline to the markdown input text:"+\
                                                                            f" - instructions: '{additional_instructions}"
                                                                             
    fifth_revision_prompt = PromptTemplate(template=f"{fifth_revision_query}")
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Generation of the (style guide) revision prompts took {processing_time} second(s)")
        
    return [first_revision_prompt, second_revision_prompt, third_revision_prompt, \
            fourth_revision_prompt, fifth_revision_prompt]

def generate_transfer_docs_to_llm_prompt() -> Tuple[partial, List[PromptTemplate]]:
    """
    Generates a set of structured prompts for transferring document content and revisions throughout
    the different stages of revisions.
 
    This function creates multiple `PromptTemplate` instances designed to structure and 
    format document content for an LLM. These prompts guide the LLM in processing original 
    and revised document content across multiple revision steps.
 
    Returns:
        Tuple[partial, List[PromptTemplate]]: 
            - A `partial` function for document formatting.
            - A list of `PromptTemplate` objects used for structuring document content transfer.
 
    Notes:
        - The function tracks and logs the time taken to generate the prompts.
        - The first prompt template structures page content for clarity.
        - The subsequent prompts progressively apply revisions in multiple steps.
    """
    ## UPLOAD DOCUMENT CONTENT TO LLM PROMPTS
    ## The prompt to "upload" the original LLM calls and subsequent LLM calls content, especially the page content
    # and metadata into a structured way for the LLM to easily understand how to proceed
    # prepare the prompt that will use the page content and apply the revision on it
    
    start_time = time.time()
    # Template for transferring document content to LLM
    first_document_content_transfer_prompt = PromptTemplate(template="- page_content:'{page_content}'") 
    # Initial document transfer prompt
    first_transfer_docs_to_prompt = PromptTemplate.from_template("Given the following markdown text input :\n\n{context} , please")
    # Partial function for formatting document content
    partial_format_document = partial(format_document, prompt=first_document_content_transfer_prompt)
    # Prompt templates for progressive revision steps
    second_transfer_docs_to_prompt = PromptTemplate.from_template("Given the following output : \
                                                                  - original_text: '{original_text}', \
                                                                  - revised_text_step_1: '{revised_text_step_1}', \
                                                                  please") # transferring documents from revision 1 to revision 2
    third_transfer_docs_to_prompt = PromptTemplate.from_template("""Given the following output : \
                                                                  - original text: '{original_text}', \
                                                                  - revised text step 2: '{revised_text_step_2}',\
                                                                  please""") # transferring documents from revision 2 to revision 3
    fourth_transfer_docs_to_prompt = PromptTemplate.from_template("""Given the following output : \
                                                                  - original text: '{original_text}', \
                                                                  - revised text step 3: '{revised_text_step_3}',\
                                                                   please""") # transferring documents from revision 3 to revision 4
    fifth_transfer_docs_to_prompt = PromptTemplate.from_template("""Given the following output : \
                                                                  - original text: '{original_text}', \
                                                                  - revised text step 4: '{revised_text_step_4}',\
                                                                  please""") # transferring documents from revision 4 to revision 5
    
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Generation of the transfer docs to llm prompt took {processing_time} second(s)")
    
    return partial_format_document, [first_transfer_docs_to_prompt, second_transfer_docs_to_prompt, \
                                    third_transfer_docs_to_prompt, fourth_transfer_docs_to_prompt, \
                                    fifth_transfer_docs_to_prompt]

def generate_output_prompts() -> List[PromptTemplate]:
    """
    Generates structured output prompts to ensure alignment with the output parser.
 
    This function creates multiple `PromptTemplate` instances to standardize and align
    the LLM's output with what the output parser expects to parse. Each prompt corresponds 
    to a specific revision step.

    Args:
        None
 
    Returns:
        List of Parsers (List[PromptTemplate]): A list of structured prompts for LLM output alignment.
 
    Notes:
        - The function tracks and logs the time taken to generate the prompts.
        - The fifth output prompt is specifically designed to apply additional 
          user-provided instructions.
    """
    ## OUTPUT PROMPTS TO ALIGN WITH THE OUTPUT PARSER
    # The goal of these prompts is to ensure the output from the LLM is aligned with what the output parser expects to parse
    # first output prompt
    start_time = time.time()
    
    first_output_query = "\n\n" + OUTPUT_AFTER_FIRST_REVISION_PROMPT
    first_output_prompt = PromptTemplate(template= f"{first_output_query}")
    # second output prompt
    second_output_query = "\n\n" + OUTPUT_AFTER_SECOND_REVISION_PROMPT
    second_output_prompt = PromptTemplate(template= f"{second_output_query}")
    # third output prompt
    third_output_query = "\n\n" + OUTPUT_AFTER_THIRD_REVISION_PROMPT
    third_output_prompt = PromptTemplate(template= f"{third_output_query}")
    # fourth output prompt
    fourth_output_query = "\n\n" + OUTPUT_AFTER_FOURTH_REVISION_PROMPT
    fourth_output_prompt = PromptTemplate(template= f"{fourth_output_query}")
    # fifth output prompt
    fifth_output_query = "\n\n" + OUTPUT_AFTER_FIFTH_REVISION_PROMPT ## TO APPLY THE ADDITIONAL INSTRUCTIONS FROM THE USER
    fifth_output_prompt = PromptTemplate(template= f"{fifth_output_query}")
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"The generation of the output prompts took {processing_time} second(s)")
    
    return [first_output_prompt, second_output_prompt, third_output_prompt, fourth_output_prompt, fifth_output_prompt]


def define_chain(
    model, ## the actual llms used to apply the re revisions on the chunks
    parsers_list: List[Any],  # List of JSON parsers
    partial_format_document: Any,  # Partial function for document formatting
    transfer_docs_to_prompts_list: List[PromptTemplate],  # Prompts for transferring document content throughout the revision stages
    revision_prompts_list: List[PromptTemplate],  # Prompts for applying revision guidelines
    output_prompts_list: List[PromptTemplate],  # Prompts to support structured output
    additional_instructions: str,  # Additional user-provided instructions for revision
    style_modification: Dict[str, bool],  # Dictionary containing style modification flags: True or False is the user requesting style modification changes
):
    """
    Defines a sequential LLM-based rephrasing and revision chain.
 
    This function constructs a chain of transformations using a large language model (LLM) to apply 
    multiple revision guidelines sequentially. It processes a given document through several stages, 
    each guided by structured prompts, and parses the results at each step.
 
    Args:
        model (An LLM Operator Object): The language model to be used for processing.
        parsers_list (List[Any]): A list of JSON parsers for structured output extraction.
        partial_format_document (Any): A preformatted function to extract and structure document content.
        transfer_docs_to_prompts_list (List[PromptTemplate]): Prompts to facilitate document content transfer.
        revision_prompts_list (List[PromptTemplate]): Prompts defining revision guidelines.
        output_prompts_list (List[PromptTemplate]): Prompts ensuring structured output.
        additional_instructions (str): User-provided instructions for additional style modifications.
        style_modification (Dict[str, bool]): A dictionary indicating True or False whether style modifications should be applied.
 
    Returns:
        sequential_rephraser_chain (A Sequential Chain) : A sequential chain that applies multiple revision steps to a given document.
    Notes:
        - If `style_modification["style_modification"]` is `True` and `additional_instructions` are provided,
          an additional revision step is applied using the user's instructions.
        - Each step follows a structured approach:
            1. Transfer document content
            2. Apply revision guidelines
            3. Generate structured output using JSON parsing
            4. And do it again until you reach the last revision step
    """
    # Unpacking parsers
    parser_1, parser_2, parser_3, parser_4, parser_5 = parsers_list[0], parsers_list[1], \
                                                       parsers_list[2], parsers_list[3], parsers_list[4]
    # Unpacking transfer document prompts
    first_transfer_docs_to_prompt, second_transfer_docs_to_prompt, third_transfer_docs_to_prompt, \
                                   fourth_transfer_docs_to_prompt, \
                                   fifth_transfer_docs_to_prompt = transfer_docs_to_prompts_list[0], \
                                                                   transfer_docs_to_prompts_list[1], \
                                                                   transfer_docs_to_prompts_list[2], \
                                                                   transfer_docs_to_prompts_list[3], \
                                                                   transfer_docs_to_prompts_list[4] \
    # Unpacking revision prompts
    first_revision_prompt, second_revision_prompt, third_revision_prompt, \
                                 fourth_revision_prompt, fifth_revision_prompt = revision_prompts_list[0], revision_prompts_list[1], \
                                 revision_prompts_list[2], revision_prompts_list[3], revision_prompts_list[4]
    # Unpacking output prompts
    first_output_prompt, second_output_prompt, third_output_prompt, \
        fourth_output_prompt, fifth_output_prompt = output_prompts_list[0], output_prompts_list[1], \
        output_prompts_list[2], output_prompts_list[3], output_prompts_list[4]
    # Define the LLM processing chain
    if bool(additional_instructions) and style_modification["style_modification"]:             
        sequential_rephraser_chain = (
                                    # first chain
                                    {"context": partial_format_document} # capture the page_content and metadata from the Langchain Document
                                    | first_transfer_docs_to_prompt + first_revision_prompt + first_output_prompt ## necessary prompts to: 
                                    #                                                                              1."upload" the docs into LLM memory 
                                    #                                                                              2. detail the revision guidelines 
                                    #                                                                              3. detail the desired output for parsing
                                    | model ## llm applying revision guideline 1
                                    | parser_1 # json parsing
                                    # end of first chain
                                    | second_transfer_docs_to_prompt + second_revision_prompt + second_output_prompt ## dito above
                                    | model ## llm applying revision guideline 2
                                    | parser_2 ## json parsing
                                    # end of second chain
                                    | third_transfer_docs_to_prompt + third_revision_prompt + third_output_prompt ## dito above
                                    | model ## llm applying revision guideline 3
                                    | parser_3 ## json parsing
                                    # end of third chain
                                    | fourth_transfer_docs_to_prompt + fourth_revision_prompt + fourth_output_prompt ## dito above
                                    | model ## llm applying revision guideline 4
                                    | parser_4 ## json parsing
                                    # end of fourth chain
                                    | fifth_transfer_docs_to_prompt + fifth_revision_prompt + fifth_output_prompt ## dito above
                                    | model ## llm applying revision requested optionally by the user - additional instructions
                                    | parser_5 ## parse results
                                    # end of fifth chain
                                )
    else:
        sequential_rephraser_chain = (
                                    # first chain
                                    {"context": partial_format_document} # capture the page_content and metadata from the Langchain Document
                                    | first_transfer_docs_to_prompt + first_revision_prompt + first_output_prompt ## necessary prompts to: 
                                    #                                                                              1."upload" the docs into LLM memory 
                                    #                                                                              2. detail the revision guidelines 
                                    #                                                                              3. detail the desired output for parsing
                                    | model ## llm applying revision guideline 1
                                    | parser_1 # json parsing
                                    # end of first chain
                                    | second_transfer_docs_to_prompt + second_revision_prompt + second_output_prompt ## dito above
                                    | model ## llm applying revision guideline 2
                                    | parser_2 ## json parsing
                                    # end of second chain
                                    | third_transfer_docs_to_prompt + third_revision_prompt + third_output_prompt ## dito above
                                    | model ## llm applying revision guideline 3
                                    | parser_3 ## json parsing
                                    # end of third chain
                                    | fourth_transfer_docs_to_prompt + fourth_revision_prompt + fourth_output_prompt ## dito above
                                    | model ## llm applying revision guideline 4
                                    | parser_4 ## json parsing
                                    # end of fourth chain
                                )
        
    return sequential_rephraser_chain

def define_runnable_output(
    additional_instructions: str,
    style_modification: Dict[str, bool]
) -> Callable[[Dict[str, Any]], Document]:
    """
    Defines a function that processes document metadata and applies modifications 
    based on revision steps.
 
    This function returns a lambda function that processes a given document, 
    extracts metadata, and determines the revised document version based on 
    provided modification settings.
 
    Args:
        additional_instructions (str): Additional instructions submitted by the user through the UX. When not empty or None,
        they force the runnable to get the revision until revision step 5. Otherwise it stops at revision step 4.
        style_modification (Dict[str, bool]): A dictionary indicating whether style 
                                              modifications should be applied.
 
    Returns:
        runnable_output (Callable[[Dict[str, Any]], Document]): A lambda function that takes a dictionary 
                                              containing a document (`doc`) and content (`content`), 
                                              and returns a `Document` with updated metadata.
 
    Notes:
        - If `style_modification["style_modification"]` is `True` and `additional_instructions` is provided, 
          the revised document will be extracted from `revised_text_step_5`.
        - Otherwise, the revised document will be extracted from `revised_text_step_4`.
        - If no revised text is found, the original document content is used.
    """
    if bool(additional_instructions) and style_modification["style_modification"]:
        runnable_output = (lambda x: Document(page_content=str(x["doc"].page_content), 
                                            metadata={"source": x["doc"].metadata["source"],
                                            "chunk_id": x["doc"].metadata["chunk_id"],
                                            "classification_type": x["doc"].metadata["classification_type"],
                                            "revised_document": x["content"].get("revised_text_step_5", "").strip()                        
                                            if x["content"].get("revised_text_step_5", "").strip() else str(x["doc"].page_content),
                                            "original_document": x["content"].get("original_text", "").strip()                       
                                            if x["content"].get("original_text", "").strip() else str(x["doc"].page_content)
                            }))
    else:
        runnable_output = (lambda x: Document(page_content=str(x["doc"].page_content), 
                                            metadata={"source": x["doc"].metadata["source"],
                                            "chunk_id": x["doc"].metadata["chunk_id"],
                                            "classification_type": x["doc"].metadata["classification_type"],
                                            "revised_document": x["content"].get("revised_text_step_4", "").strip()                       
                                            if x["content"].get("revised_text_step_4", "").strip() else str(x["doc"].page_content),
                                            "original_document": x["content"].get("original_text", "").strip()                        
                                            if x["content"].get("original_text", "").strip() else str(x["doc"].page_content)
                            }))
    
    return runnable_output
        
def define_parallelized_sequential_chain(
    additional_instructions: str,
    style_modification: Dict[str, bool],
    TOKEN
) -> Any:
    """
    Initializes and defines a parallelized sequential processing chain for revising 
    document chunks according to Content Guidelines.
 
    This function sets up a sequential rephraser chain (one revision stage after the other), applies revision guidelines, 
    and then runs the sequential chain processing in parallel for each chunk using Langchain's LCEL. 
    Example: We have 5 chunks from the document and no additional instructions: 
    That means:
    - 4 revision steps on 5 chunks
    In other words, in theory there should be 5 concurrent threads (since each chunk is processed in paralel - there
    is no dependency between chunks for this so we are fine) in which each LLM based revision step is conducted ONE AFTER THE OTHER, 
    where the output of revise step 1 goes into the input of revise step 2 etc until step 4.In total, we really have 20
    LLM based operations.
    If we had additional instructions from the user, we would then have 5 threads with 5 operations each or 25 LLM based operations
    
 
    Args:
        additional_instructions (str): Additional instructions influencing the 
                                       document revision process.
        style_modification (Dict[str, bool]): A dictionary indicating whether style 
                                              modifications should be applied.
        TOKEN (Azure Access token): API token required to instantiate the Azure Chat OpenAI model.
 
    Returns:
        map_parallelized_sequential_chain_doc_rephrasing (LangChain Chain): A parallelized runnable chain for document revision that processes 
             document chunks in parallel.
 
    Notes:
        - Uses a sequential chain (`sequential_rephraser_chain`) to apply revision 
          guidelines progressively.
        - The `RunnableParallel` wrapper retains original document metadata while 
          incorporating the revised content.
        - Parallelized processing is applied at the document chunk level to enhance efficiency since chunks can be 
        revised independently//separately from one another.
    """
    start_time = time.time()
    # Initialize the AI model using the provided TOKEN
    model = instantiate_azure_chat_openai(TOKEN)
    # Initialize revision parsers
    parsers_list = initialize_revision_parsers()
    # Generate revision prompts based on additional instructions
    revision_prompts_list = generate_revision_prompts(additional_instructions)
    # Generate document prompt transfer to LLM to process revision on the chunks sequentially
    partial_format_document, transfer_docs_to_prompts_list = generate_transfer_docs_to_llm_prompt()
    # Generate output prompts for parsing expected output
    output_prompts_list = generate_output_prompts()
    
    ## # Define sequential chain for applying Content guidelines thoroughly
    sequential_rephraser_chain = define_chain(model, 
                                              parsers_list,
                                              partial_format_document,
                                              transfer_docs_to_prompts_list, 
                                              revision_prompts_list, 
                                              output_prompts_list,
                                              additional_instructions, 
                                              style_modification)
    # Define a wrapper to retain original document metadata and structure
    runnable_output = define_runnable_output(additional_instructions, style_modification)
    # Create a parallelized chain that processes document chunks concurrently
    parallelized_sequential_rephraser_as_doc_chain = (RunnableParallel({"doc": RunnablePassthrough(), "content": sequential_rephraser_chain}) 
                                                     ## Run the classification in parallel here
                                                    # | (lambda x: x["content"]) # for debugging only
                                                      | runnable_output
                        # previousline: save for each Langchain Document a new langchain document that 
                        # has the application of guidelines and the explanation of the application of the guidelines and
                        # where in the document chunk were they applied
    ).with_config(run_name="Revise the Document (chunk) as per Content Guidelines (return doc)")
    # The finalized full revision chain
    # Map the parallelized processing across document chunks
    map_parallelized_sequential_chain_doc_rephrasing = (parallelized_sequential_rephraser_as_doc_chain.map()).\
                                                        with_config(run_name="Revision of chunks in parallel")
    

    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Initialization of the parallelized sequential chain using Langchain LCEL took {processing_time} second(s)")
    
    return map_parallelized_sequential_chain_doc_rephrasing

def process_classified_chunks_for_revision(file_chunks_doc: Dict[str, List[Document]]) -> Dict[str, List[Document]]:
    """
    Processes classified document chunks for revision by organizing them into a structured repository.
 
    Args:
        file_chunks_doc (Dict[str, List[Document]]): A dictionary mapping file paths to lists of classified 
                                                     Langchain Document that store the document chunks that require revision.
 
    Returns:
        doc_repos (Dict[str, List[Document]]): A dictionary where each file path maps to a list of processed `Document` 
                                   objects with updated metadata and most of all the revised chunks while keeping the 
                                   original chunk in the page_content attribute of the Langchain Document.
 
    Notes:
        - Each chunk is assigned a `chunk_id` for tracking.
        - The `classification_type` is preserved in metadata.
        - The function currently operates similarly to `process_chunks_for_layout_revision` in the DVoice.utilities.chunking module 
        and may be refactored and combined with that method in that other module
    """
    ## TODO: TO BE REFACTORED WITH THE PROCESS_CHUNKS_FOR_LAYOUT_REVISION METHOD
    
    start_time = time.time()
    
    doc_repos = {}
    for file_path, list_of_chunks in file_chunks_doc.items():
        docs = []
        for chk_idx, chk in enumerate(list_of_chunks):
            docs.append(
                Document(
                page_content=chk.page_content,
                metadata={"source": file_path, 
                          "chunk_id": chk_idx,
                          "classification_type": chk.metadata["classification_type"],
                          } ## final chunk that has been correctly applied all guidelines
            ))
        doc_repos[file_path] = docs # Store processed chunks under their respective file paths
        
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Processing of the document chunks took {processing_time} second(s)")
    
    return doc_repos

def apply_lcel_chain_to_single_doc(
    file_path: str, 
    parallelized_sequential_chain_doc_rephrasing: Any, ## the Langchain Parallelized Sequential chain 
    list_of_chunks_for_document: List[Any] ## List of Langchain Documents that really store each of the user uploaded file chunks 
) -> Tuple[str, Any]:
    """
    Applies the parallelized sequential LCEL chain to a single document.
 
    Args:
        file_path (str): The path of the document being processed.
        parallelized_sequential_chain_doc_rephrasing (Any): The LCEL-based parallelized sequential rephrasing chain.
        list_of_chunks_for_document (List[Any]): A list of document chunks to be processed.
 
    Returns:
        file_path, response (Tuple[str, Any]): A tuple containing the file path and the processed response.
 
    Notes:
        - The function attempts to invoke the processing chain up to three times in case of failure.
        - If all retries fail, an error message is printed, and the function exits without a valid response.
        - A 60-second delay is introduced between retries to handle rate// LLM TPM (Token per Minute) limits and
        other issues
    """
    ## TODO need to check for documents with empty chunks
    try:
        response = parallelized_sequential_chain_doc_rephrasing.invoke(list_of_chunks_for_document,
                                                                       config={"max_concurrency": 5})
    except Exception as e:
        print(f"Error {e} at initial run of sequential chain to apply guidelines for file: {file_path}")
        time.sleep(60)
        try:
            response = parallelized_sequential_chain_doc_rephrasing.invoke(list_of_chunks_for_document,
                                                                           config={"max_concurrency": 5})
        except Exception as e:
            print(f"Failure due to Exception {e} for file: {file_path}")
            time.sleep(60)
            try:
                response = parallelized_sequential_chain_doc_rephrasing.invoke(list_of_chunks_for_document,
                                                                           config={"max_concurrency": 5})
            except:
                print(f"Failure due to Exception {e} for file: {file_path}")
            
    return file_path, response

async def apply_guideline_revisions_to_docs(
    file_chunks_doc: Dict[str, List[Document]], ## dictionary of Langchain Document that store the chunks and the associate metadata
    additional_instructions: Dict[str, Any], # dictionary of the additional instructions to be applied in case the user submitted additional instructions through the UX
    style_modification: Dict[str, bool], ## {'style_modification': True} or {'style_modification': False} --> indicates whether the user requested as intent an additional style modification to the document
    TOKEN # Azure Access Token
) -> List[Document]:
    """
    Asynchronously applies guideline revisions to the document chunks.
 
    This function processes the document chunks in parallel by applying 
    a sequential chain of guidelines and returns the processed results.
 
    Args:
        file_chunks_doc (Dict[str, List[Document]]): A dictionary where the keys are file paths (str),
                                                 and the values are lists of Langchain Documents that store the 
                                                 chunks to be processed//revised.
        additional_instructions (Dict[str, Any]): Additional instructions that may modify the guideline revisions.
        style_modification (Dict[str, bool]): A dictionary indicating whether style modifications should be applied.
        TOKEN (str): The token used for authentication or model access.
 
    Returns:
        responses (List[Document]): A list of responses from processing each document chunk. Each response corresponds 
                   to a Langchain Document that has the final revised document chunk (it is stored inside the Langchain 
                   Document that is part of each file).
    Notes:
        - The function revises document chunks asynchronously, improving efficiency for handling multiple files.
        - Debugging code is included (commented out) for further inspection if needed.
    """
    start_time = time.time()
    # Process the classified document chunks for revision
    doc_repos = process_classified_chunks_for_revision(file_chunks_doc)
    number_files = len(list(doc_repos.keys()))
    # Define the sequential chain for guideline revisions
    parallelized_sequential_chain_doc_rephrasing = define_parallelized_sequential_chain(additional_instructions, 
                                                                                        style_modification,
                                                                                        TOKEN)
    # file_chunks_revised_layout_repo = {}
    # Initialize asyncio event loop for parallel processing
    loop = asyncio.get_event_loop()
    # Create tasks for applying the sequential chain to each document chunk in parallel
    tasks = []
    for file_path, docs in doc_repos.items():
        print(f"##File: {Path(file_path).stem} SEQUENTIAL CHAIN OF GUIDELINES APPLIED ON EACH CHUNK IN PARALLEL AND EACH FILE IS PROCESSED ASYNC ##")
        tasks.append(loop.run_in_executor(None, apply_lcel_chain_to_single_doc, file_path, 
                                                                               parallelized_sequential_chain_doc_rephrasing,
                                                                               docs
                                                                                ))
    responses = await asyncio.gather(*tasks) # Wait for all tasks to complete
    ## below for debugging ###############
    # file_chunks_revised_layout_repo = {}
    # for file_path, docs in doc_repos.items():
    #     response =  parallelized_sequential_chain_doc_rephrasing.invoke(
    #         docs,
    #         config={"max_concurrency": 5}
    #     )
    #     file_chunks_revised_layout_repo[file_path] = response
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Application of the guidelines on the Chunks of the document(s) submitted took {processing_time} \
            second(s) or {processing_time/number_files} second(s) per single file")

    return responses


def reconstruct_revised_chunks_into_file(revised_chunks_list: List[List[Document]]) -> Dict[str, str]:
    """
    Reconstructs a revised file from a list of revised chunks (list of Langchain Documents storing these chunks
    ) by ordering the chunks and combining
    the content based on metadata. Each list of Langchain Documents correspond to one unique file
 
    This function takes the list of revised chunks (from the Langchain Document that store these chunks), 
    orders them based on their chunk ID, and reconstructs
    the document by appending the revised or original content, depending on the classification type. If the chunk
    is text based, then we take the revised chunk of it because revisions are applied on text chunks. If the chunk is 
    not text based, then it probably is a table and we keep the original table chunk to be included in the reconstructed 
    file.
 
    Args:
        revised_chunks_list (List[List[Document]]): A list of lists where each sublist contains two elements:
                                                1. The file path (str)
                                                2. A list of revised chunks (Langchain Document objects) 
                                                that need to be reconstructed into 1 unique file
 
    Returns:
        reconstructed_revised_file_repo (Dict[str, str]): A dictionary where the keys are file paths (str), and the values are the reconstructed
                        contents of the file after having applied ealier in a different method the necessary revisions 
                        to its chunks.
            {"file.pdf": "This is the ... reconstructed file", "file.docx": "This is the ... reconstructed file"}
 
    Notes:
        - The chunks are ordered based on their "chunk_id" to ensure they are reconstructed in the correct order.
        - The function distinguishes between "textual" and non-textual classification types for determining
          whether to append the revised text or original document content (usually just tables).
    """
    ## TO REFACTOR AND MERGE WITH THE OTHER APPLICABLE METHOD ABOVE
    start_time = time.time()
    # Dictionary to store the reconstructed content for each file path
    reconstructed_revised_file_repo = {}
    # Iterate through each item in the list of revised chunks
    for revised_chunks_output in revised_chunks_list:
        file_path = revised_chunks_output[0] # File path
        list_of_revised_chunks = revised_chunks_output[1] # List of revised chunks
        ## order chunks with ascending order to ensure we re-build the chunks into the doc from begining to end...
        ## in its original order
        ordered_list_of_revised_chunks = sorted(list_of_revised_chunks, key=lambda doc: doc.metadata["chunk_id"])
         
        if file_path not in reconstructed_revised_file_repo:
            reconstructed_revised_file_repo[file_path] = ""
        # Append the content of each chunk to the file's reconstructed content
        for revised_chunk in ordered_list_of_revised_chunks:
            if revised_chunk.metadata["classification_type"]["textual"]:
                reconstructed_revised_file_repo[file_path] += '\n\n' +  revised_chunk.metadata["revised_document"] \
                                                            if revised_chunk.metadata["revised_document"] else ""
            elif revised_chunk.metadata["classification_type"]["textual"] == 'True':
                reconstructed_revised_file_repo[file_path] += '\n\n' +  revised_chunk.metadata["revised_document"] \
                                                                        if revised_chunk.metadata["revised_document"] else ""
            if (revised_chunk.metadata["classification_type"]["textual"] is False):
                reconstructed_revised_file_repo[file_path] += '\n\n' + revised_chunk.metadata["original_document"] \
                                                                       if revised_chunk.metadata["original_document"] else ""
            elif (revised_chunk.metadata["classification_type"]["textual"] == "False"):
                reconstructed_revised_file_repo[file_path] += '\n\n' + revised_chunk.metadata["original_document"] \
                                                                       if revised_chunk.metadata["original_document"] else ""
    
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Reconstruction of the file from the chunks with revised layout took {processing_time} second(s)")

    return reconstructed_revised_file_repo


def capture_revision_explanation_for_doc(revised_document_chunks: List[Tuple[str, List[Document]]], 
                                          TOKEN) -> Dict[str, str]:
    """
    Captures the explanation for the revisions made in the document chunks by comparing the original 
    and revised content for each chunk.
 
    This function processes a list of revised document chunks (stored in the Langchain Document objects), 
    where each chunk also contains the file path  (in the same LangChain Document object)
    and a list of document chunks. It compares the original and revised text for each chunk and generates 
    an explanation for the revision. If an error occurs during the comparison, a default error value is assigned to
    the revision explanation.
 
    Args:
        revised_document_chunks (List[Tuple[str, List[Document]]]): A list where each item is a tuple containing:
            - A file path (str) as the first element.
            - A list of LangChain Document objects, where each chunk contains metadata like 'original_document' and 'revised_document'.
        TOKEN (Azure Access Token): The authentication token used to interact with the external revision comparison system.
 
    Returns:
        captured_modification_explanation_repo (Dict[str, str]): A dictionary where the keys are file paths (str) and the values are the corresponding 
        revision explanations (str).
 
    Notes:
        - The function assumes that each revised document chunk has a 'metadata' attribute containing 'original_document' 
          and 'revised_document' fields, which are used for the revision comparison.
    """
    start_time = time.time()
    captured_modification_explanation_repo = {}
    for revised_chunks_output in revised_document_chunks:
        original_text = revised_chunks_output[1][0].metadata['original_document']
        revised_text = revised_chunks_output[1][0].metadata['revised_document']
        file_path = revised_chunks_output[0]
        try:
            ## get the comparison analysis between pre revision and post revision
            revision_explanation = compare_original_vs_revised_text(original_text, revised_text, TOKEN) 
        except Exception as e:
            print(f"Error is {e}")
            revision_explanation = "No revision explanation could be generated"
        captured_modification_explanation_repo[file_path] = revision_explanation
                        
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Gathering of the file modification explanations took {processing_time} second(s)")
    
    return captured_modification_explanation_repo

def generate_additional_content(additional_instructions: str, TOKEN) -> Optional[str]:
    """
    Generates additional content based on provided instructions using Azure OpenAI.
 
    This function sends the provided `additional_instructions` to a predefined model persona and
    retrieves the response to generate content accordingly. If an error occurs during the response 
    generation, the function retries once before returning an error message.
 
    Args:
        additional_instructions (str): The additional instructions that guide the content generation. 
        TOKEN (Azure Access Token): The authentication token for accessing the Azure OpenAI service.
 
    Returns:
        additional_content (Optional[str]): The generated content based on the instructions. Returns `None` if an error occurs
                       and no valid content can be generated.
 
    Notes:
        - The function replaces certain markdown formatting in the generated content.
        - It utilizes the `MODEL_PERSONA_ADDITIONAL_CONTENT_GENERATION` prompt and the 
          `ADDITIONAL_CONTENT_GENERATION_PROMPT` prompt for generating content.
    """
    from DVoice.prompt.model_persona_repo import MODEL_PERSONA_ADDITIONAL_CONTENT_GENERATION
    from DVoice.prompt.prompt_repo import ADDITIONAL_CONTENT_GENERATION_PROMPT
    from DVoice.utilities.settings import AZURE_OPENAI_MODEL_NAME
    from DVoice.utilities.llm_and_embeddings_utils import generate_response_from_text_input, instantiate_azure_openai_client
    
    client = instantiate_azure_openai_client(TOKEN)
    try:
        response = generate_response_from_text_input(MODEL_PERSONA_ADDITIONAL_CONTENT_GENERATION,
                                                     ADDITIONAL_CONTENT_GENERATION_PROMPT,
                                                     additional_instructions, 
                                                     client, 
                                                     AZURE_OPENAI_MODEL_NAME,
                                                     response_format=None)
        additional_content = response[0].choices[0].message.content
        additional_content = additional_content.replace("```markdown", "").replace("```", "").replace("```yaml", "")
    except Exception as e:
        print(f"Initial error {e}")
        try:
            response = generate_response_from_text_input(MODEL_PERSONA_ADDITIONAL_CONTENT_GENERATION,
                                                         ADDITIONAL_CONTENT_GENERATION_PROMPT,
                                                         additional_instructions, 
                                                         client, 
                                                         AZURE_OPENAI_MODEL_NAME,
                                                         response_format=None)
            additional_content = response[0].choices[0].message.content
            additional_content = additional_content.replace("```markdown", "").replace("```", "").replace("```yaml", "")
        except Exception as e:
            print(f"Complete failure parsing into markdown the manual input string with error {e}")
        
    print(f"Completed Additional Content created as per the additional instructions")
    
    return additional_content
    
    