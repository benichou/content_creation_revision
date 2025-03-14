from django.conf import settings
system_prompt = """You are an expert in text analysis. Your primary task is to help users understand the content in multiple texts. Provide clear, concise, and actionable insights. If the content provided does not answer the question. Respond with 'The content provided does not contain the answer to your question.'"""

header = f"""
**Prompt**

Your mission is to accurately respond to a user's query by utilizing the provided content and nothing else.

- **Objective:** 
  - Address the user’s question, focusing specifically on the information given.
  - Ensure answers adhere strictly to the provided material, without incorporating external knowledge or assumptions. 
  - No additional research tools, pretrain data or databases should be utilized.
  
- **Understanding the Question:**
  - Identify main components and potential sub-questions related to the provided content.
  
- **Formulating a Response Plan:**
  
  1. **Distill the Essence of the Question:**
     - Focus on the specific aspects of the provided content that the question addresses.
     
  2. **Establish a Strategy:**
     - Explore the text thoroughly to find relevant information.
     - If the content provided does not answer the question, ALWAYS Respond with "NODOCUMENTS"
     - Construct a well-informed reply based on the identified information.
     
  3. **Generate a Step-by-step Plan:**
     - Analyze the text.
     - Identify pertinent information.
     - Compile a comprehensive answer using the identified information.
  4. **Response**
     - make sure to return a response to the user that contains the comprehensive answer.
     
"""

classfication_prompt = """
You must classify the following user input into one of two categories and only two categories: Summarization or Q&A. 



Based on the content and intent of the user's input, determine whether it is a request for a summary of information or a specific question seeking an answer.

I need top 10 benefits of using old manufaturing system for producing Iron->Summarization\n\n 
In the research papers I uploaded about ocean pollution, is there a discussion on the effectiveness of recent clean-up initiatives?->Q&A\n\n
I have uploaded two articles on the evolution of smart cities. Can you identify and provide me with the top key points from both documents?->Summarization\n\n
These documents discuss the impact of climate change on agriculture. Can you boil down their content to a brief summary of key points? -> Summarization\n\n
Do the documents on nutrition and mental health link certain diets to improvements in cognitive function? -> Q&A\n\n
I have two company reports on market trends in the tech industry. Summarize the major insights and predictions for future trends from both documents. -> Summarization\n\n
Is there information in the uploaded texts about the historical development of quantum computing? -> Q&A\n\n
These two documents on psychological impacts of social media: do they mention any age group particularly affected? Can you provide details? -> Q&A\n\n
The documents I uploaded are about recent advancements in renewable energy. Can you summarize their perspectives on solar energy's potential impact? -> Summarization\n\n
Can you clarify if the articles on urban wildlife conservation detail specific strategies for species protection in metropolitan areas? -> Q&A\n\n
Please distill the main arguments presented in these two journals on renewable energy policy. -> Summarization\n\n
Do they address the economic viability of organic farming methods compared to conventional ones? -> Q&A\n\n
Is there a comparison of AI's role in safety features between different car models? -> Q&A\n\n
Here are two essays on educational reforms. Please extract the key arguments and conclusions presented in these essays. -> Summarization\n\n
I need a rundown of the most critical insights from these two case studies on educational technology. What are the main takeaways? -> Summarization\n\n
What do the two case studies say about the impact of remote working on employee productivity? -> Q&A\n\n
Please provide the main themes and any contrasting viewpoints. -> Summarization\n\n
What are these documents talk about -> Summarization\n\n
How many employees are mentioned in thsi excel file -> Summarization\n\n
How many employees are mentioned in the uploaded file -> Summarization\n\n
How many employees have available leaves greater than 10 -> Summarization\n\n
who are top most employees earning more than 100000 -> Summarization\n\n
I've uploaded two academic articles on blockchain technology. Could you summarize the key findings and any common methodologies used in both papers? -> Summarization\n\n
The articles I uploaded discuss climate change effects on coastal regions. Do they mention specific mitigation strategies being implemented? What are they? -> Q&A\n\n
In these two papers on space exploration technology, is there an analysis of the cost-effectiveness of reusable rockets? -> Q&A\n\n
Could you extract the essential themes and findings from the pair of reports I've uploaded on global economic trends? -> Summarization\n\n
"""

classfication_system_prompt ="""Classify the following user inputs into one of two categories: Summarization or Q&A. Based on the content and intent of the user's input, determine whether it is a request for a summary of information or a specific question seeking an answer."""

summarize_prompt = "provide a short summary on the following document"

function_category = {
            "name": "category",
            "description": "type of category, it is either Summarization or Q&A",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "category": "string",
                        "description": "Summarization or Q&A"
                    },
                },
                "required": ["category"]
            }
        }

regeneration_prompt = """
            Convert the following content into Markdown format (without any code block formatting) while preserving its original structure and meaning. \
            Ensure that: \
            The text has any sensitive components removed. We define senstive components as components that can force content filtering to break text generation.
            The text remains professionally structured with appropriate headings, bullet points, and paragraphs for clarity. \
            The tone is neutral and informative, avoiding speculative or alarmist language. \
            The phrasing avoids direct instructions or commands (e.g., "You must act now"), opting for softer alternatives \
            (e.g., "Organizations should consider"). \
            The content is free of casual filler words ("you know," "or whatnot") and avoids redundancy for readability. \
            Any references to uncertain future events are framed cautiously (e.g., "There is a possibility that tariffs may change" \
            instead of "Tariffs will increase dramatically"). \
                                            
                      """


