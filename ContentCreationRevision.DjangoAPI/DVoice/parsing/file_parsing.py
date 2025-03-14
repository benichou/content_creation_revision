import os, sys
import time
from docling.datamodel.base_models import InputFormat
from docling.document_converter import (
     DocumentConverter,
     PdfFormatOption,
     WordFormatOption,
 )
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import DocumentStream

from utilities.blob_storage import get_blob_file
from DVoice.utilities.llm_and_embeddings_utils import save_tensor_from_blob_to_directory, remove_any_previous_tensors_from_app_directory
from DVoice.utilities.settings import IMAGE_RESOLUTION_SCALE, GENERATE_PAGE_IMAGES, GENERATE_PICTURE_IMAGES, DEBUG
from DVoice.utilities.settings import GENERATE_TABLE_IMAGES, PDF_DOCUMENT_HIGH_QUALITY_PARSING
from DVoice.utilities.settings import DOCLING_LLM_DICT, DOCLING_TRANSFORMER_MODEL_PATH_LOCAL, PDF_DOCLING_NUMBER_PAGES_LIMIT
from DVoice.utilities.settings import DOCLING_TRANSFORMER_MODEL_PATH_DOCKER, DOCKER_MODE, REFRESH_DOCLING_TENSORS

from typing import Any, Dict, List, Optional, Tuple
import logging

## LOGGING CAPABILITIES

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
# Attach handler to the logger
logger.addHandler(handler)


