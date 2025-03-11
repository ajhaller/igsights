import os
import pandas as pd
from ig_data_scraper import load_config
from datetime import datetime


config = load_config()
INTIAL_EXTRACT_PATH = config["INTIAL_EXTRACT_PATH"]
RAW_DATA_PATH = config['RAW_DATA_PATH']

def merge_csv_files(folder_path):
    # Get all CSV files in the folder
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    if not csv_files:
        print("No CSV files found in the folder.")
        return None
    
    # Initialize merged_df as None
    merged_df = None
    
    for file in csv_files:
        file_path = os.path.join(folder_path, file)
        file_stats = os.stat(file_path)
        download_time = file_stats.st_ctime  
        df = pd.read_csv(file_path)

        # Add a datetime column capturing the current timestamp
        df['datetime_extracted'] = datetime.fromtimestamp(download_time)
        
        # Merge with the previous dataframe
        if merged_df is None:
            merged_df = df  # First file becomes the base DataFrame
        else:
            merged_df = pd.concat([merged_df, df], ignore_index=True)
    
    # In case of overlap
    merged_df = merged_df.drop_duplicates(subset=['Post ID'], keep='first')

    return merged_df

def update_data():
    final_df = merge_csv_files(INTIAL_EXTRACT_PATH)
    if final_df is not None:
        print(final_df.head())  # Display first few rows
        final_df.to_csv(RAW_DATA_PATH + "merged_intial_extract_data.csv", index=False)  # Save as CSV
    else:
        print("Resulting dataframe is None. An error has occured.")

if __name__ == "__main__":
    update_data()
