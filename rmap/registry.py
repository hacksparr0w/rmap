from __future__ import annotations

from pathlib import Path

import aiofiles

from pydantic import BaseModel

from .comment import Comment
from .post import Post


__all__ = (
    "Registry",

    "dump",
    "get_comment_file",
    "get_post_file",
    "load"
)


_DEFAULT_ENCODING = "utf-8"


async def write_model(model, output):
    await output.write(model.model_dump_json())
    await output.write("\n")


class Registry(BaseModel):
    posts: set[Post]
    comments: set[Comment]


def get_post_file(root: Path) -> Path:
    return root / "posts.feed"


def get_comment_file(root: Path) -> Path:
    return root / "comments.feed"


async def load_posts(path: Path) -> set[Post]:
    posts = set()

    async with aiofiles.open(path, "r", encoding=_DEFAULT_ENCODING) as stream:
        async for line in stream:
            posts.add(Post.model_validate_json(line))

    return posts


async def load_comments(path: Path) -> set[Post]:
    comments = set()

    async with aiofiles.open(path, "r", encoding=_DEFAULT_ENCODING) as stream:
        async for line in stream:
            comments.add(Comment.model_validate_json(line))

    return comments


async def load(root: Path) -> Registry:
    post_file = get_post_file(root)
    comment_file = get_comment_file(root)

    posts = set()
    comments = set()

    if post_file.exists():
        posts = await load_posts(post_file)

    if comment_file.exists():
        comments = await load_comments(comment_file)

    return Registry(
        posts=posts,
        comments=comments
    )


async def dump(registry: Registry, root: Path) -> None:
    post_file = get_post_file(root)
    comment_file = get_comment_file(root)
    encoding = _DEFAULT_ENCODING

    async with \
        aiofiles.open(post_file, "w", encoding=encoding) as post_stream, \
        aiofiles.open(comment_file, "w", encoding=encoding) as comment_stream:

        for post in registry.posts:
            await write_model(post, post_stream)

        for comment in registry.comments:
            await write_model(comment, comment_stream)
