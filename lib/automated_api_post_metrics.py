import os
import pandas as pd
import time
import datetime
import schedule
from ig_data_scraper import load_config, get_media_insights, business_discovery
from initial_data_extraction import update_data

# Helper Functions

def remove_duplicates(filename, sheet_name=None, type="post"):
    df = pd.read_csv(filename + ".csv")
    df['datetime_insights_pulled'] = pd.to_datetime(df['datetime_insights_pulled'])
    df['insights_pulled_date_only'] = df['datetime_insights_pulled'].dt.date
    if type == "post":
        df.drop_duplicates(subset=['id', 'insights_pulled_date_only', 'name'], keep='first', inplace=True)
    else:
        df.drop_duplicates(subset=['insights_pulled_date_only'], keep='first', inplace=True)
    df.drop('insights_pulled_date_only', axis=1, inplace=True)
    if sheet_name is not None:
        df.to_csv(filename + ".csv", mode="w", index=False, header=True)
        df.to_excel(filename + ".xlsx", sheet_name=sheet_name, index=False) 
    else:
        df.to_csv(filename + ".csv", mode="w", index=False, header=True)

def merge_data(filename, post_data):
    post_metrics = pd.read_csv(filename + ".csv")
    post_metrics['Post ID'] = post_metrics['id']
    merged_df = pd.merge(post_metrics, post_data, on='Post ID', how='left')
    return merged_df

def export_df(df, metrics_path, sheet_name="Sheet 1"):
    if sheet_name == "Sheet 1":
        print("Warning: Sheet name was not supplied. The sheet name has defaulted to Sheet 1, but it's highly recommended to provide a sheet name.")

    if os.path.exists(metrics_path + ".csv"):
        df.to_csv(metrics_path + ".csv", mode="a", index=False, header=False)  # Append without headers
        new_df = pd.read_csv(metrics_path + ".csv")
        new_df.to_excel(metrics_path + ".xlsx", sheet_name=sheet_name, index=False) # Update excel file
    else:
        df.to_csv(metrics_path + ".csv", mode="w", index=False, header=True)   # Create file with headers
        df.to_excel(metrics_path + ".xlsx", sheet_name=sheet_name, index=False) 
        
# Clean & Export Functions

def clean_and_export_post_metrics(post_metrics_path, post_data, daily_post_metrics_path):
    # removes duplicates in post_metrics and overwrites current version
    remove_duplicates(post_metrics_path, sheet_name="post_metrics", type="post")
    # merges with intial post extract data
    merged_df = merge_data(post_metrics_path, post_data)
    # exports daily_post_metrics csv and xlsx
    export_df(merged_df, daily_post_metrics_path, sheet_name="post_metrics")
    # double checks daily_post_metrics for duplicates after merge
    remove_duplicates(daily_post_metrics_path, sheet_name="post_metrics", type="post")

def clean_and_export_profile_metrics(daily_profile_metrics_path):
    # removes duplicates in profile_metrics and overwrites current version
    remove_duplicates(daily_profile_metrics_path, sheet_name="profile_metrics", type="profile")

# Requests

def post_metrics():

    start_time = time.time()
    print("Running script...")

    # SET UP
    config = load_config()
    post_metrics_csv_path = config["POST_METRICS_PATH"]
    post_metrics_path = config["RAW_DATA_PATH"] + "post_metrics"
    daily_post_metrics_path = config['CLEANED_DATA_PATH'] + "daily_post_metrics"
    update_data()
    post_data = pd.read_csv(config['M_INTITAL_EXTRACT'])

    for _, row in post_data.iterrows():
        
        # Get post details
        response = get_media_insights(row['Post ID'], type=row['Post type'])

        if response.status_code == 200:

            # FORMATTING RESPONSE

            data = response.json()
            # Convert to DataFrame
            df = pd.DataFrame(data['data'])
            # Extract 'value' from 'values' column
            df['value'] = df['values'].apply(lambda x: x[0]['value'])
            # Drop the original 'values' column
            df.drop(columns=['values'], inplace=True)
            # Extract only the numeric part before the first slash in 'id'
            df['id'] = df['id'].apply(lambda x: x.split('/')[0])

            # ADDING COLUMNS FOR POST_DATA

            df['datetime_insights_pulled'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # change to date
            df['datetime_insights_pulled'] = pd.to_datetime(df['datetime_insights_pulled'])
        
            # Creates new df or adds df to csv
            if os.path.exists(post_metrics_csv_path):
                df.to_csv(post_metrics_csv_path, mode="a", index=False, header=False)  # Append without headers
            else:
                df.to_csv(post_metrics_csv_path, mode="w", index=False, header=True)   # Create file with headers

        else:
            continue

    clean_and_export_post_metrics(post_metrics_path, post_data, daily_post_metrics_path)

def follower_tracker():
    config = load_config()
    metrics_path = config['CLEANED_DATA_PATH'] + "daily_profile_metrics"
    follower_dict = business_discovery(config["INSTAGRAM_USERNAME"])
    media_count = follower_dict['business_discovery']['media_count']
    follower_count = follower_dict['business_discovery']['followers_count']

     # Create a new DataFrame with the current stats
    df = pd.DataFrame({
        "datetime_insights_pulled": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "follower_count": [follower_count],
        "media_count": [media_count]
    })

    # change to date
    df['datetime_insights_pulled'] = pd.to_datetime(df['datetime_insights_pulled'])

    # Creates new df or adds df to csv
    if os.path.exists(metrics_path + ".csv"):
        df.to_csv(metrics_path + ".csv", mode="a", index=False, header=False)  # Append without headers
    else:
        df.to_csv(metrics_path + ".csv", mode="w", index=False, header=True)   # Create file with headers

    clean_and_export_profile_metrics(metrics_path)

# Final Script

def automated_script():
    post_metrics()
    follower_tracker()

# Run every day at 7:30PM
schedule.every().day.at("19:30").do(automated_script)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute