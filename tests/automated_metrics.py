import os
import pandas as pd
import time
import datetime
from tests_to_lib_config import set_path 
import schedule

def my_script():
    print("Running script...")

    # Set up
    config = set_path()
    METRICS_PATH = config["METRICS_PATH"]
    from ig_data_scraper import scrape_ig_post, connect_chrome_driver, disconnect_chrome_driver # type: ignore
    filename = METRICS_PATH
    post_data = pd.read_csv(config['RAW_DATA_PATH']+"unique_post_data.csv")
    driver = connect_chrome_driver(login=True)

    for idx, row in post_data.iterrows():
        
        # Scrape post details
        elements = scrape_ig_post(row['Permalink'], driver)

        # Prepare data
        datetime_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        num_likes = int(elements['likes']) if elements['likes'].isdigit() else 0

        # Save data for new entry
        new_entry = pd.DataFrame({"post_id": row['Post ID'],
                                "permalink": row['Permalink'],
                                "datetime_now": [datetime_now], 
                                "num_likes": [num_likes], 
                                # "caption": [elements['caption']], 
                                # "comments": [elements['comments']], 
                                "hashtags": [elements['likes']]})
        
        # Creates new df or adds row
        if os.path.exists(filename):
            new_entry.to_csv(filename, mode="a", index=False, header=False)  # Append without headers
        else:
            new_entry.to_csv(filename, mode="w", index=False, header=True)   # Create file with headers

    disconnect_chrome_driver(driver)


# Run every day at 5:50 PM
schedule.every().day.at("10:34").do(my_script)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute