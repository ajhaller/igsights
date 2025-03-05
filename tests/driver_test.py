import pandas as pd
import os
from tests_to_lib_config import set_path 
config = set_path()

from ig_data_scraper import scrape_ig_post, connect_chrome_driver

driver = connect_chrome_driver()
url = "https://www.instagram.com/p/DGqaNAZOfga/"
print(scrape_ig_post(url, driver, True))
    
