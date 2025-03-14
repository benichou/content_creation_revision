import requests
import json
from io import BytesIO
from typing import Literal
from django.conf import settings
from docx import Document

import logging
import sys

## LOGGING CAPABILITIES

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
# Attach handler to the logger
logger.addHandler(handler)


def get_all_blob_names(token):

    response = requests.get(settings.LIST_ALL_BLOBS_URL, params=None, headers= {
        "Authorization": "Bearer " + token.token
    }, verify=settings.CERTIFICATE_VERIFY)
    
    try:
        file_names = json.loads(response.text)["result"]

    except Exception as e:
        print("Error", response.text)
        raise e
    
    if settings.DEBUG:
        print("to upload files:",file_names)
    return file_names


def get_onboarding_file(file_name, token):
    
    params = {
        "fileName"    : file_name,
    }
    file_response = requests.get(settings.DOWNLOAD_ONBOARDING_URL, params=params, headers= {
        "Authorization": "Bearer " + token.token
        
    }, verify=settings.CERTIFICATE_VERIFY)

    if settings.DEBUG:
        print("got file: ", file_name)

    return {
        "name": file_name,
        "byte_io": BytesIO(file_response.content)
    }
def get_blob_file(token: str, file_name: str, api_type: Literal["document_analyzer", 
                                                                "deloitte_voice", 
                                                                "deloitte_voice_docling_transformers"] = 
                                                                "document_analyzer") -> BytesIO:
    """
    Retrieves a file from a blob storage based on the specified API type.
 
    Args:
        token (str): The authorization token required for accessing the blob storage.
        file_name (str): The name of the file to download.
        api_type (Literal["document_analyzer", "deloitte_voice", "deloitte_voice_docling_transformers"]):
            The type of API determining the URL and parameters for retrieval. Defaults to "document_analyzer".
 
    Returns:
        BytesIO: A BytesIO object containing the file content.
 
    Raises:
        Exception: If the file download fails, an error is raised with the status code.
    """
    if api_type == "document_analyzer":
        url = settings.DOWNLOAD_DOCUMENT_URL
        params = {
            "fileName"    : file_name,
        }
    if api_type == "deloitte_voice":
        url =settings.DVOICE_DOWNLOAD_DOCUMENT_URL
        params = {
        "container"   : settings.DVOICE_CONTAINER_NAME,
        "folderName"  : file_name.split("/")[0] + "/" + settings.DVOICE_DOWNLOAD_FOLDER,
        "fileName"    : file_name.split("/")[1],
        }
    if api_type == "deloitte_voice_docling_transformers":
        url = settings.DVOICE_DOWNLOAD_DOCUMENT_URL
        params = {
        "container"   : settings.DVOICE_TRANSFORMERS_CONTAINER_NAME,
        "folderName"  : settings.DVOICE_DOWNLOAD_TRANSFORMERS_FOLDER,
        "fileName"    : file_name,
        }
    
    response = requests.get(url, params=params, headers= {
        "Authorization": "Bearer " + token.token
    }, verify=settings.CERTIFICATE_VERIFY)
    
    logger.info(f"✅ Donwloaded {file_name} with response: {response.status_code}")
    
    if response.status_code != 200:
        # Throw an error with the status code and error message
        raise Exception(f'Failed to download file {file_name}: Status code {response.status_code}')
    
    return BytesIO(response.content)

def save_blob_file(doc_to_save: Document, file_name: str, token) -> tuple:
    """
    Saves a document as a blob file and uploads it to an external API.
 
    This function formats the file name with a timestamp, converts the document into 
    a byte stream, and uploads it to a specified Azure blob storage container via an API.
 
    Args:
        doc_to_save (Document object): The DOCX document object to be saved and uploaded.
        file_name (str): The file path, where the first part represents the user folder, 
                         and the second part is the actual file name.
        token (Azure Access Token): An authorization token object used for API authentication.
 
    Returns:
        tuple: A tuple containing:
            - final_file_name (str): The formatted file name with a timestamp to make it unique
            - folder_name (str): The destination folder path within the blob storage.
            - blob_container_name (str): The name of the blob storage container.
 
    Raises:
        requests.HTTPError: If the API request fails.
    """
    # Send the corrected document to the external API    
    import time
    from pathlib import Path
    # Extract user folder and file name from the given path
    user_folder = file_name.split("/")[0]
    file_name = file_name.split("/")[1]
    # Extract file name stem and extension
    file_name_stem = Path(file_name).stem
    extension = Path(file_name).suffix
    # Generate a timestamped file name
    current_time = time.localtime()
    formatted_time = time.strftime("%Y-%m-%d_%H-%M-%S", current_time)
    
    final_file_name = file_name_stem + "_" + formatted_time + extension
    # Convert document to a byte stream for upload
    output_stream = BytesIO()
    doc_to_save.save(output_stream)
    output_stream.seek(0)
    
    try:
        # one file at a time for now
        # Prepare the file data for the API request
        files = {
            'files': (
                final_file_name,
                output_stream.getvalue(),
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        }
        # Construct the Azure folder and blob storage details
        folder_name = user_folder + "/" + settings.DVOICE_UPLOAD_FOLDER
        blob_container_name = settings.DVOICE_CONTAINER_NAME
        # Make the API request to upload the document
        response = requests.post(
            settings.DVOICE_UPLOAD_DOCUMENT_URL,
            params={
                'container': blob_container_name,
                'folderName': folder_name
            },
            files=files,
            headers= {"Authorization": "Bearer " + token.token},
            verify= settings.CERTIFICATE_VERIFY
        )
        # Raise an error if the request was unsuccessful
        response.raise_for_status()
        print(f"Saved document {final_file_name} uploaded successfully via external API in container: {blob_container_name} \
            in blob folder path {folder_name}")
    except Exception as e:
        print(f"Error uploading corrected document to external API: {e}")
    
    return final_file_name, folder_name, blob_container_name