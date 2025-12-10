import praw
import feedparser
import time
import json
import os
import logging
import datetime
import sys
import re
import requests
import requests
from bs4 import BeautifulSoup
from praw.models import InlineImage

# --- Configuration ---
# Load environment variables
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "qglHUUE1pI38Rv6SMylqfw")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "j52XX1kivOmbdm2mij-fjhx4o1tDpA")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "python:news-bot:v1.0 (by /u/Ok_Consequence138)")
REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME", "Ok_Consequence138")
REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD", "igloo@gmail.com2")
SUBREDDIT_NAME = os.environ.get("SUBREDDIT_NAME", "4infotainment")

# RSS Feeds List - India Specific
RSS_FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",       # Times of India Top Stories
    "https://feeds.feedburner.com/ndtvnews-top-stories",                # NDTV Top Stories
    "https://www.thehindu.com/news/national/feeder/default.rss",        # The Hindu National
    "https://www.indiatoday.in/rss/1206584",                            # India Today Top Stories
    "https://indianexpress.com/section/india/feed/"                     # Indian Express India
]

POSTED_URLS_FILE = "posted_urls.json"
POST_INTERVAL = 1800  # 30 minutes in seconds

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_posted_urls():
    """Load the list of already posted URLs from a JSON file."""
    if not os.path.exists(POSTED_URLS_FILE):
        return []
    try:
        with open(POSTED_URLS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        logger.error("Failed to load posted URLs. Starting fresh.")
        return []

def fetch_article_details(url):
    """Fetch og:image and og:description from a webpage."""
    details = {"image": None, "description": None}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get Image
            og_image = soup.find("meta", property="og:image")
            if og_image:
                details["image"] = og_image.get("content")
                
            # Get Description
            og_desc = soup.find("meta", property="og:description")
            if og_desc:
                details["description"] = og_desc.get("content")
            else:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    details["description"] = meta_desc.get("content")
                    
    except Exception as e:
        logger.warning(f"Failed to fetch extracted details for {url}: {e}")
    return details

def download_image(url):
    """Download image to a temporary file."""
    try:
        if not url:
            return None
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            filename = "temp_image.jpg"
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return filename
    except Exception as e:
        logger.error(f"Failed to download image {url}: {e}")
    return None

def extract_image_url(entry, scraped_details):
    """Extract the best image URL from an RSS entry or scraped details."""
    # 0. Use scraped og:image if available
    if scraped_details.get("image"):
        return scraped_details["image"]

    # 1. Check media_content
    if "media_content" in entry:
        for media in entry.media_content:
            if media.get("medium") == "image" or "image" in media.get("type", ""):
                return media.get("url")
    
    # 2. Check media_thumbnail
    if "media_thumbnail" in entry:
        return entry.media_thumbnail[0].get("url")

    # 3. Check links (enclosures)
    if "links" in entry:
        for link in entry.links:
            if "image" in link.get("type", ""):
                return link.get("href")
    
    # 4. Check summary for img tag (fallback)
    if "summary" in entry:
        match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
        if match:
            return match.group(1)

    return None

def clean_html(raw_html):
    """Remove HTML tags from a string using BeautifulSoup."""
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    except:
        # Fallback to regex if BS4 fails
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext.strip()

def save_posted_url(url):
    """Save a new URL to the list of posted URLs."""
    posted_urls = load_posted_urls()
    posted_urls.append(url)
    # Keep the list size manageable (e.g., last 1000 posts)
    if len(posted_urls) > 1000:
        posted_urls = posted_urls[-1000:]
    
    try:
        with open(POSTED_URLS_FILE, "w") as f:
            json.dump(posted_urls, f)
    except IOError:
        logger.error("Failed to save posted URL.")

def get_reddit_instance():
    """Initialize and return the PRAW Reddit instance."""
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD
        )
        # Verify credentials
        logger.info(f"Logged in as: {reddit.user.me()}")
        return reddit
    except Exception as e:
        logger.critical(f"Failed to authenticate with Reddit: {e}")
        sys.exit(1)

def fetch_latest_article(posted_urls):
    """Fetch the latest unposted article from RSS feeds."""
    for feed_url in RSS_FEEDS:
        try:
            logger.info(f"Checking feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                continue

            # Check entries in the feed
            for entry in feed.entries:
                link = entry.get("link")
                title = entry.get("title")
                
                if link and link not in posted_urls:
                    logger.info(f"Found new article: {title}")
                    
                    # Fetch additional details from the article page
                    scraped_details = fetch_article_details(link)
                    
                    # Determine summary
                    rss_summary = entry.get("summary", "") or entry.get("description", "") or (entry.get("content")[0].get("value") if entry.get("content") else "")
                    final_summary = rss_summary if len(rss_summary) > 20 else scraped_details.get("description", "")
                    
                    return {
                        "title": title,
                        "link": link,
                        "summary": final_summary,
                        "image": extract_image_url(entry, scraped_details)
                    }
        except Exception as e:
            logger.error(f"Error parsing feed {feed_url}: {e}")
            continue
            
    return None

def main():
    """Main bot loop."""
    logger.info("Starting Reddit News Bot...")
    
    # Validate environment variables
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, SUBREDDIT_NAME]):
        logger.critical("Missing required environment variables. Please check your configuration.")
        sys.exit(1)

    reddit = get_reddit_instance()
    subreddit = reddit.subreddit(SUBREDDIT_NAME)

    while True:
        start_time = time.time()
        
        try:
            posted_urls = load_posted_urls()
            article = fetch_latest_article(posted_urls)

            if article:
                title = article["title"]
                link = article["link"]
                
                logger.info(f"Posting to r/{SUBREDDIT_NAME}: {title}")
                
                try:
                    # Construct post body
                    summary = article.get("summary", "")
                    clean_summary = clean_html(summary)
                    image_url = article.get("image")
                    
                    submission = None
                    
                    # Try to download and post as Inline Media Post (Rich Text)
                    local_image = download_image(image_url)
                    
                    if local_image:
                        try:
                            logger.info(f"Uploading inline image: {local_image}")
                            
                            # Define the placeholder key
                            img_key = "article_image"
                            
                            # Construct the rich text body
                            # Note: We use the placeholder {article_image} where we want the image to appear
                            rich_text_body = f"{clean_summary}\n\n{{article_image}}\n\n[Read the full article]({link})"
                            
                            # Create the inline media dict
                            media = {img_key: InlineImage(path=local_image)}
                            
                            # Submit
                            submission = subreddit.submit(title=title, selftext=rich_text_body, inline_media=media)
                            os.remove(local_image) # Cleanup
                            
                        except Exception as img_err:
                            logger.error(f"Failed to upload inline image: {img_err}")
                            # Fallback to Link Post if upload fails
                            submission = subreddit.submit(title=title, url=link)
                    else:
                        # Fallback to Link Post if no image
                        submission = subreddit.submit(title=title, url=link)

                    save_posted_url(link)
                    logger.info(f"Post submitted successfully: https://www.reddit.com{submission.permalink}")

                except Exception as e:
                    logger.error(f"Failed to submit post: {e}")
            else:
                logger.info("No new articles found in any feed.")

        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")

        # Calculate sleep time to maintain 2 posts/hour schedule
        elapsed_time = time.time() - start_time
        sleep_time = max(0, POST_INTERVAL - elapsed_time)
        
        logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
