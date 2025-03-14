# Use an official Python runtime based on Alpine as a parent image
FROM azcactniprdacr02.azurecr.io/python:3.11.5

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


# Install any needed packages specified in requirements.txt and uninstall python-bidi
# python-bidi is used by easy-ocr itself used in one particular functionality of docling 
# for ocr of arabic language content. Note we do not use easy-ocr at all, including the small functionality around 
# arabic language. Further, this python-bidi is GPL licensed so we remove it from our solution to avoid the GPL 
# constraints around distribution of the code
## WE ALSO MAKE SURE TO INSTALL AN ALIAS PACKAGE FOR BIDI BUILT FROM SCRATCH AND WHICH DOES NOT USE THE ORIGINAL BIDI
## OR MAKE ANY CALL TO THE PYTHON-BIDI PACKAGE TO ENSURE EASYOCR DOES NOT ERROR WHEN CALLING THE BIDI PACKAGE
## NOTE THAT WHEN EASYOCR MAKES THE BIDI STATEMENT IT DOES NOT CALL THE PYTHON-BIDI PACKAGE BUT CALLS THE 
## PSEUDO-BIDI PACKAGE WE BUILT FROM SCRATCH. AS YOU MAY SEE IN THE PSEUDO-BIDI FOLDER UNDER DVOICE/ASSETS YOU WILL 
## SEE WE ARE NOT REPRODUCING BIDI LOGIC AND CODE BUT JUST REPLICATING THE FUNCTION NAMES SO EASY OCR DOES NOT ERROR
## MAKE SURE TO NEVER REMOVE THE FOLLOWING FOLDER AND ASSOCIATED FILES: ContentCreationRevision.DjangoAPI\DVoice\assets\pseudo_bidi
RUN pip install --no-cache-dir -r requirements.txt \
                && pip uninstall -y python-bidi \
                && pip install DVoice/assets/pseudo_bidi/dist/bidi-0.0-py3-none-any.whl \
                && curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable
ENV NAME World
ENV DJANGO_SETTINGS_MODULE=home.settings

# Run the Django server when the container launches
CMD ["python", "manage.py", "runserver", "0.0.0.0:8501"]
