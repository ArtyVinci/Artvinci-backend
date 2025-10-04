from django.db import models


class Artist(models.Model):
    """
    Artist model representing artists in the Artvinci database.
    """
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    art_style = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'artists'
    
    def __str__(self):
        return f"{self.name} - {self.art_style}"
