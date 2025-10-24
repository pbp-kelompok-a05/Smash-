from django.forms import ModelForm
from .models import ForumPost, Category
from django import forms

# Import untuk keamanan dan validasi
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError
import re


class ForumPostForm(ModelForm):
    """
    Form untuk membuat dan mengedit ForumPost.
    
    Features:
    - Validasi XSS protection pada title dan content
    - Validasi media (hanya satu jenis media yang diperbolehkan)
    - Custom validation untuk video URL
    - Clean UI dengan placeholder dan class Bootstrap
    """
    
    # Field tambahan untuk validasi custom
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select a category",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ForumPost
        fields = ["title", "content", "category", "post_type", "image", "video_url"]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter post title about padel sports...',
                'maxlength': '255'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write your padel-related discussion, question, review, or nostalgia here...',
                'rows': 8,
                'minlength': '10'
            }),
            'post_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/watch?v=... or https://vimeo.com/...',
                'pattern': 'https?://.+'
            }),
        }

        # Labels yang lebih user-friendly
        labels = {
            'title': 'Post Title',
            'content': 'Post Content',
            'category': 'Category',
            'post_type': 'Post Type',
            'image': 'Upload Image',
            'video_url': 'Video URL',
        }

        # Help texts untuk panduan pengguna
        help_texts = {
            'title': 'Choose a descriptive title for your padel post (max 255 characters)',
            'content': 'Share your thoughts, questions, or experiences about padel sports',
            'post_type': 'Select the type of your post',
            'image': 'Upload a relevant image (JPEG, PNG, GIF) - max 5MB',
            'video_url': 'Paste YouTube or Vimeo link for relevant padel videos',
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize form dengan custom settings
        """
        super().__init__(*args, **kwargs)
        
        # Optimize queryset untuk category
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        
        # Set required fields
        self.fields['title'].required = True
        self.fields['content'].required = True
        self.fields['post_type'].required = True

    def clean_title(self):
        """
        Clean dan validasi title:
        - Strip HTML tags untuk prevent XSS
        - Validasi panjang minimum
        - Validasi konten tidak kosong setelah strip
        """
        title = self.cleaned_data.get('title', '').strip()
        
        # Strip HTML tags untuk prevent XSS
        cleaned_title = strip_tags(title)
        
        # Validasi panjang minimum
        if len(cleaned_title) < 5:
            raise ValidationError("Title must be at least 5 characters long.")
        
        # Validasi tidak kosong setelah strip
        if not cleaned_title:
            raise ValidationError("Title cannot be empty or contain only HTML tags.")
        
        return cleaned_title

    def clean_content(self):
        """
        Clean dan validasi content:
        - Strip HTML tags untuk prevent XSS
        - Validasi panjang minimum
        - Validasi konten tidak kosong setelah strip
        """
        content = self.cleaned_data.get('content', '').strip()
        
        # Strip HTML tags untuk prevent XSS
        cleaned_content = strip_tags(content)
        
        # Validasi panjang minimum
        if len(cleaned_content) < 10:
            raise ValidationError("Content must be at least 10 characters long.")
        
        # Validasi tidak kosong setelah strip
        if not cleaned_content:
            raise ValidationError("Content cannot be empty or contain only HTML tags.")
        
        return cleaned_content

    def clean_video_url(self):
        """
        Validasi video URL:
        - Format URL yang valid
        - Domain yang diperbolehkan (YouTube, Vimeo, dll)
        - Optional: pattern matching untuk platform video
        """
        video_url = self.cleaned_data.get('video_url', '').strip()
        
        # Jika video_url kosong, return tanpa validasi
        if not video_url:
            return video_url
        
        # Validasi format URL dasar
        if not video_url.startswith(('http://', 'https://')):
            raise ValidationError("Please enter a valid URL starting with http:// or https://")
        
        # Validasi domain video yang umum (optional tapi recommended)
        allowed_domains = [
            'youtube.com', 'youtu.be', 'www.youtube.com',
            'vimeo.com', 'www.vimeo.com',
            'dailymotion.com', 'www.dailymotion.com'
        ]
        
        if not any(domain in video_url for domain in allowed_domains):
            raise ValidationError(
                "Please enter a valid video URL from supported platforms: "
                "YouTube, Vimeo, or Dailymotion"
            )
        
        return video_url

    def clean_image(self):
        """
        Validasi image:
        - Size validation (max 5MB)
        - File type validation
        """
        image = self.cleaned_data.get('image')
        
        if image:
            # Validasi ukuran file (max 5MB)
            if image.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError("Image file too large (max 5MB)")
            
            # Validasi tipe file
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
            extension = image.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise ValidationError(
                    f"Unsupported file format. Supported formats: {', '.join(valid_extensions)}"
                )
        
        return image

    def clean(self):
        """
        Validasi cross-field:
        - Hanya satu jenis media (image atau video_url) yang diperbolehkan
        - Validasi category jika required
        """
        cleaned_data = super().clean()
        
        image = cleaned_data.get('image')
        video_url = cleaned_data.get('video_url')
        category = cleaned_data.get('category')
        post_type = cleaned_data.get('post_type')

        # Validasi media: hanya satu yang boleh diisi
        if image and video_url:
            raise ValidationError({
                'image': "Post can have either an image or a video URL, not both!",
                'video_url': "Post can have either an image or a video URL, not both!"
            })

        # Validasi category untuk post_type tertentu (optional)
        if post_type in ['review', 'nostalgia'] and not category:
            self.add_error(
                'category', 
                f"Category is recommended for {post_type} posts"
            )

        return cleaned_data


class ForumPostAdminForm(ForumPostForm):
    """
    Form khusus untuk admin interface dengan field tambahan
    """
    class Meta(ForumPostForm.Meta):
        fields = ForumPostForm.Meta.fields + ['is_pinned', 'author']
        
        widgets = {
            **ForumPostForm.Meta.widgets,
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'author': forms.Select(attrs={'class': 'form-control'}),
        }


class CategoryForm(ModelForm):
    """
    Form untuk membuat dan mengedit Category
    """
    class Meta:
        model = Category
        fields = ['name', 'description']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name...',
                'maxlength': '255'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe this category...',
                'rows': 3,
                'maxlength': '255'
            }),
        }

    def clean_name(self):
        """
        Validasi nama category: harus unik dan tidak mengandung HTML
        """
        name = self.cleaned_data.get('name', '').strip()
        cleaned_name = strip_tags(name)
        
        if len(cleaned_name) < 3:
            raise ValidationError("Category name must be at least 3 characters long.")
        
        # Check for uniqueness (exclude current instance jika update)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if Category.objects.filter(name__iexact=cleaned_name).exclude(pk=instance.pk).exists():
                raise ValidationError("A category with this name already exists.")
        else:
            if Category.objects.filter(name__iexact=cleaned_name).exists():
                raise ValidationError("A category with this name already exists.")
        
        return cleaned_name

    def clean_description(self):
        """
        Validasi description: strip HTML dan validasi panjang
        """
        description = self.cleaned_data.get('description', '').strip()
        cleaned_description = strip_tags(description)
        
        if len(cleaned_description) < 10:
            raise ValidationError("Description must be at least 10 characters long.")
        
        return cleaned_description