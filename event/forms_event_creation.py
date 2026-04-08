from django import forms

ACTIVITY_TYPE_CHOICES = [
    ('competition', 'Competition'),
    ('workshop', 'Workshop'),
    ('seminar', 'Seminar'),
    # Add more as needed
]

ACTIVITY_MODE_CHOICES = [
    ('online', 'Online'),
    ('offline', 'Offline'),
    ('hybrid', 'Hybrid'),
]

class ActivityForm(forms.Form):
    name = forms.CharField(max_length=100, label="Activity Name")
    description = forms.CharField(widget=forms.Textarea, label="Description")
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    type = forms.ChoiceField(choices=ACTIVITY_TYPE_CHOICES)
    mode = forms.ChoiceField(choices=ACTIVITY_MODE_CHOICES)
    team_size = forms.IntegerField(min_value=1, label="Team Size")

FIELD_TYPE_CHOICES = [
    ('text', 'Text'),
    ('number', 'Number'),
    ('dropdown', 'Dropdown'),
]

class RegistrationFieldForm(forms.Form):
    label = forms.CharField(max_length=100)
    field_type = forms.ChoiceField(choices=FIELD_TYPE_CHOICES)
    dropdown_options = forms.CharField(
        required=False,
        help_text="Comma-separated options (for dropdown only)"
    )

class CoordinatorForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()

TEMPLATE_CHOICES = [
    ('classic', 'Classic'),
    ('modern', 'Modern'),
    ('minimal', 'Minimal'),
]

class WebsiteSetupForm(forms.Form):
    template = forms.ChoiceField(choices=TEMPLATE_CHOICES)
    banner_text = forms.CharField(max_length=200)
