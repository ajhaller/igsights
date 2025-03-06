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
    """
    Loads the configuration settings from the 'insights_config.json' file.

    This function sets the working directory to the location of the script 
    and then reads the JSON configuration file, returning its contents as a dictionary.

    Returns:
        dict: The parsed configuration data from 'insights_config.json'.

    Raises:
        FileNotFoundError: If 'insights_config.json' does not exist in the script's directory.
        json.JSONDecodeError: If the JSON file is improperly formatted.
    """
    # Sets path to lib folder
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("insights_config.json", "r") as config_file:
        config = json.load(config_file)
        return config

# --- Instagram Login ---
def intizalize_ig_login():
    """
    Logs into Instagram using credentials from the configuration file and saves session cookies.

    This function:
    - Loads login credentials from the configuration file.
    - Opens Instagram in a Chrome browser using Selenium.
    - Enters the username and password to log in.
    - Waits for potential two-factor authentication (2FA) completion.
    - Saves session cookies to a file for future use.

    Returns:
        None

    Raises:
        KeyError: If the required credentials ('INSTAGRAM_USERNAME' or 'INSTAGRAM_PASSWORD') are missing from the config.
        WebDriverException: If the Chrome WebDriver fails to launch.
        NoSuchElementException: If the login fields cannot be found on the page.
        Exception: Catches and prints any other unexpected errors.
    """
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

def ig_login():
    """
    Logs into Instagram using previously saved session cookies.

    This function:
    - Opens Instagram in a Chrome browser using Selenium.
    - Waits briefly for the page to load.
    - Loads previously saved cookies from a file.
    - Adds the cookies to the browser session.
    - Refreshes the page to apply the cookies and complete the login.

    Returns:
        WebDriver: The Selenium WebDriver instance with an authenticated Instagram session.

    Raises:
        FileNotFoundError: If the cookies file ("instagram_cookies.pkl") is missing.
        WebDriverException: If the Chrome WebDriver fails to launch.
        Exception: Catches and prints any other unexpected errors.
    """
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
    """
    Establishes a connection to a Chrome WebDriver, with an option for Instagram login.

    This function:
    - If 'login' is set to True, logs into Instagram using the 'ig_login' function and returns a WebDriver instance with an authenticated session.
    - If 'login' is set to False, initializes a headless Chrome browser instance for general use by fetching the necessary driver path from the configuration file.

    Args:
        login (bool): Optional flag to indicate whether to log in to Instagram. Default is False.

    Returns:
        WebDriver: A Selenium WebDriver instance, either with an authenticated Instagram session or a headless browser session.

    Raises:
        FileNotFoundError: If the specified ChromeDriver path in the configuration file is incorrect or missing.
        WebDriverException: If the Chrome WebDriver fails to launch or load with the given options.
        Exception: Catches and prints any other unexpected errors.
    """
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
    """
    Terminates the Chrome WebDriver session and closes the browser.

    This function gracefully shuts down the WebDriver by quitting the session, 
    which closes the browser and releases associated resources.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance to be closed.

    Returns:
        None: The function terminates the WebDriver session, returning None.

    Raises:
        WebDriverException: If there is an issue with closing the WebDriver or browser.
    """
    driver.quit() # Close the driver
    return None

# --- Instagram Graph API Setup and Request---

def get_media_insights(post_id, type="feed", breakdown=None):
    """
    Fetches insights data for a specific Instagram post via the Facebook Graph API.

    This function retrieves insights (metrics) related to an Instagram post based on its type (feed, reel, or other) 
    and optional breakdown criteria. The function sends a request to the Instagram Graph API to gather post insights 
    such as likes, comments, reach, views, and more.

    Args:
        post_id (str): The unique identifier for the Instagram post.
        type (str): The type of post, which can be "feed", "reel", or another type. Default is "feed".
        breakdown (str, optional): The breakdown parameter for more detailed insights (e.g., "age", "gender"). Default is None.

    Returns:
        dict: A JSON response containing the requested post insights, or an error message.

    Example:
        response = get_media_insights("1234567890", type="reel", breakdown="age")
        print(response)
    
    Reference:
        Instagram Graph API documentation: https://developers.facebook.com/docs/instagram-platform/api-reference/instagram-user/insights
    """

    config = load_config()
    endpoint = f"https://graph.facebook.com/v22.0/{post_id}/insights"
    
    if type == "feed":
        metrics = "comments, follows, impressions, likes, profile_activity, profile_visits, reach, saved, shares, total_interactions, views"
    elif type == "reel":
        metrics = "clips_replays_count, comments, ig_reels_aggregated_all_plays_count, ig_reels_avg_watch_time, ig_reels_video_view_total_time, likes, plays, reach, saved, shares, total_interactions, views"
    else:
        metrics = "comments, impressions, navigation, profile_activity, profile_visits, reach, replies, shares, total_interactions, views",

    if breakdown:
        params = {
            "metric": metrics,
            "period": "day",
            "breakdown": breakdown,
            "access_token": config['ACCESS_TOKEN']
        }
    else:
        params = {
            "metric": metrics,
            "period": "day",
            "access_token": config['ACCESS_TOKEN']
        }

    response = requests.get(endpoint, params=params)
    return response.json()

def business_discovery(username):
    """
    Fetches business discovery data for a specific Instagram account using the Facebook Graph API.

    This function retrieves the followers count and media count of a business Instagram account 
    based on the provided username. The function sends a request to the Instagram Graph API to gather 
    insights into the account's popularity and media engagement.

    Args:
        username (str): The Instagram username of the business account for which data is being retrieved.

    Returns:
        dict: A JSON response containing the followers count, media count, or an error message.

    Example:
        response = business_discovery("bluebottle")
        print(response)
    
    Reference:
        Instagram Graph API documentation: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery
    """
    
    config = load_config()
    endpoint = f"https://graph.facebook.com/v22.0/{config['ACCOUNT_ID']}"
    
    params = {
        "fields": f"business_discovery.username({username}){{followers_count,media_count}}",
        "access_token": config['ACCESS_TOKEN']
    }
    
    response = requests.get(endpoint, params=params)
    return response.json()

def get_comments(media_id):
    """
    Retrieves comments for a specific Instagram media post using the Facebook Graph API.

    This function fetches all comments for a given media post by sending a request to the 
    Instagram Graph API. It returns the comments data including the text of the comments and 
    related metadata.

    Args:
        media_id (str): The ID of the Instagram media post for which comments are being retrieved.

    Returns:
        dict: A JSON response containing the list of comments or an error message.

    Example:
        comments_data = get_comments("17895695668004550")
        print(comments_data)
    
    Reference:
        Instagram Graph API documentation: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery
    """
    
    config = load_config()
    endpoint = f"https://graph.facebook.com/{media_id}/comments"

    params = {
        "access_token": config['ACCESS_TOKEN']
    }
    
    response = requests.get(endpoint, params=params)
    return response.json()

def get_hashtags(hashtag, hashtag_id=None, search=False):
    """
    Retrieves data related to a specific Instagram hashtag using the Facebook Graph API.

    This function can either search for a hashtag by name or fetch data related to a specific 
    hashtag ID. It allows you to retrieve information about recent media or top media associated 
    with the hashtag, depending on the value of the `search` argument.

    Args:
        hashtag (str): The name of the hashtag to search for.
        hashtag_id (str, optional): The ID of the hashtag if already known. If None, the function 
                                    will attempt to find the ID by searching.
        search (bool, optional): If True, fetches recent or top media for the given hashtag. 
                                  Defaults to False.

    Returns:
        dict: A JSON response containing the hashtag data, including media associated with the 
              hashtag or an error message.

    Example:
        hashtags_data = get_hashtags("bluebottle")
        print(hashtags_data)

    Reference:
        Instagram Graph API documentation: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/hashtag-search
    """

    config = load_config()

    if hashtag_id is None:
        endpoint = f"https://graph.facebook.com/ig_hashtag_search"

        params = {
            "user_id": config['ACCOUNT_ID'],
            "q": hashtag,
            "access_token": config['ACCESS_TOKEN']
        }
        
        id_response = requests.get(endpoint, params=params)
        id_dict = id_response.json()
        hashtag_id = id_dict['data'][0]['id']

    # UNDER CONSTRUCTION
    if search:

        endpoint = f"https://graph.facebook.com/{hashtag_id}/recent_media?user_id={config['ACCOUNT_ID']}"
        params = {
            "user_id": config['ACCOUNT_ID'],
            "access_token": config['ACCESS_TOKEN'],
            "fields": "recent_media, top_media"
    }
        
        id_response = requests.get(endpoint)
        print("success")

    return id_response.json()

# --- Scraping Post Data ---

## --- Helpers --

def check_likes(driver):
    """
    Retrieves the number of likes on an Instagram post by dynamically loading the 'liked by' element.

    Instagram posts load likes dynamically, so this function waits for the appropriate element to 
    appear, extracts the like count from the element, and returns the value. If the element is not 
    found or an error occurs, it returns 'Not Found'.

    Args:
        driver (WebDriver): The Selenium WebDriver instance that is controlling the browser.

    Returns:
        str: The number of likes on the post or "Not Found" if the like count cannot be retrieved.

    Example:
        like_count = check_likes(driver)
        print(like_count)

    Reference:
        This function relies on the dynamic loading of Instagram elements via Selenium and XPath.
    """
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