def parse_files(input_document: List[Dict[str, Any]], 
                token, 
                default_credential: Any, 
                file_extension: List[str]) -> Tuple[Any, int, List[Dict[str, Any]]]:
    """
    Parse and process files based on their extension and content.
 
    This function processes input documents, checks their file types, and processes them 
    accordingly. It handles `.txt` and `.pdf` files differently than docx (which is always handled by docling for now), 
    downloading tensors if necessary and performing Azure Document Intelligence analysis for large PDFs. 
    .txt files are directly ingested.
    The function returns the parsed results, the number of files processed, 
    and a list of unsupported documents.
    Unsupported documents (by Docling) are .txt and pdf files with number of pages > PDF_DOCLING_NUMBER_PAGES_LIMIT
    For now we only tested this solution with .txt, .pdf and .docx but it could support more like PPTX
 
    Args:
        input_document (List[Dict[str, Any]]): A list of documents to process, each containing metadata and content.
        Example: [{'name': "file.pdf", "byte_io':<ByteIO1xorfurhurrh>}]
        token (Azure Access Token coming from the API Call submitted by the user with the associated Default Credential generated in views.py): 
        The authentication token used to download tensors and interact with Azure services.
        default_credential (Any): Default credentials for Azure services used for Document Intelligence processing.
        file_extension (List[str]): A list of file extensions corresponding to the input documents.
        Example: [".txt", ".pdf", "docx"] ## Note the order of the file extensions follows the order of the file download which itself follows
        the order of file upload by the user through the UX
 
    Returns:
        Tuple[Any, int, List[Dict[str, Any]]]: A tuple containing:
            - The conversion object results from the document processing. Can be a conversion docling python <yield generator> object or None
            - The number of files processed. Has to be greater than 1
            - A python list of unsupported documents (empty if all documents were supported) if any unsupported documents. 
            Otherwise None: When not None:
            Example: {{'name': "file.pdf", "byte_io':<ByteIO1xorfurhurrh>}} (we just popped and transfered to unsupported documents)
 
    """

    number_of_files = len(input_document) # always 1 for now since we only have one byte io object which is not a list
    ## assess if in docker or not to set up the path to save the tensors
    if DOCKER_MODE:
        if DEBUG:
            logger.info(f"DOCKER MODE with path to llm safe tensors: {DOCLING_TRANSFORMER_MODEL_PATH_DOCKER}")
        DOCLING_TRANSFORMER_MODEL_PATH = DOCLING_TRANSFORMER_MODEL_PATH_DOCKER
    else:
        if DEBUG:
            logger.info(f"LOCAL MODE testing with path to llm safetensors: {DOCLING_TRANSFORMER_MODEL_PATH_LOCAL}")
        DOCLING_TRANSFORMER_MODEL_PATH = DOCLING_TRANSFORMER_MODEL_PATH_LOCAL  
    ## load tensor from blob storage
    if ".pdf" in file_extension:
        
        ## only check correct downloading each and every time in debug mode
        if REFRESH_DOCLING_TENSORS:
            remove_any_previous_tensors_from_app_directory() 
        # from safetensors.torch import load_file, save_file
        # import os
        for tensor_name, llm_directory_path in DOCLING_LLM_DICT.items():
            # Define input and output filenames
            output_tensor_path = DOCLING_TRANSFORMER_MODEL_PATH + llm_directory_path + tensor_name
            if not os.path.exists(output_tensor_path): # if no tensor exist
                llm_layout_tensor = get_blob_file(token, tensor_name, api_type = "deloitte_voice_docling_transformers")
                if DEBUG:
                    logger.info(f"✅DOWNLOADING TENSORS: Tensor {tensor_name} has been downloaded succesfully")
                save_tensor_from_blob_to_directory(llm_layout_tensor, output_tensor_path, tensor_name) # save tensor in directory
                if DEBUG:
                    logger.info(f"✅SAVING TENSORS IN APP DIRECTORY: Tensor {tensor_name} has been saved at {output_tensor_path}")
    
    unsupported_doc_repo = []
    file_idx_txt = [idx for idx, value in enumerate(file_extension) if value  == ".txt"] # identify the files with .txt ext if any
    ## IF .txt file it should be in unsupported documents
    if bool(file_idx_txt): # if any .txt files
        import io
        id_to_pop = [] # storage to pop the .txt files
         # capturing files that cannot be parsed by docling
        for id in file_idx_txt:
            unsupported_doc = input_document[id] # make a copy of the files
            id_to_pop.append(id) # append to the storage of files to pop from main storage
            
            with io.TextIOWrapper(unsupported_doc["byte_io"], encoding="utf-8") as text_file: ## load .txt file
                unsupported_doc["raw_content"] = text_file.read() # save txt content into unsupported document dict in raw_document object
            unsupported_doc_repo.append(unsupported_doc) ## remove non docling compliant document from the input_document (list)
        if id_to_pop:
            ## update file_extension to only include extension not in the id_to_pop, same for input document
            file_extension = [ext for id, ext in enumerate(file_extension) if id not in id_to_pop] # remove said .txt ext from list of extensions
            input_document = [doc for id, doc in enumerate(input_document) if id not in id_to_pop] # remove txt file from list of files
        
    file_idx_pdf = [idx for idx, value in enumerate(file_extension) if value  == ".pdf"]
    ## IF VERY large PDF file it should be in unsupported documents
    if bool(file_idx_pdf):
        import io
        import pypdfium2
        file_idx_pdf = [idx for idx, value in enumerate(file_extension) if value == ".pdf"]
        id_to_pop = []
        # capturing files that cannot be parsed by docling
        for id in file_idx_pdf:
            copy_pdf = io.BytesIO(input_document[id]["byte_io"].getvalue()) # take the copy of byte_io to not corrupt the original file for parsing
            
            pdf = pypdfium2.PdfDocument(copy_pdf)
            ## count number of pages
            if PDF_DOCLING_NUMBER_PAGES_LIMIT < len(pdf): ## if the pdf is too large we will not send it to processing by docling and process it with Azure Document intelligence
                from utilities.doc_process import analyze_pdf
                input_document[id]["raw_content"] = analyze_pdf(copy_pdf, default_credential) # azure document intelligence processing
                unsupported_doc_repo.append(input_document[id])
                id_to_pop.append(id)
        if id_to_pop:
            file_extension = [ext for id, ext in enumerate(file_extension) if id not in id_to_pop]## remove from the list of extension
            input_document = [doc for id, doc in enumerate(input_document) if id not in id_to_pop]## remove from list of files

    overall_start_time = time.time()
    # baseline docling parsing configuration
    pipeline_options = PdfPipelineOptions()
    pipeline_options.artifacts_path = DOCLING_TRANSFORMER_MODEL_PATH
    
    if PDF_DOCUMENT_HIGH_QUALITY_PARSING: ##please note that lower quality parsing for pdf may lead to having blank output
        print("PDF_PARSING PARAMETER: COMPLEX DOCUMENT")
        pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
        pipeline_options.generate_page_images = GENERATE_PAGE_IMAGES
        pipeline_options.generate_picture_images = GENERATE_PICTURE_IMAGES
        pipeline_options.generate_table_images = GENERATE_TABLE_IMAGES
        pdf_formatting = PdfFormatOption(pipeline_cls=StandardPdfPipeline, 
                                         backend=PyPdfiumDocumentBackend,
                                         pipeline_options=pipeline_options) # for more complex situations
        doc_converter = (
            DocumentConverter(  # all of the below is optional, has internal defaults.
                allowed_formats=[
                    InputFormat.PDF,
                    InputFormat.IMAGE,
                    InputFormat.DOCX,
                    InputFormat.HTML,
                    InputFormat.PPTX,
                    InputFormat.ASCIIDOC,
                    InputFormat.MD,
                ],  # whitelist formats, non-matching files are ignored.
                format_options={
                    InputFormat.PDF: pdf_formatting,
                    InputFormat.DOCX: WordFormatOption(
                        pipeline_cls=SimplePipeline  # , backend=MsWordDocumentBackend
                    ),
                },
            )
        ) # higher quality but faster parsing
    else:
        print("PDF_PARSING PARAMETER: LESS COMPLEX DOCUMENT")
        doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }) # lower quality but faster parsing
    if DEBUG:
        logger.info(f"✅ Initialize parameters for docling conversion")    
    
    # processing into a list of DocumentStream docling object to process the byteio output from blob
    if input_document:
        # list of accepted documents to be processed by main docling parser
        document_to_process_list = [DocumentStream(name=input_dict["name"],stream=input_dict["byte_io"]) \
                                                                                        for input_dict in input_document]
        conv_results = doc_converter.convert_all(document_to_process_list, raises_on_error=True) # docling conversion generator object
    else:
        conv_results = None
    if DEBUG:
        logger.info(f"✅ Docling object has conducted the parsing") 
    
    overall_end_time = time.time()
    overall_time = overall_end_time - overall_start_time
    print(f"Parsing initialization took {overall_time} second(s)")
    
    if unsupported_doc_repo: ## to support dvoice creation of ingestion of .txt files
        return conv_results, number_of_files, unsupported_doc_repo
    else: ## supports for dvoice revision, in the future: TODO: we could always just return the 3 variables for both revise and create
        return conv_results, number_of_files, None

