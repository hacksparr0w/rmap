import asyncio

from typing import Optional

from playwright.async_api import Locator, Page
from pydantic import BaseModel

from .base import get_main_url, get_short_url

__all__ = (
    "Post",

    "expand_comments",
    "get_url",
    "parse",
    "parse_comment",
    "scrape"
)


_EXPANDABLE_SELECTORS = (
    ('faceplate-partial[loading="action"]', None),
    ('shreddit-comment[collapsed]', {"x": 14, "y": 20})
)


class Post(BaseModel, frozen=True):
    id: str
    title: str
    permalink: str
    author: str
    author_id: Optional[str]
    subreddit: str
    subreddit_id: str
    comment_count: int
    score: int
    content: Optional[str]
    is_deleted: bool
    created_at: str


class Comment(BaseModel, frozen=True):
    id: str
    permalink: Optional[str]
    post_id: str
    parent_id: Optional[str]
    author: str
    score: Optional[int]
    content: Optional[str]
    is_deleted: bool
    created_at: str


def get_url_from_permalink(permalink: str) -> str:
    return get_main_url() + permalink


def get_url_from_id(id: str) -> str:
    return get_short_url() + "/" + id[3:]


async def parse(root: Locator) -> Post:
    id = await root.get_attribute("id")
    title = await root.get_attribute("post-title")
    permalink = await root.get_attribute("permalink")
    
    author = await root.get_attribute("author")
    author_id = await root.get_attribute("author-id")

    subreddit = await root.get_attribute("subreddit-prefixed-name")
    subreddit_id = await root.get_attribute("subreddit-id")

    comment_count = int(await root.get_attribute("comment-count"))
    score = int(await root.get_attribute("score"))

    text_body_locator = root.locator('div[slot="text-body"]')

    text_body_element_count = await text_body_locator.count() 
    content = await text_body_locator.inner_text() if \
        text_body_element_count > 0 else None

    removed_banner_element_count = await root \
        .locator('div[slot="post-removed-banner"]') \
        .count()

    is_deleted = removed_banner_element_count > 0 or \
        title == "[deleted by user]"

    created_at = await root.get_attribute("created-timestamp")

    return Post(
        id=id,
        title=title,
        permalink=permalink,
        author=author,
        author_id=author_id,
        subreddit=subreddit,
        subreddit_id=subreddit_id,
        comment_count=comment_count,
        score=score,
        content=content,
        is_deleted=is_deleted,
        created_at=created_at
    )


async def parse_comment(root: Locator, post_id: str) -> Comment:
    content_locator = root \
        .locator('div[slot="comment"]') \
        .nth(0)

    content_element_count = await content_locator.count()

    id = await root.get_attribute("thingid")
    permalink = await root.get_attribute("permalink")
    parent_id = await root.get_attribute("parentid")

    author = await root.get_attribute("author")

    is_deleted = await root.get_attribute("is-comment-deleted") == "true" or \
        content_element_count == 0

    score = await root.get_attribute("score")
    score = int(score) if score else None
    content = await content_locator.inner_text() if not is_deleted else None

    time_locator = root \
        .locator('div[slot="commentMeta"] time') \
        .nth(0)

    created_at = await time_locator.get_attribute("datetime")

    return Comment(
        id=id,
        permalink=permalink,
        post_id= post_id,
        parent_id=parent_id,
        author=author,
        score=score,
        content=content,
        is_deleted=is_deleted,
        created_at=created_at
    )


async def expand_comments(page: Page, latency: float = 0.75) -> None:
    while True:
        at_least_one = False

        for selector, position in _EXPANDABLE_SELECTORS:
            target = page.locator(selector)
            count = await target.count()
            if  count == 0:
                continue

            target = target.nth(0)
            is_visible = await target.is_visible() 

            if not is_visible:
                continue

            await page.evaluate("window.scrollTo({ top: 0 })")
            await target.click(force=True, position=position)
            at_least_one = True
            await asyncio.sleep(latency)

        if not at_least_one:
            break


async def scrape(page: Page, url: str) -> tuple[Post, list[Comment]]:
    await page.goto(url)
    await asyncio.sleep(3)

    await expand_comments(page)

    post_root = page.locator("shreddit-post").nth(0)
    post = await parse(post_root)

    comments = []

    for comment_root in await page.locator("shreddit-comment").all():
        comment = await parse_comment(comment_root, post.id)
        comments.append(comment)

    return post, comments
