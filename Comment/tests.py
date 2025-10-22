from django.test import TestCase
from django.contrib.auth.models import User
import uuid
import time

from .models import Comment
from Post.models import ForumPost


class CommentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pw")
        self.post = ForumPost.objects.create(
            title="Test Post",
            content="Post content",
            author=self.user,
            category="discussion",
        )

    def test_create_comment_fields(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="hello")
        # id should be a uuid instance
        self.assertIsInstance(c.id, uuid.UUID)
        self.assertEqual(c.content, "hello")
        self.assertEqual(c.post, self.post)
        self.assertEqual(c.author, self.user)
        self.assertIsNotNone(c.created_at)
        self.assertIsNotNone(c.updated_at)

    def test_related_name_and_count(self):
        Comment.objects.create(post=self.post, author=self.user, content="a")
        Comment.objects.create(post=self.post, author=self.user, content="b")
        self.assertEqual(self.post.comments.count(), 2)
        contents = list(self.post.comments.values_list("content", flat=True))
        self.assertIn("a", contents)
        self.assertIn("b", contents)

    def test_str(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="xyz")
        self.assertIn("Comment", str(c))
        self.assertIn(str(self.post), str(c))

    def test_author_nullable(self):
        c = Comment.objects.create(post=self.post, author=None, content="no author")
        self.assertIsNone(c.author)
        # __str__ should still return a string
        self.assertIsInstance(str(c), str)

    def test_updated_at_changes_but_created_at_stays(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="first")
        old_created = c.created_at
        old_updated = c.updated_at
        time.sleep(0.1)
        c.content = "second"
        c.save()
        c.refresh_from_db()
        self.assertEqual(c.created_at, old_created)
        self.assertGreater(c.updated_at, old_updated)

    def test_post_delete_cascades(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="x")
        self.post.delete()
        self.assertFalse(Comment.objects.filter(id=c.id).exists())

    # ...existing code...
    # New tests for ForumPost like/dislike/unlike/undislike methods

    def test_like_increments(self):
        self.assertEqual(self.post.likes, 0)
        self.post.like()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 1)
        # multiple likes accumulate
        self.post.like()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 2)

    def test_dislike_increments(self):
        self.assertEqual(self.post.dislikes, 0)
        self.post.dislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 1)
        # multiple dislikes accumulate
        self.post.dislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 2)

    def test_unlike_decrements_and_not_below_zero(self):
        # unlike when zero should not go negative
        self.assertEqual(self.post.likes, 0)
        self.post.unlike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 0)

        # set likes to 2 and decrement
        self.post.likes = 2
        self.post.save()
        self.post.unlike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 1)
        # decrement to zero and ensure no negative values
        self.post.unlike()
        self.post.unlike()  # extra call should keep at 0
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 0)

    def test_undislike_decrements_and_not_below_zero(self):
        # undislike when zero should not go negative
        self.assertEqual(self.post.dislikes, 0)
        self.post.undislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 0)

        # set dislikes to 2 and decrement
        self.post.dislikes = 2
        self.post.save()
        self.post.undislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 1)
        # decrement to zero and ensure no negative values
        self.post.undislike()
        self.post.undislike()  # extra call should keep at 0
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 0)
