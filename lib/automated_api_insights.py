import os
import pandas as pd
import time
import datetime
import schedule
from ig_data_scraper import load_config, get_media_data, get_profile_data, get_demographic_insights, get_actions_insights, get_images
from openpyxl import load_workbook

# Helper Functions

def export_df(df, metrics_path, sheet_name="Sheet 1"):
    """
    Exports the given DataFrame to both CSV and Excel formats.

    This function performs the following steps:
        - Exports the DataFrame to a CSV file, appending to it if the file already exists or creating a new one.
        - Exports the DataFrame to an Excel file, appending data to an existing sheet if the file exists, or creating a new file if not.

    Args:
        df (pandas.DataFrame): The DataFrame to be exported.
        metrics_path (str): The base file path (without extension) for saving the CSV and Excel files.
        sheet_name (str, optional): The name of the Excel sheet to append to. Defaults to "Sheet 1".

    Returns:
        None

    Notes:
        - The function will append data to the CSV and Excel files without including headers for subsequent exports.
    """

    # CSV Export
    if os.path.exists(metrics_path + ".csv"):
        df.to_csv(metrics_path + ".csv", mode="a", index=False, header=False)  # Append without headers
    else:
        df.to_csv(metrics_path + ".csv", mode="w", index=False, header=True)   # Create file with headers

    # Excel Export
    try:
        with pd.ExcelWriter(metrics_path + ".xlsx", mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=writer.sheets[sheet_name].max_row)
    except FileNotFoundError:
        # If the file does not exist, create a new one
        df.to_excel(metrics_path + ".xlsx", sheet_name=sheet_name, index=False)

def add_extraction_datetime(df):
    """
    Adds current datetime and its components as new columns to the input DataFrame.

    This function retrieves the current datetime and extracts its components, then adds the following columns to the DataFrame:
        - 'extraction_datetime': The full current datetime.
        - 'extraction_date': The current date in 'YYYY-MM-DD' format.
        - 'extraction_year': The current year.
        - 'extraction_month': The full name of the current month (e.g., "March").
        - 'extraction_day': The current day of the month.
        - 'extraction_time': The current time in 'HH:MM:SS' format.

    Args:
        df (pandas.DataFrame): A DataFrame to which the datetime components will be added.

    Returns:
        pandas.DataFrame: The input DataFrame with additional columns containing the current datetime components.
    """

    # Get the current datetime
    now = datetime.datetime.now()

    # Add datetime components to the data
    df['extraction_datetime'] = now
    df['extraction_date'] = now.strftime('%Y-%m-%d')  # YYYY-MM-DD format
    df['extraction_year'] = now.year
    df['extraction_month'] = now.strftime('%B')  # Full month name (e.g., "March")
    df['extraction_day'] = now.day
    df['extraction_time'] = now.strftime('%H:%M:%S')  # Hour:Minute:Second
    
    return df

