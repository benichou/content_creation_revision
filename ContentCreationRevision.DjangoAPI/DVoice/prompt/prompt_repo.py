########################################################################################################################
##                                 BELOW YOU MAY FIND THE LIST OF PROMPTS THAT ARE NEEDED TO SUPPORT DVOICE           ##
##                                        SUPPORTS BOTH REVISION AND CREATION                                         ##
##                                                                                                                    ##
##                                                                                                                    ##
########################################################################################################################


from DVoice.content_creation.bill_96_compliance_guidelines import get_bill_96_compliance_guideline

def read_markdown_file(file_path):
    """
    Reads the content of a markdown file and returns it as a string.

    :param file_path: Path to the markdown file.
    :return: Content of the markdown file as a string.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
    except IOError as e:
        print(f"Error reading the file: {e}")

GUIDELINE_SUMMARIZATION_PROMPT = """
                                 Your primary goal is to distill large volumes of information into\
                                 concise, clear, and accurate summaries, retaining only the most \
                                 critical facts, data, and insights. You excel at: \

                                 1. Fact-Preservation: Ensuring all key facts, statistics, and\
                                 essential details are accurately captured. \
                                 2. Table Handling: Extracting and organizing complex tables\
                                 , presenting data in a reader-friendly format without losing the intended meaning. \
                                 
                                 3. Illustrative Examples: Providing relevant and precise examples from the original \
                                content to enhance understanding and practical application. \
                                
                                4. Clarity and Coherence: Crafting summaries that are easy to understand \
                                while maintaining technical rigor. \
                                When summarizing, ensure that the structure is logical, \
                                content is contextually relevant, and the tone matches the original source. \
                                Your summaries are designed for professionals who rely on clear and factual 
                                insights to make informed decisions. \

                                Task: Summarize IN LESS THAN 200 WORDS the given MARKDOWN input text by adhering to the principles above, \
                                focusing on the most important facts, tables, and examples. \
                                Avoid redundancy, unnecessary elaboration, or loss of crucial information. \
                                Please generate the output in MARKDOWN output. \
                                """

GUIDELINE_EXTRACTION_PROMPT = """
                                 Your primary goal is to extract ALL information from an input text into\
                                 an output text close to perfectly similar to the input tet. You excel at: \

                                 1. Fact-Preservation: Ensuring all key facts, statistics, and\
                                 essential details are accurately captured. \
                                 2. Table Handling: Extracting and organizing complex tables\
                                 , presenting data in a reader-friendly format without losing the intended meaning. \
                                 
                                 3. Illustrative Examples: Providing relevant and precise examples from the original \
                                content to enhance understanding and practical application. \
                                
                                4. Clarity and Coherence: Crafting summaries that are easy to understand \
                                while maintaining technical rigor. \
                                When summarizing, ensure that the structure is logical, \
                                content is contextually relevant, and the tone matches the original source. \
                                Your summaries are designed for professionals who rely on clear and factual 
                                insights to make informed decisions. \

                                Task: EXTRACT the ENTIRETY OF THE given MARKDOWN input text by adhering to the principles above, \
                                focusing on the most important facts, tables, and examples. \
                                Avoid redundancy, unnecessary elaboration, or loss of crucial information. \
                                Please generate the output in MARKDOWN output. \
                                """

GUIDELINE_LAYOUT_REVISION_PROMPT = """
                                    Your primary goal is to improve the layout structure - ONLY WHEN THE INPUT MARKDOWN \
                                    HAS NO CLEAR TITLES/SUBHEADERS - of the input markdown text while \
                                    preserving the exact same text content in the body of the document. \
                                    
                                    Your specific responsibilities include: \

                                    1. Identify whether the document has no clear layout structure, meaning no headers, \
                                    titles, subtitles are present in the input markdown document. IF the document has \
                                    a clear layout, then do not alter the input markdown and regenerate it \
                                    exactly the same. If the input markdown has a clear layout, then skip the next \
                                    responsibilities and re-generate the input markdown text without any alterations \
                                    2. Title and Header Refinement: Rewriting titles, subtitles, headers, \
                                    and section names to ensure they are clear, engaging, and effectively \
                                    summarize the content they introduce. \
                                    3. Improved Readability: Breaking content into well-organized sections \
                                    and subsections, using headers and bullet points to enhance clarity and \
                                    reader navigation. \
                                    4. Bullet Point Optimization: Ensuring lists and bullet points are concise, \
                                    well-structured, and logically ordered. \
                                    5. Preserving Original Content: Leaving the main body text \
                                    (outside of titles, subtitles, headers, bullet points, and section names) \
                                    unchanged to maintain its original meaning and detail.\
                                    
                                    Task: Review the given text and revise its layout and structure as described above. \
                                    Focus on making the organization intuitive and reader-friendly while \
                                    preserving the integrity of the content. \
                                    Avoid modifying the main body text or introducing new content, and NEVER add \
                                    additional description. \
                                    
                                    Please generate the output in MARKDOWN output. 
                                                             
                                    
                                    """


OUTPUT_AFTER_LAYOUT_REVISION_PROMPT = f"""
                                      
                                      Given the above provided guideline: 
                                      
                                      Extract the content from 'page_content' without and put it in 'X'. \
                                      
                                     - While preserving the integrity of the content \
                                      , please conduct the task, already mentioned above, of revising the input text \
                                       layout and structure that is in 'X' following the above style guide \
                                       and assign the new content to 'Z'. \
                                     
                                     As final output please provide the following output as valid JSON, \
                                     without any code block formatting (do not include '```markdown'):\
                                     1. Please assign the value of 'Z' to the 'text_with_revised_layout' key. (IF PRESENT remove '- page_content:' at the beginning of the 'Z output')\
                                     
                                     """

                                    
CHUNK_CLASSIFICATION_PROMPT = """
                              Your task is to analyze a given markdown document and classify whether it is textual or not: \

                              1. Textual: If the document consists primarily/mostly of \
                              written paragraphs, sentences, and textual descriptions. \
                              2. Non-Textual: If the document consists primarily \
                              of visual elements such as images, pictures, charts, or tabular data, including \
                              markdown-formatted tables. \
                             
                             As final output please provide the following output as valid JSON, without any code block formatting: \
                             Your output should be a clear, binary assessment of whether the text is texttual or not. \
                             So, please provide your analysis as either 'True' or 'False' in the 'textual' key. \
                             [Note]: Ensure the value is a boolean type and not a string
                              """
## LOCAL SOLUTION IS FINE
writing_guideline_1 = read_markdown_file("DVoiceDjangoAPI\\DVoice\\guidelines\\summary_guidelines\\DVoice_summary_guideline_Param1_Writing Principles.md")

def manage_vanilla_guideline_prompt(md_markdown_guideline, style_guide_type = ""):
    VANILLA_GUIDELINE_PROMPT = f""" Given the provided input text, and as part of your text revision task, please \
                                    apply the following style guide to the input text {style_guide_type}. \
                                    Keep the content in its original input language. \
                                    Only apply the following style guide to non-tabular input text.
                                    Here is the style guide: \
                                
                                '{md_markdown_guideline}'
                                
                            """
    
    return VANILLA_GUIDELINE_PROMPT


GUIDELINE_WRITING_PRINCIPLES_PROMPT = manage_vanilla_guideline_prompt(writing_guideline_1, 
                                                                      style_guide_type = "that aims to create a \
                                                                      cohesive Content brand experience \
                                                                      in writing")
                                    
OUTPUT_AFTER_FIRST_REVISION_PROMPT = """
                                      
                                      Given the above provided guideline: 
                                      
                                      Extract the content from 'page_content' and put it in 'X'. \
                                    
                                      - Apply the following:
                                        - While keeping the same page content outline format provided and the 
                                       same underlying facts and ideas \
                                      , please rewrite and rephrase the content in 'X' \
                                      following the above style guide and assign the new content to 'Z'. 
                                      If there is no content in 'X' or 'X' == 'NOCONTENT', just assign 'NOCONTENT' to 'X' and 'Z'.

                                      As final output please provide the following output as valid JSON, without any code block formatting:
                                      1. Please assign the content from 'X' as final output and put it in 'original_text' key. (Do not add '- page_content:' at the beginning)\
                                      2. Please assign the value of 'Z' to the 'revised_text_step_1' key. (Do not add '- page_content:' at the beginning)

                                     """
## LOCAL SOLUTION IS FINE
writing_guideline_2 = read_markdown_file("DVoiceDjangoAPI\\DVoice\\guidelines\\summary_guidelines\\DVoice_summary_guideline_Param2_Referring to Content.md")
                                  

GUIDELINE_REFERRING_TO_Content_PROMPT = manage_vanilla_guideline_prompt(writing_guideline_2, 
                                                                         style_guide_type = """that aims to ensure Content as a brand name
                                                                                          is mentionned correctly in writing""")

OUTPUT_AFTER_SECOND_REVISION_PROMPT = """
                                      
                                      Given the above provided guideline: 
                                      
                                      Extract the content from 'original_text' and put it in 'X'. \
                                      Extract the content from 'revised_text_step_1' and put it in 'A'. \
                                      
                                      - Apply the following:
                                        - While keeping the same page content outline format provided and the 
                                       same underlying facts and ideas \
                                      , please rewrite and rephrase the content in 'A' \
                                      following the above style guide and assign the new content to 'Z'.\
                                      If there is no content in 'X' or 'A' or 'X' == 'NOCONTENT' or 'A' == 'NOCONTENT', just assign 'NOCONTENT' to 'X' and 'Z'.

                                      As final output please provide the following output as valid JSON, without any code block formatting:\
                                      1. Please assign the content from 'X' as final output and put it in 'original_text' key (Do not add '- page_content:' at the beginning) \
                                      2. Please assign the value of 'Z' to the 'revised_text_step_2' key. (Do not add '- page_content:' at the beginning)
                                     
                                     """
## LOCAL SOLUTION IS FINE
writing_guideline_3 = read_markdown_file("DVoiceDjangoAPI\\DVoice\\guidelines\\summary_guidelines\\DVoice_summary_guideline_Param3_Effective Writing Methods.md")
                                  


GUIDELINE_REFERRING_TO_EFFECTIVE_WRITING_PROMPT = manage_vanilla_guideline_prompt(writing_guideline_3, 
                                                                         style_guide_type = """that aims to ensure the development of good content \
                                                                                            through effective writing methods""")

OUTPUT_AFTER_THIRD_REVISION_PROMPT = """
                                      
                                      Given the above provided guideline: 
                                      
                                      Extract the content from 'original_text' and put it in 'X'. \
                                      Extract the content from 'revised_text_step_2' and put it in 'A'. \
                                      
                                      - Apply the following:
                                        - While keeping the same page content outline format provided and the 
                                       same underlying facts and ideas \
                                      , please rewrite and rephrase the content in 'A' \
                                      following the above style guide and assign the new content to 'Z'.
                                      If there is no content in 'X' or 'A' or 'X' == 'NOCONTENT' or 'A' == 'NOCONTENT', just assign 'NOCONTENT' to 'X' and 'Z'.
                                        
                                      As final output please provide the following output as valid JSON, without any code block formatting:
                                      1. Please assign the content from 'X' as final output and put it in 'original_text' key (Do not add '- page_content:' at the beginning) \
                                      2. Please assign the value of 'Z' to the 'revised_text_step_3' key. (Do not add '- page_content:' at the beginning)\
                                     
                                     """
## LOCAL SOLUTION IS FINE
writing_guideline_4 = read_markdown_file("DVoiceDjangoAPI\\DVoice\\guidelines\\summary_guidelines\\DVoice_summary_guideline_Param4_Editorial Style Guide .md")
 


GUIDELINE_REFERRING_TO_EDITORIAL_STYLE_GUIDE_PROMPT = manage_vanilla_guideline_prompt(writing_guideline_4, 
                                                                                  style_guide_type = """that serves as a style and usage guide \
                                                                                              that also serves as a dictionary of approved
                                                                                              terms""")

OUTPUT_AFTER_FOURTH_REVISION_PROMPT = """
                                      
                                      Given the above provided guideline: 
                                      
                                      Extract the content from 'original_text' and put it in 'X'. \
                                      Extract the content from 'revised_text_step_3' and put it in 'A'. \
                                      
                                      - Apply the following logic:
                                        - While keeping the same page content outline format provided and the 
                                       same underlying facts and ideas \
                                      , please rewrite and rephrase the content in 'A' \
                                      following the above style guide and assign the new content to 'Z'.
                                      If there is no content in 'X' or 'A' or 'X' == 'NOCONTENT' or 'A' == 'NOCONTENT', just assign 'NOCONTENT' to 'X' and 'Z'.
                                        
                                      As final output please provide the following output as valid JSON, without any code block formatting:
                                      1. Please assign the content from 'X' as final output and put it in 'original_text' key (Do not add '- page_content:' at the beginning) \
                                      2. Please assign the value of 'Z' to the 'revised_text_step_4' key. (Do not add '- page_content:' at the beginning)\
                                     
                                     """

OUTPUT_AFTER_FIFTH_REVISION_PROMPT = """
                                     
                                     Given the above provided guideline: 
                                      
                                      Extract the content from 'original_text' and put it in 'X'. \
                                      Extract the content from 'revised_text_step_4' and put it in 'A'. \
                                      
                                      - Apply the following logic:
                                        - While keeping the same page content outline format provided and the 
                                          same underlying facts and ideas \
                                          ,please rewrite and rephrase the content in 'A' following the last guide \
                                          style instructions provided above and assign the new content to 'Z'. \
                                          If there is no content in 'X' or 'A' or 'X' == 'NOCONTENT' or 'A' == 'NOCONTENT', just assign 'NOCONTENT' to 'X' and 'Z'.
                                          
                                      As final output please provide the following output as valid JSON, without any code block formatting:
                                      1. Please assign the content from 'X' as final output and put it in 'original_text' key (Do not add '- page_content:' at the beginning) \
                                      2. Please assign the value of 'Z' to the 'revised_text_step_5' key. (Do not add '- page_content:' at the beginning)\
                                    
                                     """

COMPARE_ORIGINAL_VS_NEW_TEXT_PROMPT = """
                      Your responsibility is to compare the 'Original' text with the 'Revised' text and list in bullet points\
                      all the modifications applied to the 'Original' text to make it better.
                      
                      """




MANUAL_INPUT_PROMPT = """
                      Your responsibility is to take the following input text and reorganize it into a Markdown format \
                      with a proper layout and thought structure. \
                      
                      As final output please provide the following output as valid JSON, without any code block formatting:
                      1. Take the reorganized text, following a markdown format and assign to 'parsed_manual_input' key.
                      
                      """

ADDITIONAL_CONTENT_GENERATION_PROMPT = """
                                       Your responsibility is to take the following user's query and generate a markdown \
                                       text that answer their requests, without any code block formatting: \
                                       
                                       """
                    
                    
ADDITIONAL_INSTRUCTION_CATEGORIZATION_PROMPT = """
                                                Given the submitted prompt, please identify whether \
                                                this prompt either requests modifying the existing text style, \
                                                or adding new paragraphs to the given text. \
                                                
                                                If the document requests to modify the existing text style, then say 'True'.
                                                If the document requests to add a new paragraph, then say 'False'.
                                                    
                                                As final output please provide the following output as valid JSON, without any code block formatting:
                                                1. So, please provide your boolean analysis as either 'True' or 'False' in the 'style_modification' key. \
                                                [Note]: Ensure the value is a boolean type and not a string
                                                """


INPUT_LANGUAGE_CLASSIFICATION_PROMPT = """
                              Your task is to analyze whether the user wants the output in French or English or both\
                              English and French when clearly specified (both French and English are required \
                              when the user asked for content in 'English and French' or \
                              when the input query states 'the output must be in 'EN/FR' or 'EN/FR'): \

                              1. language: 'FR' for French, 'EN' for English. \
                                If specified content should be in both English and French, provide the 'FR' and 'EN' in the list.
                                'EN/FR' should be ['EN', 'FR'] in the language key.
                             
                             As final output please provide the following output as a valid JSON, without any code block formatting: \
                             Your output should be a clear assessment of whether the language of input is 'FR' or/and 'EN' in a list. \
                             So, please provide your analysis as 'FR', 'EN' or both, in the 'language' key as a list. \
                                
                              """

INPUT_TRANSLATION_PROMPT = """
                           Your task is to translate the input markdown document and keep its exact content in a markdown format \
                           without any code block formatting in the following target language:
                           Only provide the translation and no additional commentary.
                           
                           
                           1. Target language:
                           """
INPUT_TRANSLATION_PARAMETER_PROMPT = """
                                      Your task is to translate the provided query parameter to its equivalent in English. \
                                      If the query parameter is already in english, leave it as is.
                                      Only provide the translation or the as-is input (where applicable) as a string output and no additional commentary
                                     
                                     """

INPUT_QUERY_BREAKDOWN_PROMPT = """
                        Your task is to break down the input query into one or multiple queries that are each associated to a clear final file output \
                        only where applicable. Keep any requests that require the creation of tabular data/table in the original request (do not break down table/tabular data requests). \
                        If the original query cannot be broken down, keep the origial query. \
                        If the original query requests to create information about more than 1 topic please address these several topics in the same query. \
                        For instance, if the request is to create output about <topic 1> and <topic 2> and ... <topic n>, \
                        then do not break down the query and keep it in the same string. \
                        But, If the original query intends to more than 1 output, break down the original query accordingly.
                        For instance, Please create X>1 <output type> about <topic_1> and <topic_2> should be broken down as:
                        1. Create 1 <output_type> about <topic_1>. 2. Create 1 <output_type> about <topic_2>.
                        Try to minimize breakding down the original query to a minimum. \
                        If the original query can be broken down make sure to keep the original intent and context still present in the new broken down queries \
                        Only provide the output without additional commentary under the 1. query_breakdown key. \
                        Note: Do not break down into multiple queries a query that aims to do the same thing across multiple files. \
                        

                        1. query_breakdown: a list of strings where each string is a broken down query or just the original query \
                        where applicable. Remove in each strings references to outside files.

                        As final output please provide the following output as a valid JSON, without any code block formatting: \
                        Your output should be the broken down query or the original query (when could not be broken down) in a list. \
                        So, please provide your analysis in a list. \

                        """

INPUT_QUERY_REWRITER_PROMPT = """
                       Your task is to re-phrase an original input query while keeping its original underlying intent. \
                       Given the input query, please follow the criteria below:

                       1. Criteria 1: Remove from the input query any and all instructions regarding \
                       the specific desired language for the output/response to said query. \
                       Example: anything asking for the output to be in French or English or EN/FR, or EN, or FR should simply
                       disappear from the input query
                       2. Criteria 2: Remove any references from the input query regarding \
                       canadianizing the content or applying bill 96 for the purpose to have both English and French content \

                       As final output, please generate the rewritten query in string format only.

                       """

INPUT_QUERY_REWRITER_CORE_ACTION_PROMPT = """
                                          Your task is to re-phrase an original input query while keeping its original underlying intent. \
                                          Given the input query, please follow the criteria below:

                                          1. Criteria 1: Make the input query action oriented and only keep elements that are \
                                          conducive to clarifying how to build the intented output response.
                                          2. Criteria 2: Remove from the input query any references to a particular file attachment \
                                          files or document that was submitted by the user. The input query needs to be action oriented \
                                          regardless of the document at stake.

                                          As final output, please generate the rewritten query in string format only.
                                          
                                          """

INPUT_BILL_96_COMPLIANCE_IDENTIFIER_PROMPT = f"""
                                      Your task is to identify whether the content to create should \
                                      comply with the Canadian bill 96. Compliance is required whenever it is \
                                      explicitly requested to comply with bill 96 or that it is explicitly requested \
                                      to have the content in both Engligh (EN) and French (FR). Otherwise, no compliance is \
                                      requested.
                                      Produce the analysis of your output as a boolean value: 
                                      True or False under the bill_96_requirement key.

                                      Some key requirements of bill 96 are: 
                                      {get_bill_96_compliance_guideline()}

                                      1. bill_96_requirement: <True> OR <False> 

                                      As final output please provide the following output as a valid JSON, without any code block formatting: \
                                      Your output should be a boolean key True or False \
                                      (not the string but the actual boolean) \

                                      """

INPUT_NUMBER_OF_OUTPUT_TO_GENERATE_PROMPT = """
                                     Your task is to identify whether the query intends to create only one file or several \
                                     files as output. Produce the analysis of your output as a boolean value: \
                                     True or False under the only_one_file key. \
                                     
                                     1. only_one_file = <True> OR <False>

                                     As final output please provide the following output as a valid JSON, without any code block formatting: \
                                     Your output should be a boolean key True or False \
                                     (not the string but the actual boolean) \

                                     """

INPUT_QUERY_INTENT_CLASSIFICATION_PROMPT = """
                                           Your task is to identify whether the intent of the query is to conduct rewriting \
                                           of some input content, summarization of the input content, or conducting a retrieval \
                                           to answer the question at hand. We define a query that has retrieval intent as any queries \
                                           that does not explicitly requests rewriting or summarization or also any queries that requests a \
                                           specific response output for a particular topic using a specific input file. \
                                           If the query requests to 're-write' some content, then it is rewriting. If that is not the case \
                                           and summarization is not explicitly requested, then determine it to be a retrieval. \
                                           
                                           Here are some additional examples for what we consider a summarization query:
                                           
                                          Example below of Summarization Queries for Content Creation:
                                          (These queries ask for condensed versions of content rather than looking up specific facts or documents.)
                                          1."Can you summarize this research paper on transformer architectures?"
                                          2. "Summarize the key takeaways from the latest earnings call of Tesla."
                                          3. "Provide a short summary from the attached book."
                                          4. "What were the main points of the last presidential debate in the attached document?"
                                          5. "Give me a concise summary of the events leading up to World War II."
                                          6. "Summarize the latest developments in AI ethics from the last 6 months."
                                          7. "Can you provide an overview of the Agile methodology?"
                                          8. "What is the key message of the UN’s climate change report?"
                                          9. "Summarize the most important findings from the recent study on deep learning interpretability."
                                          10. "What are the highlights of the recent keynote speech at the Apple event?"

                                          Example below of Retrieval Queries for Content Creation:
                                          (These queries focus on retrieving relevant information to assist in generating new content rather than summarizing existing text.)
                                          1. "Gather insights from past customer satisfaction reports to draft a new blog post."
                                          2. "Create a detailed document that encompasses key points from our product API documentation to update the user guide."
                                          3. "Compile case studies on AI adoption to construct a new industry whitepaper."
                                          4. "Locate internal research on automation trends to formulate an executive summary."
                                          5. "Pull transcripts from past leadership town halls to shape an internal newsletter."
                                          6. "Assemble previous cloud migration proposals to craft a new RFP."
                                          7. "Reference onboarding guides to enhance the employee training manual."
                                          8. "Analyze past competitor analyses to outline a new market trends report."
                                          9. "Scan expert interviews stored in our knowledge base to produce a thought leadership article."
                                          10. "Retrieve marketing campaign performance reports to structure a strategy briefing."
                                          11. "Review product feedback documents to generate an updated FAQ section."
                                          12. "Collect technical documentation on our AI models to create a developer blog post."
                                          13. "Summon past support ticket summaries to build a troubleshooting guide."
                                          14. "Survey internal presentations on cybersecurity best practices to draft a company blog post."
                                          15. "Extract insights from archived research papers on NLP techniques to compose a new whitepaper."

                                           The output of your final analysis will a boolean True or False provided to \
                                           each of the three keys below, describing if the intent of the query is either \
                                           summarization, rewriting or retrieval: 
                                     
                                          1. summarization = <True> OR <False>
                                          2. rewriting = <True> OR <False>
                                          3. retrieval = <True> OR <False>

                                     As final output please provide the following output as a valid JSON, without any code block formatting: \
                                     Your output should be a boolean key True or False assigned to each of the three keys \
                                     (not the string but the actual boolean) \

                                     """

def generate_prompt_files_identifier_for_retrieval_task(file_summaries, user_query, task_type):
    """
    """
    processed_summaries = ""
    for item in file_summaries:
        processed_summaries += "\n" + f"- '{item['title']}':" + f"'{item['summary']}'" + "\n"

    prompt_message = f"""Given the following below list of file name and summary pairs (that were provided by the user) like
                          - <file name 1>: summary for file name 1
                          - <file name 2>: summary for file name 2
                          - <file name 3>: summary for file name 3
                          -----------------------------------------------------------------
                          {processed_summaries}"""

    query = f""""Please identify the file or multiple files that support the following user query: {user_query} \
                          for the purpose of {task_type} .

                          Your task consists in listing the EXACT file name of the files that can support the user query \
                          for the specific purpose mentioned above. List the file or files as string values in the necessary_files key below:
                          
                          1. necessary_files: a list of strings where each string is one file name from the list (with no alteration and keeps extensions)

                          As final output please provide the following output as a valid JSON, without any code block formatting: \
                          Your output should be all necessary file name that support the task in a list. \
                          So, please provide your analysis in a list. \

                          """
    return prompt_message, query

INPUT_QUERY_RETRIEVER_QA = """
                           So, your task is to generate responses in markdown format to the question submitted by the user, following \
                           the tone and formatting parameters shared. \

                           As final output please provide the following output as a markdown response without any code block formatting. \

                          """

INPUT_QUERY_FILE_NAME = """
                           So, given the query provided by the user, please generate a concise name for the intended output associated with said query.
                           Do not provided any extension and simply provide a file name

                           As final output please provide the following output as a string without any code block formatting. \

                          """

