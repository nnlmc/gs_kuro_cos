from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html
import json
import os
import random
import re
import shutil
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlparse
from uuid import uuid4

import httpx

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event, Message
from gsuid_core.segment import MessageSegment
from gsuid_core.sv import Plugins, SV

from .kuro_cos_config import KuroCosConfig


Plugins(name='gs_kuro_cos', force_prefix=['ww', 'zs'], allow_empty_prefix=False)
sv = SV('库街区COS/同人')

BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / 'media_cache'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = 'https://api.kurobbs.com'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0'
)
DEV_CODE = 'H0O9l04JUG341k5UpUTMNpnGawC5Qt9p'
DISTINCT_ID = '195be91535f592-0915a368d4173f-4c657b58-1327104-195be9153601740'

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm', '.avi', '.flv', '.mkv', '.m3u8'}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
KURO_MEDIA_HOSTS = ('kurobbs.com', 'kurogame.com', 'aki-game.com')
URL_RE = re.compile(r"https?://[^\s'\"<>，。！？、）)\]}]+", re.IGNORECASE)

POST_TEXT_KEYS = (
    'postTitle', 'title', 'subject', 'content', 'summary', 'desc', 'description',
    'postContent', 'postDetail', 'textContent', 'richContent', 'articleContent',
    'markdownContent', 'topicContent', 'topicList', 'topicName', 'identifyNames',
    'newIdentifyNames', 'userName', 'nickname', 'user', 'author', 'postUser',
)
COS_KEYWORDS = (
    'cos', 'coser', 'cosplay', '正片', '返图', '试衣', '同人cos',
    '同人 cosplay', '妆造', '场照', '出镜', '摄影', '棚拍', '外景',
)
NON_COS_KEYWORDS = (
    '攻略', '养成', '培养', '配队', '阵容', '抽卡', '强度', '测评', '评测',
    '教程', '机制', '打法', '深塔', '声骸', '词条', '武器', '技能', '面板',
    '材料', '任务', '活动', '解谜', '兑换码', '签到',
)
SEARCH_KEYWORD_SUFFIXES = (
    'cos', 'COS', 'cosplay', '正片', 'cos正片', 'COS正片', '同人cos', '试衣', '返图',
)
REPOST_FORBIDDEN_KEYWORDS = (
    '禁止搬运', '禁止转载', '禁止转发', '禁止转帖', '禁止二传', '禁止二次上传',
    '禁止二改', '禁止盗图', '严禁搬运', '严禁转载', '严禁转发', '请勿搬运',
    '请勿转载', '请勿转发', '请勿二传', '未经授权转载', '未经授权搬运',
    '未经授权不得转载', '未经允许转载', '未经许可转载', '擅自转载', '擅自搬运',
    '私自转载', '私自搬运', '禁搬运', '禁转载', '禁转', '禁二传', 'do not repost',
    "don't repost", 'dont repost', 'please do not repost', 'no repost', 'repost prohibited',
    'reposting prohibited', 'repost forbidden', 'unauthorized repost', 'do not reupload',
    'no reupload', '転載禁止', '無断転載禁止', '無断使用禁止', '二次配布禁止',
    '무단전재금지', '무단배포금지',
)

RECENT_POST_IDS: deque[str] = deque(maxlen=100)
FETCH_LOCK = asyncio.Semaphore(1)


@dataclass(frozen=True, slots=True)
class MediaItem:
    url: str
    kind: str
    video_id: str = ''


@dataclass(frozen=True, slots=True)
class KuroPost:
    post_id: str
    title: str
    summary: str
    author: str
    url: str
    media: tuple[MediaItem, ...]
    label: str


@dataclass(frozen=True, slots=True)
class CommandSpec:
    prefix: str
    command: str
    label: str
    forum_id: int
    game_id: int
    video_only: bool = False
    strict_cos: bool = False
    search_suffixes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    spec: CommandSpec
    keyword: str = ''


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec('ww', 'cos视频', '鸣潮 COS', 17, 3, True, True, SEARCH_KEYWORD_SUFFIXES),
    CommandSpec('ww', 'cos', '鸣潮 COS', 17, 3, False, True, SEARCH_KEYWORD_SUFFIXES),
    CommandSpec('ww', '同人视频', '鸣潮同人', 11, 3, True),
    CommandSpec('ww', '同人', '鸣潮同人', 11, 3),
    CommandSpec('zs', '同人视频', '战双同人', 5, 2, True),
    CommandSpec('zs', '同人', '战双同人', 5, 2),
)
COMMANDS_BY_LENGTH = tuple(sorted(COMMANDS, key=lambda item: len(item.command), reverse=True))
COMMAND_PATTERN = r'\s*(?:cos视频|cos|同人视频|同人)(?:\s+.+)?'


