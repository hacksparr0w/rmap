import asyncio

from typing import Optional

from playwright.async_api import Locator, Page
from pydantic import BaseModel

from .comment import Comment, parse as parse_comment


__all__ = (
    "Post",

    "expand_comments",
    "get_url",
    "parse",
    "scrape"
)


_EXPANDABLE_SELECTORS = (
    ('faceplate-partial[loading="action"]', None),
    ('shreddit-comment[collapsed]', {"x": 10, "y": 21})
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


def get_url(permalink: str) -> str:
    return "https://www.reddit.com" + permalink


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
