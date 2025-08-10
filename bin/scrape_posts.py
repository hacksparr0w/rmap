import asyncio

from functools import wraps
from pathlib import Path
from typing import Optional

import aiohttp
import aiofiles.os
import playwright.async_api
import rmap.post
import rmap.registry


_REGISTRY_DIRECTORY = Path.home() / ".rmap"
_URLS_FILE_URL = "https://gist.githubusercontent.com/hacksparr0w/a3d74186b9ff8f23a2256e72023a5234/raw/57c49a5d5f88bab7ed1526f0758c5862814f7858/reddit_post_urls.txt"


class PlaywrightClient:
    parent: playwright.async_api.Playwright
    browser: Optional[playwright.async_api.Browser]
    browser_context: Optional[playwright.async_api.BrowserContext]
    page: Optional[playwright.async_api.Page]

    def __init__(self, parent):
        self.parent = parent
        self.browser = None
        self.browser_context = None
        self.page = None

    async def restart(self) -> None:
        if not self.browser:
            self.browser = await self.parent.firefox.launch()

        if self.browser_context:
            await self.browser_context.close()
        
        self.browser_context = await self.browser.new_context()
        self.page = await self.browser_context.new_page()
    
    async def stop(self) -> None:
        await self.browser_context.close()
        await self.browser.close()

        self.page = None
        self.browser_context = None
        self.browser = None


async def get_urls():
    async with aiohttp.ClientSession() as session:
        async with session.get(_URLS_FILE_URL) as response:
            data = await response.text()

            return data.split("\n")


def retry(
    maximum_retries = 3,
    errors = (Exception,),
    on_retry = None
):
    def decorator(function):
        @wraps(function)
        async def wrapper(*args, **kwargs):
            retries = 0
            last_error = None

            while retries < maximum_retries:
                try:
                    return await function(*args, **kwargs)
                except Exception as error:
                    if not isinstance(error, errors):
                        raise

                    last_error = error
                    retries += 1

                    if on_retry:
                        await on_retry()

            raise last_error

        return wrapper

    return decorator


async def scrape(client, url):
    return await asyncio.wait_for(
        rmap.post.scrape(
            client.page,
            url
        ),
        timeout=180.0
    )


async def main():
    try:
        await aiofiles.os.mkdir(_REGISTRY_DIRECTORY)
    except FileExistsError:
        pass

    registry = await rmap.registry.load(_REGISTRY_DIRECTORY)
    urls = []

    async with playwright.async_api.async_playwright() as parent:
        client = PlaywrightClient(parent)

        await client.restart()

        for url in urls:
            print(f"Scraping '{url}'")

            try:
                post, comments = await retry(
                    errors=(
                        asyncio.TimeoutError,
                        playwright.async_api.TimeoutError
                    ),
                    on_retry=client.restart
                )(scrape)(client, url)
            except Exception as error:
                print(f"An error occurred while scraping '{url}'")
                print(error)

                continue
            
            registry.posts.add(post)
            registry.comments.update(comments)

        await client.stop()
        await rmap.registry.dump(registry, _REGISTRY_DIRECTORY)


if __name__ == "__main__":
    asyncio.run(main())