def _cfg(key: str, default: Any = None) -> Any:
    try:
        value = KuroCosConfig.get_config(key).data
    except Exception:
        return default
    return default if value is None else value


def _cfg_bool(key: str, default: bool = False) -> bool:
    value = _cfg(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'y', 'on', 'enable', 'enabled', '开', '开启', '是'}:
            return True
        if normalized in {'0', 'false', 'no', 'n', 'off', 'disable', 'disabled', '关', '关闭', '否', ''}:
            return False
    return bool(value)


def _cfg_int(key: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        value = int(_cfg(key, default))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _cfg_float(key: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        value = float(_cfg(key, default))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _cfg_str(key: str, default: str = '') -> str:
    return str(_cfg(key, default) or '').strip()


def _debug(message: str) -> None:
    if _cfg_bool('debug_log', False):
        logger.info(f'[gs_kuro_cos] {message}')


def _clean_text(value: Any, limit: int = 120) -> str:
    text = re.sub(r'<[^>]+>', '', str(value or ''))
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]


def _strip_markup(value: Any) -> str:
    return html.unescape(re.sub(r'<[^>]+>', '', str(value or '')))


def _text_from_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ' '.join(_text_from_value(child) for child in value.values())
    if isinstance(value, list):
        return ' '.join(_text_from_value(child) for child in value)
    return ''


def _collect_post_text(node: dict[str, Any]) -> str:
    return ' '.join(_text_from_value(node.get(key)) for key in POST_TEXT_KEYS if key in node)


def _normalize_for_match(text: str) -> str:
    return re.sub(r'[\s\W_]+', '', _strip_markup(text).lower(), flags=re.UNICODE)


def _query_matches(node: dict[str, Any], query: str) -> bool:
    normalized_query = _normalize_for_match(query)
    if not normalized_query:
        return True
    return normalized_query in _normalize_for_match(_collect_post_text(node))


def _is_cos_search_result(node: dict[str, Any], query: str) -> bool:
    if not _query_matches(node, query):
        return False
    text = _normalize_for_match(_collect_post_text(node))
    title = _normalize_for_match(node.get('postTitle') or node.get('title') or node.get('subject') or '')
    cos_keywords = [_normalize_for_match(keyword) for keyword in COS_KEYWORDS]
    negative_keywords = [_normalize_for_match(keyword) for keyword in NON_COS_KEYWORDS]
    title_has_cos = any(keyword in title for keyword in cos_keywords)
    text_has_cos = any(keyword in text for keyword in cos_keywords)
    title_has_negative = any(keyword in title for keyword in negative_keywords)
    text_has_negative = any(keyword in text for keyword in negative_keywords)
    if title_has_negative or not text_has_cos:
        return False
    if text_has_negative and not title_has_cos:
        return False
    if not title_has_cos and not _extract_post_media(node):
        return False
    return True


def _has_repost_forbidden_text(node: dict[str, Any]) -> bool:
    text = _collect_post_text(node)
    if not text:
        return False
    lowered = text.lower()
    compact = _normalize_for_match(text)
    return any(keyword.lower() in lowered or _normalize_for_match(keyword) in compact for keyword in REPOST_FORBIDDEN_KEYWORDS)


def _normalize_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    url = value.strip().replace('\\/', '/').rstrip('.,;:!?，。；：！？、')
    if not url.startswith(('http://', 'https://')):
        return None
    parsed = urlparse(url)
    return url if parsed.scheme and parsed.netloc else None


def _url_suffix(url: str) -> str:
    return Path(urlparse(url).path.lower()).suffix


def _is_kuro_media_url(url: str) -> bool:
    host = (urlparse(url).hostname or '').lower()
    return any(host == key or host.endswith(f'.{key}') for key in KURO_MEDIA_HOSTS)


def _clean_video_id(value: Any) -> str:
    video_id = str(value or '').strip()
    return video_id if re.fullmatch(r'[A-Za-z0-9_-]{8,128}', video_id) else ''


def _dedupe_media(items: Iterable[MediaItem]) -> tuple[MediaItem, ...]:
    result: list[MediaItem] = []
    seen: set[str] = set()
    for item in items:
        key = item.video_id or item.url.split('?', 1)[0]
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


def _is_video_media(item: MediaItem) -> bool:
    return item.kind == 'video' or bool(item.video_id)


def _append_media_url(media: list[MediaItem], raw_url: Any, forced_kind: str | None = None) -> None:
    url = _normalize_url(raw_url)
    if not url:
        return
    suffix = _url_suffix(url)
    if not _is_kuro_media_url(url) and suffix not in MEDIA_EXTENSIONS:
        return
    if forced_kind == 'image' and suffix in VIDEO_EXTENSIONS:
        return
    if forced_kind == 'video' and suffix in IMAGE_EXTENSIONS:
        return
    kind = forced_kind
    if kind is None:
        if suffix in IMAGE_EXTENSIONS:
            kind = 'image'
        elif suffix in VIDEO_EXTENSIONS:
            kind = 'video'
    if kind:
        media.append(MediaItem(url, kind))


def _extract_urls_from_text(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [match.rstrip('.,;:!?，。；：！？、') for match in URL_RE.findall(value)]


def _extract_from_media_container(value: Any, forced_kind: str | None = None) -> list[MediaItem]:
    media: list[MediaItem] = []

    def visit(item: Any) -> None:
        if isinstance(item, str):
            if item.startswith(('http://', 'https://')):
                _append_media_url(media, item, forced_kind)
            else:
                for url in _extract_urls_from_text(item):
                    _append_media_url(media, url, forced_kind)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if isinstance(item, dict):
            if forced_kind in (None, 'video'):
                video_id = _clean_video_id(item.get('videoId') or item.get('video_id') or item.get('vodId'))
                if video_id:
                    media.append(MediaItem('', 'video', video_id))
            for key in ('url', 'imgUrl', 'imageUrl', 'picUrl', 'videoUrl', 'playUrl', 'coverUrl', 'resourceUrl', 'src', 'path'):
                if key in item:
                    _append_media_url(media, item.get(key), forced_kind)
            for key in ('urls', 'images', 'imgs', 'videos', 'resources', 'content', 'list'):
                if key in item:
                    visit(item.get(key))

    visit(value)
    return media


def _extract_post_media(node: dict[str, Any]) -> tuple[MediaItem, ...]:
    media: list[MediaItem] = []
    for key in ('imgContent', 'imageContent', 'images', 'imgs', 'picList', 'imageList'):
        if key in node:
            media.extend(_extract_from_media_container(node.get(key), 'image'))
    for key in ('videoContent', 'video', 'videos', 'videoInfo', 'videoList', 'videoUrl'):
        if key in node:
            media.extend(_extract_from_media_container(node.get(key), 'video'))
    video_id = _clean_video_id(node.get('videoId') or node.get('video_id') or node.get('vodId'))
    if video_id:
        media.append(MediaItem('', 'video', video_id))
    for key in ('postContent', 'content', 'summary', 'desc', 'postDetail', 'richContent'):
        for url in _extract_urls_from_text(node.get(key)):
            _append_media_url(media, url)
    return _dedupe_media(media)


def _extract_cover_media(node: dict[str, Any]) -> tuple[MediaItem, ...]:
    media: list[MediaItem] = []
    for key in ('coverImages', 'coverImage', 'cover', 'coverUrl', 'postCover', 'topicCover'):
        if key in node:
            media.extend(_extract_from_media_container(node.get(key), 'image'))
    return _dedupe_media(media)


def _post_from_node(node: dict[str, Any], spec: CommandSpec, allow_cover_fallback: bool) -> KuroPost | None:
    if _has_repost_forbidden_text(node):
        return None
    detail = node.get('postDetail') if isinstance(node.get('postDetail'), dict) else {}
    post_id = str(node.get('postId') or node.get('post_id') or node.get('id') or detail.get('postId') or '').strip()
    title = _clean_text(node.get('postTitle') or node.get('title') or node.get('subject') or detail.get('postTitle') or spec.label, 80)
    summary = _clean_text(
        node.get('content') or node.get('summary') or node.get('desc') or node.get('postContent') or detail.get('postH5Content') or '',
        160,
    )
    author_node = node.get('user') or node.get('author') or node.get('postUser') or detail.get('user') or {}
    author = ''
    if isinstance(author_node, dict):
        author = _clean_text(author_node.get('userName') or author_node.get('nickname') or author_node.get('name') or '', 40)
    author = author or _clean_text(node.get('userName') or node.get('nickname') or detail.get('userName') or '库街区用户', 40)
    media = _extract_post_media(node)
    if not media and detail:
        media = _extract_post_media(detail)
    if not media and allow_cover_fallback:
        media = _extract_cover_media(node)
    if not media:
        return None
    game_path = 'pns' if spec.game_id == 2 else 'mc'
    url = f'https://www.kurobbs.com/{game_path}/post/{post_id}' if post_id else 'https://www.kurobbs.com/'
    return KuroPost(post_id, title, summary, author, url, media, spec.label)


def _extract_post_list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    queue: list[Any] = [payload]
    while queue:
        current = queue.pop(0)
        if isinstance(current, list) and all(isinstance(item, dict) for item in current):
            if any('postId' in item or 'postTitle' in item or 'postDetail' in item for item in current):
                return list(current)
        if isinstance(current, dict):
            for key in ('postList', 'list', 'records', 'items', 'rows', 'data'):
                if key in current:
                    queue.append(current[key])
    return []


def _post_with_media_filter(post: KuroPost, video_only: bool) -> KuroPost | None:
    media = tuple(item for item in post.media if _is_video_media(item)) if video_only else post.media
    if not media:
        return None
    if media == post.media:
        return post
    return KuroPost(post.post_id, post.title, post.summary, post.author, post.url, media, post.label)


def _split_prefix_and_body(text: Any) -> tuple[str, str]:
    message = re.sub(r'\s+', ' ', str(text or '')).strip()
    for prefix in ('ww', 'zs'):
        if message == prefix:
            return prefix, ''
        if message.startswith(prefix + ' '):
            return prefix, message[len(prefix):].strip()
        if message.startswith(prefix):
            return prefix, message[len(prefix):].strip()
    return '', message


def _parse_command_text(text: Any) -> ParsedCommand | None:
    prefix, body = _split_prefix_and_body(text)
    if not prefix or not body:
        return None
    for spec in COMMANDS_BY_LENGTH:
        if spec.prefix != prefix:
            continue
        if body == spec.command:
            return ParsedCommand(spec)
        if body.startswith(f'{spec.command} '):
            return ParsedCommand(spec, _clean_text(body[len(spec.command):].strip(), 40))
        if body.startswith(spec.command) and len(body) > len(spec.command):
            keyword = body[len(spec.command):]
            return ParsedCommand(spec, _clean_text(keyword, 40))
    return None


def _unknown_command_text(text: Any) -> str | None:
    prefix, body = _split_prefix_and_body(text)
    if not prefix or not body:
        return None
    command = body.split(' ', 1)[0]
    if prefix == 'zs' and command.startswith('cos'):
        return '战双前缀 zs 目前支持：zs同人、zs同人视频。'
    if prefix == 'ww' and command.startswith(('cos', '同人')):
        return '鸣潮前缀 ww 支持：wwcos、wwcos视频、ww同人、ww同人视频。'
    return None


def _headers(version: str = '2.4.4') -> dict[str, str]:
    return {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': 'https://www.kurobbs.com',
        'Referer': 'https://www.kurobbs.com/',
        'User-Agent': USER_AGENT,
        'devCode': DEV_CODE,
        'distinct_id': DISTINCT_ID,
        'source': 'h5',
        'token': '',
        'version': version,
    }


def _api_url(endpoint: str) -> str:
    return f"{API_BASE}/{endpoint.lstrip('/')}"


def _chunks(values: list[int], size: int) -> Iterable[list[int]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _random_pages() -> list[int]:
    max_page = _cfg_int('random_page_max', 80, 1)
    rounds = _cfg_int('request_rounds', 30, 1, max_page)
    front_count = min(max_page, max(1, min(20, max(1, rounds // 2))))
    pages = list(range(1, front_count + 1))
    remaining = rounds - len(pages)
    if remaining > 0 and front_count < max_page:
        pool = list(range(front_count + 1, max_page + 1))
        pages.extend(random.sample(pool, k=min(remaining, len(pool))))
    random.shuffle(pages)
    return pages


async def _fetch_random_posts(spec: CommandSpec) -> list[KuroPost]:
    timeout = _cfg_float('request_timeout', 12.0, 1.0)
    page_size = _cfg_int('default_page_size', 20, 1, 50)
    search_type = _cfg_int('search_type', 3)
    concurrency = _cfg_int('request_concurrency', 5, 1, 10)
    posts: list[KuroPost] = []
    recent: list[KuroPost] = []
    seen: set[str] = set()
    requested: set[int] = set()

    def collect(payload: Any, page_index: int) -> None:
        nodes = _extract_post_list(payload)
        if not nodes:
            _debug(f'列表接口为空 pageIndex={page_index}')
            return
        accepted = 0
        for node in nodes:
            post = _post_from_node(node, spec, False)
            post = _post_with_media_filter(post, spec.video_only) if post else None
            if not post:
                continue
            key = post.post_id or post.url or post.title
            if key in seen:
                continue
            seen.add(key)
            (recent if key in RECENT_POST_IDS else posts).append(post)
            accepted += 1
        _debug(f'列表接口完成 label={spec.label} forumId={spec.forum_id} pageIndex={page_index} posts={len(nodes)} candidates={accepted}')

    async def fetch_page(client: httpx.AsyncClient, page_index: int) -> None:
        requested.add(page_index)
        body = {
            'gameId': spec.game_id,
            'forumId': spec.forum_id,
            'searchType': search_type,
            'pageIndex': page_index,
            'pageSize': page_size,
        }
        try:
            response = await client.post(_api_url('/forum/list'), data=body)
            response.raise_for_status()
            collect(response.json(), page_index)
        except Exception as exc:
            _debug(f'列表接口失败 pageIndex={page_index} error={exc!r}')

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=_headers()) as client:
        for group in _chunks(_random_pages(), concurrency):
            await asyncio.gather(*(fetch_page(client, page) for page in group))
        if not posts:
            fallback_pages = [page for page in range(1, min(_cfg_int('random_page_max', 80, 1), 30) + 1) if page not in requested]
            for group in _chunks(fallback_pages, concurrency):
                await asyncio.gather(*(fetch_page(client, page) for page in group))
                if posts:
                    break
    return posts or recent


def _make_search_keywords(keyword: str, suffixes: tuple[str, ...]) -> tuple[str, ...]:
    if not suffixes or suffixes == ('',):
        return (keyword,)
    result: list[str] = []
    seen: set[str] = set()
    for suffix in suffixes:
        kw = f"{keyword} {suffix}".strip()
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)
    if keyword not in seen:
        result.append(keyword)
    return tuple(result)


async def _fetch_search_posts(spec: CommandSpec, keyword: str) -> list[KuroPost]:
    suffixes = spec.search_suffixes or ('',)
    keywords = _make_search_keywords(keyword, suffixes)
    if not keywords:
        return []
    timeout = _cfg_float('request_timeout', 12.0, 1.0)
    page_size = _cfg_int('search_page_size', 10, 1, 30)
    rounds = _cfg_int('search_rounds', 3, 1, 10)
    search_type = _cfg_int('search_type', 3)
    strict_posts: list[KuroPost] = []
    relaxed_posts: list[KuroPost] = []
    recent_posts: list[KuroPost] = []
    seen: set[str] = set()

    def collect(payload: Any, request_keyword: str, strict_cos: bool) -> None:
        nodes = _extract_post_list(payload)
        if not nodes:
            _debug(f'搜索接口为空 keyword={request_keyword}')
            return
        accepted = 0
        for node in nodes:
            if spec.strict_cos:
                if strict_cos and not _is_cos_search_result(node, keyword):
                    continue
                if not strict_cos and not _query_matches(node, keyword):
                    continue
            elif not _query_matches(node, keyword):
                continue
            post = _post_from_node(node, spec, not spec.video_only)
            post = _post_with_media_filter(post, spec.video_only) if post else None
            if not post:
                continue
            key = post.post_id or post.url or post.title
            if key in seen:
                continue
            seen.add(key)
            if key in RECENT_POST_IDS:
                recent_posts.append(post)
            elif strict_cos:
                strict_posts.append(post)
            else:
                relaxed_posts.append(post)
            accepted += 1
        _debug(f'搜索接口完成 label={spec.label} keyword={request_keyword} posts={len(nodes)} candidates={accepted}')

    async def fetch_keyword(client: httpx.AsyncClient, request_keyword: str, strict_cos: bool) -> None:
        for page_index in range(1, rounds + 1):
            body = {
                'gameId': spec.game_id,
                'forumId': spec.forum_id,
                'searchType': search_type,
                'pageIndex': page_index,
                'pageSize': page_size,
                'keyword': request_keyword,
            }
            try:
                response = await client.post(_api_url('/forum/searchPost'), data=body)
                response.raise_for_status()
                collect(response.json(), request_keyword, strict_cos)
            except Exception as exc:
                _debug(f'搜索接口失败 keyword={request_keyword} pageIndex={page_index} error={exc!r}')
                break

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=_headers()) as client:
        for request_keyword in keywords:
            strict_cos = spec.strict_cos and request_keyword != keyword
            await fetch_keyword(client, request_keyword, strict_cos)
            if len(strict_posts) >= 8 or len(relaxed_posts) >= 8:
                break
    return strict_posts or relaxed_posts or recent_posts


async def _resolve_video(media: MediaItem) -> MediaItem:
    if media.url or not _is_video_media(media) or not media.video_id:
        return media
    play_url = await _fetch_video_play_url(media.video_id)
    return MediaItem(play_url, 'video', media.video_id) if play_url else media


async def _fetch_video_play_url(video_id: str) -> str | None:
    video_id = _clean_video_id(video_id)
    if not video_id:
        return None
    try:
        timeout = _cfg_float('request_timeout', 12.0, 1.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=_headers('3.0.3')) as client:
            response = await client.post(_api_url('/forum/video/refreshPlayCode'), data={'videoId': video_id})
            response.raise_for_status()
            play_auth = response.json().get('data', {}).get('playAuth')
            play_url = await _fetch_aliyun_play_url(play_auth, video_id, client)
            if play_url:
                _debug(f'视频解析成功 videoId={video_id} suffix={_url_suffix(play_url)}')
            return play_url
    except Exception as exc:
        _debug(f'视频解析失败 videoId={video_id} error={exc!r}')
        return None


async def _fetch_aliyun_play_url(play_auth: Any, video_id: str, client: httpx.AsyncClient) -> str | None:
    payload = _decode_play_auth(play_auth)
    access_key_id = str(payload.get('AccessKeyId') or '')
    access_key_secret = str(payload.get('AccessKeySecret') or '')
    security_token = str(payload.get('SecurityToken') or '')
    auth_info = payload.get('AuthInfo')
    region = str(payload.get('Region') or 'cn-shanghai')
    if not access_key_id or not access_key_secret or not security_token or not auth_info:
        return None
    params: dict[str, Any] = {
        'AccessKeyId': access_key_id,
        'Action': 'GetPlayInfo',
        'AuthInfo': auth_info,
        'AuthTimeout': '7200',
        'Channel': 'HTML5',
        'Definition': 'FD,LD,SD,HD',
        'Format': 'JSON',
        'Formats': '',
        'PlayConfig': '{}',
        'PlayerVersion': '2.29.2',
        'Rand': str(uuid4()),
        'ReAuthInfo': '{}',
        'SecurityToken': security_token,
        'SignatureMethod': 'HMAC-SHA1',
        'SignatureNonce': str(uuid4()),
        'SignatureVersion': '1.0',
        'StreamType': 'video',
        'Version': '2017-03-21',
        'VideoId': video_id,
    }
    params['Signature'] = _aliyun_signature(params, access_key_secret)
    response = await client.get(f'https://vod.{region}.aliyuncs.com/', params=params)
    response.raise_for_status()
    return _select_play_url(response.json().get('PlayInfoList', {}))


def _decode_play_auth(play_auth: Any) -> dict[str, Any]:
    if not isinstance(play_auth, str) or not play_auth.strip():
        return {}
    try:
        raw = play_auth.strip()
        raw += '=' * (-len(raw) % 4)
        payload = json.loads(base64.b64decode(raw).decode('utf-8'))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _aliyun_percent_encode(value: Any) -> str:
    return quote(str(value), safe='-_.~')


def _aliyun_signature(params: dict[str, Any], access_key_secret: str) -> str:
    canonical_query = '&'.join(f'{_aliyun_percent_encode(key)}={_aliyun_percent_encode(params[key])}' for key in sorted(params))
    string_to_sign = f'GET&%2F&{_aliyun_percent_encode(canonical_query)}'
    digest = hmac.new(f'{access_key_secret}&'.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha1).digest()
    return base64.b64encode(digest).decode('ascii')


def _select_play_url(play_info_list: Any) -> str | None:
    play_infos = play_info_list.get('PlayInfo') if isinstance(play_info_list, dict) else play_info_list
    if not isinstance(play_infos, list):
        return None
    candidates = [item for item in play_infos if isinstance(item, dict) and item.get('PlayURL')]
    if not candidates:
        return None
    preferred = _cfg_str('video_definition', 'HD').upper() or 'HD'
    for definition in list(dict.fromkeys([preferred, 'HD', 'SD', 'LD', 'FD'])):
        matches = [item for item in candidates if str(item.get('Definition') or '').upper() == definition]
        for suffix in ('.mp4', '.m3u8'):
            for item in matches:
                play_url = str(item.get('PlayURL') or '')
                if _url_suffix(play_url) == suffix:
                    return play_url
        if matches:
            return str(matches[0].get('PlayURL'))
    return str(candidates[0].get('PlayURL'))


def _select_post(posts: list[KuroPost], video_only: bool) -> KuroPost | None:
    fresh: list[KuroPost] = []
    recent: list[KuroPost] = []
    for post in posts:
        filtered = _post_with_media_filter(post, video_only)
        if not filtered:
            continue
        key = filtered.post_id or filtered.url or filtered.title
        (recent if key in RECENT_POST_IDS else fresh).append(filtered)
    candidates = fresh or recent
    random.shuffle(candidates)
    if not candidates:
        return None
    post = candidates[0]
    media = list(post.media)
    random.shuffle(media)
    _debug(f'候选帖子 label={post.label} post_id={post.post_id} video_only={video_only} media={len(media)}')
    return KuroPost(post.post_id, post.title, post.summary, post.author, post.url, tuple(media), post.label)


def _remember_post(post: KuroPost) -> None:
    key = post.post_id or post.url or post.title
    if key:
        RECENT_POST_IDS.append(key)


def _post_text(post: KuroPost) -> str:
    parts = [post.label, post.title, f'作者：{post.author}', post.url]
    if post.summary:
        parts.append(post.summary)
    return '\n'.join(part for part in parts if part)


def _safe_media_target(media: MediaItem, post_id: str, index: int) -> Path:
    suffix = _url_suffix(media.url)
    if media.kind == 'video' and suffix == '.m3u8':
        suffix = '.mp4'
    if suffix not in MEDIA_EXTENSIONS:
        suffix = '.jpg' if media.kind == 'image' else '.mp4'
    safe_post_id = re.sub(r'[^a-zA-Z0-9_.-]+', '_', post_id or 'post')[:80] or 'post'
    target_dir = MEDIA_DIR / time.strftime('%Y%m%d_%H%M%S')
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f'{safe_post_id}_{index}_{random.randint(1000, 9999)}{suffix}'


async def _download_media(media: MediaItem, post_id: str, index: int) -> str | None:
    if not media.url:
        return None
    target = _safe_media_target(media, post_id, index)
    timeout = _cfg_float('download_timeout', 120.0, 5.0)
    if media.kind == 'video' and _url_suffix(media.url) == '.m3u8':
        return await _download_hls(media, target, max(timeout, 120.0))
    return await _download_file(media, target, timeout)


async def _download_file(media: MediaItem, target: Path, timeout: float) -> str | None:
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={'User-Agent': USER_AGENT, 'Referer': 'https://www.kurobbs.com/'},
        ) as client:
            response = await client.get(media.url)
            response.raise_for_status()
            target.write_bytes(response.content)
        return str(target.resolve())
    except Exception as exc:
        logger.warning(f'[gs_kuro_cos] 下载媒体失败：{media.url} {exc!r}')
        target.unlink(missing_ok=True)
        return None


async def _download_hls(media: MediaItem, target: Path, timeout: float) -> str | None:
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        _debug('未找到 ffmpeg，无法把 HLS 视频转为 MP4')
        return None
    headers = f'User-Agent: {USER_AGENT}\r\nReferer: https://www.kurobbs.com/\r\n'
    command = [ffmpeg, '-y', '-loglevel', 'error', '-headers', headers, '-i', media.url, '-c', 'copy', '-movflags', '+faststart', str(target)]
    process: asyncio.subprocess.Process | None = None
    try:
        target.unlink(missing_ok=True)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        if process.returncode == 0 and target.is_file() and target.stat().st_size > 0:
            _debug(f'HLS 视频已转码为 MP4：{target}')
            return str(target.resolve())
        _debug(f"ffmpeg 转码失败 code={process.returncode} error={stderr.decode('utf-8', errors='replace')[-500:]}")
    except asyncio.TimeoutError:
        _debug(f'ffmpeg 转码超时 url={media.url}')
        if process is not None:
            process.kill()
    except Exception as exc:
        _debug(f'ffmpeg 转码异常 error={exc!r}')
    target.unlink(missing_ok=True)
    return None


def _video_size_limit_bytes() -> int:
    return int(_cfg_float('video_max_mb', 80.0, 1.0, 512.0) * 1024 * 1024)


def _segment_from_local(path: str, kind: str) -> Message | str:
    file_path = Path(path)
    if kind == 'image':
        return MessageSegment.image(file_path)
    try:
        size = file_path.stat().st_size
    except OSError:
        return f'视频文件读取失败：{file_path.name}'
    if size > _video_size_limit_bytes():
        return f'视频文件过大，已跳过发送：{file_path.name}'
    if _cfg_str('video_send_mode', 'video').lower() == 'file':
        return MessageSegment.file(file_path, file_path.name)
    return MessageSegment.video(file_path)


def _segment_from_url(url: str, kind: str) -> Message | str:
    if kind == 'image':
        return MessageSegment.image(url)
    return f'视频下载失败，请打开原帖查看：\n{url}'


async def _component_for(media: MediaItem, post_id: str, index: int) -> tuple[Message | str, str | None]:
    resolved = await _resolve_video(media)
    if resolved.kind == 'image':
        if _cfg_bool('download_images', True):
            local_path = await _download_media(resolved, post_id, index)
            if local_path:
                return _segment_from_local(local_path, resolved.kind), local_path
        if resolved.url:
            return _segment_from_url(resolved.url, resolved.kind), None
        return '图片解析失败，请打开原帖查看。', None
    if _cfg_bool('download_videos', True):
        local_path = await _download_media(resolved, post_id, index)
        if local_path:
            return _segment_from_local(local_path, resolved.kind), local_path
    if resolved.url:
        return _segment_from_url(resolved.url, resolved.kind), None
    return '视频解析失败，请打开原帖查看。', None


def _cleanup_local_files(paths: list[str]) -> None:
    cleaned_dirs: set[Path] = set()
    for path_text in paths:
        path = Path(path_text)
        try:
            if path.is_file():
                cleaned_dirs.add(path.parent)
                path.unlink()
        except Exception as exc:
            logger.warning(f'[gs_kuro_cos] 删除本地媒体失败：{path} {exc!r}')
    for directory in cleaned_dirs:
        try:
            directory.rmdir()
        except OSError:
            pass


async def _build_messages(post: KuroPost) -> tuple[list[Any], list[str]]:
    max_media = _cfg_int('max_media_per_post', 6, 1, 20)
    selected_media = post.media[:max_media]
    has_video = any(_is_video_media(item) for item in selected_media)
    text = _post_text(post)
    components: list[Message | str] = []
    local_paths: list[str] = []
    for index, media in enumerate(selected_media, 1):
        component, local_path = await _component_for(media, post.post_id or 'post', index)
        components.append(component)
        if local_path:
            local_paths.append(local_path)
    if _cfg_bool('use_forward', True) and not has_video and components:
        return [MessageSegment.node([text, *components])], local_paths
    return [[text, *components]], local_paths


async def _load_posts(parsed: ParsedCommand) -> list[KuroPost]:
    if parsed.keyword:
        return await _fetch_search_posts(parsed.spec, parsed.keyword)
    return await _fetch_random_posts(parsed.spec)


def _empty_text(parsed: ParsedCommand) -> str:
    if parsed.spec.video_only and parsed.keyword:
        return f'没找到包含「{parsed.keyword}」的 {parsed.spec.label} 视频。'
    if parsed.spec.video_only:
        return f'没找到包含 {parsed.spec.label} 视频的库街区内容。'
    if parsed.keyword:
        return f'没找到包含「{parsed.keyword}」的 {parsed.spec.label} 图片/视频。'
    return f'没找到包含 {parsed.spec.label} 图片/视频的库街区内容。'


@sv.on_regex(rf'^{COMMAND_PATTERN}$', block=True, prefix=True)
async def send_kuro_cos(bot: Bot, ev: Event) -> None:
    parsed = _parse_command_text(getattr(ev, 'raw_text', '') or getattr(ev, 'text', ''))
    if parsed is None:
        hint = _unknown_command_text(getattr(ev, 'raw_text', '') or getattr(ev, 'text', ''))
        if hint:
            await bot.send(hint)
        return
    async with FETCH_LOCK:
        posts = await _load_posts(parsed)
        post = _select_post(posts, parsed.spec.video_only)
        if post is None:
            await bot.send(_empty_text(parsed))
            return
        _remember_post(post)
        messages, local_paths = await _build_messages(post)
        try:
            for index, message in enumerate(messages):
                await bot.send(message)
                if index < len(messages) - 1:
                    await asyncio.sleep(0.5)
        finally:
            if _cfg_bool('delete_cache_after_send', True):
                _cleanup_local_files(local_paths)
