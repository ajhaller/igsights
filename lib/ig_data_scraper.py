import requests
import json
import time
import random
import os
import pickle
import shutil
import pandas as pd
from pprint import pprint
from PIL import Image
from io import BytesIO
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

def get_media_insights(post_id, type="IG image", breakdown=None):
    """
    Fetches insights data for a specific Instagram post via the Facebook Graph API.

    This function retrieves insights (metrics) related to an Instagram post based on its type (feed, reel, or other) 
    and optional breakdown criteria. The function sends a request to the Instagram Graph API to gather post insights 
    such as likes, comments, reach, views, and more.

    Args:
        post_id (str): The unique identifier for the Instagram post.
        type (str): The type of post, which can be "IG image", "IG carousel", "IG reel", or another type. Default is "IG image".
        breakdown (str, optional): The breakdown parameter for more detailed insights (e.g., "age", "gender"). Default is None.

    Returns:
        response: response containing the requested post insights, or an error message.

    Example:
        response = get_media_insights("1234567890", type="reel", breakdown="age")
        print(response)
    
    Reference:
        Instagram Graph API documentation: https://developers.facebook.com/docs/instagram-platform/api-reference/instagram-user/insights
    """

    config = load_config()
    endpoint = f"https://graph.facebook.com/{post_id}/insights"
    
    if type == "IG image" or type == "IG carousel":
        metrics = "comments, follows, likes, profile_activity, profile_visits, reach, saved, shares, total_interactions, views"
    elif type == "IG reel":
        metrics = "comments, ig_reels_avg_watch_time, ig_reels_video_view_total_time, likes, reach, saved, shares, total_interactions, views"
    else:
        metrics = "comments, navigation, profile_activity, profile_visits, reach, replies, shares, total_interactions, views",

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
        
    return response

def get_media_data(fields):
    """
    Retrieves media post data along with key engagement insights from the Instagram Graph API.

    This function requests detailed media information (e.g., caption, media type, timestamp) and 
    associated insights (e.g., impressions, reach, likes, comments, shares, follows, views) 
    for an Instagram user.

    Args:
        fields (str): A comma-separated string of media fields to retrieve (e.g., "id,caption,media_url,timestamp").

    Returns:
        list: A list of dictionaries containing media post data and insights.

    Notes:
        - Requires a valid access token and Instagram account ID from the config.
        - Uses version 22.0 of the Instagram Graph API.
        - Supports pagination to retrieve all posts up to the API limit.
    """

    config = load_config()
    ig_user_id = config ['ACCOUNT_ID']
    endpoint = f"https://graph.facebook.com/v22.0/{ig_user_id}"
    
    params = {
        "fields": f"media{{{fields},insights.metric(impressions,reach,likes,comments,shares,follows,views)}}",
        "access_token": config['ACCESS_TOKEN'],
         "limit": 1000
    }
         
    all_posts = media_data_request(endpoint, params)
        
    return all_posts

def get_profile_data(fields):
    """
    Retrieves specified profile fields for an Instagram user using the Graph API.

    Sends a request to the Instagram Graph API to fetch user profile data based on the
    provided list of fields.

    Args:
        fields (str): A comma-separated string of fields to retrieve (e.g., "username,biography,followers_count").

    Returns:
        dict: A JSON-like dictionary containing the requested profile information.

    Notes:
        - Requires a valid access token and Instagram account ID from the config.
        - Uses version 22.0 of the Instagram Graph API.
        - The 'limit' parameter is included but may be ignored depending on the requested fields.
    """

    config = load_config()
    ig_user_id = config ['ACCOUNT_ID']
    endpoint = f"https://graph.facebook.com/v22.0/{ig_user_id}"
    
    params = {
        "fields": fields,
        "access_token": config['ACCESS_TOKEN'],
        "limit": 1000
    }

    response = requests.get(endpoint, params=params)
    data = response.json()
        
    return data

def get_demographic_insights():
    """
    Retrieves lifetime Instagram demographic insights for the current month using the Graph API.

    This function queries the Instagram Graph API for lifetime metrics related to audience demographics,
    including the age and gender breakdowns of engaged users, reached users, and followers.

    Returns:
        dict: A JSON-like dictionary containing demographic insights for the current month.

    Notes:
        - Requires a valid access token and Instagram account ID from the config.
        - Uses version 22.0 of the Instagram Graph API.
        - Metrics returned include:
            - engaged_audience_demographics
            - reached_audience_demographics
            - follower_demographics
    """

    config = load_config()
    ig_user_id = config ['ACCOUNT_ID']
    endpoint = f"https://graph.facebook.com/v22.0/{ig_user_id}/insights"
    
    # Lifetime Period
    params = {
        "metric": "engaged_audience_demographics,reached_audience_demographics,follower_demographics",
        "period": "lifetime",
        "metric_type": "total_value",
        "timeframe": "this_month",
        "breakdown": "age,gender",
        "access_token": config['ACCESS_TOKEN']
    }

    response = requests.get(endpoint, params=params)
    lifetime_data = response.json()
        
    return lifetime_data

