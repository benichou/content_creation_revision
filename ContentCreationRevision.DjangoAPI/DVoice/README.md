
<a name="readme-top"></a>

 
<!-- PROJECT LOGO -->
<div align="center">
    <img
    style="display: block;
           margin-left: auto;
           margin-right: auto;
           width: 30%;"
    src="https://github.com/benichou/content_creation_revision/blob/main/ContentCreationRevision.DjangoAPI/DVoice/assets/img/dvoice_repo_img.png"
    alt="Our logo">
    </img>
 
  <h3 align="center">Content Voice Creation & Revision Agent</h3>
 
  <p align="center">
    Repository Documentation for the Content Voice Creation and Revision Agent.

   
</div>
 
## Table of Contents
 
<!-- TABLE OF CONTENTS -->
<details>
  <summary>Click to Expand</summary>
  <ol>
    <li>
      <a href="#about-the-repo">About The Repo</a>
      <ul>
        <li><a href="#repository-structure">Repository Structure</a></li>
        <li><a href="#repository-structure-analysis">Repository Structure Analysis</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#revision-history">Revision History</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>
 
<!-- ABOUT THE PROJECT -->
## About The Repo
 
This repo aims to build the base capabilities to:
1. Create new content (executive summary, social media post) or
2. Revise existing content.
 
The solution is called DVoice (aka Content Voice), because it tried to create documents following a standarized Content style policy.

We have 4 static guidelines around different components of language and document style in the following folder: ContentCreationRevision.DjangoAPI\DVoice\guidelines\summary_guidelines
We use them through prompt engineering and Langchain Expression Language to ensure content creation and revision respects Content Standards.
 
For version `0`, base parsing, markdown extraction, summarization, retrieval, and direct LLM generation capabilities have been added with
docx rendering, while striving to find the best spot between latency, accuracy and content relevance. 

No LLM Fine tuning was conducted on a specific LLM given this is a first release. Later on, and with access to more data (synthetically generated or not)
LLM fine tuning could help create an LLM with a Content Canada style.

### - Note about the Creation Module:
- a. Supports Generation of content for multiple queries sent at the same time
- b. Supports up to 5 reference files (pdf, docx, txt formats for now) in an in memory chroma db knowledge base and filters the knowledge base dynamically based on query intent
- c. Supports Content Generation in French and English, Supports Table Generation from Reference Files
- d. Supports identification of bill 96 compliance
- e. Supports `summarization`, `rewriting`, and `retrieval` (aka more Q&A type of query) tasks
- f. Supports Content Generation through direct LLM Call
- g. Supports the creation of Executive Summary, Social Media Posts and other content types, to different audiences, with different content length sizes, catered to different medium
- h. Does not support Image generation
- i. Leverages the core functionalities from revision to standardize output to Content style guideline
- j. Renders the output/outputs into a unique docx file.

### - Note about the Revision Module:
- a. Supports revision of any txt, pdf, docx files of any lengths. Revising a pdf document of 150 pages in its entirety while losing little of its content is possible 
- b. Allows the user to submit additional instructions to apply an additional style guide or create some basic new content
- c. Does not revise the existing tables from the uploaded file
- d. Renders the output/outputs into a unique docx file.

Finally, most chunking, content creation and revision functional steps are conducted async to have an efficient run time. 

 
<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
## Repository Structure
 
This repository contains the following structure to help you navigate and understand the project:
 
The repo tree to update since I have made it a package for code reusability
```plaintext
|___📄 .env
|___📄 .gitignore
|___🐍 main.py
|___📄 README.md
|___📄 requirements.txt
|___🐍 __init__.py
|
|___📁 assets
|   |___📁 content_creation_examples_and_potential_guidelines
|   |   |___📁 examples
|   |   |   |___📄 GenD-Insurance Brief-summary.docx
|   |   |   |___📄 GenD-Insurance-summaryd.docx
|   |   |   |___📄 GenD-Tariffs Brief-summary.docx
|   |   |   |___📄 GenD-Women in the boardroom-summary.docx
|   |   |   |___📄 Global-Women in the boardroom-copy.docx
|   |   |   |___📄 Pilot 1-Insurance Copy.docx
|   |   |   |___📄 Pilot 1-Insurance Survey-Transcript.docx
|   |   |   |___📄 Pilot 2-Tariff POV-Transcript.docx
|   |   |   |___📄 Pilot 2-Tariffs Copy.docx
|   |   |
|   |   |___📁 potential_guidelines
|   |   |   |___📄 Content Studio Dwriter.docx
|   |
|   |___📁 creation_work_timeline_audit
|   |   |___📄 timeline_tasks_audit.xlsx
|   |
|   |___📁 deprecated
|   |   |___🐍 deprecated_lcel_prompt_testing.py
|   |   |___🐍 TEST_TO_DEPRECATE.PY
|   |
|   |___📁 dev_testing_results
|   |   |___📄 testing_results_dev_stage.docx
|   |   |___📄 UAT API Testing.docx
|   |
|   |___📁 diagram
|   |   |___📄 high_level_api_structure_content_revision.docx
|   |   |
|   |   |___📁 high_level_creation
|   |   |   |___🖼️ dvoice_creation_workflow_v0.drawio
|   |   |   |___🖼️ dvoice_creation_workflow_v0.png
|   |   |
|   |   |___📁 high_level_revision
|   |   |   |___🖼️ dvoice_revision_workflow_v0.drawio
|   |   |   |___🖼️ dvoice_revision_workflow_v0.png
|   |
|   |___📁 dvoice_creation_high_level_design
|   |   |___📄 VERY_high_level_plan.txt
|   |
|   |___📁 img
|   |   |___🖼️ dvoice_repo_img.png
|   |
|   |___📁 postman_collection
|   |   |___📄 Content Voice Creation API local testing.postman_collection.json
|   |   |___📄 Content Voice Prod API Testing DEV STAGE.postman_collection.json
|   |   |___📄 Content Voice Prod API Testing.postman_collection.json
|   |
|   |___📁 pseudo_bidi
|   |   |___📄 setup.py
|   |   |
|   |   |___📁 bidi
|   |   |   |___🐍 algorithm.py
|   |   |   |___🐍 mirror.py
|   |   |   |___🐍 wrapper.py
|   |   |   |___🐍 __init__.py
|   |   |
|   |   |___📁 bidi.egg-info
|   |   |   |___📄 dependency_links.txt
|   |   |   |___📄 PKG-INFO
|   |   |   |___📄 SOURCES.txt
|   |   |   |___📄 top_level.txt
|   |   |
|   |   |___📁 dist
|   |   |   |___📄 bidi-0.0-py3-none-any.whl
|   |   |   |___📄 bidi-0.0.tar.gz
|
|___📁 content_creation
|   |___🐍 bill_96_compliance_guidelines.py
|   |___🐍 create_content.py
|   |___🐍 summarize.py
|
|___📁 content_revision
|   |___🐍 revision.py
|   |___🐍 __init__.py
|
|___📁 conversion
|   |___🐍 file_conversion.py
|   |___🐍 __init__.py
|
|___📁 extracted_output
|   |___📁 docx
|   |   |___📁 manual_input_inserted_by_user
|   |   |   |___📄 manual_input_inserted_by_user_DVoice_final_output.docx
|   |   |
|   |   |___📁 Oil and Gas_Spotlight article_ENs v1
|   |   |   |___📄 Oil and Gas_Spotlight article_ENs v1_DVoice_final_output.docx
|   |
|   |___📁 markdown
|   |   |___📁 Economic outlook_FY25_Q1_EN_V2_EDR3 v3
|   |   |   |___📄 Economic outlook_FY25_Q1_EN_V2_EDR3 v3_DVoice_final_output.md
|   |   |
|   |   |___📁 manual_input_inserted_by_user
|   |   |   |___📄 manual_input_inserted_by_user_DVoice_final_output.md
|   |   |
|   |   |___📁 Oil and Gas_Spotlight article_ENs v1
|   |   |   |___📄 Oil and Gas_Spotlight article_ENs v1_DVoice_final_output.md
|
|___📁 guidelines
|   |___📁 creating_actionable_guideline_summary_for_prompt
|   |   |___🐍 guideline_prompt_creation.py
|   |   |___🐍 __init__.py
|   |
|   |___📁 guideline_files
|   |   |___📄 Content Voice_2021.pdf
|   |   |
|   |   |___📁 checklist
|   |   |   |___📄 Content Voice 2021-the checklist.pdf
|   |   |
|   |   |___📁 guidelines
|   |   |   |___📄 Content Voice_2021_Param1_Writing Principles.pdf
|   |   |   |___📄 Content Voice_2021_Param2_Referring to the Company.pdf
|   |   |   |___📄 Content Voice_2021_Param3_Effective Writing Methods.pdf
|   |   |   |___📄 Content Voice_2021_Param4_Editorial Style Guide.pdf
|   |
|   |___📁 summary_guidelines
|   |   |___📄 DVoice_summary_guideline_Param1_Writing Principles.md
|   |   |___📄 DVoice_summary_guideline_Param2_Referring to the Company.md
|   |   |___📄 DVoice_summary_guideline_Param3_Effective Writing Methods.md
|   |   |___📄 DVoice_summary_guideline_Param4_Editorial Style Guide.md
|
|___📁 input_files
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|
|___📁 output_summary
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|   |___📄 <not versioned>
|
|___📁 parsing
|   |___🐍 file_parsing.py
|   |___🐍 manual_input_parsing.py
|
|___📁 prompt
|   |___🐍 model_persona_repo.py
|   |___🐍 prompt_actions.py
|   |___🐍 prompt_repo.py
|   |___🐍 __init__.py
|
|___📁 utilities
|   |___🐍 chunking.py
|   |___🐍 llm_and_embeddings_utils.py
|   |___🐍 llm_structured_output.py
|   |___🐍 settings.py
|   |___🐍 __init__.py

 
```
<p align="right">(<a href="#readme-top">back to top</a>)</p> 

