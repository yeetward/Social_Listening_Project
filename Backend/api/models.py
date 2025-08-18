from django.db import models

# Create your models here.
class project(models.Model):
    Subject = models.CharField(max_length=100)
    Location = models.CharField(max_length=100, blank= True)
    industry = models.CharField(max_length=100, blank=True)