##################################################################################################################
## Definition of Structured Output in LLMs
# # Structured output in Large Language Models (LLMs) refers to responses that follow a predefined format or 
# # schema, such as JSON, XML, YAML, or other structured data representations. Instead 
# # of generating free-text responses, the model produces outputs that adhere to a 
# # predictable structure, making them easier to parse and integrate into automated systems.
# # For example, instead of generating a plain text answer:
# # Unstructured Output (Free Text)
# # "The user's name is John Doe, and they are 29 years old, living in New York."
# # A structured output would look like:
# # Structured Output (JSON Format)
# # {
# #   "name": "John Doe",
# #   "age": 29,
# #   "location": "New York"
# # }
##

# # Why Are Structured Outputs Useful?
# # Structured outputs are beneficial in many scenarios, 
# # especially when LLMs are used in production applications that require automation, 
# # integration, or downstream processing.

##################################################################################################################

from pydantic import BaseModel, Field
from typing import List
# Define your desired data structure.

## BELOW are STRUCTURED OUTPUT CLASSES USED FOR PROMPT ACTIONS AND OTHER LLM ACTIONS

class PromptCategorizationParser(BaseModel):
    style_modification : str = Field(description="Identifies whether the prompt aims to modify the style of the document")

class ManualInputParser(BaseModel):
    parsed_manual_input : str = Field(description="Captures the slightly reorganized manual input")

class LayoutParser(BaseModel):
    text_with_revised_layout: str = Field(description="Captures the text with the revised layout")

class TextualClassificationOrNot(BaseModel):
    textual: bool = Field(description="Captures the summary")

class LanguageCategorization(BaseModel):
    language: List[str] = Field(description="Identifies whether the input language (that determines the output language) is 'FR' or 'EN'")

class BrokenDownQueries(BaseModel):
    query_breakdown: List[str] = Field(description="Lists the broken down parts of the query or the original query if it could not be broken down further")

class Bill96Compliance(BaseModel):
    bill_96_compliance: bool = Field(description="Describes True or False whether the query must comply with the bill 96 in Canada")

class NumberOfOutputFiles(BaseModel):
    only_one_file: bool = Field(description="Describes True or False whether only one file is ot be generated as output")

class QueryIntent(BaseModel):
    summarization: bool = Field(description="Describes True or False whether the intent is to summarize")
    rewriting: bool = Field(description="Describes True or False whether the intent is to rewrite the input content")
    retrieval: bool = Field(description="Describes True or False whether the intent is to retrieve particular content to answer the question")

class ListFiles(BaseModel):
    file_list: List[str] = Field(description="Lists the files that supports the query submitted by the user")


## BELOW are STRUCTURED OUTPUT CLASSES USED FOR REVISION
    
class Guideline1Parser(BaseModel):
    original_text:               str = Field(description="Captures the original chunk text before the application of the guideline")
    revised_text_step_1:         str = Field(description="Captures the revised text after the application of the first guideline")
    
class Guideline2Parser(BaseModel):
    original_text:               str = Field(description="Captures the original chunk text before the application of the guideline")
    # revised_text_step_1:         str = Field(description="Captures the revised text after the application of the first guideline")
    revised_text_step_2:         str = Field(description="Captures the revised text after the application of the second guideline, coming already from the output of the first revision")

class Guideline3Parser(BaseModel):
    original_text:               str = Field(description="Captures the original chunk text before the application of the guideline")
    # revised_text_step_1:         str = Field(description="Captures the revised text after the application of the first guideline")
    # revised_text_step_2:         str = Field(description="Captures the revised text after the application of the second guideline, coming already from the output of the first revision")
    revised_text_step_3:         str = Field(description="Captures the revised text after the application of the third guideline, coming already from the output of the second revision")

class Guideline4Parser(BaseModel):
    original_text:               str = Field(description="Captures the original chunk text before the application of the guideline")
    # revised_text_step_1:         str = Field(description="Captures the revised text after the application of the first guideline")
    # revised_text_step_2:         str = Field(description="Captures the revised text after the application of the second guideline, coming already from the output of the first revision")
    # revised_text_step_3:         str = Field(description="Captures the revised text after the application of the third guideline, coming already from the output of the second revision")
    revised_text_step_4:         str = Field(description="Captures the revised text after the application of the fourth guideline, coming already from the output of the third revision")

class GuidelinesWithAdditionalUserInstructionsParser(BaseModel):
    original_text              : str = Field(description="Captures the original chunk text before the application of the guideline")
    # revised_text_step_1:         str = Field(description="Captures the revised text after the application of the first guideline")
    # revised_text_step_2:         str = Field(description="Captures the revised text after the application of the second guideline, coming already from the output of the first revision")
    # revised_text_step_3:         str = Field(description="Captures the revised text after the application of the third guideline, coming already from the output of the second revision")
    # revised_text_step_4        : str = Field(description="Captures the revised text after the application of the fourth guideline, coming already from the output of the fourth revision")
    revised_text_step_5        : str = Field(description="Captures the rationale behind the revision of the text as per additional user instructions where applicable | step 5 is indeed for additional user instructions")# final revised_text_step if additional instructions are applied