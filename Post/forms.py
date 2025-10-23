from django.forms import ModelForm
from .models import ForumPost, Category
from django import forms

# Tambahan import untuk melindungi aplikasi web dari XSS
from django.utils.html import strip_tags

class ReportForm(ModelForm):
    class Meta:
        model = ForumPost
        fields = ["title", "description", "category", "thumbnail", "is_featured"]
        # Menambahkan widgets
        widgets = {
            # Handle untuk form Post Title
            'title' : forms.TextInput(attrs={
                'class' : 'form-control',
                'placeholder' : 'Enter post title'
            }),
            # Handle untuk Post Content
            'content' : forms.Textarea(attrs={
                'class' : 'form-control',
                'placeholder' : 'Write your description here ...',
                'rows' : 5        
            }),
            # Handle untuk category, tipe, dan media
            'category': forms.Select(attrs={'class' : 'form-control'}),
            'post_type': forms.Select(attrs={'class' : 'form-control'}),
            'image' : forms.FileInput(attrs={'class' : 'form-control'}),
            'video-url' : forms.URLInput(attrs={
                'class' : 'form-control',
                'placeholder' : 'https://example.com/video'
            }),
        }

    # tambahan method untuk clean title and content saat handle AJAX request dan DOMpurify
    def clean(self):
        # Membuat data clean
        cleaned_data = super().clean()
        # Mengambil data image dan video_url
        image = cleaned_data.get('image')
        video_url = cleaned_data.get('video_url')

        # Handle ketika user memasukkan dua jenis media
        if image and video_url:
            raise forms.ValidationError("Post can have either image or video URL, not both!")
        
        return cleaned_data