# post/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape
import re
from .models import Post

class PostCreateForm(forms.ModelForm):
    """
    Form untuk membuat post baru.
    Mendukung validasi custom dan sanitasi input.
    """
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'id': 'post-image-input'
        }),
        label='Gambar Post'
    )
    
    video_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://youtube.com/embed/...',
            'id': 'post-video-input'
        }),
        label='Tautan Video'
    )

    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'video_link']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Judul post tentang Padel...',
                'maxlength': '255',
                'id': 'post-title-input'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Bagikan pengalaman atau tips Padel Anda...',
                'rows': 6,
                'id': 'post-content-input'
            }),
        }
        labels = {
            'title': 'Judul Post',
            'content': 'Konten Post',
        }
        help_texts = {
            'content': 'Diskusi harus berkaitan dengan olahraga Padel',
        }

    def clean_title(self):
        """
        Validasi custom untuk title:
        - Menghilangkan whitespace berlebihan
        - Memastikan title tidak hanya berisi karakter spesial
        """
        title = self.cleaned_data.get('title', '').strip()
        
        if len(title) < 5:
            raise ValidationError("Judul post harus minimal 5 karakter.")
        
        # Cek jika title hanya berisi karakter spesial/angka
        if not any(c.isalpha() for c in title):
            raise ValidationError("Judul post harus mengandung teks.")
        
        # Sanitasi input
        return escape(title)

    def clean_content(self):
        """
        Validasi custom untuk content:
        - Memastikan content memiliki panjang minimum
        - Sanitasi HTML
        """
        content = self.cleaned_data.get('content', '').strip()
        
        if len(content) < 10:
            raise ValidationError("Konten post harus minimal 10 karakter.")
        
        if len(content) > 10000:
            raise ValidationError("Konten post maksimal 10,000 karakter.")
        
        # Sanitasi input
        return escape(content)

    def clean_video_link(self):
        """
        Validasi custom untuk video link:
        - Memastikan format URL valid
        - Support platform video populer
        """
        video_link = self.cleaned_data.get('video_link', '').strip()
        
        if not video_link:
            return video_link
        
        # Pattern untuk platform video populer
        video_patterns = [
            r'https?://(?:www\.)?youtube\.com/.*',
            r'https?://(?:www\.)?youtu\.be/.*',
            r'https?://(?:www\.)?vimeo\.com/.*',
            r'https?://(?:www\.)?dailymotion\.com/.*'
        ]
        
        if not any(re.match(pattern, video_link) for pattern in video_patterns):
            raise ValidationError(
                "Format tautan video tidak didukung. Gunakan YouTube, Vimeo, atau Dailymotion."
            )
        
        return video_link

    def clean(self):
        """
        Validasi cross-field:
        - Post harus memiliki gambar ATAU video link
        """
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        video_link = cleaned_data.get('video_link')
        
        if not image and not video_link:
            raise ValidationError(
                "Post harus memiliki minimal gambar atau tautan video."
            )
        
        return cleaned_data


class PostUpdateForm(PostCreateForm):
    """
    Form untuk mengupdate post existing.
    Inherit dari PostCreateForm dengan modifikasi tertentu.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Untuk update, gambar dan video tidak wajib
        self.fields['image'].required = False
        self.fields['video_link'].required = False

    def clean(self):
        """
        Override clean untuk update form:
        - Gambar dan video link tidak wajib saat update
        - Tetap validasi jika ada input
        """
        cleaned_data = super(PostCreateForm, self).clean()  # Skip parent's clean
        
        # Validasi individual fields tetap berjalan
        return cleaned_data


class PostAdminForm(forms.ModelForm):
    """
    Form khusus untuk admin/superuser.
    Memungkinkan modifikasi semua field termasuk user.
    """
    class Meta:
        model = Post
        fields = '__all__'
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'video_link': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def clean_user(self):
        """Validasi bahwa user exists dan active"""
        user = self.cleaned_data.get('user')
        if not user or not user.is_active:
            raise ValidationError("User harus active dan valid.")
        return user