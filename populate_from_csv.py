"""
Django script to populate database from padel_posts_dataset_refined.csv

This script:
1. Creates users from unique authors in the CSV
2. Creates posts with title, content, likes, and dislikes
3. Creates random comments for each post matching the num_comments count

Usage:
    python populate_from_csv.py
"""

import os
import django
import csv
import random
import string
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smash.settings")
django.setup()

from django.contrib.auth.models import User
from post.models import Post, PostInteraction
from comment.models import Comment, CommentInteraction

# Sample comment texts for random generation
SAMPLE_COMMENTS = [
    "Great post! Thanks for sharing.",
    "I totally agree with this.",
    "Interesting perspective!",
    "This is very helpful, thank you!",
    "I have a different opinion on this matter.",
    "Can you elaborate more on this point?",
    "Excellent analysis!",
    "I've been looking for information like this.",
    "Not sure I agree, but interesting nonetheless.",
    "Thanks for the detailed explanation!",
    "This deserves more attention.",
    "Well written and informative.",
    "I learned something new today.",
    "Could you provide more examples?",
    "This is exactly what I needed.",
    "Great discussion starter!",
    "I've experienced this too.",
    "Very insightful post.",
    "Thanks for bringing this up!",
    "Looking forward to more posts like this.",
]


def generate_random_password(length=12):
    """Generate a random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choice(characters) for _ in range(length))


def create_users_from_csv(csv_file):
    """Create users from unique authors in CSV"""
    print("Creating users from CSV...")

    authors = set()
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            author = row["author"].strip() if row["author"] else ""
            if author:  # Only add non-empty authors
                authors.add(author)

    created_count = 0
    skipped_count = 0

    for author in authors:
        # Skip if user already exists
        if User.objects.filter(username=author).exists():
            print(f"  ⊘ Skipping '{author}' - already exists")
            skipped_count += 1
            continue

        # Create new user
        password = generate_random_password()
        user = User.objects.create_user(username=author, password=password)
        print(f"  ✓ Created user: {author}")
        created_count += 1

    print(f"\nUser creation complete: {created_count} created, {skipped_count} skipped")
    return created_count, skipped_count


def create_random_comments(post, num_comments, all_users):
    """Create random comments for a post"""
    if num_comments == 0 or not all_users:
        return

    for i in range(num_comments):
        # Pick random user for comment
        commenter = random.choice(all_users)

        # Pick random comment text
        content = random.choice(SAMPLE_COMMENTS)

        # Randomly decide if it's a reply (30% chance if there are existing comments)
        parent = None
        existing_comments = list(Comment.objects.filter(post=post, parent=None))
        if existing_comments and random.random() < 0.3:
            parent = random.choice(existing_comments)

        # Create comment
        comment = Comment.objects.create(
            user=commenter,
            post=post,
            parent=parent,
            content=content,
            likes_count=random.randint(0, 50),
            dislikes_count=random.randint(0, 10),
        )

        # Optionally add some interactions to match likes/dislikes
        # Create random like/dislike interactions
        interaction_users = random.sample(
            all_users, min(random.randint(0, 5), len(all_users))
        )
        for int_user in interaction_users:
            try:
                CommentInteraction.objects.create(
                    user=int_user,
                    comment=comment,
                    interaction_type=random.choice(["like", "dislike"]),
                )
            except:
                pass  # Skip if duplicate


def create_posts_from_csv(csv_file):
    """Create posts from CSV with likes, dislikes, and comments"""
    print("\nCreating posts from CSV...")

    all_users = list(User.objects.all())
    if not all_users:
        print("Error: No users found in database!")
        return 0

    created_count = 0
    error_count = 0

    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, 1):
            try:
                author_username = row["author"].strip() if row["author"] else ""

                # Skip rows with empty author
                if not author_username:
                    print(f"  ⊘ Row {idx}: Empty author, skipping")
                    error_count += 1
                    continue

                title = row["title"]
                content = row["selftext"]
                ups = int(row["ups"]) if row["ups"] else 0
                downs = int(row["downs"]) if row["downs"] else 0
                num_comments = int(row["num_comments"]) if row["num_comments"] else 0

                # Get the author user
                try:
                    author = User.objects.get(username=author_username)
                except User.DoesNotExist:
                    print(
                        f"  ⊘ Row {idx}: User '{author_username}' not found, skipping"
                    )
                    error_count += 1
                    continue

                # Create post
                post = Post.objects.create(
                    user=author,
                    title=title[:255],  # Truncate if too long
                    content=content if content else "No content provided.",
                )

                # Create like interactions (ups)
                like_users = random.sample(all_users, min(ups, len(all_users)))
                for like_user in like_users:
                    try:
                        PostInteraction.objects.create(
                            user=like_user, post=post, interaction_type="like"
                        )
                    except:
                        pass  # Skip if duplicate

                # Create dislike interactions (downs)
                dislike_users = random.sample(all_users, min(downs, len(all_users)))
                for dislike_user in dislike_users:
                    try:
                        PostInteraction.objects.create(
                            user=dislike_user, post=post, interaction_type="dislike"
                        )
                    except:
                        pass  # Skip if duplicate

                # Create comments
                create_random_comments(post, num_comments, all_users)

                print(
                    f"  ✓ Post {idx}: '{title[:50]}...' by {author_username} "
                    f"(likes: {ups}, dislikes: {downs}, comments: {num_comments})"
                )
                created_count += 1

            except Exception as e:
                print(f"  ✗ Row {idx}: Error - {str(e)}")
                error_count += 1

    print(f"\nPost creation complete: {created_count} created, {error_count} errors")
    return created_count


def main():
    """Main function to populate database"""
    csv_file = "padel_posts_dataset_refined.csv"

    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found!")
        return

    print("=" * 70)
    print("POPULATING DATABASE FROM CSV")
    print("=" * 70)

    # Step 1: Create users
    users_created, users_skipped = create_users_from_csv(csv_file)

    # Step 2: Create posts with interactions and comments
    posts_created = create_posts_from_csv(csv_file)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Users created: {users_created}")
    print(f"Users skipped: {users_skipped}")
    print(f"Posts created: {posts_created}")
    print(f"Total users in database: {User.objects.count()}")
    print(f"Total posts in database: {Post.objects.count()}")
    print(f"Total comments in database: {Comment.objects.count()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