def extract_markdown_from_parsed_output(
    conv_results: Optional[List[Any]], 
    number_of_files: int, 
    TOKEN, 
    unsupported_doc_repo: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, str]:
    """
    Extract Markdown content from the parsed output of documents.
 
    This function processes the conversion results and any unsupported documents that were 
    parsed manually. It extracts and formats the content of the documents into Markdown format 
    and stores it in a dictionary. If there are unsupported documents, it uses a separate 
    function to parse them manually and includes their extracted Markdown content in the output.
 
    Args:
        conv_results (Optional[List[Any]]): A list of parsed conversion results that contain the documents to be converted to Markdown. 
                                             If None, no conversion results are available for processing.
        number_of_files (int): The total number of files being processed.
        TOKEN (Azure Access Token): The authentication token used for interacting with the system (e.g., for parsing).
        unsupported_doc_repo (Optional[List[Dict[str, Any]]], optional): A list of unsupported documents that could not be parsed 
                                                                          by the main document processing pipeline. Defaults to None.
 
    Returns:
        Dict[str, str]: A dictionary where the keys are document names and the values are their corresponding Markdown content.
        Returns:
        {"Canadian Economic Trends.docx": "## Canadian Economic Trends ...", 
        "IFRS_VERY_VERY_LARGE_FILE.pdf": "## USA IFRS Guidelines .... Print with Recycle Paper ", 
        ...}
    """
    overall_start_time = time.time()
    markdown_extract_repo = {}
    
    if bool(unsupported_doc_repo): ## if there are some documents that could not be parsed by docling and were parsed manually
        from DVoice.parsing.manual_input_parsing import parse_manual_input
        for unsupported_doc in unsupported_doc_repo:
            markdown_formatted_doc = parse_manual_input(unsupported_doc["raw_content"], TOKEN) # parse the raw content manually
            ## put the parsed content (to markdown) in the markdown storage of parsed files
            markdown_extract_repo[unsupported_doc["name"]] = "".join(list(markdown_formatted_doc.values())) 
    
    print("Starting the extraction")
    if DEBUG:
        logger.info(f"✅ Starting extraction")
    # if docling object (used for parsing of documents) is not None
    if conv_results:
        try:
            for res in conv_results:
                markdown = res.document.export_to_markdown() # use the generator and export the existing parsed output to markdown
                markdown_extract_repo[str(f"{res.input.file}")] = markdown # ingest in the main markdown storage of parsed files
        except Exception as e: # try a second time in case there was a failure 
            print(f"Initial error with {e}")
            if DEBUG:
                logger.error(f"Error {e}")
            for res in conv_results:
                markdown = res.document.export_to_markdown()
                markdown_extract_repo[str(f"{res.input.file}")] = markdown
        if DEBUG:
            logger.info(f"✅ Markdown conversion step is passed")
    
    # logger.info(f"✅ That is what the markdown is like: {markdown}")
     
    overall_end_time = time.time()
    overall_time = overall_end_time - overall_start_time
    print(f"Overall Parsing and Markdown extraction took {overall_time} second(s) / Processing per File \
        {overall_time / number_of_files} second(s)")
    
    return markdown_extract_repo


## TODO: for next iteration load the checklist and assess whether the document chunk in particular should be applied guidelines
## TODO: For refactoring, please use a specialized SLM for the classification of the chunks into text vs not text
### TODO: Query rewriting??
## TODO: NEED TO Grade the document and if the chunk is all compliant then we should mark it as compliant and not go through the 
## application of the guidelines revision


