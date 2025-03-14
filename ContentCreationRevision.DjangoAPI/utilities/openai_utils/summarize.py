from functools import partial
from django.conf import settings
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential
from langchain.chains.combine_documents import collapse_docs, split_list_of_docs
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain.schema.prompt_template import format_document
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
# from langchain.chat_models import AzureChatOpenAI
from langchain.schema import Document
import sys

from utilities.openai_utils.models import instantiate_llm_client
from utilities.openai_utils.prompt import regeneration_prompt

# Prompt and method for converting Document -> str.


class MapReduce:

    def __init__(self, selected_model, task_type, summarization_at_chunk_level):
        default_credential = ChainedTokenCredential(AzureCliCredential(), DefaultAzureCredential())
        token = default_credential.get_token(settings.COGNITIVE_SERVICES_URL) ## get the token to Access Azure resources
        temperature_task = settings.MODEL_TEMPERATURE_BY_TASK[task_type] ## set the temperature -- usually 0 - for the generative ai task
        
        self.llm = instantiate_llm_client(token, selected_model, temperature_task)
        self.summarization_at_chunk_level = summarization_at_chunk_level ## determines to summarize at the chunk level or document level. Chunk level means that the document chunk are first summarized and then use to create the final summary

        self.total_request_tokens  = 0
        self.total_response_tokens = 0
        
    def use_mapreduce(self, prompt, data, no_docs=False):

        # The chain we'll apply to each individual document.
        # Returns a summary of the document.
        document_prompt = PromptTemplate.from_template("{page_content}")
        self.partial_format_document = partial(format_document, prompt=document_prompt)

        docs = []
        for elm in data:
            docs.append(
                Document(
                page_content=elm["text"],
                metadata={"source": elm["title"]},
            ))
        if self.summarization_at_chunk_level:
            map_chain_prompt = "Summarize this content"
        else:
            # if we choose not to summarize at the chunk level, we then just preserve the chunk and
            # rephrase it a bit to ensure it does not trigger a content management filtering policy bug
            map_chain_prompt = regeneration_prompt 
        map_chain = (
            {"context":self. partial_format_document}
            | PromptTemplate.from_template(map_chain_prompt + ":\n\n{context}")
            | (lambda prompt: self._custom_llm_invoke(prompt))
            | StrOutputParser()
        )

        # A wrapper chain to keep the original Document metadata
        map_as_doc_chain = (
            RunnableParallel({"doc": RunnablePassthrough(), "content": map_chain})
            | (lambda x: Document(page_content=x["content"], metadata=x["doc"].metadata))
        ).with_config(run_name="Summarize (return doc)")

        end_prompt = ""
        if no_docs:
            if settings.DEBUG:
                print("No documents found, summary is being processed with added prompt")
            end_prompt = """ If the question clearly demands information not present or implied in the context, respond with 'The content provided does not contain the answer to your question.'"""


        reduce_chain = (
            {"context": self._format_docs}
            | PromptTemplate.from_template("{context}" + f"""\n\nBased on the above context, complete the following task or question '{prompt}'.{end_prompt}""")
            | (lambda prompt: self._custom_llm_invoke(prompt))
            | StrOutputParser()
        ).with_config(run_name="Reduce")
        # The final full chain
        map_reduce = (map_as_doc_chain.map() | self._collapse | reduce_chain).with_config(
            run_name="Map reduce"
        )

        response = map_reduce.invoke(docs, config={"max_concurrency": 5})



        return  {
                    "text":response, 
                    "token_count_prompt": self.total_request_tokens,
                    "token_count_completion":  self.total_response_tokens
                }

    def _custom_llm_invoke(self, prompt):
        response = self.llm.invoke(prompt)
        request_tokens = self.llm.get_num_tokens(prompt.to_string())
        response_tokens = self.llm.get_num_tokens(response.content)
        self.total_request_tokens += request_tokens
        self.total_response_tokens += response_tokens
        return response
    

    def _format_docs(self, docs):
        return "\n\n".join(self.partial_format_document(doc) for doc in docs)
    
    def _collapse(self, docs, config, token_max=10_000,):

        collapse_chain = (
            {"context": self._format_docs}
            | PromptTemplate.from_template("Collapse this content:\n\n{context}")
            | (lambda prompt: self._custom_llm_invoke(prompt))
            | StrOutputParser()
        )

        collapse_ct = 1
        while self._get_num_tokens(docs) > token_max:
            config["run_name"] = f"Collapse {collapse_ct}"
            invoke = partial(collapse_chain.invoke, config=config)
            split_docs = split_list_of_docs(docs, self._get_num_tokens, token_max)
            docs = [collapse_docs(_docs, invoke) for _docs in split_docs]
            collapse_ct += 1
        return docs
    

    def _get_num_tokens(self, docs):
        return self.llm.get_num_tokens(self._format_docs(docs))