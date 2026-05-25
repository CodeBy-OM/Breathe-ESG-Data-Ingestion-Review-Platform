from django.contrib import admin
from .models import DataImport, NormalizedRecord
admin.site.register(DataImport)
admin.site.register(NormalizedRecord)
