import random
import time
import os
from atproto import Client
from datetime import datetime, timezone, timedelta

# Bluesky credentials
BLUESKY_HANDLE = "joealwynpenguin.bsky.social"
BLUESKY_PASSWORD = os.environ.get("BLUESKY_PASSWORD")

# Path to the image you want to reply with
FUNERAL_IMAGE_PATH = "funeral_image.jpeg"

# The AT-URI for the list you linked
# (Translated from: https://bsky.app/profile/did:plc:sqiwiasxodn6p37ypdiif2mn/lists/3laobzajs672u)
TARGET_LIST_URI = "at://did:plc:sqiwiasxodn6p37ypdiif2mn/app.bsky.graph.list/3laobzajs672u"

# File to permanently store replied post URIs
REPLIED_POSTS_FILE = "replied_posts.txt"

# Load existing replies from the file
def load_replied_posts():
    if os.path.exists(REPLIED_POSTS_FILE):
        with open(REPLIED_POSTS_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()

replied_posts = load_replied_posts()

# Helper function to save a new reply to the file and our set
def save_replied_post(uri):
    with open(REPLIED_POSTS_FILE, "a") as f:
        f.write(uri + "\n")
    replied_posts.add(uri)

# Function to choose a random line from the file
def get_random_line(filename="joealwyn.txt"):
    with open(filename, "r", encoding="utf-8") as file:
        lines = file.readlines()
    return random.choice(lines).strip() if lines else "No content available."

# Function to post on Bluesky
def post_to_bluesky():
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
    text = get_random_line()
    if text:
        client.send_post("joe alwyn " + text)
        print(f"Posted: {text}")
    else:
        print("File is empty, no post made.")

# NEW: Function to fetch all handles from your specific Bluesky list
def get_list_members(client, list_uri):
    handles = set()
    cursor = None

    print("Fetching allowed accounts from your Bluesky list...")
    while True:
        params = {'list': list_uri, 'limit': 100}
        if cursor:
            params['cursor'] = cursor

        try:
            response = client.app.bsky.graph.get_list(params=params)
            for item in response.items:
                handles.add(item.subject.handle)

            # Check if there's another page of accounts to fetch
            cursor = getattr(response, 'cursor', None)
            if not cursor:
                break
        except Exception as e:
            print(f"Error fetching list: {e}")
            break

    print(f"Found {len(handles)} accounts in the list.")
    return handles

# Function to search for posts and reply
def search_and_reply():
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

    # 1. Dynamically fetch the allowed accounts right before searching
    allowed_accounts = get_list_members(client, TARGET_LIST_URI)

    if not allowed_accounts:
        print("Allowed accounts list is empty or failed to load. Skipping search cycle.")
        return

    # Search for posts containing the trigger phrases
    search_phrases = ["we've reached the funeral scene", "we are in the funeral scene", "are we in the funeral scene", "this is the funeral scene", "is this the funeral scene"]

    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time - timedelta(hours=24)

    for phrase in search_phrases:
        try:
            search_results = client.app.bsky.feed.search_posts(params={'q': phrase, 'limit': 25})

            for post in search_results.posts:
                # 2. Check if the author is in our dynamically fetched list
                if post.author.handle not in allowed_accounts:
                    continue

                if post.uri in replied_posts:
                    continue

                post_time = datetime.fromisoformat(post.indexed_at.replace('Z', '+00:00'))
                if post_time < cutoff_time:
                    continue

                post_text = post.record.text.lower()
                phrase_in_text = phrase in post_text

                phrase_in_alt = False
                if hasattr(post.record, 'embed') and post.record.embed:
                    if hasattr(post.record.embed, 'images'):
                        for img in post.record.embed.images:
                            if hasattr(img, 'alt') and img.alt and phrase in img.alt.lower():
                                phrase_in_alt = True
                                break

                if not phrase_in_text:
                    continue

                try:
                    with open(FUNERAL_IMAGE_PATH, 'rb') as f:
                        img_data = f.read()

                    upload = client.upload_blob(img_data)

                    reply_ref = {
                        'root': {
                            'uri': post.record.reply.root.uri if hasattr(post.record, 'reply') and post.record.reply else post.uri,
                            'cid': post.record.reply.root.cid if hasattr(post.record, 'reply') and post.record.reply else post.cid
                        },
                        'parent': {
                            'uri': post.uri,
                            'cid': post.cid
                        }
                    }

                    client.send_post(
                        text="",
                        reply_to=reply_ref,
                        embed={
                            '$type': 'app.bsky.embed.images',
                            'images': [{
                                'alt': "Meme image with 'we've reached the funeral scene' written over again with arrows in an endless cycle",
                                'image': upload.blob
                            }]
                        }
                    )

                    print(f"Replied with image to post by @{post.author.handle}: {post.record.text[:50]}...")
                    save_replied_post(post.uri)
                    time.sleep(2)

                except Exception as e:
                    print(f"Error replying to post: {e}")

        except Exception as e:
            print(f"Error searching for '{phrase}': {e}")

if __name__ == "__main__":
    post_to_bluesky()
    search_and_reply()