# UNDER CONSTRUCTION
def check_caption(driver):
    """
    Retrieves the caption text of an Instagram post or reel by waiting for the caption element to load.

    Instagram captions are loaded dynamically, so this function waits for the caption element to become 
    visible, extracts the caption text, and returns it. If the caption element cannot be located or an error 
    occurs, it returns 'Not Found'.

    Args:
        driver (WebDriver): The Selenium WebDriver instance that is controlling the browser.

    Returns:
        str: The caption text of the Instagram post or reel, or "Not Found" if the caption cannot be retrieved.

    Example:
        caption = check_caption(driver)
        print(caption)

    Reference:
        This function relies on the dynamic loading of Instagram caption elements via Selenium and XPath.
    """
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
# UNDER CONSTRUCTION
def check_comments(driver):
    """
    Retrieves the list of comments from an Instagram post or reel by waiting for the comments elements to load.

    Instagram comments are loaded dynamically, so this function waits for the comments elements to become 
    visible, extracts all the comments, and returns them in a list. If the comments cannot be retrieved or an 
    error occurs, it returns 'Not Found'.

    Args:
        driver (WebDriver): The Selenium WebDriver instance that is controlling the browser.

    Returns:
        list: A list containing the text of all comments on the Instagram post or reel, or "Not Found" if the 
              comments cannot be retrieved.

    Example:
        comments = check_comments(driver)
        print(comments)

    Reference:
        This function relies on the dynamic loading of Instagram comment elements via Selenium and XPath.
    """
    # Wait for the caption element to load
    
    #html = "//span[contains(@class, 'x1lliihq x1plvlek xryxfnj x1n2onr6')]"
    html = "//div[contains(@class, 'x9f619 xjbqb8w x78zum5 x168nmei')]"

    try:
        comments_element = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, html))
        )
        comments_text = [comment.text for comment in comments_element]
    except Exception as e:
        print(f"Error: {e}")
        comments_text = "Not Found"
    return comments_text

def check_hashtags(driver):
    """
    Retrieves all hashtags mentioned in the caption of an Instagram post or reel.

    This function waits for the hashtag elements to load dynamically on the page and then extracts the text 
    of all hashtags. If no hashtags are found or an error occurs, it returns 'Not Found'.

    Args:
        driver (WebDriver): The Selenium WebDriver instance that is controlling the browser.

    Returns:
        list: A list containing the text of all hashtags in the caption of the Instagram post or reel, or 
              "Not Found" if no hashtags are found or an error occurs.

    Example:
        hashtags = check_hashtags(driver)
        print(hashtags)

    Reference:
        This function relies on the dynamic loading of Instagram hashtag elements via Selenium and XPath.
    """
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
    """
    Navigates to a specified URL and retrieves data from it using the provided Selenium WebDriver.

    This function loads the provided URL in the browser, waits for the JavaScript to fully load by
    pausing execution for 5 seconds, and then returns the driver instance.

    Args:
        driver (WebDriver): The Selenium WebDriver instance that is controlling the browser.
        url (str): The URL of the page from which data should be retrieved.

    Returns:
        WebDriver: The Selenium WebDriver instance with the loaded page.

    Example:
        driver = get_data(driver, "https://example.com")
        print(driver.page_source)
    """
    # Get url data
    driver.get(url)
    time.sleep(5)  # Allow JavaScript to load fully
    return driver

## --- Manual Scrapers ---

def get_ig_post_links(username, max_scrolls=100, connected_driver=None, login=False):
    """
    Retrieves a list of Instagram post URLs from a given user's profile by scrolling through the page.

    This function visits the specified Instagram profile, extracts post URLs (both regular posts and reels),
    and scrolls through the page until a specified maximum number of scrolls is reached or no new posts are loaded.

    Args:
        username (str): The Instagram username whose posts are to be retrieved.
        max_scrolls (int, optional): The maximum number of scrolls to perform (default is 100).
        connected_driver (WebDriver, optional): An existing Selenium WebDriver instance (default is None).
        login (bool, optional): Whether to log in to Instagram (default is False). If True, login will be performed.

    Returns:
        list: A list of unique Instagram post URLs.
        int: The number of unique post URLs found.

    Example:
        post_links, count = get_ig_post_links('username')
        print(post_links, count)

    Note:
        The function uses a randomized scrolling approach to avoid Instagram detection of automated browsing.
        It stops scrolling if no new posts are loaded or the maximum scroll count is reached.
    """

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
    """
    Downloads an image from the provided Instagram post URL and saves it to the specified location.

    Args:
        url (str): The URL of the Instagram post.
        connected_driver (WebDriver, optional): An existing Selenium WebDriver instance (default is None).
        login (bool, optional): Whether to log in to Instagram (default is False).
        save_path (str, optional): The path to save the image file (default is "_image.jpg").

    Returns:
        str: The path where the image is saved or an error message.
    """
    
    config = load_config()
    IMAGE_PATH = config['IMAGE_PATH']

    if url is not None:
        try:
            # Initial request to check URL
            response = requests.get(url, timeout=10)
            
            # Check if the request was successful
            if response.status_code == 200:
                if connected_driver is None:
                    # Fetch the HTML of the Instagram post
                    connected_driver = connect_chrome_driver(login=login)

                driver = get_data(connected_driver, url)

                # XPath for finding the image element
                html = "//img[contains(@alt, 'Photo by')]"
                post_id = url.split("/p/")[1].strip("/")

                try:
                    # Wait for the image element to load
                    image_elements = WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located((By.XPATH, html))
                    )
                    # Get the image URL
                    img_url = image_elements[0].get_attribute("src")

                    # Download and save the image
                    response = requests.get(img_url, stream=True)
                    if response.status_code == 200:
                        os.makedirs(IMAGE_PATH, exist_ok=True)
                        image_file_path = os.path.join(IMAGE_PATH, post_id + save_path)
                        with open(image_file_path, "wb") as file:
                            for chunk in response.iter_content(1024):
                                file.write(chunk)
                        print(f"Image saved as {image_file_path}")
                        return image_file_path
                    else:
                        print("Failed to download image")
                        return "Failed to download"
                except Exception as e:
                    print(f"Error while retrieving image: {e}")
                    return "Image element not found"
        except Exception as e:
            print(f"Error: {e}")
            return "URL did not work. Use the permalink for the Instagram post."

def scrape_ig_post(url, connected_driver=None, login=False, elements=None):
    """
    Scrapes specified elements (likes, hashtags, comments, etc.) from an Instagram post.

    Args:
        url (str): The URL of the Instagram post.
        connected_driver (WebDriver, optional): An existing Selenium WebDriver instance (default is None).
        login (bool, optional): Whether to log in to Instagram (default is False).
        elements (list, optional): A list of elements to scrape, e.g., ['likes', 'hashtags'].

    Returns:
        dict: A dictionary containing the scraped elements (e.g., likes, hashtags).
    """

    elements_dict = {}

    if connected_driver is None:
        # Fetches the full Instagram post HTML
        connected_driver = connect_chrome_driver(login=login)

    driver_data = get_data(connected_driver, url)

    if elements is None:
        # Instagram loads some elements dynamically
        elements_dict['likes'] = check_likes(driver_data)
        # elements_dict['comments'] = check_comments(driver_data)
        elements_dict['hashtags'] = check_hashtags(driver_data)
        # elements_dict['caption'] = check_caption(driver_data)

    else:
        if "likes" in elements:
            elements_dict['likes'] = check_likes(driver_data)
        # UNDER CONSTRUCTION
        # if "comments" in elements:
        #     elements_dict['comments'] = check_comments(driver_data)
        if "hashtags" in elements:
            elements_dict['hashtags'] = check_hashtags(driver_data)
        # UNDER CONSTRUCTION
        # if "caption" in elements:
        #     elements_dict['caption'] = check_caption(driver_data)

    if connected_driver is None:
        disconnect_chrome_driver(driver_data)

    return elements_dict

def scrape_instagram_profile(username, connected_driver=None, login=False):
    """
    Scrapes Instagram profile information like follower count for a given username.

    Args:
        username (str): The Instagram username.
        connected_driver (WebDriver, optional): An existing Selenium WebDriver instance (default is None).
        login (bool, optional): Whether to log in to Instagram (default is False).

    Returns:
        dict: A dictionary containing the username and follower count.
    """
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
# UNDER CONSTRUCTION
def get_hashtag_data(hashtag, connected_driver=None, login=False):
    """
    Scrapes Instagram hashtag data such as the number of posts for a given hashtag.

    Args:
        hashtag (str): The Instagram hashtag.
        connected_driver (WebDriver, optional): An existing Selenium WebDriver instance (default is None).
        login (bool, optional): Whether to log in to Instagram (default is False).

    Returns:
        dict: A dictionary containing the hashtag and the number of posts.
    """
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

    pprint(get_media_insights("18020822986857508", type="feed", breakdown=None))

    # print(business_discovery("locwithaush"))

    # print(get_hashtags("locs", "17841563554099067", True))

    # config = load_config()
    # test_url = f"https://graph.facebook.com/v22.0/17841563554099067?fields=recent_media&access_token={config['ACCESS_TOKEN']}"
    # test_response = requests.get(test_url)
    # print(test_response.json())  # Should return your IG Business ID

    # intizalize_ig_login()

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