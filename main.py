import json
import time

import requests
import bs4
import asyncio
import aiohttp
import sys


# script to scrape https://www.atollsofmaldives.gov.mv


async def get_page(session: aiohttp.ClientSession, link: str):
    """asynchronously get a page"""
    async with session.get(link) as response:
        raw_get = await response.text()
    return raw_get


async def get_island_pages(session: aiohttp.ClientSession, islands: dict):
    island_urls = []
    for island_name in islands:
        island = islands[island_name]
        island_urls.append(island["Island Link"])

    tasks: list = []
    for url in island_urls:
        task = asyncio.create_task(get_page(session, url))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    return results


async def get_atolls(root_url: str) -> dict:
    """get names and initial details of atolls"""
    root_raw: requests.api = requests.get(f"{root_url}/atolls")

    root_soup: bs4.BeautifulSoup = bs4.BeautifulSoup(root_raw.content.decode(), "html.parser")

    atoll_divs: bs4.ResultSet = root_soup.findAll("div", class_="listing-body")
    atolls: dict = {}

    atoll_div: bs4.element.Tag
    for atoll_div in atoll_divs:
        title_details: bs4.element.Tag = atoll_div.find("div", class_="listing-title")
        link: str = atoll_div.find("a")["href"]
        names_raw: str = title_details.find("a").get_text()
        names: list = names_raw.split("  ")
        short_name: str = (names[1]).replace("(", "")
        short_name: str = short_name.replace(")", "")
        short_name: str = short_name.replace(" Atoll", "")
        long_name: str = (names[0])

        text_class: bs4.element.Tag = atoll_div.find("div", class_="listing-text")
        text_element: bs4.element.Tag = text_class.find("p")
        text: str = text_element.get_text()

        atoll = {
            "Full Name": long_name,
            "Short Name": short_name,
            "Short Description": text,
            "Long Description": "",
            "absolute_link": f"{root_url}/{link}",
        }

        atolls.update({short_name: atoll})

    return atolls


def format_name(island_name: str) -> str:
    remove: list = ["(R)", "(U)", "(IND)", "(H)", "(PR)", "(I)", "(P)", "(I)", "(ADF,H)"]
    for string in remove:
        island_name = island_name.replace(string, "")
    island_name = island_name.rstrip(" ")
    return island_name


async def update_atolls(atolls: dict, root_url: str, session: aiohttp.ClientSession) -> dict:
    """get each atolls page, scrape and update the dict"""
    for name in atolls:
        atoll = atolls[name]
        link = atoll["absolute_link"]

        raw_get = await asyncio.create_task(get_page(session, link))

        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(raw_get, "html.parser")

        text_class: bs4.element.Tag = soup.find_all("div", class_="listing-text details")[0]
        text: str = text_class.find("p").get_text()

        islands_class: bs4.ResultSet = soup.find_all("ul", class_="list")
        islands: dict = {}
        for island_class in islands_class:
            island_element: bs4.element.Tag = island_class.find("a")
            island_link: str = island_element["href"]
            island_name: str = island_element.get_text()
            island_name = format_name(island_name)
            island_absolute_link = root_url + island_link

            island: dict = {
                "Island Name": island_name,
                "Island Link": island_absolute_link
            }

            # island = await scrape_island(island, session)
            islands.update({island_name: island})

        pages: asyncio.tasks = await get_island_pages(session, islands)

        islands = await scrape_islands(islands, pages)

        atoll.update({
            "Long Description": text,
            "Number of Islands": len(islands),
            "Islands": islands
        })
        atolls.update({name: atoll})
        print(f"{name}: done")

    return atolls


async def scrape_islands(islands: dict, pages: asyncio.tasks) -> dict:
    """get each island in the island list and scrape, update dict"""

    # island_raw: requests.api = requests.get(link) # synchronous code

    for island_raw in pages:
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(island_raw, "html.parser")

        island_element: bs4.element.Tag = soup.find_all(class_="block-title")[0]

        split = island_element.get_text().split("-")
        split.pop()
        island_name = "-".join(split)
        island_name = island_name.replace("\n", "")
        island_name = format_name(island_name)

        island: dict = islands[island_name]

        table_raw: bs4.element.Tag = soup.find_all("fieldset", class_="container-15")[0]
        table: bs4.ResultSet = table_raw.select("tr")
        row: bs4.element.Tag

        for row in table:
            content: str = row.get_text()
            contents: list = content.split("\n")
            explanation: str = contents[1]
            value: str = contents[2]

            island.update({
                explanation: value
            })

        table_raw: bs4.element.Tag = soup.find_all("table", class_="display tbl_details dataTable")[0]

        for row in table_raw:
            text: str = row.get_text()
            texts = text.split("\n")
            explanation = texts[1]

            if texts[0] == "" == texts[1]:
                continue

            if explanation == "Weather condition":
                value: str = texts[2]
            else:
                text_value: bs4.element.Tag = row.find("div")
                class_string: str = str(text_value)

                class_strings: list = class_string.split('"')
                try:
                    cross_tick: str = class_strings[1]
                except IndexError:
                    value: str = "Unknown"
                else:
                    if cross_tick == "tick-mark":
                        value: bool = True
                    elif cross_tick == "cross-mark":
                        value: bool = False
                    else:
                        value: str = "Unknown"

            island.update({
                explanation: value
            })
        islands.update({island_name: island})

    return islands


async def main() -> None:
    root_url = "https://www.atollsofmaldives.gov.mv/"
    atolls: dict = await get_atolls(root_url)

    async with aiohttp.ClientSession() as session:
        atolls: dict = await update_atolls(atolls, root_url, session)

    with open("atolls.json", 'w') as f:
        json.dump(atolls, f, indent=4)


if __name__ == '__main__':
    start = time.time()
    asyncio.run(main())
    print(time.time() - start)