def get_actions_insights():
    """
    Retrieves daily Instagram account action insights for the current month using the Graph API.

    This function sends a request to the Instagram Graph API to obtain daily metrics such as reach,
    website clicks, profile views, interactions, likes, comments, and more. The metrics are aggregated
    for the current month using the "day" period and returned as JSON.

    Returns:
        dict: A JSON-like dictionary containing the requested insight metrics for the current month.

    Notes:
        - Requires a valid access token and Instagram account ID from the config file.
        - Uses version 22.0 of the Instagram Graph API.
        - Metrics returned include user engagement and account interaction indicators.
    """

    config = load_config()
    ig_user_id = config ['ACCOUNT_ID']
    endpoint = f"https://graph.facebook.com/v22.0/{ig_user_id}/insights"

    # Day Period
    params = {
        "metric": "reach, website_clicks, profile_views, total_interactions, likes, comments, shares, saves, replies, views, follows_and_unfollows, profile_links_taps",
        "period": "day",
        "metric_type": "total_value",
        "timeframe": "this_month",
        "access_token": config['ACCESS_TOKEN']
    }

    response = requests.get(endpoint, params=params)
    data = response.json()
        
    return data

def get_images():
    """
    Retrieves and stores the most recent Instagram post images for Tableau visualization.

    This function performs the following steps:
    1. Loads the cleaned post metrics CSV file from the configured path.
    2. Filters the dataset to only include posts from the most recent extraction date.
    3. Extracts unique post IDs and media types for the latest posts.
    4. Uses the Instagram Graph API to fetch the image URL for each post.
    5. Downloads and loads each image using Pillow.
    6. Saves the images locally and moves them to the configured Tableau shapes directory.

    The images are intended for use in Tableau dashboards (e.g., as custom shapes),
    and this function ensures that only the most up-to-date post visuals are included.

    Returns:
        None
    """
    
    config = load_config()
    posts = pd.read_csv(config["CLEANED_DATA_PATH"] + "daily_post_metrics.csv")

    # Ensure 'extraction_date' column is datetime type
    posts['extraction_date'] = pd.to_datetime(posts['extraction_date'])

    # Filter to only include rows with the most recent extract date
    most_recent_date = posts['extraction_date'].max()
    latest_posts = posts[posts['extraction_date'] == most_recent_date]

    # Get unique posts from the latest extract date
    unique_posts = latest_posts[['post_id', 'media_type']].drop_duplicates().reset_index(drop=True)

    # unique_posts = posts[['post_id', 'media_type']].drop_duplicates().reset_index(drop=True)
    data = []
    
    for _, post in unique_posts.iterrows():
        post_id = post['post_id']
        media_type = post['media_type']
        image_url = first_image_url_request(post_id, media_type)
        
        if image_url:
            try:
                image_response = requests.get(image_url)
                image = Image.open(BytesIO(image_response.content))
            except Exception as e:
                image = None
        else:
            image = None
        
        data.append({
            "post_id": post_id,
            "image_url": image_url,
            "image": image
        })
    
    df = pd.DataFrame(data)

    download_images(df)
    move_images_to_tableau()

    return None

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

def media_data_request(endpoint, params):
    """
    Sends a request to the Instagram Graph API to retrieve media post data, handling pagination.

    This function fetches media posts from a given API endpoint using the provided parameters,
    appends the results to a list, and continues retrieving data through pagination links until
    all available posts have been collected.

    Args:
        endpoint (str): The initial URL endpoint to send the GET request to.
        params (dict): A dictionary of parameters to include in the initial request (e.g., access token, fields).

    Returns:
        list or None: A list of media post data dictionaries if successful, or None if the request fails.

    Notes:
        - Prints the status code and response if the initial request is unsuccessful.
        - Supports pagination through the 'paging.next' field in the response.
        - Designed for use with Instagram Graph API responses that nest media under a "media" field.
    """
    # Initialize list to store posts
    all_posts = []

    response = requests.get(endpoint, params=params)
    data = response.json()

    if response.status_code != 200:
        print(response.status_code)
        print("Response JSON:", response.json())  #
        return None
    else:
        # Collect posts
        all_posts.extend(data.get("media", {}).get("data", []))

        # Handle pagination
        i = 1
        while "paging" in data and "next" in data["paging"] or "paging" in data.get("media", {}) and "next" in data["media"]["paging"]:
            if i > 1:
                next_url = data["paging"]["next"]
            else:
                next_url = data["media"]["paging"]["next"]
            response = requests.get(next_url)
            data = response.json()
            all_posts.extend(data.get("data", []))
            i += 1
            
        return all_posts

def first_image_url_request(media_id, media_type):
    """
    Retrieves the appropriate image URL for a given media object from the Instagram Graph API.

    Depending on the media type, this function returns:
        - The direct media URL for single images.
        - The first image URL from a carousel album.
        - The thumbnail URL for videos.

    Args:
        media_id (str): The ID of the media object to retrieve.
        media_type (str): The type of media. Expected values are "IMAGE", "CAROUSEL_ALBUM", or "VIDEO".

    Returns:
        str or None: The URL of the media image or thumbnail. Returns None if the media type is unrecognized
        or if the expected URL cannot be extracted.

    Notes:
        - Requires a valid access token in the loaded config.
        - Uses version 19.0 of the Instagram Graph API.
    """
    config = load_config()
    url = f"https://graph.facebook.com/v19.0/{media_id}"

    if media_type == "IMAGE" or media_type == "CAROUSEL_ALBUM":
        params = {
            "fields": "id,media_type,media_url,children{media_url}",
            "access_token": config['ACCESS_TOKEN']
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if media_type == "IMAGE":
            return data.get("media_url")
        else:
            return data.get("children", {}).get("data", [{}])[0].get("media_url")
    elif media_type == "VIDEO":
        params = {
            "fields": "id,media_type,media_url,thumbnail_url",
            "access_token": config['ACCESS_TOKEN']
        }
        response = requests.get(url, params=params)
        data = response.json()
        return data.get("thumbnail_url")
    return None

def download_images(df):
    """
    Downloads images from URLs in a DataFrame and saves them to a local directory.

    This function reads image URLs and corresponding post IDs from the provided DataFrame,
    deletes any existing 'images' directory in the raw data path (as specified in the config),
    creates a new one, and downloads each image as a JPEG using the post ID as the filename.

    Args:
        df (pandas.DataFrame): A DataFrame containing at least two columns:
            - 'post_id': Unique identifier for each image (used as the filename).
            - 'image_url': Direct URL to the image.

    Notes:
        - Skips any row with an invalid or missing image URL.
        - Prints progress and error messages during the download process.
    """
    config = load_config()
    images_dir = os.path.join(config["RAW_DATA_PATH"], "images")

    # If the directory exists, remove it (faster than deleting contents one by one)
    if os.path.exists(images_dir):
        shutil.rmtree(images_dir)
    os.makedirs(images_dir)
    
    # Download images
    for index, row in df.iterrows():
        post_id = row["post_id"]
        image_url = row["image_url"]

        # Skip if image_url is missing or invalid
        if not isinstance(image_url, str) or not image_url.startswith("http"):
            print(f"Skipping post {post_id} due to missing or invalid URL: {image_url}")
            continue

        # Define the image file path
        image_path = os.path.join(images_dir, f"{post_id}.jpg")

        # Download the image
        try:
            response = requests.get(image_url)

            if response.status_code == 200:  # Ensure request was successful
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded image for post {post_id}")
            else:
                print(f"Failed to download image for post {post_id}: {response.status_code}")

        except Exception as e:
            print(f"Error downloading image for post {post_id}: {e}")

def move_images_to_tableau():
    """
    Copies image files from a raw data directory to the Tableau shapes folder.

    This function loads configuration settings, locates the source directory containing images,
    and copies it to the specified destination used by Tableau for custom shapes. If the destination
    folder already exists, it will be removed before copying the new files.

    Raises:
        Prints an error message if the copy operation fails.
    """
    config = load_config()
    # Move images to the Tableau repo shapes folder
    source_dir = os.path.join(config["RAW_DATA_PATH"], "images")

    destination_dir = config["SHAPES_PATH"] + "images/"  # Update with the correct path to the Tableau repo shapes folder

    if os.path.exists(destination_dir):
        shutil.rmtree(destination_dir)

    try:
        shutil.copytree(source_dir, destination_dir)
        print(f"Successfully copied the '{source_dir}' folder to '{destination_dir}'")
        
    except Exception as e:
        print(f"Error copying the folder: {e}")

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
    
    #fields = ["biography,followers_count,follows_count,media_count,profile_picture_url"]
    # fields = "biography"
    # response = get_profile_data(fields)
    # pprint(response)

    # fields = "media_type,timestamp"
    # response = get_media_data(fields)
    # pprint(response)

    # rep = get_demographic_insights()
    # pprint(rep)

    # rep = get_actions_insights()
    # pprint(rep)
 

    #response = get_media_insights("18001667618673220", type="IG image", breakdown=None)
    #print(response.json())

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
    # post = "https://www.instagram.com/p/DHdzPUEuJOY/"
    # image_path = download_image(post)
    # print(image_path)
    # # Open and display the image
    # img = Image.open(image_path)
    # img.show()

    # print("Scraping post urls...")
    # posts = get_ig_post_links("locwithaush")
    # print(posts)