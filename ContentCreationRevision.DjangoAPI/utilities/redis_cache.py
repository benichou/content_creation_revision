import redis
import json
from django.conf import settings
class RedisCache:

    def __init__(self, token) -> None:
        # Create a Redis client instance

        if settings.REDIS_LOCAL:
            self._client = redis.Redis(host=settings.REDIS_LOCAL_URL, port=settings.REDIS_PORT)
        else:
            self._client = redis.StrictRedis(
                host=settings.REDIS_HOST_NAME,
                port=settings.REDIS_PORT, 
                db=0, 
                password=settings.REDIS_SECRET_KEY, 
                ssl=True,
            )

    def set_user_data(self, data, username):
        
        cached_data = self._client.get(username)
        

        if cached_data:
            cached_data = json.loads(cached_data.decode('utf-8'))
            cached_data = cached_data + data  
            
            self._client.set(username, json.dumps(cached_data))
        else:
            self._client.set(username, json.dumps(data))
        


    def get_user_data(self, username):
        cached_data   = self._client.get(username)
        if cached_data is None:
            raise RuntimeError("Documents must be uploaded before requesting information.")
        
        cached_data   = json.loads(cached_data.decode('utf-8'))
        return cached_data
    
    def delete_by_title(self, username, title):
        
        cached_data   = self._client.get(username)
        cached_data   = json.loads(cached_data.decode('utf-8'))
        filtered_data = [item for item in cached_data if item.get('title') != title]
        self._client.set(username, json.dumps(filtered_data))

    def delete_user(self, username):
        self._client.delete(username) 