from django import forms
from .models import ForumPost

class ForumPostForm(forms.ModelForm):
    """
    Form untuk membuat dan mengupdate ForumPost.
    """
    class Meta:
        model = ForumPost
        fields = ['title', 'content', 'image', 'video_link']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Masukkan judul post yang menarik...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Tulis konten post Anda di sini...'
            }),
            'video_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/video'
            }),
        }
        labels = {
            'title': 'Judul Post',
            'content': 'Konten',
            'image': 'Gambar',
            'video_link': 'Tautan Video',
        }
        help_texts = {
            'video_link': 'Masukkan tautan video YouTube atau Vimeo',
            'image': 'Unggah gambar pendukung (opsional)',
        }