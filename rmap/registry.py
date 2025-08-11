from __future__ import annotations

from pathlib import Path

import aiofiles

from pydantic import BaseModel

from .post import Post, Comment as PostComment
from .user import Comment as UserComment


__all__ = (
    "Registry",

    "dump",
    "dump_models",
    "get_post_comment_file",
    "get_post_file",
    "get_user_comment_file",
    "load",
    "load_models",
)


_DEFAULT_ENCODING = "utf-8"


class Registry(BaseModel):
    posts: set[Post]
    post_comments: set[PostComment]
    user_comments: set[UserComment]


def get_post_file(root: Path) -> Path:
    return root / "posts.feed"


def get_post_comment_file(root: Path) -> Path:
    return root / "post_comments.feed"


def get_user_comment_file(root: Path) -> Path:
    return root / "user_comments.feed"


async def dump_models(models: Iterable[BaseModel], path: Path) -> None:
    if not models:
        return

    async with aiofiles.open(path, "w", encoding=_DEFAULT_ENCODING) as stream:
        for model in models:
            await stream.write(model.model_dump_json())
            await stream.write("\n")


async def load_models[T: BaseModel](
    model_type: type[T],
    path: Path
) -> set[T]:
    models = set()

    async with aiofiles.open(path, "r", encoding=_DEFAULT_ENCODING) as stream:
        async for line in stream:
            models.add(model_type.model_validate_json(line))

    return models


async def load(root: Path) -> Registry:
    post_file = get_post_file(root)
    post_comment_file = get_post_comment_file(root)
    user_comment_file = get_user_comment_file(root)

    posts = set()
    post_comments = set()
    user_comments = set()

    if post_file.exists():
        posts = await load_models(Post, post_file)

    if post_comment_file.exists():
        post_comments = await load_models(PostComment, post_comment_file)

    if user_comment_file.exists():
        user_comments = await load_models(UserComment, user_comment_file)

    return Registry(
        posts=posts,
        post_comments=post_comments,
        user_comments=user_comments
    )


async def dump(registry: Registry, root: Path) -> None:
    post_file = get_post_file(root)
    post_comment_file = get_post_comment_file(root)
    user_comment_file = get_user_comment_file(root)
    encoding = _DEFAULT_ENCODING

    await dump_models(registry.posts, post_file)
    await dump_models(registry.post_comments, post_comment_file)
    await dump_models(registry.user_comments, user_comment_file)
