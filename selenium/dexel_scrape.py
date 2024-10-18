from selenium.webdriver.common.by import By
from selenium.common import exceptions as ex
import undetected_chromedriver as uc
from pymongo import MongoClient
from time import sleep
import re
import pandas as pd


class DexelScrape:
    """
    Scrapes www.dexel.co.uk for tyre information
    """
    def __init__(self):
        client = MongoClient("mongodb://localhost:27017")
        self.db = client['dexel_data']['results']

        self.driver = uc.Chrome()

        self.all_search_params = [
            {
                "Width": 205,
                "Aspect Ratio": 55,
                "Rim Size": 16
            },
            {
                "Width": 225,
                "Aspect Ratio": 50,
                "Rim Size": 16
            },
            {
                "Width": 185,
                "Aspect Ratio": 60,
                "Rim Size": 14
            }
            ]

    def search_values(self, search_params: dict = None):
        """
        Carries out the search to get to the tyre list page
        :param search_params:
        :return:
        """
        self.driver.get("https://www.dexel.co.uk/tyres")
        sleep(6)
        search_box = self.driver.find_element(By.CSS_SELECTOR, "div.api-tabs")

        search_box.find_element(By.CSS_SELECTOR, ".tab-li-child:nth-of-type(2) a").click()
        sleep(4)
        search_box.find_element(By.CSS_SELECTOR,
                                f"select.width_list option[value='{search_params['Width']}'").click()
        sleep(2)
        search_box.find_element(By.CSS_SELECTOR,
                                f"select.profile_list option[value='{search_params['Aspect Ratio']}'").click()
        sleep(2)
        search_box.find_element(By.CSS_SELECTOR,
                                f"select.size_list option[value='{search_params['Rim Size']}'").click()
        sleep(2)
        search_box.find_element(By.CSS_SELECTOR, "a.tyre-size-select").click()
        sleep(4)
        self.driver.find_element(By.CSS_SELECTOR, "button.btn-add-tyre").location_once_scrolled_into_view
        sleep(2)
        self.driver.find_element(By.CSS_SELECTOR, "button.btn-add-tyre").click()
        sleep(4)

    def get_tyres(self, search_num: int):
        """
        Gets tyres from page and adds the information to the database
        :param search_num: Keeps track of which search parameters are currently in use
        :return:
        """
        elements = self.driver.find_elements(By.CSS_SELECTOR, ".tkf-product-section:nth-of-type(1) div.box")
        for element in elements:
            # Getting all information listed in requirements
            brand = element.find_element(By.CSS_SELECTOR, ".brand-logo-wrapper img").get_attribute('alt').strip()
            seasonality = element.find_element(By.CSS_SELECTOR, "div.tyre-icons i").get_attribute('title').strip()
            price = element.find_element(By.CSS_SELECTOR, "span.price-number").text.strip()
            # Getting size and pattern in element search, so they can be split
            tyre_info = element.find_element(By.CSS_SELECTOR, "p").text.strip()
            # Carrying out regex search to find tyre size, so it can be separated
            try:
                regex = re.compile(r"^[0-9]+/[0-9]+[A-Za-z]+[0-9]+ [0-9]+[A-Za-z]", re.IGNORECASE)
                size = regex.findall(tyre_info)[0].strip()
            except IndexError:
                regex = re.compile(r"[0-9]+/[0-9]+[A-Za-z]+[0-9]+ \([0-9]+[A-Za-z]\)\s", re.IGNORECASE)
            pattern = tyre_info.replace(size, "").strip()

            # Getting extra info
            try:
                resistance = element.find_element(By.CSS_SELECTOR, "a.icon1").text
                grip = element.find_element(By.CSS_SELECTOR, "a.icon2").text
                noise = element.find_element(By.CSS_SELECTOR, "a.icon3").text
            except ex.NoSuchElementException:
                resistance = None
                grip = None
                noise = None

            # Adding data to database
            record = {
                "Website Scraped": "www.dexel.co.uk",
                "Tyre Brand": brand,
                "Tyre Pattern": pattern,
                "Tyre Size": size,
                "Seasonality": seasonality,
                "Price": price,
                "Rolling Resistance": resistance,
                "Wet Grip": grip,
                "Exterior Noise": noise,
                "Search Number": search_num
            }
            self.db.insert_one(record)

    def next_page(self, search_num: int):
        """
        Moves scrape to the next page
        :param search_num: Keeps track of which search parameters are currently in use
        :return:
        """
        try:
            next_button = self.driver.find_element(By.XPATH, ".//a[contains(text(), '>')]")
            next_button.location_once_scrolled_into_view
            sleep(2)
            next_button.click()
            sleep(6)
            self.get_tyres(search_num)
            return True
        except ex.NoSuchElementException:
            print("NO MORE PAGES!!!")
            return False


def main():
    scrape = DexelScrape()
    for num, search_params in enumerate(scrape.all_search_params):
        scrape.search_values(search_params)
        scrape.get_tyres(num+1)
        page_count = 1
        while True:
            print(f"Current Page: {page_count}")
            if not scrape.next_page(num+1):
                break
            page_count += 1

    # Exports data from database to csv
    input("Press ENTER to download file")
    results_df = pd.DataFrame(scrape.db.find({}))
    results_df.to_csv("dexel_results.csv", index=False)


if __name__ == "__main__":
    main()
