import requests
import json
import time
import random
import os
import pickle
from pprint import pprint
from PIL import Image
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
    # Sets path to lib folder
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("insights_config.json", "r") as config_file:
        config = json.load(config_file)
        return config

# --- Instagram Login ---
def intizalize_ig_login():
    config = load_config()
    driver = webdriver.Chrome()
    driver.get("https://www.instagram.com")

    try:
        # Wait and find login fields
        time.sleep(5)
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")

        # Enter credentials
        username_input.send_keys(config['INSTAGRAM_USERNAME'])
        password_input.send_keys(config['INSTAGRAM_PASSWORD'])
        password_input.send_keys(Keys.RETURN)
        
        time.sleep(15)  # Wait for 2FA to complete

        # Save session cookies
        pickle.dump(driver.get_cookies(), open("instagram_cookies.pkl", "wb"))
        print("Cookies saved!")
    
    except Exception as e:
        print(f"Login failed: {e}")

# intizalize_ig_login()

def ig_login():
    # Open Instagram
    driver = webdriver.Chrome()
    driver.get("https://www.instagram.com")

    # Wait for Instagram to fully load
    time.sleep(2)

    # Load saved cookies
    # Sets path to lib folder
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cookies = pickle.load(open("instagram_cookies.pkl", "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)

    driver.refresh()  # Reload page with cookies
    print("Logged in successfully!")
    return driver

# --- Driver Connections ---
def connect_chrome_driver(login=False):
    # IG Login
    if login:
        driver = ig_login()
    else:
        # Fetches the full Instagram post HTML
        config = load_config()
        options = Options()
        options.headless = True
        service = Service(config['CHROMEDRIVER_PATH'])  # Update with your chromedriver path
        driver = webdriver.Chrome(service=service, options=options)  

    return driver

def disconnect_chrome_driver(driver):
    driver.quit() # Close the driver
    return None

# --- Instagram Graph API Setup and Request---

def get_instagram_insights():
# refer to https://developers.facebook.com/docs/instagram-platform/api-reference/instagram-user/insights for more details
    config = load_config()
    endpoint = f"https://graph.facebook.com/v18.0/{config['ACCOUNT_ID']}/insights"
    params = {
        "metric": "likes",
        "period": "day",
        #"timeframe": "last_90_days",
        "metric_type": "total_value",
        #"breakdown": "BREAKDOWN_METRIC>
        #"since": "1740096000",
        #"until": "1740613184",
        "access_token": config['ACCESS_TOKEN']
    }
    response = requests.get(endpoint, params=params)
    return response.json()

# --- Scraping Post Data ---

## --- Helpers --

def check_likes(driver):
    ## Instagram loads likes dynamically, this is required to gather like count
    # Wait for the likes element to load

    html = "//a[contains(@href, 'liked_by')]/span/span"
    
    try:
        likes_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, html))
        )
        likes_text = likes_element.get_attribute("innerHTML").strip()
    except Exception as e:
        print(f"Error: {e}")
        likes_text = "Not Found"
    return likes_text

def check_caption(driver):
    # Wait for the caption element to load

    #html = "//h1[contains(@class, '_ap3a')]/text()"
    #html = "//span[contains(@class, 'x6ikm8r x10wlt62 xuxw1ft')]"
    #html = '//h1'
    
    # if media == "post":
    #     html = "//h1[contains(@class, '_ap3a')]"
    # elif media == "reel":
    #     html = "//span[contains(@class, 'x6ikm8r x10wlt62 xuxw1ft')]"
    # else:
    #     return None
    
    # try:
    #     caption_element = WebDriverWait(driver, 15).until(
    #         EC.presence_of_element_located((By.XPATH, html))
    #     )
    #     caption_text = caption_element.get_attribute("innerText")

    try:
        caption_text = WebDriverWait(driver, 25).until(
        #caption_element = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.TAG_NAME, "h1"))
            # EC.presence_of_element_located((By.XPATH, html))
        ).text
        #caption_text = caption_element.get_attribute("innerText")
    except Exception as e:
        print(f"Error: {e}")
        caption_text = "Not Found"

    return caption_text

