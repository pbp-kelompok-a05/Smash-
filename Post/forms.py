from django.forms import ModelForm
from .models import Post

# Tambahan import untuk melindungi aplikasi web dari XSS
from django.utils.html import strip_tags

class ReportForm(ModelForm):
    class Meta:
        model = Post
        fields = ["title", "description", "category", "thumbnail", "is_featured"]


    # tambahan method untuk clean title and content saat handle AJAX request dan DOMpurify
    def clean_title(self):
        title = self.cleaned_data["title"]
        return strip_tags(title)

    def clean_content(self):
        content = self.cleaned_data["description"]
        return strip_tags(content)