## Repository Structure Analysis
```
Root-Level Files
 -📄 .env → Environment variables file, likely storing API keys or configuration settings. NOT VERSIONED THANKS TO GITIGNORE | NEVER VERSION!
 -📄 .gitignore → Specifies files and folders to ignore in version control, including.env
 -🐍 main.py → Main entry point for the application when called by Django API Revision and Creation views, possibly coordinating workflow execution.
 -📄 README.md → Documentation explaining the repository's purpose, setup, and usage.
 -📄 requirements.txt → Lists required Python dependencies for the project, this file has the same req as Content.Ca.DBotBeta.DjangoAPI\requirements.txt
 -🐍 init.py → Marks the directory as a Python package.

📁 assets → Stores supporting resources such as documentation, test results, and images.
 - 📁 content_creation_examples_and_potential_guidelines → Examples and guidelines for content creation.
    - 📁 examples → Contains various sample documents used in content creation testing.
    - 📁 potential_guidelines → Stores early drafts or proposals for content creation guidelines.
 - 📁 creation_work_timeline_audit → Contains an Excel file tracking project timelines and task for audits.
 - 📁 deprecated → Old or unused scripts.
 - 📁 dev_testing_results → Results from development-stage tests, including UAT and API tests.
 - 📁 diagram → High-level architecture diagrams for content workflows.
    - 📁 high_level_creation → Contains workflow diagrams for content creation.
    - 📁 high_level_revision → Contains workflow diagrams for content revision.
 - 📁 dvoice_creation_high_level_design → High-level project planning documents.
 - 📁 img → Stores images related to the repository (logo of this README.md)
 - 📁 postman_collection → API test collections for Postman.
 - 📁 pseudo_bidi → Implements a shell of the python-bidi package to ensure easy-ocr works after we pip-uninstall the real python-bidi (because not MIT licensed)
    - 📁 bidi → Main python-bidi folder, storing scripts, to build the python-bidi package
    - 📁 bidi.egg-info → Metadata files for the bidi package. We conducted `pip install setuptools wheel` then `python setup.py bdist_wheel` to s
    - 📁 dist → Contains distribution files (.whl, .tar.gz) for the package.
    - 🐍 setup.py → Used to create a python packages out of the bidi shell to pretend we have python-bidi in the environment (to ensure no dependency issues with easy-ocr; note we do not need python-bidi but it is a dependency to easy-ocr that can use it for arabic language processing; since we do not need arabic language processing and given the python-bidi package is GPL-licensed, we created a fake version of python-bidi to ensure easy-ocr continues working)
📁 content_creation → Scripts handling content generation.
    - 🐍 bill_96_compliance_guidelines.py → Generates a short guideline for compliance with Bill 96.
    - 🐍 create_content.py → Main script for generating content using AI models (covers retrieval processes and direct llm api calls for generation)
    - 🐍 summarize.py → Summarization utility for condensing large text documents.
📁 content_revision → Handles modifications and updates to generated content.
    - 🐍 revision.py → Script for revising content following Content static guidelines
    - 🐍 init.py → Marks the folder as a Python package.
📁 conversion → File format conversion utilities.
    - 🐍 file_conversion.py → Converts files between formats (e.g., DOCX to PDF, TXT to MD).
    - 🐍 init.py → Marks the folder as a Python package.
📁 extracted_output → Stores processed/generated content in different formats.
    - 📁 docx → Extracted outputs in .docx format.
    - 📁 markdown → Extracted outputs in .md format.
📁 guidelines → Contains reference materials and extracted summaries for AI writing.
    - 📁 creating_actionable_guideline_summary_for_prompt → Scripts for creating the structured summary guidelines
    - 📁 guideline_files → Contains official reference guidelines in .pdf format.
    - 📁 summary_guidelines → Extracted and structured versions of guidelines in .md format.
📁 input_files → Contains input files for content creation, parsing, or testing.
📁 output_summary → Stores summarized outputs of input files in markdown format.
📁 parsing → Extracts structured data from files.
    - 🐍 file_parsing.py → Parses text from various file formats (DOCX, PDF, TXT etc.). PPTX is not yet covered. Covers markdown extraction too.
    - 🐍 manual_input_parsing.py → Handles manual input parsing.
📁 prompt → Manages prompts for AI models.
    - 🐍 model_persona_repo.py → Defines AI model personas and behavior.
    - 🐍 prompt_actions.py → Manages different prompt-based actions.
    - 🐍 prompt_repo.py → Stores predefined prompts for AI interactions.
    - 🐍 init.py → Marks the folder as a Python package.
📁 utilities → Helper functions for processing and AI integration.
    - 🐍 chunking.py → Contains the functions used to split content cohesively
    - 🐍 llm_and_embeddings_utils.py → Utilities for working with language models and embeddings.
    - 🐍 llm_structured_output.py → Ensures AI output follows a structured format. One example: JSON Parsers
    - 🐍 settings.py → Configuration settings for the project. 
    - 🐍 init.py → Marks the folder as a Python package.
```
 
 
<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
## Built With
 
