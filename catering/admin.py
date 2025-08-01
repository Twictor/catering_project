from django.contrib import admin
from django.http import HttpResponse
from django.core.files.uploadhandler import StopUpload
from django.utils.html import format_html
import csv
from .models import Dish, Order, OrderItem, Restaurant
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django import forms
from django.shortcuts import render
from django.contrib import messages
from import_export.formats import base_formats

admin.site.register(Restaurant)
admin.site.register(OrderItem)

class DishResource(resources.ModelResource):
    class Meta:
        model = Dish
        fields = ('id', 'name', 'price', 'restaurant')
        import_id_fields = ['id'] 
        skip_unchanged = True
        report_skipped = False

class CsvImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")

@admin.register(Dish)
class DishAdmin(ImportExportModelAdmin):
    resource_class = DishResource
    list_display = ("name", "price", "restaurant")
    search_fields = ("name",)
    list_filter = ("name", "restaurant")
    formats = [base_formats.CSV]

    @admin.action(description='Import Dishes from CSV')
    def import_csv(self, request, queryset):
        if not request.user.is_superuser:
            return self.message_user(request, "You do not have permission to perform this action.", level='ERROR')

        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data['csv_file']
                try:
                    # Import data using import_export
                    data = csv_file.read().decode('utf-8')
                    dish_resource = self.get_resource_class()()
                    dataset = dish_resource.import_data(data, dry_run=False, raise_errors=True, file_format=base_formats.CSV)

                    if dataset.has_errors():
                        for err in dataset.invalid_rows:
                            self.message_user(request, f"Ошибка в строке {err.number}: {err.error}", level=messages.ERROR)
                    else:
                        self.message_user(request, "Successfully imported dishes from CSV.")

                except Exception as e:
                    self.message_user(request, f"Error importing dishes: {e}", level='ERROR')
        else:
            form = CsvImportForm()
            return render(request, "admin/csv_form.html", {"form": form}) # Return the form

class DishOrderItemInline(admin.TabularInline):
    model = OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "id", "status")
    inlines = (DishOrderItemInline,)