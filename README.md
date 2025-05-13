# igsights

**igsights** is a powerful tool designed to extract, analyze, and visualize Instagram insights data using the Facebook Graph API. By connecting with your Instagram account, it helps you pull important metrics, demographic data, media performance, and more — all in one place. With this repository, you can seamlessly integrate your social media data into your Tableau visualizations, enabling data-driven decision-making for social engagement.

---

## Table of Contents  
1. [Mission](#mission)  
2. [Getting Started](#getting-started)  
3. [Project Installation Instructions](#project-installation-instructions)  
4. [Environment Usage](#environment-usage)  
5. [Updating the Environment](#updating-the-environment)
6. [Authentication & Prereqs](#authentication-and-prereqs)
7. [Configuration File Structure](#configuration-file-structure)  
8. [Contributing to the Project](#contributing-to-the-project)  
9. [Getting Help](#getting-help)  
10. [Who We Are](#who-we-are)  

---

## Mission

The mission of **igsights** is to provide a seamless and powerful tool for extracting and analyzing Instagram insights. By connecting Instagram's Graph API with visualization tools like Tableau, our goal is to provide data-driven insights for optimizing social media performance, audience engagement, and content strategy. The tool is designed with social impact in mind, helping users make informed decisions to drive meaningful change through engagement.

---

## Getting Started

To get started with **igsights**, follow the steps below:

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-username/igsights.git
   cd igsights
   ```

2. **Set up the environment (see Project Setup Instructions)**

3. **Update your `config.json` file with your credentials and paths (see below)**

---

## Project Installation Instructions

This project uses Conda for environment management. You can set up your environment with the provided environment.yml file.

### Create the environment:
```bash
conda env create -f environment.yml
```
### Activate the environment:
```bash
conda activate igsights
```
### Install any missing dependencies (optional):
If needed:

```bash
conda install [package_name]
```

## Environment Usage
Once your environment is activated, you can run any of the scripts to extract data.

For example:

```bash
python automated_api_insights.py
```

---

## Updating the Environment  

If new packages are added during development, follow these steps to ensure all team members can stay in sync.  

### Method 1: Create a New Environment File  
```bash
conda env export > igsights_env.yml  
```  

### Method 2: Update the Existing `igsights_env.yml` File  
```bash
conda env update --file igsights_env.yml --prune  
```  
💡 **Note**: The `--prune` flag ensures any removed packages are also deleted locally.  

---

## Authentication and Prereqs

### Getting Access to Facebook/Instagram Data through API

To use this project, you’ll need credentials from Meta’s Graph API. Follow these steps:

1. Create a Meta App
    * Go to the [Meta for Developers Dashboard](https://developers.facebook.com/apps/).
    * Click Create App → Choose Business or None (depending on your needs).
    * Give your app a name and complete the required fields.

2. Get Your `APP_SECRET` and `ACCESS_TOKEN`
* After creating the app, go to Settings → Basic to find your `APP_SECRET`.
* Under Tools → Graph API Explorer, generate a User Access Token with the following permissions:
    * instagram_basic
    * pages_read_engagement
    * pages_show_list
    * instagram_manage_insights
    * ads_read (if needed)
* Click "Generate Access Token" and copy the token to your `config.json`.

⚠️ Remember that short-lived tokens expire after ~1 hour. To get a long-lived token, follow [Meta’s guide here](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived).

3. Get Your `ACCOUNT_ID` and `FACEBOOK_PAGE_ID`
You can fetch these via the Graph API:

* To get your Facebook Page ID:
    ```bash
    curl -X GET "https://graph.facebook.com/me/accounts?access_token=YOUR_ACCESS_TOKEN"

    ```
* To get your Instagram Account ID (connected to that page):
    ```bash
    curl -X GET "https://graph.facebook.com/v17.0/PAGE_ID?fields=connected_instagram_account&access_token=YOUR_ACCESS_TOKEN"
    ```

4. Add Credentials to `config.json`

### Setting Up Chrome Driver for Manual Data Scraping

This project includes functionality to manually scrape data from Instagram, although these functions are not being used to extract data. If you need to manually extract, the function provided uses selenium and requires ChromeDriver to be installed and in your path.

#### Steps:
1. Check your Chrome browser version.
2. Download the matching ChromeDriver for your version.
3. Extract and place the binary in an accessible location (e.g., /usr/local/bin or add to config.json path).

Update your config.json:

```json
"CHROMEDRIVER_PATH": "/your/path/to/chromedriver"
```

✅ Test that it's working:

```bash
chromedriver --version
```

---

## Configuration File Structure

The `config.json` file holds all necessary credentials and directory paths for data access, processing, and visualization set up. Below is a description of each key:

| Key                     | Description                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| `ACCESS_TOKEN`          | OAuth token used to authenticate requests to the Instagram Graph API.       |
| `APP_SECRET`            | App secret for secure API authentication.                                   |
| `ACCOUNT_ID`            | Instagram Business Account ID tied to the project.                          |
| `FACEBOOK_PAGE_ID`      | Facebook Page ID linked to the Instagram account.                           |
| `INSTAGRAM_USERNAME`    | Username used for scraping or login via browser automation.                 |
| `INSTAGRAM_PASSWORD`    | Password associated with the Instagram account.                             |
| `CHROMEDRIVER_PATH`     | Path to your local ChromeDriver executable for automation tasks.            |
| `RAW_DATA_PATH`         | Root directory where raw data like downloaded images is stored.             |
| `CLEANED_DATA_PATH`     | Location for storing cleaned dataframes (e.g., `cleaned_post_data.csv`).    |
| `IMAGE_PATH`            | Temporary path for downloaded media files (e.g., before Tableau move).      |
| `SHAPES_PATH`           | Path to Tableau shapes directory (used for uploading custom images).        |

> ⚠️ **Make sure to keep this file private and avoid committing it to public repositories.** Use `.gitignore` to protect it.

---

## Contributing to the Project

While this is currently a personal tool, contributions may be welcomed in the future! If you're interested in collaborating, feel free to open an issue or reach out.

---

## Getting Help

If you're running into issues:

* Double check your config.json is correctly formatted.
* Ensure your access token is valid and has the right permissions.
* Run scripts inside the activated conda environment ([Environment Usage](#environment-usage)).

---

## Who We Are

This project is developed & maintained by **Aushanae Haller**, a data scientist, social impact strategist and creative dedicated to leveraging technology for equity and empowerment.  
You can learn more about me at my [website](https://www.aushanaehaller.com/).

---