from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

from .models import Comment, CommentInteraction
from post.models import Post

User = get_user_model()


class CommentModelTests(TestCase):
    """Tests for Comment model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", password="testpass123"
        )
        self.post = Post.objects.create(
            user=self.user,
            title="Test Post",
            content="This is a test post content",
        )

    def test_create_comment(self):
        """Test creating a basic comment"""
        comment = Comment.objects.create(
            user=self.user, post=self.post, content="This is a test comment"
        )
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.content, "This is a test comment")
        self.assertIsNotNone(comment.created_at)
        self.assertIsNotNone(comment.updated_at)
        self.assertEqual(comment.likes_count, 0)
        self.assertEqual(comment.dislikes_count, 0)
        self.assertFalse(comment.is_deleted)

    def test_comment_str(self):
        """Test comment string representation"""
        comment = Comment.objects.create(user=self.user, post=self.post, content="Test")
        expected = f"Komentar oleh {self.user.username} pada {self.post.title}"
        self.assertEqual(str(comment), expected)

    def test_comment_with_emoji(self):
        """Test comment with emoji"""
        comment = Comment.objects.create(
            user=self.user, post=self.post, content="Great post!", emoji="👍"
        )
        self.assertEqual(comment.emoji, "👍")

    def test_nested_comment(self):
        """Test nested comment (reply)"""
        parent_comment = Comment.objects.create(
            user=self.user, post=self.post, content="Parent comment"
        )
        reply = Comment.objects.create(
            user=self.user2,
            post=self.post,
            parent=parent_comment,
            content="Reply to parent",
        )
        self.assertEqual(reply.parent, parent_comment)
        self.assertTrue(reply.is_reply)
        self.assertFalse(parent_comment.is_reply)
        self.assertIn(reply, parent_comment.replies.all())

    def test_soft_delete_comment(self):
        """Test soft delete functionality"""
        comment = Comment.objects.create(
            user=self.user, post=self.post, content="To be deleted"
        )
        comment.delete()
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)
        # Verify comment still exists in database
        self.assertTrue(Comment.objects.filter(id=comment.id).exists())

    def test_comment_ordering(self):
        """Test comment ordering by likes and created_at"""
        comment1 = Comment.objects.create(
            user=self.user, post=self.post, content="First comment", likes_count=5
        )
        comment2 = Comment.objects.create(
            user=self.user, post=self.post, content="Second comment", likes_count=10
        )
        comment3 = Comment.objects.create(
            user=self.user, post=self.post, content="Third comment", likes_count=10
        )

        comments = Comment.objects.filter(post=self.post)
        # Should be ordered by likes_count desc, then created_at desc
        self.assertEqual(comments[0].likes_count, 10)
        self.assertIn(comments[0], [comment2, comment3])

    def test_post_cascade_delete(self):
        """Test that deleting post soft-deletes it (comments remain)"""
        comment = Comment.objects.create(user=self.user, post=self.post, content="Test")
        comment_id = comment.id

        # Post uses soft delete, so it just marks as deleted
        self.post.delete()

        # Comment should still exist in database
        self.assertTrue(Comment.objects.filter(id=comment_id).exists())

        # But post should be marked as deleted
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)

        # Test actual cascade delete (hard delete)
        Comment.objects.all().delete()
        Post.objects.filter(id=self.post.id).delete()
        self.assertFalse(Comment.objects.filter(id=comment_id).exists())


class CommentInteractionModelTests(TestCase):
    """Tests for CommentInteraction model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", password="testpass123"
        )
        self.post = Post.objects.create(
            user=self.user, title="Test Post", content="Test content"
        )
        self.comment = Comment.objects.create(
            user=self.user, post=self.post, content="Test comment"
        )

    def test_create_like_interaction(self):
        """Test creating a like interaction"""
        interaction = CommentInteraction.objects.create(
            user=self.user2, comment=self.comment, interaction_type="like"
        )
        self.assertEqual(interaction.user, self.user2)
        self.assertEqual(interaction.comment, self.comment)
        self.assertEqual(interaction.interaction_type, "like")
        self.assertIsNotNone(interaction.created_at)

    def test_create_dislike_interaction(self):
        """Test creating a dislike interaction"""
        interaction = CommentInteraction.objects.create(
            user=self.user2, comment=self.comment, interaction_type="dislike"
        )
        self.assertEqual(interaction.interaction_type, "dislike")

    def test_interaction_str(self):
        """Test interaction string representation"""
        interaction = CommentInteraction.objects.create(
            user=self.user2, comment=self.comment, interaction_type="like"
        )
        expected = f"{self.user2.username} - like - Comment #{self.comment.id}"
        self.assertEqual(str(interaction), expected)

    def test_unique_together_constraint(self):
        """Test that a user can only have one interaction per comment"""
        CommentInteraction.objects.create(
            user=self.user2, comment=self.comment, interaction_type="like"
        )
        # Trying to create another interaction should fail
        with self.assertRaises(Exception):
            CommentInteraction.objects.create(
                user=self.user2, comment=self.comment, interaction_type="dislike"
            )

    def test_interaction_cascade_delete_on_comment(self):
        """Test that deleting comment cascades to interactions"""
        interaction = CommentInteraction.objects.create(
            user=self.user2, comment=self.comment, interaction_type="like"
        )
        interaction_id = interaction.id
        self.comment.delete()
        # Hard delete for this test
        Comment.objects.filter(id=self.comment.id).delete()
        self.assertFalse(CommentInteraction.objects.filter(id=interaction_id).exists())

    def test_interaction_cascade_delete_on_user(self):
        """Test that deleting user cascades to their interactions"""
        interaction = CommentInteraction.objects.create(
            user=self.user2, comment=self.comment, interaction_type="like"
        )
        interaction_id = interaction.id
        self.user2.delete()
        self.assertFalse(CommentInteraction.objects.filter(id=interaction_id).exists())


