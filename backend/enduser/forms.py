from django import forms

from workspaces.models import Workspace


class DatasetUploadForm(forms.Form):
    name = forms.CharField(max_length=255)
    workspace = forms.ModelChoiceField(queryset=Workspace.objects.none(), required=False)
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["workspace"].queryset = Workspace.objects.filter(owner=user)
