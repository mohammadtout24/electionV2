from django import forms
from .models import Candidate

class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        # Includes image and cv_pdf for file uploads
        fields = ['name', 'party', 'description', 'image']
        
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }