import requests
import json
import time
from pprint import pprint
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Load Configuration Securely ---
def load_config():
    with open("insights_config.json", "r") as config_file:
        return json.load(config_file)

config = load_config()
ACCESS_TOKEN = config["ACCESS_TOKEN"]
ACCOUNT_ID = config["ACCOUNT_ID"]
CHROMEDRIVER_PATH = config["CHROMEDRIVER_PATH"]

BASE_URL = "https://graph.facebook.com/v17.0/"

# --- Driver Connections ---
def connect_chrome_driver(url):
    # Fetches the full Instagram post HTML
    options = Options()
    options.headless = True
    service = Service(CHROMEDRIVER_PATH)  # Update with your chromedriver path
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(5)  # Allow JavaScript to load fully
    return driver

def disconnect_chrome_driver(driver):
    driver.quit() # Close the driver
    return None

# --- Instagram Graph API Setup ---

def get_instagram_insights():
# refer to https://developers.facebook.com/docs/instagram-platform/api-reference/instagram-user/insights for more details
    endpoint = f"{BASE_URL}{ACCOUNT_ID}/insights"
    params = {
        "metric": "likes",
        "period": "day",
        #"timeframe": "last_90_days",
        "metric_type": "total_value",
        #"breakdown": "BREAKDOWN_METRIC>
        #"since": "1740096000",
        #"until": "1740613184",
        "access_token": ACCESS_TOKEN
    }
    response = requests.get(endpoint, params=params)
    return response.json()

# --- Scraping Post Data ---

def check_likes(driver, media):
    ## Instagram loads likes dynamically, this is required to gather like count
    # Wait for the likes element to load
    
    if media == "post":
        html = "//a[contains(@href, 'liked_by')]/span/span"
    elif media == "reel":
        html = "//span[contains(@class, 'xdj266r x11i5rnm')]"
    else:
        return None
    
    try:
        likes_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, html))
        )
        likes_text = likes_element.get_attribute("innerHTML").strip()
    except Exception as e:
        print(f"Error: {e}")
        likes_text = "Not Found"
    return likes_text

def check_caption(driver, media):
    # Wait for the caption element to load
    
    if media == "post":
        html = "//h1[contains(@class, '_ap3a')]"
    elif media == "reel":
        html = "//span[contains(@class, 'x6ikm8r x10wlt62 xuxw1ft')]"
    else:
        return None
    
    try:
        caption_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, html))
        )
        caption_text = caption_element.get_attribute("innerText")
    except Exception as e:
        print(f"Error: {e}")
        caption_text = "Not Found"
    return caption_text

def scrape_ig_post(url):

    # Fetches the full Instagram post HTML
    driver = connect_chrome_driver(url)

    # Instagram loads some elements dynamically
    likes_text = check_likes(driver, "post")
    caption_text = check_caption(driver, "post")

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    disconnect_chrome_driver(driver)

    # Extract hashtags
    hashtags = [a.get_text() for a in soup.find_all("a") if a.get_text().startswith("#")]

    return caption_text, hashtags, likes_text

def scrape_ig_reel(url):

    # Fetches the full Instagram post HTML
    driver = connect_chrome_driver(url)

    # Instagram loads some elements dynamically
    likes_text = check_likes(driver, "reel")
    caption_text = check_caption(driver, "reel")

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    disconnect_chrome_driver(driver)

    # NEED TO FIX
    # Extract hashtags
    hashtags = [a.get_text() for a in soup.find_all("a") if a.get_text().startswith("#")]

    return caption_text + " " + " ".join(hashtags) + " --- " + likes_text + " likes"

# --- Scraping Public Profile Data ---

def scrape_instagram_profile(username):
    url = f"https://www.instagram.com/{username}/"
    driver = connect_chrome_driver(url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    disconnect_chrome_driver(driver)
    
    # Extract follower count 
    meta_tag = soup.find("meta", property="og:description")
    if meta_tag:
        content = meta_tag["content"]
        followers = content.split(" Followers")[0].split(" ")[-1]
        return {"username": username, "followers": followers}
    else:
        return {"username": username, "followers": "Not found"}

# --- Hashtag Analysis ---
def get_hashtag_data(hashtag):
    url = f"https://www.instagram.com/explore/tags/{hashtag}/"
    driver = connect_chrome_driver(url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    disconnect_chrome_driver(driver)

    # Extract post count (Example, might need tweaking)
    meta_tag = soup.find("meta", property="og:description")
    if meta_tag:
        content = meta_tag["content"]
        print(content)
        posts = content.split(" Posts")[0].split(" ")[-1]
        return {"hashtag": hashtag, "posts": posts}
    else:
        return {"hashtag": hashtag, "posts": "Not found"}

if __name__ == "__main__":

    # print("Fetching Instagram Insights...")
    # insights = get_instagram_insights()
    # print(json.dumps(insights, indent=2))
    
    # print("Scraping competitor data...")
    # competitor_data = scrape_instagram_profile("locwithaush")
    # print(competitor_data)
    
    # print("Fetching hashtag data...")
    # hashtag_data = get_hashtag_data("locjourney")
    # print(hashtag_data)

    post = "https://www.instagram.com/p/DEgepvgRB-J/"
    reel = "https://www.instagram.com/reels/DGl0LAApSrn/"
    print("Scraping reel data...")
    post_data = scrape_ig_reel(reel)
    print(post_data)
    # print("Scraping post data...")
    # post_data = scrape_ig_post(post)
    # print(post_data)
    