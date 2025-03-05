import pandas as pd
import datetime
import schedule
import time
import os
from tests_to_lib_config import set_path 


def my_script():
    print("Running script...")

    config = set_path()
    POST_TEST_CSV_PATH = config["POST_TEST_CSV_PATH"]
    from ig_data_scraper import scrape_ig_post

    url = "https://www.instagram.com/p/DGlXekKOweU/"
    filename = POST_TEST_CSV_PATH

    # Scrape post details
    # caption, hashtags, likes = scrape_ig_post(url)
    hashtags, likes = scrape_ig_post(url)

    # Prepare data
    datetime_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    num_likes = int(likes) if likes.isdigit() else 0
    hashtags_str = ", ".join(hashtags)  # Convert list to string

    # Save data for new entry
    new_entry = pd.DataFrame({"datetime_now": [datetime_now], 
                    "num_likes": [num_likes], 
                    #"caption": [caption], 
                    "hashtags": [hashtags_str]})
    
    # Creates new df or adds row
    if os.path.exists(filename):
        new_entry.to_csv(filename, mode="a", index=False, header=False)  # Append without headers
    else:
        new_entry.to_csv(filename, mode="w", index=False, header=True)   # Create file with headers


# Run every day at 11:35 AM
schedule.every().day.at("11:35").do(my_script)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute