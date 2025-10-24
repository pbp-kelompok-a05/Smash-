import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smash.settings")
django.setup()

from django.contrib.auth.models import User
from post.models import Post

# Get or create test user
user, created = User.objects.get_or_create(username="testuser")
if created:
    user.set_password("testpass123")
    user.save()
    print("✓ Test user created")
else:
    print("✓ Using existing test user")

# Create a test post
post = Post.objects.create(
    user=user,
    title="Welcome to SMASH!",
    content="This is a test post to demonstrate the forum functionality. Join our padel community and share your experiences!",
)

print(f"\n✓ Test post created successfully!")
print(f"  Post ID: {post.id}")
print(f"  Title: {post.title}")
print(f"  Author: {post.user.username}")
print(f"\nTotal posts in database: {Post.objects.count()}")
