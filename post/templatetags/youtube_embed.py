from django import template
from urllib.parse import urlparse, parse_qs
import re

register = template.Library()


@register.filter
def youtube_embed_url(url):
    """
    Convert a YouTube URL to an embed URL.
    Supports formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID (already embed)
    """
    if not url:
        return url

    # Extract video ID
    video_id = None

    # Handle youtu.be/VIDEO_ID format
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]

    # Handle youtube.com/watch?v=VIDEO_ID format
    elif "youtube.com/watch" in url:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        video_id = query_params.get("v", [None])[0]

    # Handle youtube.com/embed/VIDEO_ID (already embed)
    elif "youtube.com/embed/" in url:
        video_id = url.split("youtube.com/embed/")[1].split("?")[0].split("&")[0]

    # If we found a video ID, return the embed URL
    if video_id:
        # Use youtube-nocookie.com for better privacy and add necessary parameters
        return (
            f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1"
        )

    # Return original URL if we couldn't parse it
    return url
