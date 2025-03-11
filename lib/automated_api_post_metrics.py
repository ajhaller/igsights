import os
import pandas as pd
import time
import datetime
import schedule
from ig_data_scraper import load_config, get_media_insights
from initial_data_extraction import update_data

def check_duplicates(filename, daily=None):
    df = pd.read_csv(filename)
    df['datetime_insights_pulled'] = pd.to_datetime(df['datetime_insights_pulled'])
    df['insights_pulled_date_only'] = df['datetime_insights_pulled'].dt.date
    df.drop_duplicates(subset=['id', 'insights_pulled_date_only', 'name'], keep='first', inplace=True)
    df.drop('insights_pulled_date_only', axis=1, inplace=True)
    if daily is not None:
        df.to_csv(filename, mode="w", index=False, header=True)
        df.to_excel(daily + ".xlsx", sheet_name="post_metrics", index=False) 
    else:
        df.to_csv(filename, mode="w", index=False, header=True)

def merge_data(filename, post_data):
    post_metrics = pd.read_csv(filename)
    post_metrics['Post ID'] = post_metrics['id']
    merged_df = pd.merge(post_metrics, post_data, on='Post ID', how='left')
    return merged_df

def export_merged_df(merged_df, daily_post_metrics_path):
    if os.path.exists(daily_post_metrics_path + ".csv"):
        merged_df.to_csv(daily_post_metrics_path + ".csv", mode="a", index=False, header=False)  # Append without headers
        new_df = pd.read_csv(daily_post_metrics_path + ".csv")
        new_df.to_excel(daily_post_metrics_path + ".xlsx", sheet_name="post_metrics", index=False) # Update excel file
    else:
        merged_df.to_csv(daily_post_metrics_path + ".csv", mode="w", index=False, header=True)   # Create file with headers
        merged_df.to_excel(daily_post_metrics_path + ".xlsx", sheet_name="post_metrics", index=False) 

def clean_and_export(filename, post_data, daily_post_metrics_path):
    # checks duplicates in post_metrics
    check_duplicates(filename)
    # merges with intial post extract data
    merged_df = merge_data(filename, post_data)
    # updates csv and excel files
    export_merged_df(merged_df, daily_post_metrics_path)
    # double checks daily_post_metrics for duplicates
    check_duplicates(daily_post_metrics_path + ".csv", daily=daily_post_metrics_path)

def post_metrics():

    start_time = time.time()
    print("Running script...")

    # SET UP
    config = load_config()
    filename = config["POST_METRICS_PATH"]
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
        
            # Creates new df or adds df to csv
            if os.path.exists(filename):
                df.to_csv(filename, mode="a", index=False, header=False)  # Append without headers
            else:
                df.to_csv(filename, mode="w", index=False, header=True)   # Create file with headers

        else:
            continue

    clean_and_export(filename, post_data, daily_post_metrics_path)

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time  # Calculate elapsed time
    print(f"This script ran for: {elapsed_time:.2f} seconds")

# Run every day at 1:11AM
schedule.every().day.at("01:11").do(post_metrics)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute