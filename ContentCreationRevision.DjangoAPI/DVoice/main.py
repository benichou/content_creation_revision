import os, sys
import time
import asyncio
from collections import defaultdict

from DVoice.utilities.chunking import chunk_classification, chunk_documents_cohesively, prepare_list_chunks_and_metadata
from DVoice.content_revision.revision import apply_chunk_layout_revision, reconstruct_revised_layout_chunk_into_file
from DVoice.content_revision.revision import apply_guideline_revisions_to_docs, reconstruct_revised_layout_chunk_into_file
from DVoice.content_revision.revision import reconstruct_revised_chunks_into_file, capture_revision_explanation_for_doc
from DVoice.content_creation.summarize import create_doc_summary
from DVoice.content_creation.create_content import conduct_retrieval_based_content_generation
from DVoice.conversion.file_conversion import convert_to_markdown_and_docx_document
from utilities.blob_storage import save_blob_file
from utilities.cosmos_process import update_file_thread_flag
from django.conf import settings
from DVoice.prompt.prompt_actions import determine_input_language, translate_query_to_desired_language
from DVoice.prompt.prompt_actions import rewrite_query, break_down_query_to_multiple_query_output, identify_number_output_files
from DVoice.prompt.prompt_actions import identify_bill_96_compliance, determine_query_task_type_pairs
from DVoice.prompt.prompt_actions import rewrite_query_core_action, determine_necessary_files, determine_file_output_user_friendly_name
from DVoice.prompt.prompt_actions import process_parameter_translation
from DVoice.utilities.settings import CONTEXT_WINDOW_LIMIT

import shutil
import logging

from typing import Dict, Any, Tuple, Optional, List

## LOGGING CAPABILITIES

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
# Attach handler to the logger
logger.addHandler(handler)




class DVoiceReviser():
    """
    A class to process Content Voice revisions by analyzing documents, applying formatting rules,
    and generating revised versions with explanations.
    """
    def __init__(self, post_request_data: Dict[str, Any]) -> None:
        """
        Initializes the DVoiceReviser class with user request data.
 
        Args:
            post_request_data (Dict[str, Any]): Dictionary containing user request data, including credentials,
                                                file details, instructions, and authentication token.
        """
        self.post_request_data = post_request_data
        self.default_credential = post_request_data["defaultCredential"]
        self.saved_revision_path_repo: Optional[Dict[str, Any]] = None
        self.captured_modification_explanation_repo: Optional[Dict[str, Any]] = None
        self.file_name: Optional[str] = None
        self.folder_name: Optional[str] = None
        self.container_name: Optional[str] = None
        
        # Log init message for azure log streams
        if settings.DEBUG:
            logger.info("✅ INIT: Initialization of the DVoice Reviser is complete")
        
    def remove_local_output_folder(self, folder_path: str) -> None:
        """
        Removes the specified local output folder if it exists.
 
        Args:
            folder_path (str): Path to the folder that needs to be removed.
        Returns:
            Nothing is returned, just output folder is removed
        """
        if os.path.exists(folder_path): 
            shutil.rmtree(folder_path) # Deletes the folder and its contents 
            print(f"Folder '{folder_path}' has been removed successfully.") 
        else: 
            print(f"Folder '{folder_path}' does not exist.") 
           
           
    def _conduct_Content_voice_revision_processing(
        self,
        markdown_extract_repo: Dict[str, str],
        additional_instructions: str,
        style_modification: Dict[str, bool]
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Conducts Content Voice revision processing, applying chunking, layout reconstruction,
        classification, and guideline-based revisions.
 
        Args:
            markdown_extract_repo (Dict[str, str]): Repository containing extracted markdown content.
            additional_instructions (str): Additional user-provided instructions for content modification.
            style_modification (Dict[str, bool]): Dictionary indicating style modification settings.
 
        Returns:
            reconstructed_revised_file_repo & captured_modification_explanation_repo:
            - Tuple[Dict[str, str], Dict[str, str]]: A tuple containing:
                - The revised document chunks with applied modifications.
                - The captured modification explanations for auditing.
        """
        # Initial chunking before layout reconstruction
        chuncked_documents_pre_layout = chunk_documents_cohesively(markdown_extract_repo)
        # Layout revision using LLM driven revision on layout (Langchain Expression Language: LCEL)
        chunk_revised_layout_output_raw = asyncio.run(apply_chunk_layout_revision(chuncked_documents_pre_layout, 
                                                                                  self.post_request_data["token"]))
        # Reconstruct document from revised chunks
        reconstructed_file_repo = reconstruct_revised_layout_chunk_into_file(chunk_revised_layout_output_raw) ## quick concatenation of the chunks
        # Second chunking after layout reconstruction
        chunked_documents_post_layout = chunk_documents_cohesively(reconstructed_file_repo) # second chunking after layout reconstruction
        # Classify chunks based on Content Voice guidelines
        file_chunks_classification_repo = chunk_classification(chunked_documents_post_layout, self.post_request_data["token"]) # classify whether the input is to be considered for DVoice
        ## TODO: for next iteration load the checklist and grade whether the documents already comply with the checklist
        # HEART OF THE REVISION PROCESS: Apply guideline-based revisions
        revised_document_chunks = asyncio.run(apply_guideline_revisions_to_docs(file_chunks_classification_repo, 
                                                                                additional_instructions, 
                                                                                style_modification,
                                                                                self.post_request_data["token"]))
        # Reconstruct final revised document
        reconstructed_revised_file_repo = reconstruct_revised_chunks_into_file(revised_document_chunks)
        # Capture modifications applied to the document
        captured_modification_explanation_repo = capture_revision_explanation_for_doc(revised_document_chunks, 
                                                                                      self.post_request_data["token"])
        
        return reconstructed_revised_file_repo, captured_modification_explanation_repo


    def run_DVoice_revision(self) -> None:
        """
        Runs the Content Voice revision workflow by processing uploaded files or manual input,
        applying necessary transformations, and storing revised documents.

        Updates thread flag to handle asyn threading.
 
        Raises:
            Exception: Propagates any error encountered during processing.
        """
        try:
            start_time = time.time()
            additional_instructions = self.post_request_data["additionalInstructions"]
            
            # Determine style modifications
            if bool(additional_instructions):
                from DVoice.prompt.prompt_actions import determine_additional_insturctions_intent, determine_clean_intent  
                prompt_categorization = determine_additional_insturctions_intent(additional_instructions, 
                                                                                 self.post_request_data["token"])
                style_modification = determine_clean_intent(prompt_categorization)
                
            else:
                style_modification = {"style_modification": False}
            print(style_modification)
            
            # File-based revision
            if "fileName" in self.post_request_data: ## when 'fileName' is present in the post call to the api, that means it is a file upload --> file revision
                from DVoice.parsing.file_parsing import parse_files, extract_markdown_from_parsed_output # only needed when file upload
            
                source_name = self.post_request_data["fileNameInput"][0]["name"] ## FOR THE MOMENT WE DEAL WITH JUST ONE FILE IN DVOICE REVISER ## TODO: will have to adjust when multiple files and just use the filename in post message
                input_document = self.post_request_data["fileNameInput"] # byte io with blob storage
                if settings.DEBUG:
                    logger.info("✅ WE ARE GOING TO ENTER THE METHOD TO PARSE THE FILE")
                ## parse files with Docling or Azure Document Intelligence
                conv_results, number_of_files, unsupported_doc_repo = parse_files(input_document=input_document, 
                                                            token=self.post_request_data["token"],
                                                            default_credential= self.default_credential,
                                                            file_extension=self.post_request_data["fileExtension"]) # with docling ## TODO: will have to adjust lofic in docling when multiple files
                ## extract the parsed files into a markdown format
                markdown_extract_repo = extract_markdown_from_parsed_output(conv_results, 
                                                                            number_of_files, 
                                                                            self.post_request_data["token"], 
                                                                            unsupported_doc_repo) # with docling
            # Manual input-based revision
            if "manualInput" in self.post_request_data: ## when 'manual_input' is present in the post call to the api, that means it is a manual input --> manual input revision
                from DVoice.parsing.manual_input_parsing import parse_manual_input ## only needed for manual input revision
                
                source_name = self.post_request_data["manualInputFile"]["name"]
                manual_input_string = self.post_request_data["manualInput"]
                ## note only one single file is always returned in these cases since the manual input only allows to submit one manual input in the UX
                ## Parse manual input from user
                markdown_extract_repo = parse_manual_input(manual_input_string, self.post_request_data["token"])
                number_of_files = 1 # TODO: hard coded value for now but in the future we could deal with more than 1 file
            
            # Perform the revision processing
            reconstructed_revised_file_repo, \
                captured_modification_explanation_repo = self._conduct_Content_voice_revision_processing(markdown_extract_repo,
                                                                                                          additional_instructions,
                                                                                                          style_modification)
            ## if additional instructions have been submitted by the user through the front end
            if bool(additional_instructions) and style_modification["style_modification"] is False:
                ## CAREFUL! ONLY DEALS WITH SINGLE FILE IN MIND, IF CONTENT GENERATION ON THE SAME TWO DOCS AT THE END OK BUT BE CAREFUL
                from DVoice.content_revision.revision import generate_additional_content
                from DVoice.parsing.manual_input_parsing import parse_manual_input
                ## TODO: only added the add content functionality but we should build the functionality to delete too specific content indicated by the user
                ## Generate additional content
                additional_content = generate_additional_content(additional_instructions, self.post_request_data["token"])
                ## parse additional content into markdown
                markdown_extract_repo_extra = parse_manual_input(additional_content, self.post_request_data["token"])
                ## conduct revision processing on the additional content that has just been generated
                reconstructed_revised_file_repo_extra, \
                    captured_modification_explanation_repo_extra = self._conduct_Content_voice_revision_processing(markdown_extract_repo_extra,
                                                                                                                    additional_instructions,
                                                                                                                    style_modification)
                ## add to existing file the additional content
                if "fileName" in self.post_request_data:
                    reconstructed_revised_file_repo\
                    [list(reconstructed_revised_file_repo.keys())[0]] += '\n\n' + reconstructed_revised_file_repo_extra\
                                                                                [list(reconstructed_revised_file_repo_extra.keys())[0]]
                else:
                    reconstructed_revised_file_repo\
                        [list(reconstructed_revised_file_repo_extra.keys())[0]] += '\n\n ' + reconstructed_revised_file_repo_extra\
                                                                                    [list(reconstructed_revised_file_repo_extra.keys())[0]]
                ## add explanation to the revision of the existing content
                captured_modification_explanation_repo\
                    [list(captured_modification_explanation_repo.keys())[0] + "add_content"] = captured_modification_explanation_repo_extra\
                                                                                                [list(captured_modification_explanation_repo_extra.keys())[0]]
                
            # Save results and generate output paths
            saved_revision_path_repo = {}
            for file_path, file_content in reconstructed_revised_file_repo.items():

                final_md_file_path, final_docx_path, final_file_name, doc = convert_to_markdown_and_docx_document(file_path, 
                                                                                                                  file_content)
                saved_revision_path_repo[file_path] = {"docx":final_docx_path,
                                                       "markdown":final_md_file_path}
            
            print(f"Revised files and associated locations: {saved_revision_path_repo}")
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"Content Voice Revision of {number_of_files} files took {processing_time} seconds \
                that is {processing_time/number_of_files} seconds")
            ## if manual input save with a hard coded file name
            if "manualInput" in self.post_request_data:
                file_name, folder_name, container_name = save_blob_file(doc_to_save= doc, 
                                                                        file_name=f"{self.post_request_data['userId'].split('@')[0]}/DVoice_Revised_Manual_Input.docx",
                                                                        token= self.post_request_data["token"])

            else:
                file_name, folder_name, container_name = save_blob_file(doc_to_save= doc, 
                                                                        file_name= f"{self.post_request_data['userId'].split('@')[0]}/{final_file_name}",
                                                                        token= self.post_request_data["token"])
            # save the results in the DVoiceReviser class attributes
            self.saved_revision_path_repo = saved_revision_path_repo
            self.captured_modification_explanation_repo = captured_modification_explanation_repo
            self.file_name = file_name
            self.folder_name = folder_name
            self.container_name = container_name
            
            if not self.post_request_data['debug']: # if solution deployed in prod no need to save the file in the application here - save it in app directory for easier review of output
                self.remove_local_output_folder(folder_path="Dvoice//")
            
            thread_output = {"newStatus": "Completed",
                             "outputFileName": file_name,
                             "outputPath"    : folder_name,
                             "detailedOutput": {"successful": 
                                               {"created_doc_local_output_path": saved_revision_path_repo,
                                               "creation_explanation":captured_modification_explanation_repo,
                                               "blob_name": file_name,
                                               "blob_folder_name": folder_name,
                                               "blob_container_name": container_name}}}
            
                            
            update_file_thread_flag(task_id=self.post_request_data["taskId"],
                                    file_name=source_name,
                                    thread_status="Completed",
                                    token= self.post_request_data["token"],
                                    thread_output=thread_output)
        except Exception as e:
            
            if "fileName" in self.post_request_data:
                source_name = self.post_request_data["fileName"]
            elif "manualInput" in self.post_request_data:
                source_name = self.post_request_data["manualInputFile"]["name"]
                
            update_file_thread_flag(task_id=self.post_request_data["taskId"],
                                    file_name= source_name,
                                    thread_status="Failed",
                                    token= self.post_request_data["token"],
                                    thread_output=str(e))
            raise e


## TODO: in content generation in summarization and retrieval, make sure to json parse the output in structured output and you ll need to make some tweaks to the code accordingly 
## TODO: MAKE SURE TO TRANSLATE TO ENGLISH ALL parameters from branding requirements in case it is not in english ## TODO
class DVoiceCreator(DVoiceReviser):
    """
    A class to process Content Voice creation by analyzing the uploaded documents, applying formatting rules,
    creating the content through either of 1. summarization 2. rewriting or 3. retrieval and applying the guideline
    revisions mandated by Content Marketing to have Content Compliant content.
    If no files are uploaded by the user, the processing goes into direct LLM API call to generate the content 
    directly.
    """
    def __init__(self, post_request_data: Dict[str, Any]) -> None:
        """
        Initializes the DVoiceCreator class with provided request data.
 
        Args:
            post_request_data (Dict[str, Any]): A dictionary containing input parameters for content generation.
        """
        self.post_request_data = post_request_data
        self.default_credential = post_request_data["defaultCredential"]
        self.chroma_db = post_request_data["chromaDB"]
        logger.info("Initialized new chroma db vector db")
        self.token = post_request_data["token"]
        self.user_id = post_request_data["userId"]
        self.task_id = post_request_data["taskId"]
        self.saved_creation_path_repo: Optional[Dict[str, Any]] = None
        self.captured_creation_explanation_repo: Optional[Dict[str, Any]] = None
        self.input_file_name_list: Optional[str] = None
        self.user_friendly_file_name_root: Optional[str] = None
        self.folder_name: Optional[str] = None
        self.container_name: Optional[str] = None
        self.dvoice_content_repo = {}
        
        # post_request_data={"topicPrompt": "Please write one unique output that combines content about the Canadian economy outlook and the Oil and Gas Industry and include some key facts and tabular data.", ## another Generate a comprehensive output that integrates information on the Canadian economy, its economic outlook, and the Oil and Gas industry, incorporating key facts and tabular data.
        #                    "targetAudience": "Industry Professional", ## note, potential values can be: General Public, Industry Professional, Client, Student / Intern / Co-op, {Other}
        #                    "overallStyle": "Business Casual", ## note, potential values can be: Personable, Business Casual, Professional, Formal
        #                    "contentLength": "Very short", ## note, potential values can be: Very short, Concise, Medium, Elaborate
        #                    "contentMedium": "Social Media Post", ## note, potential values can be: Long Form Article, Social Media Post, {other}
        #                    "referenceFiles": ["", ""], ## referenceFiles has to be a list to accomodate more than 1 file used in the context to help generate content
        #                    "title": "", ## The title of the document//documents optional
        #                    "includeKeywords": "", ## included keywords
        #                    "excludeKeywords": "" ## excluded keywords
        #             }
        list_params_to_guarantee_in_english = [self.post_request_data['targetAudience'], self.post_request_data['contentMedium']]
        ## translate parameters that need to be in English to English
        self.post_request_data['targetAudience'], \
            self.post_request_data['contentMedium'] = asyncio.run(process_parameter_translation(list_params_to_guarantee_in_english, 
                                                                                                self.token))
        # Optional branding message parameters
        optional_param_1 = f"Additional requirement. The Document title unless stated otherwise is : \
            '{self.post_request_data['title']}' (keep original input language for Document Title)" \
                if self.post_request_data['title'] else ""
        optional_param_2 = f"Additional requirement. The keywords to include in the content unless stated otherwise are: \
            '{self.post_request_data['includeKeywords']}' (keep original input language for keywords to include)" \
                if self.post_request_data['includeKeywords'] else ""
        optional_param_3 = f"Additional requirement. The keywords to exclude from the content unless stated otherwise are:\
              '{self.post_request_data['excludeKeywords']}' (keep original input language for keywords to exclude)" \
                if self.post_request_data['excludeKeywords'] else ""

        self.branding_requirements_message = f"""
                                The branding requirements are as follow:
                                1. Target Audience you need to cater to: {self.post_request_data['targetAudience']} \
                                2. Overall Style you need to write in: {self.post_request_data['overallStyle']} \
                                3. Content Length you need to follow is: {'Long and Detailed' if self.post_request_data['contentLength'] == 'Elaborate' else self.post_request_data['contentLength']}
                                4. The structure of the content needs to be of a: {self.post_request_data['contentMedium']}
                                
                                """ + optional_param_1 + optional_param_2 + optional_param_3
    
    def _create_summarization_query(self, query_new: str, 
                                    branding_requirements_message: str, 
                                    language_of_output: Dict[str, List[str]]) -> str:
        """
        Creates a summarization query incorporating branding requirements and output language.
 
        Args:
            query_new (str): The base query text.
            branding_requirements_message (str): Branding guidelines to follow.
            language_of_output (Dict[str, List[str]]): Language settings. {'language' : ['EN', 'FR']}
 
        Returns:
            query:
            str: The formatted query for summarization.
        """
        # rewrite core query
        core_query = rewrite_query_core_action(self.token, query_new)
        ## put together the different components of the summarization query
        branding_requirements_message_adj = "Please follow these instructions: " + " \n\n " + branding_requirements_message
        output_format = " and please make sure the content is generated in markdown format without any code block formatting. "
        language_instructions = f" and please generate the output in {'French' if language_of_output['language'][0] == 'FR' else 'English'} "
        query = core_query + branding_requirements_message_adj + output_format + language_instructions

        return query
    
    def _filter_to_correct_documents(self, concatenated_data: Dict[str, List[Dict[str, Any]]], 
                                     necessary_input_files: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filters documents to retain only necessary input files.
 
        Args:
            concatenated_data (Dict[str, List[Dict[str, Any]]]): Dictionary of document data.
            necessary_input_files (List[str]): List of required file names.
 
        Returns:
            filtered_concatenated_data:
            Dict[str, List[Dict[str, Any]]]: Filtered document dictionary.
        """
        filtered_concatenated_data = defaultdict(list, {k: concatenated_data[k] for k 
                                                       in necessary_input_files if k in concatenated_data})
        return filtered_concatenated_data
    
    def _count_tokens_from_filtered_documents(self, filtered_concatenated_data: Dict[str, List[Dict[str, Any]]]) -> int:
        """
        Counts the total number of tokens in the filtered documents.
 
        Args:
            filtered_concatenated_data (Dict[str, List[Dict[str, Any]]]): Filtered document dictionary.
 
        Returns:
            token_count:
            int: The total token count.
        """
        token_count = 0
        for _, list_chunks in filtered_concatenated_data.items():
            token_count += sum([item["n_tokens"] for item in list_chunks])
        return token_count
    
    def _collate_documents_for_summary(self, 
                                       token_count: int, 
                                       final_data_chunk_level_summary: List[Dict[str, Any]], 
                                       filtered_concatenated_data: Dict[str, List[Dict[str, Any]]], 
                                       necessary_input_files: List[str]) -> Dict[str, str]:
        """
        Collates documents for summarization based on token count constraints.
 
        Args:
            token_count (int): Total token count.
            final_data_chunk_level_summary (List[Dict[str, Any]]): Summaries of data chunks.
            filtered_concatenated_data (Dict[str, List[Dict[str, Any]]]): Filtered document data.
            necessary_input_files (List[str]): List of required file names.
 
        Returns:
            combined_docs_repo :Dict[str, str]: Dictionary containing collated document text.
        """
        if token_count > CONTEXT_WINDOW_LIMIT:
            try:
                final_data_doc_level_detailed_summary =create_doc_summary(filtered_concatenated_data, 
                                            query = "Please create a detailed summary description of the document \
                                                that preserves the intent and formatting of the original document", 
                                            hard_compression=False)
                final_data_chunk_level_summary_adj = [mini_summary for mini_summary in \
                                                    final_data_doc_level_detailed_summary if mini_summary["title"]\
                                                    in necessary_input_files]
            except Exception as e:
                print(f"Exception error when trying to gather smaller collation of documents for summary:{e} \
                      We are swithching to collating the compressed summaries")
                final_data_chunk_level_summary_adj = [mini_summary for mini_summary in \
                                                    final_data_chunk_level_summary if mini_summary["title"]\
                                                    in necessary_input_files]
            base_input = "".join([" \n\n "+ f"Mini File summary {id+1} from  File {summary_dict['title']} \n\n " \
                                    + summary_dict["summary"] for id, summary_dict in enumerate(final_data_chunk_level_summary_adj)])
        elif token_count <= CONTEXT_WINDOW_LIMIT:
            base_input = ""
            for _, list_chunks in filtered_concatenated_data.items():
                base_input += "".join([f" \n\n Chunk id {chunk['id'].split('|')[1]} from file {chunk['title']} \n\n " \
                                        + chunk["text"] for chunk in list_chunks])
        combined_docs_repo = {}
        combined_docs_repo["combined_docs"] = base_input

        return combined_docs_repo
    
    def _apply_revision(self, dvoice_content_repo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply revisions to the documents in the repository based on guidelines.

        Args:
            dvoice_content_repo (Dict[str, Any]): Repository containing document content.

        Returns:
            reconstructed_revised_file_repo:
            Dict[str, Any]: Repository with revised document content.
        """
        # Second chunking after layout reconstruction
        chunked_documents_post_layout = chunk_documents_cohesively(dvoice_content_repo)
        # Classify whether the input is to be considered for DVoice
        file_chunks_classification_repo = chunk_classification(chunked_documents_post_layout, self.token)
        ## TODO: for next iteration load the checklist and grade whether the documents already comply with the checklist
        revised_document_chunks = asyncio.run(apply_guideline_revisions_to_docs(file_chunks_classification_repo, 
                                                                                "",    # no additioal instructions to the application of the revision guideline
                                                                                False, # no additional style modification
                                                                                self.token))
        # Reconstruct revised chunks into a file
        reconstructed_revised_file_repo = reconstruct_revised_chunks_into_file(revised_document_chunks)

        return reconstructed_revised_file_repo
    
    def _create_single_output_file(self, 
                                   reconstructed_revised_file_repo: Dict[str, Any]) -> Tuple[str, Any, Dict[str, Dict[str, str]]]:
        """
        Create a single output file from the reconstructed revised file repository.

        Args:
            reconstructed_revised_file_repo (Dict[str, Any]): Repository containing reconstructed revised file content.

        Returns:
            final_file_name, doc, saved_revision_path_repo:
            Tuple[str, Any, Dict[str, Dict[str, str]]]: Final file name, document object, and saved revision path repository.
        """
        saved_revision_path_repo = {}
        for file_path, file_content in reconstructed_revised_file_repo.items():
            final_md_file_path, final_docx_path, final_file_name, doc = convert_to_markdown_and_docx_document(file_path, 
                                                                                                              file_content)
            saved_revision_path_repo[file_path] = {"docx":final_docx_path,
                                                   "markdown":final_md_file_path}
        
        return final_file_name, doc, saved_revision_path_repo

    def _conduct_dvoice_creation_from_files(self, 
                                            markdown_extract_repo: Dict[str, Any], 
                                            number_of_files: int, 
                                            rewritten_query: str, 
                                            language_of_output: Dict[str, Any], 
                                            create_second_output_other_official_language: bool) -> Dict[str, Any]:
        """
        Conduct DVoice creation from files in the context.

        Args:
            markdown_extract_repo (Dict[str, Any]): Repository containing markdown extracted content.
            number_of_files (int): Number of files to process.
            rewritten_query (str): Rewritten query for content generation.
            language_of_output (Dict[str, Any]): Language settings for the output.
            create_second_output_other_official_language (bool): Flag to create a second output in another official language.

        Returns:
            self.dvoice_content_repo: Dict[str, Any]: Repository containing generated DVoice content.
        """
        print("creation process -- with files in context")
        ## chunk the document or several document cohesively
        chuncked_documents_pre_layout = chunk_documents_cohesively(markdown_extract_repo)
        ## prepare the chunks for processing for summarization
        concatenated_data = prepare_list_chunks_and_metadata(chuncked_documents_pre_layout)
        ## generate a very high level summary for each of the files, hard compression = True means it is a high level 
        ## summary
        final_data_chunk_level_summary = create_doc_summary(concatenated_data, 
                                                            query = "Please summarize the document", 
                                                            hard_compression=True)

        if number_of_files >= 1: # if there is at least one file for processing
            ## break down the entire query submitted by the user to multiple granular queries that limits themsles
            ## to one singular concern//output. In other words, we identify the list of sub queries
            list_of_tasks_to_complete = break_down_query_to_multiple_query_output(self.token, rewritten_query)
            ## identify whether the query aims to generate one output only
            only_one_file_indicator = identify_number_output_files(self.token, rewritten_query)
            ## identify whether each sub query is summarization, rewriting or retrieval type of task
            query_task_pairs = determine_query_task_type_pairs(self.token, rewritten_query, list_of_tasks_to_complete)
            ## initialize the generated content
            generated_content = ""
            ## if only one expected output as per the intent of the user:
            if only_one_file_indicator["only_one_file"]:
                query_new = ""
                for key, _ in query_task_pairs.items():
                    query_new += " " + key # make sure to constrain to only one query even if by mistake we broke it down to several subqueries
                task_type = query_task_pairs[list(query_task_pairs.keys())[0]] ## take only as the first task if several the main task type
                ## identify the necessary files amongst those that were uploaded that can help answer the query
                necessary_input_files = determine_necessary_files(self.token, 
                                                                  final_data_chunk_level_summary, 
                                                                  query_new, 
                                                                  task_type[0])["file_list"]
                ## initialize the translated content
                translated_content = ""
                ## if no uploaded files have been found to help then error and we will try to give a more 
                ## generic answer by falling back to the direct llm call
                if not necessary_input_files:
                    if settings.DEBUG:
                        logger.error("The query cannot be answered with files because none of the files attached could answer the query")
                        logger.info("Intead, we will answer the query through direct LLM generation")
                    # direct llm call
                    dvoice_content_repo = self._conduct_dvoice_creation_without_files(rewritten_query,
                                                                                      language_of_output,
                                                                                      create_second_output_other_official_language) ## note translation is already covered inside
                    ## generated/created content
                    return dvoice_content_repo
                ## if the query is better answered through a retrieval process
                if task_type[0] == "retrieval":
                    ## conduct a RAG to get the content you need
                    generated_content = conduct_retrieval_based_content_generation(self.token,
                                                                                   concatenated_data,
                                                                                   necessary_input_files,
                                                                                   query_new,
                                                                                   self.branding_requirements_message,
                                                                                   language_of_output, 
                                                                                   self.chroma_db)
                    ## if it was determined that translation into the other canadian official language is required
                    if create_second_output_other_official_language:
                        from DVoice.prompt.prompt_actions import translate_identical_alternative_language
                        # translate content
                        translated_content = translate_identical_alternative_language(self.token, generated_content, language_of_output["language"][1])
                        ## UNTIL WE ALLOW MULTI FILE OUTPUT, FOR NOW WE JUST CONCATENATE THE CONTENT FROM BOTH LANGUAGES IN THE SAME OUTPUT THAT WILL BE IN THE SAME DOCX
                        # self.dvoice_content_repo["generated_output_creation.docx"] = generated_content
                    ## collate the translated content now to the already generated content in the primary language
                    self.dvoice_content_repo[f"{self.user_friendly_file_name_root}.docx"] = generated_content + " \n\n " + translated_content
                
                ## if the task is deemed summarization or rewriting (rewriting is close to summarization so we put them together)
                elif "summarization" == task_type[0] or "rewriting" == task_type[0]:
                    
                    # create an enhanced query fpor summarization
                    query = self._create_summarization_query(query_new, self.branding_requirements_message, language_of_output)
                    # filter to only the necessary input files for that query
                    filtered_concatenated_data = self._filter_to_correct_documents(concatenated_data, necessary_input_files)
                    # count tokens for the filtered documents (we need to respect the context window)
                    token_count = self._count_tokens_from_filtered_documents(filtered_concatenated_data)
                    ## put the documents together
                    combined_docs_repo = self._collate_documents_for_summary(token_count,
                                                                             final_data_chunk_level_summary,
                                                                             filtered_concatenated_data,
                                                                             necessary_input_files)
                    ## chunk documents cohesively
                    chuncked_documents = chunk_documents_cohesively(combined_docs_repo)
                    ## prepare the chunks for summarization
                    filtered_concatenated_data_new = prepare_list_chunks_and_metadata(chuncked_documents)
                    # conduct detailed summaries that keep good level of details. hard_compression= False
                    final_data_doc_level_summary = create_doc_summary(filtered_concatenated_data_new, 
                                                                      query,
                                                                      hard_compression=False)
                    # get the summary that answer the user's query
                    generated_content = final_data_doc_level_summary[0]["summary"]
                    ## if we need to translate to the other canadian official language
                    if create_second_output_other_official_language:
                        from DVoice.prompt.prompt_actions import translate_identical_alternative_language
                        # translate the summary from primary language to the other official language
                        translated_content = translate_identical_alternative_language(self.token, generated_content, language_of_output["language"][1])
                        ## UNTIL WE ALLOW MULTI FILE OUTPUT, FOR NOW WE JUST CONCATENATE THE CONTENT FROM BOTH LANGUAGES 
                        # IN THE SAME OUTPUT THAT WILL BE IN THE SAME DOCX
                    ## collate the content from primary language to translated content from other official language
                    self.dvoice_content_repo[f"{self.user_friendly_file_name_root}.docx"] = generated_content + " \n\n " + translated_content
                else: # in case the query is not summarization, rewriting or retrieval then we fall back to direct llm call without the uploaded files
                    print("This query type could not be covered by DVoice Writer, Make sure to submit a query that \
                          requests to summarize or create new content")
                    if settings.DEBUG:
                        logger.error("The query cannot be answered with files because none of the files attached could answer the query")
                        logger.info("Intead, we will answer the query through direct LLM generation")
                    # direct llm call
                    dvoice_content_repo = self._conduct_dvoice_creation_without_files(rewritten_query,
                                                                                      language_of_output,
                                                                                      create_second_output_other_official_language) ## note translation is already covered inside
                    return dvoice_content_repo
            # if more than output is expected from the user intent
            elif only_one_file_indicator["only_one_file"] is False:
                ## iterate over each of the sub queries determined prior and associated tasl type (sumamrization, rewriting, retrieval)
                for query_new, task_type in query_task_pairs.items():
                    print(f"Processing the following task: '{query_new}' of task type {task_type[0]}")
                    
                    # determine the necessary uploaded files that can serve the query
                    necessary_input_files = determine_necessary_files(self.token, 
                                                                      final_data_chunk_level_summary, 
                                                                      query_new, 
                                                                      task_type[0])["file_list"]
                    ## initialize translated content
                    translated_content = ""
                    ## if no files in context can support a sub query then we go for a direct llm cal and then we come back
                    ## here to bring the generated content
                    if not necessary_input_files:
                        if settings.DEBUG:
                            logger.error("The query cannot be answered with files because none of the files attached could answer the query")
                            logger.info("Intead, we will answer the query through direct LLM generation")
                        alternative_generated_content = self._conduct_dvoice_creation_without_files(rewritten_query,
                                                                                          language_of_output,
                                                                                          create_second_output_other_official_language
                                                                                            )
                        ## the brought content from the direct llm call is then appended to the generated content variable
                        ## indeed product decided that for now we only generate one file only even when multiple
                        ## are to be generated
                        generated_content_item = alternative_generated_content[list(alternative_generated_content.keys())[0]]
                        generated_content += " \n\n "+ generated_content_item ## no need to add translation content in this case because _conduct_dvoice_creation_without_files already conducts translation when requested by user
                        continue ## no need to go with the other type of tasks given no files to help with generation. We go to the next sub query
                    ## if retrieval is required to answer the sub query
                    if task_type[0] == "retrieval":
                        ## conduct the RAG process
                        generated_content_item = conduct_retrieval_based_content_generation(self.token,
                                                                                       concatenated_data,
                                                                                       necessary_input_files,
                                                                                       query_new,
                                                                                       self.branding_requirements_message,
                                                                                       language_of_output)
                        ## if the primary content needs to be translated into the other official language
                        if create_second_output_other_official_language:
                            from DVoice.prompt.prompt_actions import translate_identical_alternative_language
                            translated_content = translate_identical_alternative_language(self.token, 
                                                                                          generated_content_item, 
                                                                                          language_of_output["language"][1])
                            ## UNTIL WE ALLOW MULTI FILE OUTPUT, FOR NOW WE JUST CONCATENATE THE CONTENT FROM BOTH LANGUAGES IN THE SAME OUTPUT THAT WILL BE IN THE SAME DOCX
                            # generated_content += " \n\n " + translated_content
                            # self.dvoice_content_repo["generated_output_creation.docx"] = generated_content
                        # put together primary content with the translated content
                        generated_content += " \n\n "+  generated_content_item + " \n\n " + translated_content
                    
                    ## if summarization or rewriting 
                    elif "summarization" in task_type[0] or "rewriting" in task_type[0]:
                        # enhance the query for summarization
                        query = self._create_summarization_query(query_new, self.branding_requirements_message, language_of_output)
                        # filter to only the necessary files to answer the user sub query
                        filtered_concatenated_data = self._filter_to_correct_documents(concatenated_data, necessary_input_files)
                        # count number of tokens
                        token_count = self._count_tokens_from_filtered_documents(filtered_concatenated_data)
                        # put documents together for summary
                        combined_docs_repo = self._collate_documents_for_summary(token_count,
                                                                                final_data_chunk_level_summary,
                                                                                filtered_concatenated_data,
                                                                                necessary_input_files)
                        # chunk cohesively
                        chuncked_documents = chunk_documents_cohesively(combined_docs_repo)
                        # prepare documents for summarization
                        filtered_concatenated_data_new = prepare_list_chunks_and_metadata(chuncked_documents)
                        ## create a detailed summary. hard compression = False
                        final_data_doc_level_summary = create_doc_summary(filtered_concatenated_data_new, 
                                                                        query,
                                                                        hard_compression=False)
                        ## if it is required to translate into the other official language
                        if create_second_output_other_official_language:
                            from DVoice.prompt.prompt_actions import translate_identical_alternative_language
                            ## translate primary content to other official language
                            translated_content = translate_identical_alternative_language(self.token, 
                                                                                          final_data_doc_level_summary[0]["summary"], 
                                                                                          language_of_output["language"][1])
                        # put together primary content with the other official language content
                        generated_content += " \n\n " + final_data_doc_level_summary[0]["summary"] + " \n\n " + translated_content

                self.dvoice_content_repo[f"{self.user_friendly_file_name_root}.docx"] = generated_content
            else:
                print("An error occured, please try again")
                if settings.DEBUG:
                    logger.error("An error occured, please try again")
                # prepare the thread body for update
                thread_output = {"newStatus": "Completed",
                            "outputFileName": f"{self.user_friendly_file_name_root}.docx",
                            "outputPath"    : None,
                            "detailedOutput": {"successful": 
                                            {"created_doc_local_output_path": None,
                                            "creation_explanation": None,
                                            "blob_name": None,
                                            "blob_folder_name": None,
                                            "blob_container_name": None}}}
                # update the thread flag for async threading
                update_file_thread_flag(task_id=self.task_id,
                                    file_name= "attempted_dvoice_creation_output_failed.docx",
                                    thread_status="Completed - could not generate any content",
                                    token= self.token, 
                                    thread_output=thread_output)

        return self.dvoice_content_repo # final DVoice creation output for situation when user upload files
    
    def _conduct_dvoice_creation_without_files(self,
                                               rewritten_query: str,
                                               language_of_output: Dict[str, List[str]],
                                               create_second_output_other_official_language: Optional[bool]
                                               ) -> Dict[str, str]:
        """
        Conducts the DVoice creation process without any reference files.
 
        Args:
            rewritten_query (str): The rewritten query to be processed.
            language_of_output (Dict[str, List[str]]): The language(s) of the output.
            create_second_output_other_official_language (Optional[bool]): Flag to create output in a second official language.
 
        Returns:
            Dict[str, str]: The repository containing the generated DVoice content.
        """
        print("creation process -- no files in context")
        from DVoice.content_creation.create_content import generate_dvoice_response_no_context
        ## break down the user query into a list of subqueries
        list_of_tasks_to_complete = break_down_query_to_multiple_query_output(self.token, rewritten_query)
        ## initialize the generated content
        generated_content = ""
        ## iterate over the list of sub queries
        for core_query in list_of_tasks_to_complete["query_breakdown"]:
            ## that function should be in the creation folder
            print(f"Processing the following query {core_query}")
            ## initialize the translated content
            translated_content = ""
            ## make the direct api call for the sub query
            generated_content_item = generate_dvoice_response_no_context(self.token, 
                                                                         core_query, 
                                                                         self.branding_requirements_message, 
                                                                         language_of_output["language"][0])
            # if the sub query also requested the output to be in the other official language
            if create_second_output_other_official_language:
                from DVoice.prompt.prompt_actions import translate_identical_alternative_language
                ## translate to other official language
                translated_content = translate_identical_alternative_language(self.token, generated_content_item, language_of_output["language"][1])
                ## UNTIL WE ALLOW MULTI FILE OUTPUT, FOR NOW WE JUST CONCATENATE THE CONTENT FROM BOTH LANGUAGES IN THE SAME OUTPUT THAT WILL BE IN THE SAME DOCX
            generated_content += " \n\n "+ generated_content_item + " \n\n " + translated_content
        self.dvoice_content_repo[f"{self.user_friendly_file_name_root}.docx"] = generated_content

        return self.dvoice_content_repo
    
    def _revise_and_save_output(self,
                                dvoice_content_repo: Dict[str, str]) -> None:
        """
        Revises and saves the generated DVoice content.
        Leverages some of the core DVoice Revision functionalities
 
        Args:
            dvoice_content_repo (Dict[str, str]): The repository containing the generated DVoice content.
        """
        # conduct revsion
        reconstructed_revised_file_repo = self._apply_revision(dvoice_content_repo)
        ## save output into unique output file. For now it is just a unique output file and format docx but could be easily changed if need be.
        final_file_name, doc, \
            saved_revision_path_repo = self._create_single_output_file(reconstructed_revised_file_repo)
        ## save to blob storage
        file_name, folder_name, container_name = save_blob_file(doc_to_save= doc, 
                                                            file_name= f"{self.user_id.split('@')[0]}/{final_file_name}",
                                                            token= self.token)
        # save the results in the DVoiceReviser class attributes
        self.saved_revision_path_repo = saved_revision_path_repo
        self.captured_modification_explanation_repo = "No explanation are captured for DVoice creation but they can easily if need be :)"
        self.file_name = file_name
        self.folder_name = folder_name
        self.container_name = container_name

        thread_output = {"newStatus": "Completed",
                            "outputFileName": file_name,
                            "outputPath"    : folder_name,
                            "detailedOutput": {"successful": 
                                            {"created_doc_local_output_path": saved_revision_path_repo,
                                            "creation_explanation": self.captured_modification_explanation_repo,
                                            "blob_name": file_name,
                                            "blob_folder_name": folder_name,
                                            "blob_container_name": container_name}}}
        update_file_thread_flag(task_id=self.task_id,
                                file_name=file_name,
                                thread_status="Completed",
                                token= self.token,
                                thread_output=thread_output)
        
    def run_DVoice_creation(self) -> None:
        """
        Initiates the DVoice creation process, which involves analyzing the input query,
        determining the language, ensuring Bill 96 compliance, and generating the output
        content either from provided files or directly through direct llm api call without any files in context

        Raises:
            Exception: If any error occurs during the DVoice creation process.
        """

        print("Starting DVoice creation process")
        
        ## test complex query: Create an executive summary from the attached Global article copy into 
        # a Canadianized article page abiding by Bill 96 compliance on a narrative for board directors
        try:
            start_time = time.time()
            query = self.post_request_data["topicPrompt"]
            # analyze the language in the query to determine the intended output language
            # that is a business rule decided by product            
            language_of_output = determine_input_language(query, self.token)
            # identify the initial language of output
            initial_language_of_output = language_of_output
            try:
                # determine the user friendly name for the output file
                self.user_friendly_file_name_root = determine_file_output_user_friendly_name(query, 
                                                                                             initial_language_of_output['language'][0], 
                                                                                             self.token)
            except Exception as e:
                self.user_friendly_file_name_root = "generated_output_creation_DVoice"
            ## identify whether the query requires bill 96 compliance
            bill_96_compliance_analysis = identify_bill_96_compliance(self.token, query)
            ## if the query is in French we translate it to English because our prompts expect a query in English
            if "FR" in language_of_output["language"] and len(language_of_output["language"]) == 1:
                query = translate_query_to_desired_language(self.token, query)
                language_of_output = determine_input_language(query, self.token)
                ## translate {other} potential values where applicable from Fr to English
            ## iitlialize the second language flag
            create_second_output_other_official_language = None
            ## if 2 languages are needed or bill 96 compliance is required
            if bill_96_compliance_analysis["bill_96_compliance"] or (("FR" in language_of_output["language"]) \
                                                                      and ("EN" in language_of_output["language"])):
                # makr the need for content in second language as true
                create_second_output_other_official_language = True
                ## in case bill 96 compliance but the system did not identify easily that there needs to be 2 languages of output
                ## then make it bilingual
                if len(language_of_output["language"]) == 1:
                    if "EN" in language_of_output["language"]:
                        language_of_output["language"].append("FR")
                    elif "FR" in language_of_output["language"]:
                        language_of_output["language"].append("EN")
                ## make sure in case it has to be bilingual content that EN is first in the list
                language_of_output["language"] = sorted(language_of_output["language"])

            # rewrite query
            rewritten_query = rewrite_query(self.token, query)
            ## maybe putting the query break down action after the analysis
            # if files have been uploaded as references
            if bool(self.post_request_data["referenceFileListInput"]): # self.post_request_data['referenceFilesListInput']
                from DVoice.parsing.file_parsing import parse_files, extract_markdown_from_parsed_output # only needed when file upload
                
                # source_file_name_list = [input_doc["name"] for input_doc in post_request_data["referenceFileListInput"]] ## TODO: should be self in the future
                input_document_list = self.post_request_data["referenceFileListInput"]
                # parse the files
                conv_results, number_of_files, unsupported_doc_repo = parse_files(input_document=input_document_list, 
                                                                                  token=self.token, #self.post_request_data["token"],
                                                                                  default_credential = self.default_credential,
                                                                                  file_extension= self.post_request_data["fileExtension"]) # self.post_request_data["fileExtension"])
                # extract the content into markdown
                markdown_extract_repo = extract_markdown_from_parsed_output(conv_results, 
                                                                            number_of_files, 
                                                                            self.token,
                                                                            unsupported_doc_repo) 
                # conduct the creation process
                dvoice_content_repo = self._conduct_dvoice_creation_from_files(markdown_extract_repo, 
                                                                               number_of_files,
                                                                               rewritten_query,
                                                                               language_of_output,
                                                                               create_second_output_other_official_language)
                
                if not dvoice_content_repo:
                    print("Please retry with a more precise prompt")
                    if settings.DEBUG:
                        logger.error("Please retry with a more precise prompt and/or files that are more associated to your query") 
                    # Update thread flag
                    thread_output = {"newStatus": "Completed",
                            "outputFileName": f"{self.user_friendly_file_name_root}.docx",
                            "outputPath"    : None,
                            "detailedOutput": {"successful": 
                                            {"created_doc_local_output_path": None,
                                            "creation_explanation": None,
                                            "blob_name": None,
                                            "blob_folder_name": None,
                                            "blob_container_name": None}}}
                    update_file_thread_flag(task_id=self.task_id,
                                    file_name= "attempted_dvoice_creation_output_failed.docx",
                                    thread_status="Completed - could not generate any content",
                                    token= self.token, 
                                    thread_output=thread_output)
                else:
                    ## conduct the revision process
                    self._revise_and_save_output(dvoice_content_repo)
                    
            else: # no files are uploaded, direct llm generation in this case
                dvoice_content_repo = self._conduct_dvoice_creation_without_files(rewritten_query,
                                                                                  language_of_output,
                                                                                  create_second_output_other_official_language,
                                                                                )
                if not dvoice_content_repo:
                    if settings.DEBUG:
                        logger.error("Please retry with a more precise prompt and/or files that are more associated to your query") 
                    # Update thread flag
                    thread_output = {"newStatus": "Completed",
                            "outputFileName": f"{self.user_friendly_file_name_root}.docx",
                            "outputPath"    : None,
                            "detailedOutput": {"successful": 
                                            {"created_doc_local_output_path": None,
                                            "creation_explanation": None,
                                            "blob_name": None,
                                            "blob_folder_name": None,
                                            "blob_container_name": None}}}
                    update_file_thread_flag(task_id=self.task_id,
                                    file_name= "attempted_dvoice_creation_output_failed.docx",
                                    thread_status="Completed - could not generate any content",
                                    token= self.token, 
                                    thread_output=thread_output)
                    return
                else:
                    self._revise_and_save_output(dvoice_content_repo) ## conduct the revision process 
                
            if not self.post_request_data['debug']: # if solution deployed in prod no need to save the file in the application here - save it in app directory for easier review of output
                self.remove_local_output_folder(folder_path="Dvoice//") # remove the folder where the files are saved
            end_time =  time.time()
            process_time = end_time - start_time

            logging.info(f"DVoice Creation took {process_time} seconds")

        except Exception as e:
            logging.error(f"Error due to {e}")
                            
            update_file_thread_flag(task_id=self.task_id,
                                    file_name= "attempted_dvoice_creation_output_failed.docx",
                                    thread_status="Failed",
                                    token= self.token, 
                                    thread_output=str(e))
            raise e     
               
if __name__ == "__main__":
    
    reviser = DVoiceReviser(post_request_data={"manualInput": "Queen Elizabeth II, born in 1926, ascended the throne in 1952, becoming Britain s longest-reigning monarch. Her life was defined by duty and resilience. During World War II, she served as a mechanic, displaying an early sense of responsibility. As queen, she navigated a rapidly changing world, witnessing the decline of the British Empire, the rise of globalism, and advancements in technology. Known for her poise, she maintained the monarchy’s relevance, fostering connections across the Commonwealth. Her love for corgis and horses revealed a softer side, while her unyielding commitment to her role earned admiration worldwide. Her legacy endures in history.",
                                               "additionalInstructions": ""})
    reviser_output = reviser.run_DVoice_revision()
    

    post_request_data={"topicPrompt": "Please write for me a specific content about the Canadian economy and include some key facts and tabular data.",
                       "targetAudience": "",
                       "overallStyle": "",
                       "contentLength": "",
                       "contentMedium": "",
                       "referenceFiles": ["", ""], ## referenceFiles has to be a list to accomodate more than 1 file used in the context to help generate content
                       "title": "",
                       "includeKeywords": "",
                       "excludeKeywords": ""
                    }






