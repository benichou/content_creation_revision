from django.db import models
# The following are strictly for guidelines processing
class ProcessedFile(models.Model):
    id = models.AutoField(primary_key=True)
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    topic = models.CharField(max_length=255, null=True, blank=True)
    target_audience = models.CharField(max_length=255, null=True, blank=True)
    target_medium = models.CharField(max_length=255, null=True, blank=True)  
    content_medium = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    error = models.TextField(null=True, blank=True)
    word_limit = models.IntegerField(default=100)
    generated_text = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.filename

class ParagraphSet(models.Model):
    id = models.AutoField(primary_key=True)
    index = models.IntegerField()
    paragraph_original = models.TextField()
    processed_file = models.ForeignKey(ProcessedFile, related_name='paragraphs', on_delete=models.CASCADE)

    def __str__(self):
        return f"Paragraph {self.index} in {self.processed_file.filename}"

class Correction(models.Model):
    id = models.AutoField(primary_key=True)
    paragraph_corrected = models.TextField()
    correction_source = models.CharField(max_length=255)
    paragraph_set = models.ForeignKey(ParagraphSet, related_name='corrections', on_delete=models.CASCADE)

    def __str__(self):
        return f"Correction by {self.correction_source} for {self.paragraph_set}"
# Create your models here.
