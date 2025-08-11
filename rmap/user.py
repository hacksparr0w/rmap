import asyncio

from typing import Optional

from playwright.async_api import Locator, Page
from pydantic import BaseModel

from .base import get_main_url


__all__ = (
    "Comment",

    "expand_page",
    "get_comment_permalink",
    "get_comment_url",
    "get_overview_permalink",
    "parse_comment",
    "scrape_comments"
)


class Comment(BaseModel, frozen=True):
    id: str
    href: str
    post_id: str
    author: str
    author_id: str
    subreddit: str
    score: int
    content: Optional[str]
    is_deleted: bool


def get_overview_permalink(username: str) -> str:
    return f"/user/{username}/"


def get_comment_permalink(username: str) -> str:
    return get_overview_permalink(username) + "comments/"


def get_comment_url(username: str) -> str:
    return get_main_url() + get_comment_permalink(username)


async def expand_page(page: Page, latecy: float = 1.5) -> None:
    async def get_body_scroll_height(page: Page) -> int:
        return await page.evaluate("document.body.scrollHeight")

    previous_scroll_height = await get_body_scroll_height(page)

    while True:
        await page.evaluate(
            f"document.body.scrollTo({{ y: {previous_scroll_height} }})"
        )

        await asyncio.sleep(latecy)

        current_scroll_height = await get_body_scroll_height(page)

        if current_scroll_height <= previous_scroll_height:
            return


async def parse_comment(root_locator: Locator, author: str) -> Comment:
    id = await root_locator.get_attribute("comment-id")
    href = await root_locator.get_attribute("href")
    author_id = await root_locator.get_attribute("user-id")

    parts = href.split("/")
    subreddit = parts[2]
    post_id = parts[4]

    post_id = "t3_" + post_id

    action_row_locator = root_locator.locator("shreddit-comment-action-row")
    score = await action_row_locator.get_attribute("score")
    score = int(score)

    content_locator = root_locator.locator("#-post-rtjson-content")
    content_locator_count = await content_locator.count()

    is_deleted = content_locator_count == 0

    content = await content_locator.inner_text() if not is_deleted else None

    return Comment(
        id=id,
        href=href,
        post_id=post_id,
        author=author,
        author_id=author_id,
        subreddit=subreddit,
        score=score,
        content=content,
        is_deleted=is_deleted
    )


async def scrape_comments(page: Page) -> list[Comment]:
    username_locator = page.locator("h1").nth(0)
    username = await username_locator.inner_text()

    await expand_page(page)

    comments = []
    comment_locators = await page.locator("shreddit-profile-comment").all()

    for comment_locator in comment_locators:
        comment = await parse_comment(comment_locator, username)
        comments.append(comment)

    return comments
