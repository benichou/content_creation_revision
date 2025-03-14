import tiktoken
from django.conf import settings
from transformers import GPT2Tokenizer
from utilities.openai_utils.summarize import MapReduce
from utilities.openai_utils.prompt import header, classfication_prompt, function_category, classfication_system_prompt
from utilities.openai_utils.models import get_prompt_category, get_gpt4_32k_completion, get_gpt_completion
# Define a custom sorting function

def answer_query_with_summarization(data, user_prompt, 
                                    selected_model, 
                                    no_docs=False, 
                                    task_type="SUMMARIZATION",
                                    summarization_at_chunk_level=True):
    
    sorted_sections = sorted(data, key=custom_sort)
    summarize = MapReduce(selected_model=selected_model,task_type=task_type, 
                          summarization_at_chunk_level=summarization_at_chunk_level)
    return summarize.use_mapreduce(user_prompt, sorted_sections, no_docs)
    
def get_token_count(text, selected_model):
    encoding = tiktoken.get_encoding("o200k_base")# tiktoken.get_encoding(settings.COUNT_ENCODING_BASE_DICTIONARY[selected_model])
    token_count = len(encoding.encode(text))
    return token_count

# def get_token_count(text):
#      tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
#      return len(tokenizer.encode(text))


def _get_prompt_sections(most_relevant_document_sections, selected_model):

    """
    Keep track of the selected documents: text, length, and index
    """
    chosen_sections = []
    position = 1
    """
    token length for SEPARATOR
    """
    separator_token_len = 3

    """
    retrive the most relevant documents to the user's question. 
    We are reversing the array so heighest score section is at beginning of the array.
    """
    
    documents_found = most_relevant_document_sections["documents"][0]
    found_distance  = most_relevant_document_sections["distances"][0]
    found_metadata  = most_relevant_document_sections["metadatas"][0]

    """
    Track the score of the closest document. This score is located at location 0 of most_relevant_document_sections
    """
    
    context_window_size = 128000 # settings.MODEL_CONTEXT_WINDOW_SIZE[selected_model] # TODO : to reinstate once in dev
    total_token_count = 0
    
    if len(found_distance) > 0:
        lowest_distance = found_distance[0]
    

    """
    Loop through the documents and save the document if:
        get document text from df based on section_index  
        document combine length is less than MAX_PROMPT_LEN
        current document score is greater than .75 and it is within .15 of top score.
        append all documents together that satisfy the above criteria.
    """
    
    for section_index, distance in enumerate(found_distance):
        
        if total_token_count > min(context_window_size, context_window_size * 0.25): #settings.CONTEXT_WINDOW_SIZE_CUTOFF): # TODO: to reinstate once in local dev
            break
        document_section = documents_found[section_index]
        section_token_count = get_token_count(document_section, selected_model) + separator_token_len
        
        
        """
        Get docs that are greater than 50% probability and withing 15% range from top score.     
        """  
        ## TODO: need to inspect this and maybe apply re-ranker later on this     
        # if settings.DEBUG:
        #     print("BREAKCONDITION", distance, ">",.60, distance > .60, "or ABS(",lowest_distance, "-", distance, ")> .15", abs(lowest_distance - distance) > .15)
        #     print( distance > .60 or abs(lowest_distance - distance) > .15)
        # if distance > .60 or abs(lowest_distance - distance) > .15:
        #     break
        
            
        chosen_sections.append({
            "text"  : "\n*" + document_section, # settings.SEPARATOR + document_section,
            "id"    : found_metadata[section_index]["id"] ,
            "score" : distance,
            "title" : found_metadata[section_index]["title"]
        })
        total_token_count += section_token_count
        position+=1
    # Sort the chosen_sections array using the custom sorting function
    sorted_sections = sorted(chosen_sections, key=custom_sort)
    joined_text = " ".join([section["text"] for section in sorted_sections])
    titles = [x["title"] for x in sorted_sections ]
    titles_set = set(titles)
    context_sections  = [section["text"] for section in sorted_sections]
    return (joined_text, titles_set, context_sections)

def answer_query_with_context(question, closest_docs, token, selected_model):

    """
    get prompt header and relevant documets 
    """
    chosen_sections, titles, context_sections  = _get_prompt_sections(closest_docs, selected_model)

    """
    Set ChatGPT prompt and get answer based on chatGPT pretrain data. 
    """
    chatGPT_system_prompt ="""
    You are an advanced chatbot for internal company use. 
    Your primary goal is to assist users to the best of your ability. 
    This will involve answering questions and providing helpful information in the same language as the question.
    
    If the answers have hyperlinks, dont repeat them.
    In order to effectively assist users, it is important to be detailed and thorough in your responses.
    """
    token_count_prompt = 0
    token_count_completion = 0
    
    """
    Only use openai if Content documetns are retrived. 
    If no documetns are retrieved then Content response will be an empty string.
    """
    if chosen_sections:


        """
        Generated the prompt for Content questions.
        """
        prompt =  header + f"**\nContent:**\n{chosen_sections}" + "\n\n **Question:** " + question  +"**Answer:**"       
        
        """
        Get answer based on Content documents.
        """ 
        message = []
        message.append({
            "role": "system",
            "content" : chatGPT_system_prompt
        })
        message.append({
            "role": "user", 
            "content": prompt
        })

        # model_responce          = get_gpt4_32k_completion(Content_message, token)
        raw_response            = get_gpt_completion(message, token, selected_model)
        response                = raw_response["choices"][0]["message"]["content"]
        token_count_prompt      = raw_response["usage"]["prompt_tokens"]
        token_count_completion  = raw_response["usage"]["completion_tokens"]

    
    else:
        response                = settings.NO_DOCS_FLAG
        # moderated_question = question
        

    """
    structure and return string with Pretrain model answer and answer generated based on relevant Content documents. 
    """
    return {
                "text"                   : response,
                "token_count_prompt"     : token_count_prompt,
                "token_count_completion" : token_count_completion,
                "titles" : titles,
                "context" : context_sections
            }          

def get_classification(_token, prompt, selected_model):
    
    message = []
    prompt_message = f"{classfication_prompt}\n{prompt}->"
    message.append({
        "role": "system",
        "content": classfication_system_prompt
    })
    message.append({
        "role": "user", 
        "content": prompt_message
    })

    function =[
        function_category,
    ]

    category               = get_prompt_category(_token, message, function)
    token_count_prompt     = get_token_count(classfication_system_prompt, selected_model) + get_token_count(prompt_message, selected_model)
    token_count_completion = get_token_count(category, selected_model)

    return  {
             "category"               : category,
             "token_count_prompt"     : token_count_prompt, 
             "token_count_completion" : token_count_completion
            }


def custom_sort(item):
    prefix, number = item["id"].split("|")
    return (prefix, int(number))