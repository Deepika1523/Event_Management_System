from django import forms
from .models import Activity


class ActivityForm(forms.ModelForm):
    image = forms.ImageField(required=False, label="Activity Image")
    qr_code_image = forms.ImageField(required=False, label="Activity QR Code Image")
    class Meta:
        model = Activity
        fields = [
            "name",
            "description",
            "date",
            "max_participants",
            "start_time",
            "end_time",
            "registration_fee",
            "prize",
            "is_team_event",
            "team_size",
            "image",
            "qr_code_image",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.organizer = kwargs.pop('organizer', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        event = self.event
        organizer = self.organizer
        if name and event and organizer:
            qs = Activity.objects.filter(event=event, organizer=organizer, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("An activity with this name already exists for this event and organizer.")
        return name
