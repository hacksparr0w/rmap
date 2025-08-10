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


async def _write(entity, output):
    await output.write(entity.model_dump_json())
    await output.write("\n")


class Registry(BaseModel):
    posts: set[Post]
    comments: set[Comment]


def get_post_file(root: Path) -> Path:
    return root / "posts.feed"


def get_comment_file(root: Path) -> Path:
    return root / "comments.feed"


async def load(root: Path) -> Registry:
    post_file = get_post_file(root)
    comment_file = get_comment_file(root)
    encoding = _DEFAULT_ENCODING

    async with \
        aiofiles.open(post_file, "r", encoding=encoding) as post_stream, \
        aiofiles.open(comment_file, "r", encoding=encoding) as comment_stream:

        posts = {Post.model_validate_json(line) for line in post_stream}
        comments = {
            Comment.model_validate_json(line) for line in comment_stream
        }

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

        for post in posts:
            await _write(post, post_stream)

        for comment in comments:
            await _write(comment, comment_stream)
