from django.conf import settings
import requests
import json
# from langchain.chat_models import AzureChatOpenAI
from langchain_openai import AzureChatOpenAI

import os

def instantiate_llm_client(token,
                           selected_model,
                           temperature_task,
                           ):
    """
    
    """
    llm  = AzureChatOpenAI(
            openai_api_version = settings.API_VERSION,
            temperature        = temperature_task, 
            deployment_name    = settings.MODEL_DICTIONARY[selected_model],
            azure_ad_token     = token.token,
            azure_endpoint     = settings.API_BASE,
            max_tokens         = settings.MODEL_MAX_OUTPUT_SIZE[selected_model],
            model              = settings.MODEL_NAME_DICTIONARY[selected_model]  
        )
        
    return llm

def get_gpt35_completion(messages, token, func=None):

    url = settings.API_BASE + f"/openai/deployments/{settings.TEXT_MODEL_GPT3_5}/chat/completions?api-version={settings.API_VERSION}"
    
    r_chatGPT = requests.post(url, headers={ "Authorization": "Bearer " + token.token}, json={
        "messages"   : messages,
        "temperature": 0,
        "max_tokens" : settings.MAX_COMPLETION_LEN,
       
        
    })
    parsed_json = json.loads(r_chatGPT.text)

    if "error" in parsed_json:
        raise Exception(f"OpenAI API Error: {parsed_json['error']['message']}")
    
    return parsed_json['choices'][0]["message"]["content"]

def get_gpt4_8k_completion(messages, token, func=None):

    url = settings.API_BASE + f"/openai/deployments/{settings.TEXT_MODEL_GPT4_8K}/chat/completions?api-version={settings.API_VERSION}"
   
    r_chatGPT = requests.post(url, headers={ "Authorization": "Bearer " + token.token}, json={
        "messages"   : messages,
        "temperature": 0,
        "max_tokens" : settings.MAX_COMPLETION_LEN,
        
        
    })
    parsed_json = json.loads(r_chatGPT.text)

    if "error" in parsed_json:
        raise Exception(f"OpenAI API Error: {parsed_json['error']['message']}")
    
    return parsed_json['choices'][0]["message"]["content"]
#
def get_gpt4_32k_completion(messages, token, func=None):

    url = settings.API_BASE + f"/openai/deployments/{settings.TEXT_MODEL_GPT4_32K}/chat/completions?api-version={settings.API_VERSION}"
   
    r_chatGPT = requests.post(url, headers={ "Authorization": "Bearer " + token.token}, json={
        "messages"   : messages,
        "temperature": 0,
        "max_tokens" : settings.MAX_COMPLETION_LEN,
       
        
    })
    parsed_json = json.loads(r_chatGPT.text)

    if "error" in parsed_json:
        raise Exception(f"OpenAI API Error: {parsed_json['error']['message']}")
    
    print(parsed_json['usage'])
    return {"responce": parsed_json['choices'][0]["message"]["content"], "usage" : parsed_json['usage']}

from typing import List, Dict, Any
 
def get_gpt_completion(messages: List[Dict[str, Any]], 
                       token: str, 
                       selected_model: str) -> Dict[str, Any]:
    """
    Sends a request to the OpenAI API to get a GPT completion based on the provided messages and model.
 
    Args:
        messages (List[Dict[str, Any]]): A list of message dictionaries containing the conversation history.
        token (str): The API token used for authentication.
        selected_model (str): The model to use for generating completions, specified by its key in the settings.
 
    Raises:
        Exception: Raised if the OpenAI API returns an error in the response.
 
    Returns:
        Dict[str, Any]: The parsed JSON response from the OpenAI API containing the completion results.
    """
 
    url = settings.API_BASE + f"/openai/deployments/{settings.MODEL_DICTIONARY[selected_model]}/chat/completions?api-version={settings.API_VERSION_MODEL_DICTIONARY[selected_model]}"
    r_chatGPT = requests.post(url, headers={ "Authorization": "Bearer " + token.token}, json={
        "messages"   : messages,
        "temperature": 0,
        "max_tokens" : settings.MODEL_MAX_OUTPUT_SIZE[selected_model],

    })
    parsed_json = json.loads(r_chatGPT.text)
    if "error" in parsed_json:
        raise Exception(f"OpenAI API Error: {parsed_json['error']['message']}")
    return parsed_json


def get_prompt_category(_token, messages, func=None):

    url = settings.API_BASE + f"/openai/deployments/{settings.TEXT_MODEL_GPT3_5}/chat/completions?api-version={settings.API_VERSION}"
    
    r_chatGPT = requests.post(url, headers={ "Authorization": "Bearer " + _token.token}, json={
        "messages"   : messages,
        "functions"  : func
        
    })
    parsed_json = json.loads(r_chatGPT.text)

    if settings.DEBUG:
        print("parsed_json", parsed_json)

    if "error" in parsed_json:
        raise Exception(f"OpenAI API Error: {parsed_json['error']['message']}")
    
    try:
        if "function_call" in parsed_json["choices"][0]["message"]:
            return json.loads(parsed_json["choices"][0]["message"]["function_call"]["arguments"])["type"]
        else: 
            return parsed_json["choices"][0]["message"]["content"]
    except:
        if settings.DEBUG:
            print("openai call failed - summarization backup occured")
        return "Summarization"

