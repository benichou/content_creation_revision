import os
from rest_framework import serializers

class FileUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        allow_empty=False
    )

    def validate_files(self, value):
        # Validate each file in the list
        for upload_file in value:
            # Check file type
            if not upload_file.endswith(('.pdf', '.docx')):
                raise serializers.ValidationError("Invalid file type.")
        return value
class FileUploadResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    

class FileNameValidatorSerializer(serializers.Serializer):
    
    fileName = serializers.CharField(max_length=255)
 
    def validate_fileName(self, value):
        """
        Custom validation to ensure the input is a valid file path and has a .pdf or .docx extension.
        """
 
        # Check if the file has the correct extension
        if not (value.lower().endswith('.pdf') or value.lower().endswith('.docx')):
            raise serializers.ValidationError("File must have a .pdf or .docx extension.")
 
        return value