This section should list any major frameworks/libraries used to bootstrap your project. Leave any add-ons/plugins for the acknowledgements section. Here are a few examples.
 
- [![Python][Python]][Python]
- [![Langchain][Langchain]][Langchain]
- Parsing with Docling & Azure Document Intelligence
- [![Openai][Openai]][Openai]
- [![Azure][Azure]][Azure]
- [![Git][Git]][Git]
 
<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
 
## Getting Started
 
This is a section to get started on running the solution locally.
 
<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
### Prerequisites
 
Make sure you have the following:
- `git`
- `Python`
- Azure Credentials to run the api calls to the LLM or Azure Access Token 
- You have been through the Django `config.json` and Django `home/settings.py` to be familiar with all the important variables
 
<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
### Installation
 
1. Make sure to have a correct Open AI API key and add below to the `.env` file.
```
AZURE_OPENAI_API_KEY = ""
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_API_TYPE = ""
AZURE_OPENAI_API_VERSION = ""
AZURE_OPENAI_MODEL_NAME = ""
AZURE_OPEN_AI_MODEL = ""
CONTEXT_WINDOW_LIMIT = (expects an integet, not a string)
```

or make sure you have access to an Azure Access Token
 
2. Clone the repo
 
```sh
git clone https://github.com/benichou/content_creation_revision.git
```

Note: make sure to be in the branch with the most updated version of DVoice Creation & Revision
 
3. Python version
 
Make sure the python version is 3.11 (3.11.8 specifically)
 
4. Create a new venv environment in a specific python envrionment folder preferrably
 
```sh
python -m venv dvoice_api_env
```
 
5. Activate venv environment
 
```sh
dvoice_api_env\Scripts\activate
```
 
6. Install the necessary dependencies by running the following command (make sure you are at the root of the repo)
 
```sh
cd Content_Creation_Revision\Content.Ca.DBotBeta.DjangoAPI
pip install -r requirements.txt
```


7. Ensure you can access Azure resources
```sh
az login
```

Make sure to select the a correct subscriptions  
 
<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
## Usage
 
1. Go to Postman and create an account

2. #### To test :
- ### DVoice Creation:
 - Create a postman collection as follows and inserts values (if no postman, go to postman.com):
 - Ensure you have all the needed parameters in the POST HTTPS Request + Bearer Token + Access to Azure

  - ### DVoice Revision:
   - Create a postman collection as follows and inserts values (if no postman, go to postman.com):
   - Ensure you have all the needed parameters in the POST HTTPS Request + Bearer Token + Access to Azure



<p align="right">(<a href="#readme-top">back to top</a>)</p>
 
 
## High Level Logic
 
### DVoice Creation High Level Logic:
![High Level Logic DVoice Creation](/ContentCreationRevision.DjangoAPI/DVoice/assets/diagram/high_level_creation/dvoice_creation_workflow_v1.png)

### DVoice Revision High Level Logic:
![High Level Logic DVoice Revision](/ContentCreationRevision.DjangoAPI/DVoice/assets/diagram/high_level_revision/dvoice_revision_workflow_v1.png)


 
## Roadmap
 
- [] Support PPTX parsing
- [] Explore more parsing solutions that maintain accuracy while improving latency
- [] Build Functionalities to have more control over the length and tone of the output.
- [] Explore Multiple DOCX file output when multiple files are to be generated
- [] Explore additional techniques to improve retrieval of chunks 
- [] Explore applying revision or not during dvoice creation (since revision is the first job in terms of run time)
- [] Explore shorterning the revision prompt to make the revision process faster
- [] Explore Image ReGeneration/Generation in output
- [] Explore PDF Generation
- [] Explore using this first release as a tool to ITERATIVELY GENERATE content through the help of a co-pilot (a bit like canvass)
- [] Use Web Search Functionality to ground the information more
- [] Send output via email
 
<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Revision History

- Version `0`: Creation of the base Content Voice capability. Date: March 2025

 <p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact
 
Franck Benichou - franck.benichou@sciencespo.fr
 

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
 
[Python]: https://img.shields.io/badge/python-000000?style=for-the-badge&logo=python&logoColor=blue
[Langchain]: https://img.shields.io/badge/langchain-000000?style=for-the-badge&logo=langchain&logoColor=blue
[Openai]: https://img.shields.io/badge/openai-000001?style=for-the-badge&logo=openai&logoColor=orange
[Azure]: https://img.shields.io/badge/azure-000001?style=for-the-badge&logo=azuredevops&logoColor=blue
[Git]: https://img.shields.io/badge/git-000001?style=for-the-badge&logo=git&logoColor=white

<p align="right">(<a href="#readme-top">back to top</a>)</p>