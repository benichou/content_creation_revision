import os
# from dotenv import load_dotenv ## use it only for local development or issue with tokens to azure resources

from django.conf import settings ## connect to the django main settings
# from azure.identity import DefaultAzureCredential ## use it only for local development or issue with tokens to azure resources
# default_credential = DefaultAzureCredential() ## use it only for local development or issue with tokens to azure resources


## DOCLING PARSING PARAMETERS
IMAGE_RESOLUTION_SCALE = 2.0
GENERATE_PAGE_IMAGES = True
GENERATE_PICTURE_IMAGES = True
GENERATE_TABLE_IMAGES = True
PDF_DOCUMENT_HIGH_QUALITY_PARSING = False ## WE PUT IT TO FALSE TO HAVE THE FASTEST LATENCY WHILE ENSURING ACCURACY FROM DOCLING PARSING
PDF_DOCLING_NUMBER_PAGES_LIMIT = 20 ## maximum number we agree docling can process before it takes too long

## EXTRACTED OUTPUT PATH
WORD_DOCUMENT_FINAL_OUTPUT_PATH = '\\output_summary\\docx\\final\\' ## LOCAL PATH FOR WORD
MARKDOWN_INDIVIDUAL_PAGES_FROM_PPTX_PAGES_OUTPUT_PATH = '\\output_summary\\markdown\\pptx_pages_converted_to_markdown\\' ## LOCAL PATH FOR MD OUTPUT PAGES
MARKDOWN_DOCUMENT_FINAL_OUTPUT_PATH = '\\output_summary\\markdown\\final\\' ## LOCAL PATH FOR FINAL MARKDOWN OUTPUT

## CHUNKING (COHESIVE CHUNKING SIZE FOR DVOICE CREATION AND REVISION)
CHUNK_SIZE = 1000 # more or less equivalent to 900 words. Through experiments and rule of thumbs it was determined to work best.

## AZURE OPEN AI CREDENTIALS
SELECTED_MODEL = "MULTIMODAL_MODEL_GPT4O_128K_DVOICE" ## PSEUDO MODEL DEPLOYMENT NAME (THAT WE GIVE IN THE DJANGO CONFIG HERE) FOR THE GPT 4o MODEL THAT SUPPORTS STRUCTURED OUTPUT

API_VERSION = settings.API_VERSION_MODEL_DICTIONARY[SELECTED_MODEL] ## LLM API VERSION
AZURE_OPENAI_ENDPOINT = settings.API_BASE ## THE ACTUAL URL ENDPOINT
AZURE_OPENAI_MODEL_NAME = settings.MODEL_DICTIONARY[SELECTED_MODEL] ## THE DEPLOYMENT NAME
AZURE_OPENAI_MODEL = settings.MODEL_NAME_DICTIONARY[SELECTED_MODEL] ## THE MODEL NAME
CONTEXT_WINDOW_LIMIT = settings.MODEL_CONTEXT_WINDOW_SIZE[SELECTED_MODEL] ## MAXIMUM NUMBER OF TOKENS INGESTABLE IN LLMS

## MODEL PARAMETERS 
MAX_TOKEN_COMPLETION = settings.MODEL_MAX_OUTPUT_SIZE[SELECTED_MODEL] ## MAX NUMBER OF TOKENS FOR COMPLETION, IE GPT4o is 4096 so we chose 4000 at time of implementation
TEMPERATURE = 0 ## WE TRY TO BE AS DETERMINISTIC AS POSSIBLE


## DOCLING TRANSFORMERS PARAMETERS
DOCKER_MODE = True # IN LOCAL DEV AND TESTING SET IT TO FALSE SO YOU CAN SAVE THE DOCLING LLMS IN THE EXPECTED FOLDER
DOCLING_TRANSFORMER_MODEL_PATH_LOCAL = "ContentCreationRevision.DjangoAPI\\DVoice\\parsing\\ds4sd_docling-models"
DOCLING_LLM_LAYOUT_PATH_LOCAL = "\\model_artifacts\\layout\\" # WHY SPECIFICALLY THESE PATHS? TO MIMIC THE STRUCTURE OF THE LLMs DIRECTORY - check open source version
DOCLING_ACCURATE_TABLE_LLM_PATH_LOCAL = "\\model_artifacts\\tableformer\\accurate\\"
DOCLING_FAST_TABLE_LLM_PATH_LOCAL = "\\model_artifacts\\tableformer\\fast\\"

DOCLING_TRANSFORMER_MODEL_PATH_DOCKER = "DVoice/parsing/ds4sd_docling-models" ## IN DOCKER, nOTE THE WORKING DIR IS app/
DOCLING_LLM_LAYOUT_PATH_DOCKER = "/model_artifacts/layout/" # WHY SPECIFICALLY THESE PATHS? TO MIMIC THE STRUCTURE OF THE LLMs DIRECTORY - check open source version
DOCLING_ACCURATE_TABLE_LLM_PATH_DOCKER = "/model_artifacts/tableformer/accurate/"
DOCLING_FAST_TABLE_LLM_PATH_DOCKER = "/model_artifacts/tableformer/fast/"


## actual llm model name for docling
DOCLING_LAYOUT_LLM = "model.safetensors" # INCLUDES THE SAFETENSORS EXTENSION lower case extension fyi
DOCLING_ACCURATE_TABLE_LLM = "tableformer_accurate.safetensors"
DOCLING_FAST_TABLE_LLM = "tableformer_fast.safetensors"

if DOCKER_MODE:
    DOCLING_LLM_DICT = {DOCLING_LAYOUT_LLM: DOCLING_LLM_LAYOUT_PATH_DOCKER
                        ,DOCLING_ACCURATE_TABLE_LLM: DOCLING_ACCURATE_TABLE_LLM_PATH_DOCKER
                        ,DOCLING_FAST_TABLE_LLM: DOCLING_FAST_TABLE_LLM_PATH_DOCKER}
if DOCKER_MODE is False:
    DOCLING_LLM_DICT = {DOCLING_LAYOUT_LLM: DOCLING_LLM_LAYOUT_PATH_LOCAL
                        ,DOCLING_ACCURATE_TABLE_LLM: DOCLING_ACCURATE_TABLE_LLM_PATH_LOCAL
                        ,DOCLING_FAST_TABLE_LLM: DOCLING_FAST_TABLE_LLM_PATH_LOCAL}

REFRESH_DOCLING_TENSORS = False # set to false because we do not want to refresh it. In theory, we should always have it as false;
## so you may wonder why we have this bool. We need it it just in case to debug the downloading of the docling llm objects

DEBUG = settings.DEBUG
    