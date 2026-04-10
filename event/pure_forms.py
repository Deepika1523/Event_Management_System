from django import forms
from django.utils import timezone
from .models import Event, Activity, ActivityCoordinator

class OrganizerEventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "date_of_event",
            "time_of_event",
            "venue",
            "description",
            "category",
            "location",
            "website",
            "image_url",
        ]
        widgets = {
            "date_of_event": forms.DateInput(attrs={"type": "date"}),
            "time_of_event": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-input"

    def clean_name(self):
        name = self.cleaned_data.get("name")
        qs = Event.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An event with this name already exists.")
        return name

class OrganizerActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            "name",
            "description",
            "date",
            "start_time",
            "end_time",
            "registration_fee",
            "is_team_event",
            "team_size",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-input"

class RegistrationFormFieldForm(forms.Form):
    label = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Field Label (e.g. Student ID)"}))
    field_type = forms.ChoiceField(
        choices=[
            ("text", "Text"),
            ("number", "Number"),
            ("email", "Email"),
            ("textarea", "Long Text"),
        ],
        widget=forms.Select(attrs={"class": "form-input"})
    )
    required = forms.BooleanField(required=False, initial=True)

class PureCoordinatorForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "coordinator@example.com"}))
    role = forms.ChoiceField(
        choices=[
            ("activity", "Activity Coordinator"),
            ("event", "Event Coordinator"),
        ],
        widget=forms.Select(attrs={"class": "form-input"})
    )
