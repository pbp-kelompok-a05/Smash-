from django.forms import ModelForm
from Comment.models import Comment

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['content']