import os
import pandas as pd
import time
import datetime
import schedule
from ig_data_scraper import load_config, get_media_insights

def post_metrics():

    start_time = time.time()
    print("Running script...")

    # SET UP
    config = load_config()
    filename = config["POST_METRICS_PATH"]
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

            datetime_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df['datetime_now'] = datetime_now
        
            # Creates new df or adds df to csv
            if os.path.exists(filename):
                df.to_csv(filename, mode="a", index=False, header=False)  # Append without headers
            else:
                df.to_csv(filename, mode="w", index=False, header=True)   # Create file with headers

        else:
            continue

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time  # Calculate elapsed time
    print(f"This script ran for: {elapsed_time:.2f} seconds")

# Run every day at 3:16 PM
schedule.every().day.at("15:16").do(post_metrics)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute