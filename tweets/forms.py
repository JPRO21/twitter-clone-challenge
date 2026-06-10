from django import forms

from .models import Tweet

_INPUT_CSS = (
    "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TweetForm(forms.ModelForm):
    class Meta:
        model = Tweet
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={
                "rows": 3,
                "maxlength": "280",
                "placeholder": "What's happening?",
                "class": _INPUT_CSS,
            }),
        }
        labels = {"body": ""}
