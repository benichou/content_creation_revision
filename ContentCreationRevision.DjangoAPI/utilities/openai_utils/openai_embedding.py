from django.conf import settings
# from django.conf import  QUERY_MODEL_ID_EMBEDDING, AZURE_OPENAI_BASE, AZURE_OPENAI_KEY
import requests 
import json
import time

def openai_create_embedding(question, token):

     while True:
        url = settings.API_BASE + f"/openai/deployments/{settings.EMBEDDING_DEPLOYMENT_NAME}/embeddings?api-version={settings.EMBEDDING_DEPLOYMENT_API_VERSION_DICTIONARY[settings.EMBEDDING_DEPLOYMENT_NAME]}"
        r = requests.post(url, headers={"Authorization": "Bearer " + token.token}, json={"input": question})
        j = json.loads(r.text)

        # Check for rate limit error
        if 'error' in j and j['error'].get('code') == '429':
            print("Rate limit exceeded. Timeout 1 minute.")
            time.sleep(60)  # Sleep for 60 seconds
            continue  # Retry after the sleep
        elif 'error' in j:
            print("Error:", j)
        try:
            return j['data'][0]['embedding']
        except:
            print(f"EMBEDDINGS ERROR:{j}")
            return j['data'][0]['embedding']