def parse_timestamp(df):
    """
    Converts timestamp data in a DataFrame to datetime components and adds them as separate columns.

    This function performs the following operations on the 'timestamp' column in the input DataFrame:
        - Converts the 'timestamp' to a datetime object, removing the timezone information.
        - Extracts and adds the following components as new columns:
            - 'publish_date': The date portion of the timestamp.
            - 'publish_year': The year portion of the timestamp.
            - 'publish_month': The month portion of the timestamp.
            - 'publish_day': The day portion of the timestamp.
            - 'publish_time': The time portion of the timestamp.

    Args:
        df (pandas.DataFrame): A DataFrame containing a 'timestamp' column to be parsed.

    Returns:
        pandas.DataFrame: The input DataFrame with additional columns for the extracted datetime components.
    """

    # Convert to datetime
    df["publish_datetime"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

    # Extract components
    df['publish_date'] = df['publish_datetime'].dt.date
    df['publish_year'] = df['publish_datetime'].dt.year
    df['publish_month'] = df['publish_datetime'].dt.month
    df['publish_day'] = df['publish_datetime'].dt.day
    df['publish_time'] = df['publish_datetime'].dt.time

    return df

# Custom Post Classification

def classify_caption(row):
    caption = str(row['caption']).lower()
    date_threshold_pre_influencer = datetime.datetime(2025, 2, 4)
    date_threshold_self_liberation = datetime.datetime(2025, 4, 7)
    date_threshold_lifestyle = datetime.datetime(2025, 3, 7)

    if row['publish_date'] < date_threshold_pre_influencer:
        return 'locs'
    elif any(tag in caption for tag in ['progress', 'texture', 'wrap']):
        return 'locs'
    elif any(tag in caption for tag in ['recap', 'dump']) and row['publish_date'] > date_threshold_lifestyle:
        return 'lifestyle'
    elif any(tag in caption for tag in ['creative', 'creativity', 'art', 'liberation']) and row['publish_date'] > date_threshold_self_liberation:
        return 'self liberation'
    elif any(tag in caption for tag in ['loc', 'hair']):
        return 'locs'
    else:
        return 'lifestyle'

# Requests

def get_media_insights():
    """
    Retrieves and processes media insights for posts, then exports the data to a specified path.

    The function performs the following steps:
        - Loads the configuration to get the file paths.
        - Makes a request to retrieve media data, including post caption, media type, URL, permalink, and timestamp.
        - Extracts insights data, including metric names and values, for each post.
        - Stores the data for each post, including the insights, in a structured format.
        - Converts the extracted post data into a pandas DataFrame.
        - Adds the extraction datetime and formats the timestamp.
        - Exports the DataFrame to a specified path for storage or further analysis.

    The processed insights include media details such as captions, media type, URLs, and associated metric values,
    and are exported as a structured dataset for further use.

    Returns:
        None
    """

    # SET UP
    config = load_config()
    daily_post_metrics_path = config['CLEANED_DATA_PATH'] + "daily_post_metrics"

    # Make request
    fields = "caption,media_type,media_url,permalink,timestamp"
    data = get_media_data(fields)

    posts_data = []
    for post in data:
        post_info = {
            'caption': post.get('caption', ''),
            'media_type': post.get('media_type', ''),
            'media_url': post.get('media_url', ''),
            'permalink': post.get('permalink', ''),
            'post_id': post.get('id', ''),
            'timestamp': post.get('timestamp', '')
        }
        
        # Extract insights data (if present)
        insights = post.get('insights', {}).get('data', [])
        for insight in insights:
            post_info["name"] = insight['name']  # Put the metric name in "name"
            post_info["value"] = insight['values'][0]['value']  # Put the metric value in "value"
            
            posts_data.append(post_info.copy())  # Use copy to avoid overwriting

    # Create a DataFrame
    df = pd.DataFrame(posts_data)

    # Format dates
    df = add_extraction_datetime(df)
    df = parse_timestamp(df)
    df['publish_date'] = pd.to_datetime(df['publish_date'], errors='coerce')
    df['content_pillar'] = df.apply(classify_caption, axis=1)

    export_df(df, daily_post_metrics_path, sheet_name="post_metrics")

def get_profile_insights():
    """
    Retrieves and processes profile insights, then exports the data to a specified path.

    The function performs the following steps:
        - Loads the configuration to get the file paths.
        - Makes a request to retrieve profile data, including biography, follower count, following count, media count, and profile picture URL.
        - Converts the retrieved profile data into a pandas DataFrame.
        - Adds the extraction datetime to the DataFrame.
        - Exports the DataFrame to a specified path for storage or further analysis.

    The processed profile insights include key metrics about the profile, such as followers, media content, and profile picture URL, 
    and are exported as a structured dataset for further use.

    Returns:
        None
    """

    # SET UP
    config = load_config()
    daily_profile_metrics_path = config['CLEANED_DATA_PATH'] + "daily_profile_metrics"
    
    # Make request
    fields = "biography,followers_count,follows_count,media_count,profile_picture_url"
    response = get_profile_data(fields)

    df = pd.DataFrame([response])
    df = add_extraction_datetime(df)

    export_df(df, daily_profile_metrics_path, sheet_name="profile_metrics")

def get_demo_insights():
    """
    Retrieves and processes demographic insights, then exports the data to a specified path.

    The function performs the following steps:
        - Loads the configuration to get the file paths.
        - Makes a request to retrieve demographic insights data.
        - Extracts and processes the demographic data, including categories, age, gender, and associated values.
        - Converts the extracted records into a pandas DataFrame.
        - Adds the extraction datetime to the DataFrame.
        - Exports the DataFrame to a specified path for storage or further analysis.

    The processed insights include demographic breakdowns by category, age, gender, and value,
    and are exported as a structured dataset for further use.

    Returns:
        None
    """
    # SET UP
    config = load_config()
    daily_demographic_metrics_path = config['CLEANED_DATA_PATH'] + "daily_demographic_metrics"
    
    # Make request
    data = get_demographic_insights()

    records = []
    for item in data["data"]:
        category = item["name"]
        for breakdown in item["total_value"]["breakdowns"]:
            for result in breakdown["results"]:
                age, gender = result["dimension_values"]
                value = result["value"]
                records.append({"category": category, "age": age, "gender": gender, "value": value})

    # Convert to DataFrame
    df = pd.DataFrame(records)
    df = add_extraction_datetime(df)

    export_df(df, daily_demographic_metrics_path, sheet_name="demographics_metrics")

def get_act_insights():
    """
    Retrieves and processes activity-based insights, then exports the data to a specified path.

    The function performs the following steps:
        - Loads the configuration to get the file paths.
        - Makes a request to get activity insights data.
        - Extracts and processes relevant metrics from the response data, ensuring numerical values are integers.
        - Converts the extracted metrics into a pandas DataFrame.
        - Adds the extraction datetime to the DataFrame.
        - Exports the DataFrame to a specified path for storage or further analysis.

    The processed insights include metric names, titles, and associated values, which are exported 
    as a clean and structured dataset.

    Returns:
        None
    """

    # SET UP
    config = load_config()
    daily_actions_metrics_path = config['CLEANED_DATA_PATH'] + "daily_actions_metrics"
    
    # Make request
    data = get_actions_insights()

    # Extracting data
    metrics = []
    for item in data['data']:
        metrics.append({
            'Metric Name': item['name'],
            'Title': item['title'],
            'Value': int(item.get('total_value', {}).get('value', 0))  # Ensuring integer
        })

    # Convert to DataFrame
    df = pd.DataFrame(metrics)
    df = add_extraction_datetime(df)

    export_df(df, daily_actions_metrics_path, sheet_name="actions_metrics")

def get_post_images():
    """
    Calls the get_images function to download images from URLs in a dataframe 
    and move them to a Tableau repository shape folder.

    This function acts as a wrapper for the get_images function, triggering the 
    image extraction and processing process, which includes:
        - Downloading images from URLs in the dataframe.
        - Moving the downloaded images to a designated Tableau repo shape folder.

    Returns:
        None
    """
    
    get_images()

# Final Script

def automated_script():
    """
    Executes a series of functions to gather insights and data for a social media profile.

    The following functions are called in sequence:
        - get_media_insights(): Collects insights related to media content.
        - get_profile_insights(): Retrieves insights about the profile's performance.
        - get_demo_insights(): Gathers demographic insights for the profile's audience.
        - get_act_insights(): Collects activity-based insights, such as engagement metrics.
        - get_post_images(): Retrieves images associated with posts.

    This script automates the process of collecting various types of insights for analysis and reporting.
    """

    get_media_insights()
    get_profile_insights()
    get_demo_insights()
    get_act_insights()
    get_post_images()

# Run every day
schedule.every().day.at("17:38").do(automated_script)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute