from django import forms
from django.utils import timezone
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'event', 'description', 'tagline', 'schedule', 
            'activities_overview', 'rules', 'date_of_event', 
            'time_of_event', 'venue', 'location', 
            'category', 'registration', 'last_registration_date', 
            'contact_info', 'registration_form_fields', 
            'past_event_history', 'image_url', 'template_choice'
        ]
        widgets = {
            'date_of_event': forms.DateInput(attrs={'type': 'date'}),
            'time_of_event': forms.TimeInput(attrs={'type': 'time'}),
            'last_registration_date': forms.DateInput(attrs={'type': 'date'}),
            'template_choice': forms.Select(),
            'category': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark required fields for easier logic in templates if needed
        # and ensure everything has the 'form-input' class
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-input'
            if field.required:
                field.label = f"{field.label} *"

    def clean_last_registration_date(self):
        last_registration_date = self.cleaned_data.get('last_registration_date')
        if last_registration_date and last_registration_date < timezone.now().date():
            raise forms.ValidationError("Registration close date cannot be in the past.")
        return last_registration_date
