import json
import requests
import bs4
import asyncio


# script to scrape https://www.atollsofmaldives.gov.mv


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


async def update_atolls(atolls: dict, root_url: str) -> dict:
    """get each atolls page, scrape and update the dict"""
    for name in atolls:
        atoll = atolls[name]
        link = atoll["absolute_link"]

        raw_get: requests.api = requests.get(link)
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(raw_get.content.decode(), "html.parser")

        text_class: bs4.element.Tag = soup.find_all("div", class_="listing-text details")[0]
        text: str = text_class.find("p").get_text()

        islands_class: bs4.ResultSet = soup.find_all("ul", class_="list")
        islands: dict = {}
        for island_class in islands_class:
            island_element: bs4.element.Tag = island_class.find("a")
            island_link: str = island_element["href"]
            island_name: str = island_element.get_text()
            island_absolute_link = root_url + island_link

            island: dict = {
                "Island Name": island_name,
                "Island Link": island_absolute_link
            }

            island = await scrape_island(island)
            islands.update({island_name: island})

        atoll.update({
            "Long Description": text,
            "Number of Islands": len(islands),
            "Islands": islands
        })
        atolls.update({name: atoll})
        print(f"{name}: done")

    return atolls


async def scrape_island(island: dict) -> dict:
    """get each island in the island list and scrape, update dict"""
    link = island["Island Link"]
    island_raw: requests.api = requests.get(link)

    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(island_raw.content.decode(), "html.parser")
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

    return island


async def main() -> None:
    root_url = ""
    atolls: dict = await get_atolls(root_url)
    atolls: dict = await update_atolls(atolls, root_url)

    with open("atolls.json", 'w') as f:
        json.dump(atolls, f, indent=4)


if __name__ == '__main__':
    asyncio.run(main())