def check_hashtags(driver):
    # Wait for the caption element to load
    
    html = "//a[contains(text(), '#')]"
    
    try:
        hashtags_element = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, html))
        )
        hashtags_text = [element.text for element in hashtags_element]
    except Exception as e:
        print(f"Error: {e}")
        hashtags_text = "Not Found"
    return hashtags_text

def get_data(driver, url):
    # Get url data
    driver.get(url)
    time.sleep(5)  # Allow JavaScript to load fully
    return driver

## --- Scrapers ---

def get_ig_post_links(username, max_scrolls=100, connected_driver=None, login=False):
    url = f"https://www.instagram.com/{username}/"

    if connected_driver is None:
        # Fetches the full Instagram post HTML
        connected_driver = connect_chrome_driver(login=login)

    driver = get_data(connected_driver, url)

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
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]"))
            )
        except:
            print("⚠️ No new elements detected, stopping early.")
            break

    disconnect_chrome_driver(driver)
    return list(post_links), len(post_links)

def download_image(url, connected_driver=None, login=False, save_path="_image.jpg"):
    
    config = load_config()
    IMAGE_PATH = config['IMAGE_PATH']

    if url is not None:
        try:
            response = requests.get(url, timeout=10)
            # Check if the request was successful
            if response.status_code == 200:
                if connected_driver is None:
                    # Fetches the full Instagram post HTML
                    connected_driver = connect_chrome_driver(login=login)

                driver = get_data(connected_driver, url)

                html = "//img[contains(@alt, 'Photo by')]"
                post_id = url.split("/p/")[1].strip("/")

                try:
                    image_elements = WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located((By.XPATH, html))
                    )
                    img_url = image_elements[0].get_attribute("src")

                    # Download and save the image
                    response = requests.get(img_url, stream=True)
                    if response.status_code == 200:
                        os.makedirs(IMAGE_PATH, exist_ok=True)
                        with open(IMAGE_PATH + post_id + save_path, "wb") as file:
                            for chunk in response.iter_content(1024):
                                file.write(chunk)
                        print(f"Image saved as {post_id + save_path}")
                        return IMAGE_PATH + post_id + save_path
                    else:
                        print("Failed to download image")
                        return "Failed to download"
                except Exception as e:
                    print(f"Error: {e}")
                    return "Not Found"
        except Exception as e:
                    print(f"Error: {e}")
                    return "URL did not work. Use the permalink for the instagram post."

def scrape_ig_post(url, connected_driver=None, login=False):

    if connected_driver is None:
        # Fetches the full Instagram post HTML
        connected_driver = connect_chrome_driver(login=login)

    driver_data = get_data(connected_driver, url)

    # Instagram loads some elements dynamically
    likes_text = check_likes(driver_data)
    # caption_text = check_caption(driver_data, media)
    hashtags = check_hashtags(driver_data)

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(driver_data.page_source, "html.parser")

    if connected_driver is None:
        disconnect_chrome_driver(driver_data)

    #return caption_text, hashtags, likes_text
    return hashtags, likes_text

def scrape_instagram_profile(username, connected_driver=None, login=False):
    url = f"https://www.instagram.com/{username}/"

    if connected_driver is None:
        # Fetches the full Instagram post HTML
        connected_driver = connect_chrome_driver(login=login)

    driver = get_data(connected_driver, url)
    
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
def get_hashtag_data(hashtag, connected_driver=None, login=False):
    url = f"https://www.instagram.com/explore/tags/{hashtag}/"

    if connected_driver is None:
        # Fetches the full Instagram post HTML
        connected_driver = connect_chrome_driver(login=login)

    driver = get_data(connected_driver, url)
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

    # post = "https://www.instagram.com/p/DGqaNAZOfga/"
    # print("Scraping post data...")
    # post_data = scrape_ig_post(url=post, login=True)
    # print(post_data)

    # print("Downloading Image...")
    # post = "https://www.instagram.com/p/DGQxLfTum2n/"
    # image_path = download_image(post)
    # print(image_path)
    # # Open and display the image
    # img = Image.open(image_path)
    # img.show()

    # print("Scraping post urls...")
    # posts = get_ig_post_links("locwithaush")
    # print(posts)