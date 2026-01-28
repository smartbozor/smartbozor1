from django import forms

from apps.camera.models import Camera


class CameraUpdateAuthForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].required = True
        self.fields['password'].required = True

    class Meta:
        model = Camera
        fields = ["username", "password"]



