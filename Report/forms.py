from django import forms
from .models import Report

class ReportForm(forms.ModelForm):
    class Meta:
        # Model diambil dari models Report 
        model = Report
        # Input yang akan diminta 
        fields = ['reason', 'description']    
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Jelaskan mengapa Anda melaporkan konten ini...'
            }),
        }
        labels = {
            'reason': 'Alasan Pelaporan',
            'description': 'Deskripsi Tambahan',
        }
        help_texts = {
            'description': 'Berikan penjelasan detail untuk membantu moderator memahami laporan Anda.',
        }

class ReportAdminForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = '__all__'
        widgets = {
            'admin_notes': forms.Textarea(attrs={'rows': 3}),
        }