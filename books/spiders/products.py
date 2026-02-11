from pathlib import Path
from typing import Generator, Union
from scrapy.http import Response, Request
import html
import scrapy
from scrapy import Selector
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class ProductsSpider(scrapy.Spider):
    name = "products"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.driver = webdriver.Chrome()

    def close(self, reason: str) -> None:
        if hasattr(self, "driver") and self.driver:
            self.driver.quit()
            # def close(self, reason: str) -> None:
    #     self.driver.close()
    #     return self.close(reason)

    def parse(
            self, response: Response, **kwargs
    ) -> Generator[Union[dict, Request], None, None]:
        for product in response.css(".product_pod"):
            yield {
                "title": product.css("a::attr(title)").get(),
                "price": product.css(
                    ".price_color::text"
                ).get().replace("£", ""),
                "rating": RATING_MAP.get(
                    product.css(
                        "p.star-rating::attr(class)"
                    ).get().split()[-1], 0
                ),
                **self._parse_product(response, product),
            }

        filename = "products.html"
        Path(filename).write_bytes(response.body)
        self.log(f"Saved file {filename}")

        next_page = response.css(".next a::attr(href)").get()
        if next_page is not None:
            next_page_url = response.urljoin(next_page)
            yield scrapy.Request(url=next_page_url, callback=self.parse)

    def _parse_product(
            self, response: Response, product: Selector
    ) -> dict:
        absolute_url = response.urljoin(product.css("a::attr(href)").get())
        self.driver.get(absolute_url)
        try:
            description_list = self.driver.find_element(
                By.XPATH,
                "//div[@id='product_description']/following-sibling::p"
            )
            description = html.unescape(description_list.text).strip()
        except NoSuchElementException:
            description = ""
        try:
            upc_list = self.driver.find_element(By.CLASS_NAME, "table")
            upc = upc_list.find_element(By.TAG_NAME, "td").text
        except NoSuchElementException:
            upc = ""
        # category_elem = self.driver.find_element(By.CLASS_NAME, "breadcrumb")
        # all_lis = category_elem.find_elements(By.TAG_NAME, "li")  # ВСІ <li>
        # category = all_lis[-2].text if all_lis else ""
        try:
            category = self.driver.find_element(
                By.XPATH, "//ul[@class='breadcrumb']/li[last()-1]"
            ).text
        except NoSuchElementException:
            category = ""
        try:
            table = self.driver.find_element(By.CLASS_NAME, "table")
            tds = table.find_elements(By.TAG_NAME, "td")
            amount_in_stock = tds[3].text.strip("()") if len(tds) > 3 else ""
        except NoSuchElementException:
            amount_in_stock = ""

        return {
            "upc": upc,
            "category": category,
            "amount_in_stock": amount_in_stock,
            "description": description,
        }
