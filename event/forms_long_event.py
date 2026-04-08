from django import forms

ACTIVITY_TYPE_CHOICES = [
    ('competition', 'Competition'),
    ('workshop', 'Workshop'),
    ('seminar', 'Seminar'),
]
ACTIVITY_MODE_CHOICES = [
    ('online', 'Online'),
    ('offline', 'Offline'),
    ('hybrid', 'Hybrid'),
]
FIELD_TYPE_CHOICES = [
    ('text', 'Text'),
    ('number', 'Number'),
    ('dropdown', 'Dropdown'),
]
TEMPLATE_CHOICES = [
    ('classic', 'Classic'),
    ('modern', 'Modern'),
    ('minimal', 'Minimal'),
]

class LongEventForm(forms.Form):
    # Step 2: Activities (allow up to 5 for simplicity)
    activity1_name = forms.CharField(max_length=100, required=False, label="Activity 1 Name")
    activity1_description = forms.CharField(widget=forms.Textarea, required=False, label="Activity 1 Description")
    activity1_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    activity1_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    activity1_type = forms.ChoiceField(choices=ACTIVITY_TYPE_CHOICES, required=False)
    activity1_mode = forms.ChoiceField(choices=ACTIVITY_MODE_CHOICES, required=False)
    activity1_team_size = forms.IntegerField(min_value=1, required=False, label="Activity 1 Team Size")
    # Repeat for up to 3 activities
    activity2_name = forms.CharField(max_length=100, required=False, label="Activity 2 Name")
    activity2_description = forms.CharField(widget=forms.Textarea, required=False, label="Activity 2 Description")
    activity2_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    activity2_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    activity2_type = forms.ChoiceField(choices=ACTIVITY_TYPE_CHOICES, required=False)
    activity2_mode = forms.ChoiceField(choices=ACTIVITY_MODE_CHOICES, required=False)
    activity2_team_size = forms.IntegerField(min_value=1, required=False, label="Activity 2 Team Size")
    activity3_name = forms.CharField(max_length=100, required=False, label="Activity 3 Name")
    activity3_description = forms.CharField(widget=forms.Textarea, required=False, label="Activity 3 Description")
    activity3_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    activity3_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)
    activity3_type = forms.ChoiceField(choices=ACTIVITY_TYPE_CHOICES, required=False)
    activity3_mode = forms.ChoiceField(choices=ACTIVITY_MODE_CHOICES, required=False)
    activity3_team_size = forms.IntegerField(min_value=1, required=False, label="Activity 3 Team Size")

    # Step 3: Registration Form Builder (up to 3 fields)
    regfield1_label = forms.CharField(max_length=100, required=False, label="Registration Field 1 Label")
    regfield1_type = forms.ChoiceField(choices=FIELD_TYPE_CHOICES, required=False, label="Registration Field 1 Type")
    regfield1_options = forms.CharField(required=False, label="Dropdown Options (comma separated)")
    regfield2_label = forms.CharField(max_length=100, required=False, label="Registration Field 2 Label")
    regfield2_type = forms.ChoiceField(choices=FIELD_TYPE_CHOICES, required=False, label="Registration Field 2 Type")
    regfield2_options = forms.CharField(required=False, label="Dropdown Options (comma separated)")
    regfield3_label = forms.CharField(max_length=100, required=False, label="Registration Field 3 Label")
    regfield3_type = forms.ChoiceField(choices=FIELD_TYPE_CHOICES, required=False, label="Registration Field 3 Type")
    regfield3_options = forms.CharField(required=False, label="Dropdown Options (comma separated)")

    # Step 4: Coordinators (up to 3)
    coordinator1_name = forms.CharField(max_length=100, required=False, label="Coordinator 1 Name")
    coordinator1_email = forms.EmailField(required=False, label="Coordinator 1 Email")
    coordinator2_name = forms.CharField(max_length=100, required=False, label="Coordinator 2 Name")
    coordinator2_email = forms.EmailField(required=False, label="Coordinator 2 Email")
    coordinator3_name = forms.CharField(max_length=100, required=False, label="Coordinator 3 Name")
    coordinator3_email = forms.EmailField(required=False, label="Coordinator 3 Email")

    # Step 5: Website Setup
    template = forms.ChoiceField(choices=TEMPLATE_CHOICES, required=True)
    banner_text = forms.CharField(max_length=200, required=True)
