from typing import Optional

from playwright.async_api import Locator
from pydantic import BaseModel


__all__ = (
    "Comment",
    "parse"
)


class Comment(BaseModel):
    id: str
    permalink: Optional[str]
    post_id: str
    parent_id: Optional[str]
    author: str
    score: Optional[int]
    content: Optional[str]
    is_deleted: bool
    created_at: str


async def parse(root: Locator, post_id: str) -> Comment:
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
