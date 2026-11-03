from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    # Honeypot: real people never see or fill this. Bots usually do.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': ' ', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'placeholder': ' ', 'autocomplete': 'email'}),
            'subject': forms.TextInput(attrs={'placeholder': ' '}),
            'message': forms.Textarea(attrs={'placeholder': ' ', 'rows': 6, 'maxlength': 2000}),
        }

    def clean_message(self):
        msg = self.cleaned_data['message'].strip()
        if len(msg) < 10:
            raise forms.ValidationError('Please write at least a sentence so I can reply properly.')
        return msg
