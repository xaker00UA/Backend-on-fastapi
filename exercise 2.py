import aiohttp
from bs4 import BeautifulSoup
import asyncio
from pymongo import MongoClient

cluster = MongoClient("mongodb://localhost:27017/")
collection = cluster.ebay["product"]


class Two_Task:
    def __init__(
        self,
    ):
        self.sem = asyncio.Semaphore(10)

    async def get_html(self, items):
        async def run(url, session):
            async with session.get(url) as res:
                return await res.text()

        async with aiohttp.ClientSession() as session:
            tasks = [run(item, session) for item in items]
            return await asyncio.gather(*tasks)

    def html(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        name = soup.find(name="h1", class_="x-item-title__mainTitle").find("span").text
        price = soup.find(name="div", class_="x-price-primary").find("span").text
        img = (
            soup.find(
                name="div",
                class_="ux-image-carousel-item image-treatment active image",
            )
            .find("img")
            .get("src")
        )
        shop = (
            soup.find("div", class_="x-sellercard-atf__info")
            .find(name="span", class_="ux-textspans ux-textspans--BOLD")
            .text
        )
        dos = soup.find("div", class_="ux-labels-values__values col-9").text
        return {
            "name": name,
            "price": price,
            "img": img,
            "shop": shop,
            "dos": dos,
            "url": url,
        }

    def get_json(self, items: list):
        html = asyncio.run(self.get_html(items))
        res = []
        for h, url in zip(html, items):
            res.append(self.html(h, url))
        return res


params = [
    "https://www.ebay.com/itm/375111511309?itmmeta=01J2RSYR28M27TXWYN4J3CM3GP&hash=item5756636d0d:g:oyoAAOSwntdlDHDO",
    "https://www.ebay.com/itm/374984508099?_trkparms=amclksrc%3DITM%26aid%3D1110025%26algo%3DHOMESPLICE.COMPOSITELISTINGS%26ao%3D1%26asc%3D267025%26meid%3D36becc8132034a57a35d2ca1b7b362e2%26pid%3D101506%26rk%3D3%26rkt%3D25%26sd%3D375111511309%26itm%3D374984508099%26pmt%3D1%26noa%3D1%26pg%3D4481478%26algv%3DAlgoIndex5SimRanker%26brand%3DHP&_trksid=p4481478.c101506.m1851",
    "https://www.ebay.com/itm/226155223034?itmmeta=01J2RSYR28JJDNB5YNYA9TMWS6&hash=item34a7e6d7fa:g:318AAOSwzyVmS-gb&var=525282910013",
]


def main():
    A = Two_Task().get_json(params)
    collection.insert_many(A)


main()
