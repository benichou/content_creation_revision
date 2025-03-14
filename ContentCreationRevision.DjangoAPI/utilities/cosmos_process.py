import requests
import json
from django.conf import settings

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


def update_file_thread_flag(task_id,
                            file_name,
                            thread_status,
                            token,
                            thread_output=None):
    """_summary_

    Args:
        file_name (_type_): _description_
        thread_status (_type_): _description_
        thread_output (_type_, optional): _description_. Defaults to None.

    Raises:
        e: _description_

    Returns:
        _type_: _description_
    """
    if thread_status == "Failed":
        request_body = {"newStatus": thread_status,
                        "errorMessage": thread_output}
    elif thread_status == "Completed": # flag thread as "Completed"
        request_body = thread_output # the final output sent to the cosmo db row once the thread is indeed complete --> that is why we flag it as "Completed"
    elif thread_status == "inProgress":
        request_body = {"newStatus": thread_status}
        
    url = f"{settings.DVOICE_UPDATE_INPROGRESS_THREAD_FLAG_URL}/{task_id}"
    logging.info(f"URL is {url}")
    logging.info(f"taskid is {task_id}")
    
    update_response = requests.put(url=url, data = json.dumps(request_body), headers= {"Authorization": "Bearer " + token.token,
                                                                                      "Content-Type": "application/json"}, verify=settings.CERTIFICATE_VERIFY)
    
    try:
        import sys
        sys.stdout.flush()
        if bool(update_response.text):
            result = json.loads(update_response.text)["message"]
            logger.info(f"Results are {result}")
        else:
            result = "Success"
            if update_response.status_code == 200:
                logger.info(f"Update Thread Flag successful")
        sys.stdout.flush()

    except Exception as e:
        print("Error", update_response.text)
        logging.error(f"Error is {e} for {update_response.text}")
        raise e
    
    if settings.DEBUG:
        print(f"Thread Flagging was done to update thread flag of file: {file_name} with thread_status {thread_status}")
    
    return result