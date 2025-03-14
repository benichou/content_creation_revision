import chromadb
from django.conf import settings

class ChromaDBHandler:


    def __init__(self):
        """
        Initialize the ChromaDB handler.
         Create a new collection named 'collection' and add data from the provided dataframe.
        """
        self._chroma_client = chromadb.Client()
        self.collection = self._chroma_client.get_or_create_collection(name=settings.COLLECTION_NAME)


    def add_document(self, df):
        """
        Args:
            df (pd.DataFrame): Dataframe containing data to be added to the collection.
                               The dataframe is expected to have columns 'Topic Body', 'Object', 
                               and 'embeddings'.

        Returns:
            tuple: A tuple containing the chroma client and the created collection.
        """
        content    = df['text'].tolist()
        metadata   = df.apply(lambda row: {'title':row['title'],'id': row['id'], 'n_tokens': row['n_tokens']}, axis=1).tolist()
        index      = [str(i) for i in  df.index.tolist()]
        embeddings = df['embedding'].tolist()


        self.collection.add(
            documents=content,
            metadatas=metadata,
            ids=index,
            embeddings=embeddings
        )
    

    def delete_collection(self):
        """
        Delete the collection.
        """
        self._chroma_client.delete_collection(name=settings.COLLECTION_NAME)
         
    def get_docs(self, query_embedding):

        results = self.collection.query(
            n_results=20,
            query_embeddings = query_embedding
        )
        return results



