import os
import pandas as pd
import time
import datetime
import schedule
from ig_data_scraper import load_config, get_media_data, get_profile_data, get_demographic_insights, get_actions_insights
from openpyxl import load_workbook

# Helper Functions

def export_df(df, metrics_path, sheet_name="Sheet 1"):

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
    # Convert to datetime
    df["publish_datetime"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

    # Extract components
    df['publish_date'] = df['publish_datetime'].dt.date
    df['publish_year'] = df['publish_datetime'].dt.year
    df['publish_month'] = df['publish_datetime'].dt.month
    df['publish_day'] = df['publish_datetime'].dt.day
    df['publish_time'] = df['publish_datetime'].dt.time

    return df

# Requests

def get_media_insights():

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

    export_df(df, daily_post_metrics_path, sheet_name="post_metrics")

def get_profile_insights():
    
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

# Final Script

def automated_script():
    get_media_insights()
    get_profile_insights()
    get_demo_insights()
    get_act_insights()

# Run every day at 4:52PM
schedule.every().day.at("16:52").do(automated_script)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute