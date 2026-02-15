from django.contrib.gis.db import models


class FuelStation(models.Model):
    opis_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=10)
    retail_price = models.FloatField()
    location = models.PointField(srid=4326, null=True, blank=True)

    def __str__(self):
        return f"{self.city} - ${self.retail_price}"