class CommentAPIViewTests(TestCase):
    """Tests for Comment API views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", password="testpass123"
        )
        self.post = Post.objects.create(
            user=self.user, title="Test Post", content="Test content"
        )

    def test_get_comments_for_post(self):
        """Test getting all comments for a post"""
        Comment.objects.create(user=self.user, post=self.post, content="Comment 1")
        Comment.objects.create(user=self.user2, post=self.post, content="Comment 2")

        response = self.client.get(f"/comments/post/{self.post.id}/")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["comments"]), 2)
        self.assertEqual(data["total_comments"], 2)

    def test_create_comment_authenticated(self):
        """Test creating a comment when authenticated"""
        self.client.login(username="testuser", password="testpass123")

        comment_data = {"content": "New test comment", "emoji": "😊"}
        response = self.client.post(
            f"/comments/post/{self.post.id}/",
            data=json.dumps(comment_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertIn("comment_id", data)

        # Verify comment was created
        comment = Comment.objects.get(id=data["comment_id"])
        self.assertEqual(comment.content, "New test comment")
        self.assertEqual(comment.emoji, "😊")

    def test_create_comment_unauthenticated(self):
        """Test creating comment without authentication"""
        comment_data = {"content": "Test comment"}
        response = self.client.post(
            f"/comments/post/{self.post.id}/",
            data=json.dumps(comment_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_create_comment_without_content_or_emoji(self):
        """Test creating comment without content or emoji fails"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            f"/comments/post/{self.post.id}/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_nested_comment(self):
        """Test creating a reply to a comment"""
        self.client.login(username="testuser", password="testpass123")

        parent = Comment.objects.create(
            user=self.user, post=self.post, content="Parent comment"
        )

        reply_data = {"content": "Reply comment", "parent_id": parent.id}
        response = self.client.post(
            f"/comments/post/{self.post.id}/",
            data=json.dumps(reply_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        reply = Comment.objects.get(id=data["comment_id"])
        self.assertEqual(reply.parent, parent)
        self.assertTrue(reply.is_reply)

    def test_update_comment_as_owner(self):
        """Test updating comment as the owner"""
        self.client.login(username="testuser", password="testpass123")

        comment = Comment.objects.create(
            user=self.user, post=self.post, content="Original content"
        )

        update_data = {"content": "Updated content"}
        response = self.client.put(
            f"/comments/{comment.id}/",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "Updated content")

    def test_update_comment_as_non_owner(self):
        """Test updating comment as non-owner fails"""
        self.client.login(username="testuser2", password="testpass123")

        comment = Comment.objects.create(
            user=self.user, post=self.post, content="Original content"
        )

        update_data = {"content": "Hacked content"}
        response = self.client.put(
            f"/comments/{comment.id}/",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_delete_comment_as_owner(self):
        """Test deleting comment as owner"""
        self.client.login(username="testuser", password="testpass123")

        comment = Comment.objects.create(
            user=self.user, post=self.post, content="To be deleted"
        )

        response = self.client.delete(f"/comments/{comment.id}/")
        self.assertEqual(response.status_code, 200)

        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)

    def test_get_comments_excludes_deleted(self):
        """Test that deleted comments are not returned"""
        comment1 = Comment.objects.create(
            user=self.user, post=self.post, content="Active comment"
        )
        comment2 = Comment.objects.create(
            user=self.user, post=self.post, content="Deleted comment", is_deleted=True
        )

        response = self.client.get(f"/comments/post/{self.post.id}/")
        data = json.loads(response.content)

        self.assertEqual(data["total_comments"], 1)
        self.assertEqual(data["comments"][0]["content"], "Active comment")


class CommentInteractionViewTests(TestCase):
    """Tests for Comment Interaction views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.post = Post.objects.create(
            user=self.user, title="Test Post", content="Test content"
        )
        self.comment = Comment.objects.create(
            user=self.user, post=self.post, content="Test comment"
        )

    def test_like_comment(self):
        """Test liking a comment"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            f"/comments/{self.comment.id}/like/", content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "liked")
        self.assertEqual(data["likes_count"], 1)

        # Verify interaction was created
        self.assertTrue(
            CommentInteraction.objects.filter(
                user=self.user, comment=self.comment, interaction_type="like"
            ).exists()
        )

    def test_unlike_comment(self):
        """Test unliking a comment (toggle off)"""
        self.client.login(username="testuser", password="testpass123")

        # First like
        CommentInteraction.objects.create(
            user=self.user, comment=self.comment, interaction_type="like"
        )
        self.comment.likes_count = 1
        self.comment.save()

        # Then unlike
        response = self.client.post(
            f"/comments/{self.comment.id}/like/", content_type="application/json"
        )
        data = json.loads(response.content)

        self.assertEqual(data["message"], "Like removed")
        self.assertEqual(data["likes_count"], 0)
        self.assertFalse(
            CommentInteraction.objects.filter(
                user=self.user, comment=self.comment
            ).exists()
        )

    def test_dislike_comment(self):
        """Test disliking a comment"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            f"/comments/{self.comment.id}/dislike/", content_type="application/json"
        )
        data = json.loads(response.content)

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "disliked")
        self.assertEqual(data["dislikes_count"], 1)

    def test_switch_like_to_dislike(self):
        """Test switching from like to dislike"""
        self.client.login(username="testuser", password="testpass123")

        # First like
        CommentInteraction.objects.create(
            user=self.user, comment=self.comment, interaction_type="like"
        )
        self.comment.likes_count = 1
        self.comment.save()

        # Then dislike
        response = self.client.post(
            f"/comments/{self.comment.id}/dislike/", content_type="application/json"
        )
        data = json.loads(response.content)

        self.assertEqual(data["message"], "Changed to dislike")
        self.assertEqual(data["likes_count"], 0)
        self.assertEqual(data["dislikes_count"], 1)

        # Verify interaction type changed
        interaction = CommentInteraction.objects.get(
            user=self.user, comment=self.comment
        )
        self.assertEqual(interaction.interaction_type, "dislike")

    def test_interaction_unauthenticated(self):
        """Test that unauthenticated users cannot interact"""
        response = self.client.post(
            f"/comments/{self.comment.id}/like/", content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_action(self):
        """Test invalid action returns error"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            f"/comments/{self.comment.id}/invalid_action/",
            content_type="application/json",
        )
        # Check if it's either 400 or 404 (both are acceptable for invalid route)
        self.assertIn(response.status_code, [400, 404])

    def test_interaction_on_deleted_comment(self):
        """Test interaction on deleted comment fails"""
        self.client.login(username="testuser", password="testpass123")

        self.comment.is_deleted = True
        self.comment.save()

        response = self.client.post(
            f"/comments/{self.comment.id}/like/", content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)


class CommentEdgeCasesTests(TestCase):
    """Tests for edge cases and error handling"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.post = Post.objects.create(
            user=self.user, title="Test Post", content="Test content"
        )
        self.comment = Comment.objects.create(
            user=self.user, post=self.post, content="Test comment"
        )

    def test_get_single_comment(self):
        """Test getting a single comment by ID"""
        response = self.client.get(f"/comments/{self.comment.id}/")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["comment"]["id"], self.comment.id)
        self.assertEqual(data["comment"]["content"], "Test comment")
        self.assertIn("replies", data["comment"])

    def test_get_single_comment_with_replies(self):
        """Test getting a comment with its replies"""
        reply = Comment.objects.create(
            user=self.user,
            post=self.post,
            parent=self.comment,
            content="Reply to comment",
        )

        response = self.client.get(f"/comments/{self.comment.id}/")
        data = json.loads(response.content)

        self.assertEqual(len(data["comment"]["replies"]), 1)
        self.assertEqual(data["comment"]["replies"][0]["content"], "Reply to comment")

    def test_get_single_comment_not_found(self):
        """Test getting non-existent comment returns 404"""
        response = self.client.get("/comments/99999/")
        self.assertEqual(response.status_code, 404)

    def test_get_comments_without_post_or_comment_id(self):
        """Test GET without post_id or comment_id returns error"""
        response = self.client.get("/comments/post//")
        # This will likely return 404 from URL routing
        self.assertIn(response.status_code, [400, 404])

    def test_create_comment_missing_post_id(self):
        """Test creating comment without post_id fails"""
        self.client.login(username="testuser", password="testpass123")

        # This should fail in URL routing or view logic
        comment_data = {"content": "Test"}
        response = self.client.post(
            "/comments/post//",
            data=json.dumps(comment_data),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [400, 404])

    def test_create_comment_nonexistent_post(self):
        """Test creating comment for non-existent post"""
        self.client.login(username="testuser", password="testpass123")

        comment_data = {"content": "Test comment"}
        response = self.client.post(
            "/comments/post/99999/",
            data=json.dumps(comment_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_create_comment_with_nonexistent_parent(self):
        """Test creating reply with non-existent parent comment"""
        self.client.login(username="testuser", password="testpass123")

        reply_data = {"content": "Reply", "parent_id": 99999}
        response = self.client.post(
            f"/comments/post/{self.post.id}/",
            data=json.dumps(reply_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_create_comment_exception_handling(self):
        """Test exception handling in comment creation"""
        self.client.login(username="testuser", password="testpass123")

        # Send invalid JSON to trigger exception
        response = self.client.post(
            f"/comments/post/{self.post.id}/",
            data="invalid json{",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_update_comment_without_comment_id(self):
        """Test updating comment without comment_id"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.put(
            "/comments//",
            data=json.dumps({"content": "Updated"}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [400, 404])

    def test_update_nonexistent_comment(self):
        """Test updating non-existent comment"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.put(
            "/comments/99999/",
            data=json.dumps({"content": "Updated"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_update_comment_exception_handling(self):
        """Test exception handling in comment update"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.put(
            f"/comments/{self.comment.id}/",
            data="invalid json{",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_delete_comment_without_comment_id(self):
        """Test deleting comment without comment_id"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.delete("/comments//")
        self.assertIn(response.status_code, [400, 404])

    def test_delete_nonexistent_comment(self):
        """Test deleting non-existent comment"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.delete("/comments/99999/")
        self.assertEqual(response.status_code, 404)

    def test_delete_comment_exception_handling(self):
        """Test exception handling in comment deletion"""
        self.client.login(username="testuser", password="testpass123")

        # Create a comment and then manually delete it to cause DB inconsistency
        comment = Comment.objects.create(
            user=self.user, post=self.post, content="To delete"
        )
        comment_id = comment.id
        Comment.objects.filter(id=comment_id).delete()

        response = self.client.delete(f"/comments/{comment_id}/")
        self.assertEqual(response.status_code, 404)

    def test_get_comments_with_user_interaction(self):
        """Test getting comments includes user interaction when authenticated"""
        self.client.login(username="testuser", password="testpass123")

        # Create interaction
        CommentInteraction.objects.create(
            user=self.user, comment=self.comment, interaction_type="like"
        )

        response = self.client.get(f"/comments/post/{self.post.id}/")
        data = json.loads(response.content)

        self.assertEqual(data["comments"][0]["user_interaction"], "like")

    def test_get_comments_sorted(self):
        """Test getting comments with custom sorting"""
        Comment.objects.create(user=self.user, post=self.post, content="Comment 2")

        response = self.client.get(f"/comments/post/{self.post.id}/?sort_by=created_at")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(len(data["comments"]), 2)

    def test_get_comments_with_replies(self):
        """Test getting comments includes nested replies"""
        reply1 = Comment.objects.create(
            user=self.user,
            post=self.post,
            parent=self.comment,
            content="Reply 1",
        )
        reply2 = Comment.objects.create(
            user=self.user,
            post=self.post,
            parent=self.comment,
            content="Reply 2",
        )

        response = self.client.get(f"/comments/post/{self.post.id}/")
        data = json.loads(response.content)

        self.assertEqual(len(data["comments"][0]["replies"]), 2)

    def test_get_comments_excludes_child_comments(self):
        """Test that child comments are not returned as top-level"""
        Comment.objects.create(
            user=self.user,
            post=self.post,
            parent=self.comment,
            content="Reply",
        )

        response = self.client.get(f"/comments/post/{self.post.id}/")
        data = json.loads(response.content)

        # Should only have 1 parent comment, not the reply
        self.assertEqual(data["total_comments"], 1)

    def test_report_comment(self):
        """Test reporting a comment"""
        self.client.login(username="testuser", password="testpass123")

        report_data = {"category": "SPAM", "description": "This is spam"}
        response = self.client.post(
            f"/comments/{self.comment.id}/report/",
            data=json.dumps(report_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertIn("report_id", data)

    def test_interaction_nonexistent_comment(self):
        """Test interaction on non-existent comment"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            "/comments/99999/like/", content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

    def test_interaction_exception_handling(self):
        """Test exception handling in comment interactions"""
        self.client.login(username="testuser", password="testpass123")

        # Send invalid JSON
        response = self.client.post(
            f"/comments/{self.comment.id}/report/",
            data="invalid json{",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_update_comment_with_emoji(self):
        """Test updating comment emoji"""
        self.client.login(username="testuser", password="testpass123")

        update_data = {"emoji": "🎉"}
        response = self.client.put(
            f"/comments/{self.comment.id}/",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.emoji, "🎉")

    def test_switch_dislike_to_like(self):
        """Test switching from dislike to like"""
        self.client.login(username="testuser", password="testpass123")

        # First dislike
        CommentInteraction.objects.create(
            user=self.user, comment=self.comment, interaction_type="dislike"
        )
        self.comment.dislikes_count = 1
        self.comment.save()

        # Then like
        response = self.client.post(
            f"/comments/{self.comment.id}/like/", content_type="application/json"
        )
        data = json.loads(response.content)

        self.assertEqual(data["message"], "Changed to like")
        self.assertEqual(data["likes_count"], 1)
        self.assertEqual(data["dislikes_count"], 0)

        # Verify interaction type changed
        interaction = CommentInteraction.objects.get(
            user=self.user, comment=self.comment
        )
        self.assertEqual(interaction.interaction_type, "like")

    def test_undislike_comment(self):
        """Test undisliking a comment (toggle dislike off)"""
        self.client.login(username="testuser", password="testpass123")

        # First dislike
        CommentInteraction.objects.create(
            user=self.user, comment=self.comment, interaction_type="dislike"
        )
        self.comment.dislikes_count = 1
        self.comment.save()

        # Then undislike
        response = self.client.post(
            f"/comments/{self.comment.id}/dislike/", content_type="application/json"
        )
        data = json.loads(response.content)

        self.assertEqual(data["message"], "Dislike removed")
        self.assertEqual(data["dislikes_count"], 0)
        self.assertFalse(
            CommentInteraction.objects.filter(
                user=self.user, comment=self.comment
            ).exists()
        )

    def test_get_comment_exception_handling(self):
        """Test exception handling when getting comments"""
        # This tests the generic Exception handler
        # We can trigger it by causing a database error or similar
        # For now, we'll test with an invalid scenario

        # Test accessing CommentAPIView.get directly without proper setup
        from comment.views import CommentAPIView
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/comments/invalid/")
        request.user = self.user

        view = CommentAPIView()
        # This should trigger exception handling
        response = view.get(request, post_id=None, comment_id=None)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")

    def test_get_comments_unauthenticated_no_interaction(self):
        """Test getting comments when unauthenticated shows no interaction"""
        # Don't login - test as anonymous user
        Comment.objects.create(user=self.user, post=self.post, content="Test")

        response = self.client.get(f"/comments/post/{self.post.id}/")
        data = json.loads(response.content)

        # Should succeed but user_interaction should be None
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(data["comments"][0]["user_interaction"])

    def test_update_comment_unauthenticated(self):
        """Test updating comment without authentication"""
        update_data = {"content": "Hacked"}
        response = self.client.put(
            f"/comments/{self.comment.id}/",
            data=json.dumps(update_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_comment_unauthenticated(self):
        """Test deleting comment without authentication"""
        response = self.client.delete(f"/comments/{self.comment.id}/")
        self.assertEqual(response.status_code, 401)

    def test_delete_comment_generic_exception(self):
        """Test generic exception handling in delete"""
        self.client.login(username="testuser", password="testpass123")

        # Trigger exception by mocking
        from unittest.mock import patch

        with patch.object(
            Comment.objects, "get", side_effect=Exception("Database error")
        ):
            response = self.client.delete(f"/comments/{self.comment.id}/")
            data = json.loads(response.content)

            self.assertEqual(response.status_code, 500)
            self.assertIn("Error deleting comment", data["message"])

    def test_get_comments_generic_exception(self):
        """Test generic exception handling in get comments"""
        from unittest.mock import patch

        # Trigger exception during query
        with patch.object(Post.objects, "get", side_effect=Exception("Database error")):
            response = self.client.get(f"/comments/post/{self.post.id}/")
            data = json.loads(response.content)

            self.assertEqual(response.status_code, 500)
            self.assertIn("Error retrieving comments", data["message"])
