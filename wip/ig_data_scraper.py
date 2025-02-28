import requests
import json
import time
import random
import pickle
from pprint import pprint
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
INSTAGRAM_USERNAME = config["INSTAGRAM_USERNAME"]
INSTAGRAM_PASSWORD = config["INSTAGRAM_PASSWORD"]

BASE_URL = "https://graph.facebook.com/v17.0/"

# --- Instagram Login ---
def intizalize_ig_login():
    driver = webdriver.Chrome()
    driver.get("https://www.instagram.com")

    try:
        # Wait and find login fields
        time.sleep(5)
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")

        # Enter credentials
        username_input.send_keys(INSTAGRAM_USERNAME)
        password_input.send_keys(INSTAGRAM_PASSWORD)
        password_input.send_keys(Keys.RETURN)
        
        time.sleep(15)  # Wait for 2FA to complete

        # Save session cookies
        pickle.dump(driver.get_cookies(), open("instagram_cookies.pkl", "wb"))
        print("Cookies saved!")
    
    except Exception as e:
        print(f"Login failed: {e}")

    # input("Log in manually and press Enter here...")  # Wait for manual login

    # pickle.dump(driver.get_cookies(), open("instagram_cookies.pkl", "wb"))
    # print("Cookies saved!")

# intizalize_ig_login()

def ig_login():
    # Open Instagram
    driver = webdriver.Chrome()
    driver.get("https://www.instagram.com")

    # Wait for Instagram to fully load
    time.sleep(2)

    # Load saved cookies
    cookies = pickle.load(open("instagram_cookies.pkl", "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)

    driver.refresh()  # Reload page with cookies
    print("Logged in successfully!")
    return driver

# --- Driver Connections ---
def connect_chrome_driver(url, login=False):
    # IG Login
    if login:
        driver = ig_login()
    else:
        # Fetches the full Instagram post HTML
        options = Options()
        options.headless = True
        service = Service(CHROMEDRIVER_PATH)  # Update with your chromedriver path
        driver = webdriver.Chrome(service=service, options=options)
    # Get url data
    driver.get(url)
    time.sleep(5)  # Allow JavaScript to load fully
    return driver

def disconnect_chrome_driver(driver):
    driver.quit() # Close the driver
    return None

# --- Instagram Graph API Setup and Request---

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

## --- Helpers --

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
        likes_element = WebDriverWait(driver, 15).until(
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
        caption_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, html))
        )
        caption_text = caption_element.get_attribute("innerText")
    except Exception as e:
        print(f"Error: {e}")
        caption_text = "Not Found"
    return caption_text

def check_hashtags(driver, media):
    # Wait for the caption element to load
    
    if media == "post":
        html = "//a[contains(text(), '#')]"
    elif media == "reel":
        # UNDER CONSTRUCTION
        # html = "//a[contains(text(), '#')]"
        return None
    else:
        return None
    
    try:
        hashtags_element = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, html))
        )
        hashtags_text = [element.text for element in hashtags_element]
    except Exception as e:
        print(f"Error: {e}")
        hashtags_text = "Not Found"
    return hashtags_text

## --- Scrapers ---

def get_ig_post_links(username, max_scrolls=100):
    url = f"https://www.instagram.com/{username}/"

    # Fetches the full Instagram post HTML
    driver = connect_chrome_driver(url, True)

    # Extract post URLs
    post_links = set()
    last_count = 0

    for scroll in range(max_scrolls):
        # Extract current posts
        posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        
        for post in posts:
            post_links.add(post.get_attribute("href"))

        print(f"🔹 Scroll {scroll+1}: {len(post_links)} posts found...")

        # Stop if no new posts were loaded
        if len(post_links) == last_count:
            print("✅ No new posts loaded, stopping.")
            break
        last_count = len(post_links)

        # Randomized scrolling up & down
        scroll_distance = random.randint(800, 1200)
        driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
        time.sleep(random.uniform(2, 5))

        driver.execute_script(f"window.scrollBy(0, {-scroll_distance//2});")
        time.sleep(random.uniform(2, 5))

        # Wait for new posts to load
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]"))
            )
        except:
            print("⚠️ No new elements detected, stopping early.")
            break

    disconnect_chrome_driver(driver)
    return list(post_links), len(post_links)

def scrape_ig_post(url):

    # Fetches the full Instagram post HTML
    driver = connect_chrome_driver(url)

    # Instagram loads some elements dynamically
    likes_text = check_likes(driver, "post")
    caption_text = check_caption(driver, "post")
    hashtags = check_hashtags(driver, "post")

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    disconnect_chrome_driver(driver)

    return caption_text, hashtags, likes_text

def scrape_ig_reel(url):

    # Fetches the full Instagram post HTML
    driver = connect_chrome_driver(url)

    # Instagram loads some elements dynamically
    likes_text = check_likes(driver, "reel")
    caption_text = check_caption(driver, "reel")
    hashtags = check_hashtags(driver, "reel")

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    disconnect_chrome_driver(driver)

    # NEED TO FIX
    # Extract hashtags
    # hashtags = [a.get_text() for a in soup.find_all("a") if a.get_text().startswith("#")]

    return caption_text, hashtags, likes_text

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
    placeholder = None

    # print("Fetching Instagram Insights...")
    # insights = get_instagram_insights()
    # print(json.dumps(insights, indent=2))
    
    # print("Scraping profile data...")
    # competitor_data = scrape_instagram_profile("locwithaush")
    # print(competitor_data)
    
    # print("Fetching hashtag data...")
    # hashtag_data = get_hashtag_data("locjourney")
    # print(hashtag_data)

    # reel = "https://www.instagram.com/reels/DGl0LAApSrn/"
    # print("Scraping reel data...")
    # post_data = scrape_ig_reel(reel)
    # print(post_data)

    # post = "https://www.instagram.com/p/DEgepvgRB-J/"
    # print("Scraping post data...")
    # post_data = scrape_ig_post(post)
    # print(post_data)

    print("Scraping post urls...")
    posts = get_ig_post_links("locwithaush")
    print(posts)