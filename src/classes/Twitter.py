import re
import g4f
import sys
import time
import os
import json

from cache import *
from config import *
from status import *
from constants import *
from typing import List
from datetime import datetime
from termcolor import colored
from selenium_firefox import *
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common import keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

class Twitter:
    """
    Class for the Bot, that grows a Twitter (X) account.
    """
    def __init__(self, account_uuid: str, account_nickname: str, fp_profile_path: str, topic: str) -> None:
        """
        Initializes the Twitter Bot.

        Args:
            account_uuid (str): The account UUID
            account_nickname (str): The account nickname
            fp_profile_path (str): The path to the Firefox profile
            topic (str): The main topic to post about

        Returns:
            None
        """
        self.account_uuid: str = account_uuid
        self.account_nickname: str = account_nickname
        self.fp_profile_path: str = fp_profile_path
        self.topic: str = topic

        # Initialize the Firefox options with a profile
        self.options: Options = Options()
        
        # Set headless state if configured
        if get_headless():
            self.options.add_argument("--headless")

        # Set the Firefox profile using FirefoxProfile (preferred method)
        firefox_profile = FirefoxProfile(fp_profile_path)
        self.options.profile = firefox_profile

        # Initialize the GeckoDriver service
        self.service: Service = Service(GeckoDriverManager().install())

        # Initialize the Firefox WebDriver
        self.browser: webdriver.Firefox = webdriver.Firefox(service=self.service, options=self.options)

    def post(self, text: str = None) -> None:
        """
        Posts generated text (or a provided text) to Twitter (X).

        Args:
            text (str): Optional text to post. If None, a generated post will be used.

        Returns:
            None
        """
        bot: webdriver.Firefox = self.browser
        verbose: bool = get_verbose()

        # Navigate directly to x.com/home
        bot.get("https://x.com")
        time.sleep(2)

        # Generate or use provided post content
        post_content: str = self.generate_post() if text is None else text
        now: datetime = datetime.now()

        print(colored(f" => Posting to Twitter:", "blue"), post_content[:30] + "...")

        try:
            # 1) Locate the visible text area for composing a new post
            #    This is typically data-testid='tweetTextarea_0' if you're logged in and on Home
            tweet_box = WebDriverWait(bot, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']")
                )
            )

            # Click into the composer to ensure focus (sometimes needed)
            tweet_box.click()

            # 2) Enter your text into the composer
            tweet_box.send_keys(post_content)

        except exceptions.TimeoutException:
            print("Timeout: Unable to locate the tweet input box on the Home feed.")
            return

        # 3) Locate the inline Tweet button (data-testid='tweetButtonInline') and click
        try:
            tweet_button = WebDriverWait(bot, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "div[data-testid='tweetButtonInline']")
                )
            )
            tweet_button.click()
        except exceptions.TimeoutException:
            print("Timeout: Unable to find or click the Tweet button.")
            return

        if verbose:
            print(colored(" => Clicked the Tweet button on X (Home composer).", "blue"))

        time.sleep(4)

        # Add the posted content to the local cache
        self.add_post({
            "content": post_content,
            "date": now.strftime("%m/%d/%Y, %H:%M:%S")
        })

        success("Posted to Twitter successfully!")

    def get_posts(self) -> List[dict]:
        """
        Gets the posts from the cache for this account.

        Returns:
            A list of post dictionaries
        """
        if not os.path.exists(get_twitter_cache_path()):
            # Create the cache file if it doesn't exist
            with open(get_twitter_cache_path(), 'w') as file:
                json.dump({
                    "posts": [],
                    "accounts": []
                }, file, indent=4)

        with open(get_twitter_cache_path(), 'r') as file:
            parsed = json.load(file)

            # Find our account
            if "accounts" in parsed:
                for account in parsed["accounts"]:
                    if account["id"] == self.account_uuid:
                        return account.get("posts", [])
            return []

    def add_post(self, post: dict) -> None:
        """
        Adds a new post to the cache for this account.

        Args:
            post (dict): The post to add, must contain 'content' and 'date'.

        Returns:
            None
        """
        posts = self.get_posts()
        posts.append(post)

        with open(get_twitter_cache_path(), "r") as file:
            previous_json = json.loads(file.read())
            
            # Ensure 'accounts' exists
            if "accounts" not in previous_json:
                previous_json["accounts"] = []

            # Find our account by ID or create if missing
            account_found = False
            for account in previous_json["accounts"]:
                if account["id"] == self.account_uuid:
                    if "posts" not in account:
                        account["posts"] = []
                    account["posts"].append(post)
                    account_found = True
                    break

            if not account_found:
                previous_json["accounts"].append({
                    "id": self.account_uuid,
                    "posts": [post]
                })
            
            # Commit changes
            with open(get_twitter_cache_path(), "w") as f:
                f.write(json.dumps(previous_json, indent=4))

    def generate_post(self) -> str:
        """
        Generates a short post for the Twitter account based on the self.topic,
        using a GPT-like AI model via g4f.

        Returns:
            (str) Generated post text
        """
        # Prompt the model
        completion = g4f.ChatCompletion.create(
            model=parse_model(get_model()),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Generate a Twitter post about: {self.topic} "
                        f"in {get_twitter_language()}. "
                        f"The limit is 2 sentences. "
                        f"Choose a specific sub-topic of the provided topic."
                    )
                }
            ]
        )

        if get_verbose():
            info("Generating a post...")

        if completion is None:
            error("Failed to generate a post. Please try again.")
            sys.exit(1)

        # Clean up the generated text (remove * and any extra quotes)
        completion = re.sub(r"\*", "", completion).replace("\"", "")

        if get_verbose():
            info(f"Length of post: {len(completion)}")

        # If the post is too long (>= 260 chars), regenerate
        if len(completion) >= 260:
            return self.generate_post()

        return completion