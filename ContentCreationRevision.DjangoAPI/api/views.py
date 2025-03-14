import os, sys
import traceback
import threading
import pandas as pd
from rest_framework.views                     import APIView
from rest_framework.response                  import Response
from azure.identity                           import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential
from django.conf                              import settings
from utilities.blob_storage                   import get_blob_file
from utilities.cosmos_process                import update_file_thread_flag
from utilities.chromadb                      import ChromaDBHandler
from rest_framework                          import status
from pathlib                                 import Path
from typing                                  import Dict, Any



##################################### START OF Content VOICE APIS ######################################################
##################################### REVISION #########################################################################
class DVoiceRevisionAPIView(APIView):
    """
    API View for handling Content Voice revision requests. 
    This endpoint processes file-based and manual input revisions asynchronously.
    """
    def __init__(self) -> None:
        """
        Initializes the API view by setting up Azure authentication credentials.
        """
        self.default_credential = ChainedTokenCredential(AzureCliCredential(), DefaultAzureCredential())
        self.token         = self.default_credential.get_token(settings.COGNITIVE_SERVICES_URL)
    
    def post(self, request: Any) -> Response:
        """
        Handles POST requests to start a Content Voice revision task.
        Args:
            request (Any): The incoming HTTP request containing the task data.
        Returns:
            Response: A JSON response indicating success or failure.
        """
        # import necessary packages to run the Content Voice API
        from .serializers import FileNameValidatorSerializer
        
        data=request.data
        post_message = data.dict()
        self.user_id = post_message["userId"]
        self.task_id = post_message["taskId"]
        post_message["defaultCredential"] = self.default_credential
        post_message["token"] = self.token
        post_message["debug"] = settings.DEBUG
        try:
            if "fileName" in post_message:    
                serializer = FileNameValidatorSerializer(data=request.data)
                if serializer.is_valid():
                    post_message["fileExtension"] = [Path(post_message["fileName"]).suffix]
                    self.file_name = post_message["fileName"]
                    print({"message": f"Request contains valid files."})
                    print(Response({"message": f"Valid file"}, status=status.HTTP_200_OK))
                    file = {"name": self.file_name,
                            "byte_io": get_blob_file(self.token, 
                                            f"{self.user_id.split('@')[0]}/{self.file_name}",
                                            api_type = "Content_voice"),
                                            }
                    # Currently, only supports single file processing.
                    post_message["fileNameInput"] = [file] ## TODO: MAKE SURE TO ADJUST WHEN MULTIPLE FILES TO REVISE IN A BATCH
                    # Update the async thread task status to 'inProgress': 
                    # why async thread? Depending on the size and complexity of the file, 
                    # the task can go beyond the 240 seconds limit before a job is identified as a timeout by Azure
                    update_file_thread_flag(task_id = self.task_id,
                                            file_name=self.file_name,
                                            thread_status="inProgress",
                                            token=self.token)
                    # IT ALL STARTS HERE: Start asynchronous revision process
                    self.run_async_revision(post_message)
                    
                    return Response({
                                    "status" : "Success",
                                    "message" : f"DVoice Revision Started for file: {self.file_name}"
                                }, status=status.HTTP_200_OK)
                    
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            elif "manualInput" in post_message:
                # Handle manual input revision //manual input is when the user inserts no file but only some free text in the manual input box
                file = {"name": "manualInput"}
                post_message["manualInputFile"] = file
                update_file_thread_flag(task_id = self.task_id,
                                        file_name = post_message["manualInputFile"]["name"],
                                        thread_status = "inProgress",
                                        token=self.token)
                self.run_async_revision(post_message)
                
                return Response({
                                "status" : "Success",
                                "message" : f"DVoice Revision Started for Manual Input"
                                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            print("Exception encountered")
            if "fileName" in post_message:
                source_name = post_message["fileName"]
            elif "manualInput" in post_message:
                source_name = post_message["manualInputFile"]["name"]
            # Update task status to 'Failed' if error capture by e of Exception above
            update_file_thread_flag(task_id = self.task_id,
                                    file_name=source_name,
                                    thread_status="Failed",
                                    token=self.token,
                                    thread_output=str(e))
            traceback.print_exc()
            sys.stdout.flush()
            return Response({
                "status" :  "Failed",
                "message": repr(e),
                "debugging_advice": "Please note this error is probably due to a taskId or a Token issue not being found. Make sure \
                the thread taskId exists in the sql db for the environment you are running this solution. Otherwise, make sure \
                sure the TOKEN is not expired either."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  
            
    def run_async_revision(self, post_message: Dict[str, Any]) -> None:
        """
        Runs the Content Voice revision process asynchronously in a separate thread.
        Args:
            post_message (Dict[str, Any]): The message containing task data.
        Returns:
            Per se Nothing, but this is where we eventually creates the revision output and convert it to a docx file that is 
            later saved locally temporarily for development and also in blob storage in all stages including dev
            Note: During testing, you can test this class by calling this specific django api view. Details in the postman 
            collection in Content.Ca.DBotBeta.DjangoAPI\\DVoice\\assets\\postman_collection (in this repo)
        """
        from DVoice.main import DVoiceReviser
        reviser = DVoiceReviser(post_message)
        thread = threading.Thread(target=reviser.run_DVoice_revision) ## this is really where the async thread starts and revision starts, go to DVoice folder now
        thread.start() ## we start the thread but notice we do not "join" (that is how we make it async) aka close it because we want to avoid the azure timeout that is set as of we speak at 240 seconds
        

##################################### CREATION #########################################################################

class DVoiceCreationAPIView(APIView):
    """
        API view to handle the creation of DVoice tasks.
        This view processes user-submitted requests, validates input files, 
        and initiates an asynchronous creation process for DVoice Creation Solution.
        """
    def __init__(self) -> None:
        """
        Initialize the API view by setting up authentication and database handlers.
        """
        self.chroma_db = ChromaDBHandler()
        self.default_credential = ChainedTokenCredential(AzureCliCredential(), DefaultAzureCredential())
        self.token         = self.default_credential.get_token(settings.COGNITIVE_SERVICES_URL)
    
    def post(self, request: Any) -> Response:
        """
        Handle POST requests for DVoice creation.
 
        Args:
            request (Any): The HTTP request object containing user input data.
 
        Returns:
            Response: A JSON response indicating success or failure of the operation.
        """
        data=request.data
        self.post_message = data.dict()
        self.user_id = self.post_message["userId"]
        self.task_id = self.post_message["taskId"]
        self.post_message["defaultCredential"] = self.default_credential
        self.post_message["chromaDB"] = self.chroma_db
        
        self.post_message["token"] = self.token
        self.post_message["debug"] = settings.DEBUG

        # Process reference files from the request
        self.reference_files_list = [file_name.strip() for file_name in self.post_message["referenceFiles"].split(",")]
        self.post_message["referenceFiles"] = self.reference_files_list
        if self.post_message["referenceFiles"][0] == "": # If no files are present
            self.post_message["referenceFiles"] = [] # simplification of the data type
        self.post_message["fileExtension"] = [Path(input_doc_name).suffix for input_doc_name in self.reference_files_list] 
        
        try:
            print("processing")
            # If reference files are provided, download them
            if bool(self.post_message["referenceFiles"]):
                self.reference_file_list = []
                for reference_file_name in self.post_message["referenceFiles"]:
                    # download the reference files
                    reference_file = {"name": reference_file_name,
                                      "byte_io": get_blob_file(self.token, 
                                      f"{self.user_id.split('@')[0]}/{reference_file_name}",
                                      api_type = "Content_voice")
                                      }
                    self.reference_file_list.append(reference_file)
                self.post_message["referenceFileListInput"] = self.reference_file_list
            else:
                self.post_message["referenceFileListInput"] = []
            
        except Exception as e:
            update_file_thread_flag(task_id = self.task_id,
                                    file_name=self.post_message["referenceFiles"] \
                                        if bool(self.post_message["referenceFiles"]) else "No Uploaded files",
                                    thread_status="Failed",
                                    token=self.token,
                                    thread_output=str(e))
            traceback.print_exc()
            sys.stdout.flush()
            return Response({
                "status" :  "Failed",
                "message": repr(e),
                "debugging_advice": "Please note this error is probably due to a taskId or a Token issue not being found. Make sure \
                the thread taskId exists in the sql db for the environment you are running this solution. Otherwise, make sure \
                sure the TOKEN is not expired either."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # Update task status to in-progress if no errors
            update_file_thread_flag(task_id = self.task_id,
                                    file_name= self.post_message["referenceFiles"] \
                                        if bool(self.post_message["referenceFiles"]) else "No Uploaded files",
                                    thread_status="inProgress",
                                    token=self.token)
            # Start async processing
            self.run_async_creation(self.post_message)

            return Response({"status" : "Success",
                            "message" : f"DVoice Creation Started."
                        }, status=status.HTTP_200_OK)

        except Exception as e:
            update_file_thread_flag(task_id = self.task_id,
                                    file_name=self.post_message["referenceFiles"] \
                                        if bool(self.post_message["referenceFiles"]) else "No Uploaded files",
                                    thread_status="Failed",
                                    token=self.token,
                                    thread_output=str(e))
            traceback.print_exc()
            sys.stdout.flush()
            return Response({
                "status" :  "Failed",
                "message": repr(e),
                "debugging_advice": "Please note this error is probably due to a taskId or a Token issue not being found. Make sure \
                the thread taskId exists in the sql db for the environment you are running this solution. Otherwise, make sure \
                sure the TOKEN is not expired either."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

    def run_async_creation(self, post_message: Dict[str, Any]) -> None:
        """
        Run the DVoice creation process asynchronously.
        Args:
            post_message (Dict[str, Any]): The processed user request data containing necessary parameters and downloaded file in the form of Byte IO
            Note: During testing, you can test this class by calling this specific django api view. Details in the postman 
            collection in ContentCreationRevision.Ca.DBotBeta.DjangoAPI\\DVoice\\assets\\postman_collection (in this repo)
        """
        from DVoice.main import DVoiceCreator
        creator = DVoiceCreator(post_message) # initializes the creator class
        thread = threading.Thread(target=creator.run_DVoice_creation) # really starts here the dvoice creation async process, then go to the main of DVoice folder
        thread.start() ## like in revision, we start the thread but please notice we do not "join" aka close it because we want to avoid the azure timeout (that is how we make it async) that is set as of we speak at 240 seconds