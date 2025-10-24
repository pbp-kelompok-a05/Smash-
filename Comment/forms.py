# comment/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape
from .models import Comment

class CommentCreateForm(forms.ModelForm):
    """
    Form untuk membuat komentar baru.
    Mendukung teks dan emoji, serta nested comments.
    """
    emoji = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'id': 'comment-emoji-input'
        }),
        label='Emoji'
    )
    
    parent_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'id': 'comment-parent-input'
        }),
        label='Komentar Induk'
    )

    class Meta:
        model = Comment
        fields = ['content', 'emoji']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tulis komentar Anda...',
                'rows': 3,
                'maxlength': '1000',
                'id': 'comment-content-input'
            }),
        }
        labels = {
            'content': 'Komentar',
        }
        help_texts = {
            'content': 'Maksimal 1000 karakter. Gunakan emoji untuk ekspresi cepat.',
        }

    def __init__(self, *args, **kwargs):
        self.post = kwargs.pop('post', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_content(self):
        """
        Validasi custom untuk content komentar:
        - Sanitasi input
        - Validasi panjang
        """
        content = self.cleaned_data.get('content', '').strip()
        emoji = self.cleaned_data.get('emoji', '').strip()
        
        # Jika ada emoji, content tidak wajib
        if not content and not emoji:
            raise ValidationError("Komentar harus berisi teks atau emoji.")
        
        if content and len(content) < 2:
            raise ValidationError("Komentar terlalu pendek.")
        
        if content and len(content) > 1000:
            raise ValidationError("Komentar maksimal 1000 karakter.")
        
        # Sanitasi input
        return escape(content) if content else content

    def clean_emoji(self):
        """
        Validasi custom untuk emoji:
        - Memastikan emoji valid
        - Batasi panjang emoji
        """
        emoji = self.cleaned_data.get('emoji', '').strip()
        
        if emoji and len(emoji) > 10:
            raise ValidationError("Emoji terlalu panjang.")
        
        # Validasi format emoji dasar
        if emoji and not any(c in emoji for c in ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣', '😊', '😇', '🙂', '🙃', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳', '😏', '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😩', '🥺', '😢', '😭', '😤', '😠', '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨', '😰', '😥', '😓', '🤗', '🤔', '🤭', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧', '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐', '🥴', '🤢', '🤮', '🤧', '😷', '🤒', '🤕', '🤑', '🤠', '😈', '👿', '👹', '👺', '🤡', '💩', '👻', '💀', '☠️', '👽', '👾', '🤖', '🎃', '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾']):
            # Basic emoji validation - dalam praktiknya bisa menggunakan library emoji
            raise ValidationError("Format emoji tidak valid.")
        
        return emoji

    def clean(self):
        """
        Validasi cross-field:
        - Memastikan post exists
        - Validasi parent comment jika ada
        """
        cleaned_data = super().clean()
        
        if not self.post:
            raise ValidationError("Post harus ditentukan.")
        
        parent_id = cleaned_data.get('parent_id')
        if parent_id:
            try:
                from .models import Comment
                parent_comment = Comment.objects.get(id=parent_id, post=self.post)
                cleaned_data['parent'] = parent_comment
            except Comment.DoesNotExist:
                raise ValidationError("Komentar induk tidak ditemukan.")
        
        return cleaned_data

    def save(self, commit=True):
        """
        Override save untuk menambahkan post dan user
        """
        comment = super().save(commit=False)
        comment.post = self.post
        comment.user = self.user
        
        if commit:
            comment.save()
        
        return comment


class CommentUpdateForm(forms.ModelForm):
    """
    Form untuk mengupdate komentar existing.
    """
    class Meta:
        model = Comment
        fields = ['content', 'emoji']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': '1000',
                'id': 'comment-update-content-input'
            }),
            'emoji': forms.HiddenInput(attrs={
                'id': 'comment-update-emoji-input'
            }),
        }

    def clean_content(self):
        """
        Validasi content untuk update
        """
        content = self.cleaned_data.get('content', '').strip()
        emoji = self.cleaned_data.get('emoji', '').strip()
        
        if not content and not emoji:
            raise ValidationError("Komentar harus berisi teks atau emoji.")
        
        if content and len(content) < 2:
            raise ValidationError("Komentar terlalu pendek.")
        
        if content and len(content) > 1000:
            raise ValidationError("Komentar maksimal 1000 karakter.")
        
        return escape(content) if content else content


class CommentAdminForm(forms.ModelForm):
    """
    Form khusus admin untuk manage semua komentar.
    """
    class Meta:
        model = Comment
        fields = '__all__'
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'post': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emoji': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_user(self):
        """Validasi user"""
        user = self.cleaned_data.get('user')
        if not user or not user.is_active:
            raise ValidationError("User harus active dan valid.")
        return user

    def clean_post(self):
        """Validasi post"""
        post = self.cleaned_data.get('post')
        if post and post.is_deleted:
            raise ValidationError("Tidak dapat mengomentari post yang dihapus.")
        return post