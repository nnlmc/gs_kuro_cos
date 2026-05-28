from __future__ import annotations

import asyncio
import html
import random
import re
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from gsuid_core.sv import Plugins, SV

from .kuro_cos_config import KuroCosConfig


Plugins(
    name='gs_kuro_cos',
    allow_empty_prefix=True,
)

sv = SV('鸣潮库街区COS')
BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / 'media_cache'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm', '.avi', '.flv', '.mkv', '.m3u8'}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
KURO_MEDIA_HOST_KEYWORDS = ('kurobbs.com', 'kurogame.com', 'aki-game.com')
DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0'
)
DEFAULT_DEV_CODE = 'H0O9l04JUG341k5UpUTMNpnGawC5Qt9p'
DEFAULT_DISTINCT_ID = '195be91535f592-0915a368d4173f-4c657b58-1327104-195be9153601740'
URL_RE = re.compile(r"https?://[^\s'\"<>，。！？、）)\]}]+", re.IGNORECASE)
POST_TEXT_KEYS = (
    'postTitle',
    'title',
    'subject',
    'content',
    'summary',
    'desc',
    'description',
    'postContent',
    'postDetail',
    'textContent',
    'richContent',
    'articleContent',
    'markdownContent',
    'topicContent',
)
COS_KEYWORDS = (
    'cos',
    'coser',
    'cosplay',
    '正片',
    '返图',
    '试衣',
    '同人cos',
    '同人 cosplay',
    '妆造',
    '场照',
    '出镜',
    '摄影',
    '棚拍',
    '外景',
)
NON_COS_SEARCH_KEYWORDS = (
    '攻略',
    '养成',
    '培养',
    '配队',
    '阵容',
    '抽卡',
    '抽取建议',
    '卡池',
    '强度',
    '测评',
    '评测',
    '教程',
    '机制',
    '手法',
    '打法',
    '深塔',
    '逆境深塔',
    '刷分',
    '声骸',
    '词条',
    '武器',
    '共鸣链',
    '技能',
    '加点',
    '面板',
    '毕业',
    '材料',
    '突破',
    '任务',
    '活动',
    '解谜',
    '剧情',
    '卡牌',
    '桌游',
    '押注',
    '投票',
    '兑换码',
    '签到',
)
SEARCH_KEYWORD_SUFFIXES = (
    'cos',
    'COS',
    'cosplay',
    '正片',
    'cos正片',
    'COS正片',
    '同人cos',
    '试衣',
    '返图',
)
REPOST_FORBIDDEN_KEYWORDS = (
    '禁止搬运',
    '禁止转载',
    '禁止转发',
    '禁止转帖',
    '禁止二传',
    '禁止二次上传',
    '禁止二改',
    '禁止盗图',
    '严禁搬运',
    '严禁转载',
    '严禁转发',
    '严禁二传',
    '请勿搬运',
    '请勿转载',
    '请勿转发',
    '请勿二传',
    '请勿二改',
    '勿搬运',
    '勿转载',
    '勿转发',
    '勿二传',
    '不要搬运',
    '不要转载',
    '不要转发',
    '不要二传',
    '请不要搬运',
    '请不要转载',
    '请不要转发',
    '不得搬运',
    '不得转载',
    '不得转发',
    '不得二传',
    '不许搬运',
    '不许转载',
    '不许转发',
    '不许二传',
    '不准搬运',
    '不准转载',
    '不准转发',
    '不准二传',
    '不能搬运',
    '不能转载',
    '不能转发',
    '不能二传',
    '不可搬运',
    '不可转载',
    '不可转发',
    '不可二传',
    '不允许搬运',
    '不允许转载',
    '不允许转发',
    '不允许二传',
    '谢绝搬运',
    '谢绝转载',
    '谢绝转发',
    '拒绝搬运',
    '拒绝转载',
    '拒绝转发',
    '婉拒搬运',
    '婉拒转载',
    '未经授权转载',
    '未经授权搬运',
    '未经授权转发',
    '未经授权不得转载',
    '未经授权请勿转载',
    '未经允许转载',
    '未经允许搬运',
    '未经允许转发',
    '未经许可转载',
    '未经许可搬运',
    '未经许可转发',
    '未授权转载',
    '未授权搬运',
    '无授权转载',
    '无授权搬运',
    '擅自转载',
    '擅自搬运',
    '私自转载',
    '私自搬运',
    '不授权转载',
    '不授权搬运',
    '不开放转载',
    '不开放搬运',
    '禁搬运',
    '禁转载',
    '禁转',
    '禁二传',
    '禁二改',
    '禁止任何形式转载',
    '禁止任何形式搬运',
    '禁止任何形式转发',
    'do not repost',
    "don't repost",
    'dont repost',
    'please do not repost',
    "please don't repost",
    'no repost',
    'no re-post',
    'repost prohibited',
    'reposting prohibited',
    'repost forbidden',
    'unauthorized repost',
    'unauthorised repost',
    'do not reupload',
    'do not re-upload',
    'no reupload',
    'no re-upload',
    'reupload prohibited',
    're-upload prohibited',
    '転載禁止',
    '無断転載禁止',
    '無断使用禁止',
    '無断転載お断り',
    '無断転載は禁止',
    '二次配布禁止',
    '무단전재금지',
    '무단배포금지',
)
_RECENT_POST_IDS: deque[str] = deque(maxlen=80)
_FETCH_LOCK = asyncio.Semaphore(1)


@dataclass(frozen=True)
class MediaItem:
    url: str
    kind: str


@dataclass(frozen=True)
class KuroPost:
    post_id: str
    title: str
    summary: str
    author: str
    url: str
    media: tuple[MediaItem, ...]


def _cfg(key: str, default: Any = None) -> Any:
    try:
        value = KuroCosConfig.get_config(key).data
    except Exception:
        return default
    return default if value is None else value


def _debug(message: str):
    if bool(_cfg('debug_log', False)):
        logger.info(f'[gs_kuro_cos] {message}')


def _clean_text(value: Any, limit: int = 120) -> str:
    text = re.sub(r'<[^>]+>', '', str(value or ''))
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]


def _strip_markup(value: Any) -> str:
    text = re.sub(r'<[^>]+>', '', str(value or ''))
    return html.unescape(text)


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


def _normalize_for_keyword_match(text: str) -> str:
    text = _strip_markup(text).lower()
    return re.sub(r'[\s\W_]+', '', text, flags=re.UNICODE)


def _searchable_post_text(node: dict[str, Any]) -> str:
    return _strip_markup(_collect_post_text(node))


def _make_search_keywords(query: str) -> list[str]:
    query = _clean_text(query, 40)
    if not query:
        return []
    keywords: list[str] = []
    for suffix in SEARCH_KEYWORD_SUFFIXES:
        keywords.append(f'{query} {suffix}')
        if re.fullmatch(r'[A-Za-z0-9_+-]+', suffix):
            continue
        keywords.append(f'{query}{suffix}')
    keywords.append(query)

    seen: set[str] = set()
    result: list[str] = []
    for keyword in keywords:
        keyword = re.sub(r'\s+', ' ', keyword).strip()
        if keyword and keyword.lower() not in seen:
            seen.add(keyword.lower())
            result.append(keyword)
    return result


def _is_search_result_relevant(node: dict[str, Any], query: str, *, strict_cos: bool = True) -> bool:
    text = _searchable_post_text(node)
    if not text:
        return False
    normalized_text = _normalize_for_keyword_match(text)
    normalized_query = _normalize_for_keyword_match(query)
    if normalized_query and normalized_query not in normalized_text:
        return False

    normalized_cos_keywords = [_normalize_for_keyword_match(keyword) for keyword in COS_KEYWORDS]
    normalized_negative_keywords = [_normalize_for_keyword_match(keyword) for keyword in NON_COS_SEARCH_KEYWORDS]
    title_text = _strip_markup(node.get('postTitle') or node.get('title') or node.get('subject') or '')
    normalized_title = _normalize_for_keyword_match(title_text)
    title_has_cos_keyword = any(keyword in normalized_title for keyword in normalized_cos_keywords)
    title_has_negative_keyword = any(keyword in normalized_title for keyword in normalized_negative_keywords)
    if title_has_negative_keyword:
        return False

    text_has_cos_keyword = any(keyword in normalized_text for keyword in normalized_cos_keywords)
    if not text_has_cos_keyword:
        return False

    text_has_negative_keyword = any(keyword in normalized_text for keyword in normalized_negative_keywords)
    if text_has_negative_keyword and not title_has_cos_keyword:
        return False

    # 标题没有 COS 标识时，必须至少有正文媒体，避免把攻略/活动帖封面当成 COS 兜底发送。
    if not title_has_cos_keyword and not _extract_post_media(node):
        return False
    return True


def _has_repost_forbidden_text(node: dict[str, Any]) -> bool:
    text = _collect_post_text(node)
    if not text:
        return False
    compact_text = _normalize_for_keyword_match(text)
    for keyword in REPOST_FORBIDDEN_KEYWORDS:
        if keyword.lower() in text.lower() or _normalize_for_keyword_match(keyword) in compact_text:
            return True
    return False


def _normalize_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    url = value.strip().replace('\\/', '/').rstrip('.,;:!?，。；：！？、')
    if not url.startswith(('http://', 'https://')):
        return None
    parsed = urlparse(url)
    if not parsed.netloc:
        return None
    return url


def _url_suffix(url: str) -> str:
    return Path(urlparse(url).path.lower()).suffix


def _looks_like_kuro_media(url: str) -> bool:
    host = (urlparse(url).hostname or '').lower()
    return any(host == key or host.endswith(f'.{key}') for key in KURO_MEDIA_HOST_KEYWORDS)


def _dedupe_media(items: list[MediaItem]) -> tuple[MediaItem, ...]:
    seen: set[str] = set()
    result: list[MediaItem] = []
    for item in items:
        key = item.url.split('?', 1)[0]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


def _append_media_url(media: list[MediaItem], raw_url: Any, forced_kind: str | None = None):
    url = _normalize_url(raw_url)
    if not url or not _looks_like_kuro_media(url):
        return
    suffix = _url_suffix(url)
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
        media.append(MediaItem(url=url, kind=kind))


def _extract_urls_from_text(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [match.rstrip('.,;:!?，。；：！？、') for match in URL_RE.findall(value)]


def _extract_from_media_container(value: Any, forced_kind: str | None = None) -> list[MediaItem]:
    media: list[MediaItem] = []

    def visit(item: Any):
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
            for key in ('url', 'imgUrl', 'imageUrl', 'picUrl', 'videoUrl', 'coverUrl', 'resourceUrl', 'src', 'path'):
                if key in item:
                    _append_media_url(media, item.get(key), forced_kind)
            for key in ('urls', 'images', 'imgs', 'videos', 'resources', 'content'):
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

    for key in ('postContent', 'content', 'summary', 'desc', 'postDetail'):
        for url in _extract_urls_from_text(node.get(key)):
            _append_media_url(media, url)

    return _dedupe_media(media)


def _extract_cover_media(node: dict[str, Any]) -> tuple[MediaItem, ...]:
    media: list[MediaItem] = []
    for key in ('coverImages', 'coverImage', 'cover', 'coverUrl', 'postCover', 'topicCover'):
        if key in node:
            media.extend(_extract_from_media_container(node.get(key), 'image'))
    return _dedupe_media(media)


def _post_from_node(node: dict[str, Any], *, allow_cover_fallback: bool = False) -> KuroPost | None:
    if _has_repost_forbidden_text(node):
        return None

    post_id = str(node.get('postId') or node.get('post_id') or node.get('id') or '').strip()
    title = _clean_text(node.get('postTitle') or node.get('title') or node.get('subject') or '鸣潮 COS', 80)
    summary = _clean_text(node.get('content') or node.get('summary') or node.get('desc') or node.get('postContent') or '', 160)
    author_node = node.get('user') or node.get('author') or node.get('postUser') or {}
    author = ''
    if isinstance(author_node, dict):
        author = _clean_text(author_node.get('userName') or author_node.get('nickname') or author_node.get('name') or '', 40)
    author = author or _clean_text(node.get('userName') or node.get('nickname') or '库街区用户', 40)
    media = _extract_post_media(node)
    if not media and allow_cover_fallback:
        media = _extract_cover_media(node)
    if not media:
        return None
    url = f'https://www.kurobbs.com/mc/post/{post_id}' if post_id else 'https://www.kurobbs.com/'
    return KuroPost(post_id=post_id, title=title, summary=summary, author=author, url=url, media=media)


def _extract_post_list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get('data')
    if isinstance(data, dict) and isinstance(data.get('postList'), list):
        return [item for item in data['postList'] if isinstance(item, dict)]
    if isinstance(payload.get('postList'), list):
        return [item for item in payload['postList'] if isinstance(item, dict)]
    return []


def _build_headers() -> dict[str, str]:
    dev_code = str(_cfg('dev_code', DEFAULT_DEV_CODE) or DEFAULT_DEV_CODE)
    distinct_id = str(_cfg('distinct_id', DEFAULT_DISTINCT_ID) or DEFAULT_DISTINCT_ID)
    return {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': 'https://www.kurobbs.com',
        'Referer': 'https://www.kurobbs.com/',
        'User-Agent': DEFAULT_USER_AGENT,
        'devCode': dev_code,
        'distinct_id': distinct_id,
        'source': 'h5',
        'token': '',
        'version': '2.4.4',
    }


def _api_url(endpoint_key: str, default_endpoint: str) -> str:
    base = str(_cfg('api_base', 'https://api.kurobbs.com')).rstrip('/')
    endpoint = str(_cfg(endpoint_key, default_endpoint))
    return endpoint if endpoint.startswith('http') else f"{base}/{endpoint.lstrip('/')}"


async def _fetch_random_posts() -> list[KuroPost]:
    timeout = float(_cfg('request_timeout', 12.0))
    url = _api_url('list_endpoint', '/forum/list')
    page_size = max(1, int(_cfg('default_page_size', 20)))
    game_id = int(_cfg('game_id', 3))
    forum_id = int(_cfg('forum_id', 17))
    search_type = int(_cfg('search_type', 3))
    random_page_max = max(1, int(_cfg('random_page_max', 80)))
    request_rounds = max(1, int(_cfg('request_rounds', 30)))

    target_request_count = min(request_rounds, random_page_max)
    front_page_count = min(random_page_max, max(1, min(20, max(1, request_rounds // 2))))
    page_indexes = list(range(1, front_page_count + 1))
    random_pick_count = target_request_count - len(page_indexes)
    if random_pick_count > 0 and front_page_count < random_page_max:
        page_indexes.extend(
            random.sample(
                range(front_page_count + 1, random_page_max + 1),
                k=min(random_pick_count, random_page_max - front_page_count),
            )
        )
    random.shuffle(page_indexes)

    posts: list[KuroPost] = []
    recent_posts: list[KuroPost] = []
    seen: set[str] = set()
    requested_pages: set[int] = set()

    def collect_posts(payload: Any, page_index: int):
        nodes = _extract_post_list(payload)
        if not nodes:
            _debug(f'列表接口为空 pageIndex={page_index}')
            return
        accepted_count = 0
        for node in nodes:
            post = _post_from_node(node)
            if not post:
                continue
            key = post.post_id or post.url or post.title
            if key in seen:
                continue
            seen.add(key)
            if key in _RECENT_POST_IDS:
                recent_posts.append(post)
            else:
                posts.append(post)
            accepted_count += 1
        _debug(f'列表接口完成 pageIndex={page_index} posts={len(nodes)} candidates={accepted_count}')

    async def fetch_page(client: httpx.AsyncClient, page_index: int):
        requested_pages.add(page_index)
        body = {
            'gameId': game_id,
            'forumId': forum_id,
            'searchType': search_type,
            'pageIndex': page_index,
            'pageSize': page_size,
        }
        try:
            response = await client.post(url, data=body)
            response.raise_for_status()
            collect_posts(response.json(), page_index)
        except Exception as exc:
            _debug(f'列表接口失败 url={url} pageIndex={page_index} error={exc!r}')

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=_build_headers()) as client:
        for page_index in page_indexes:
            await fetch_page(client, page_index)

        if not posts:
            fallback_limit = min(random_page_max, max(front_page_count, 30))
            fallback_pages = [page for page in range(1, fallback_limit + 1) if page not in requested_pages]
            if fallback_pages:
                _debug(f'未获取到新候选，回退检查前 {fallback_limit} 页')
            for page_index in fallback_pages:
                await fetch_page(client, page_index)
                if posts:
                    break

    candidates = posts
    if not candidates and recent_posts:
        candidates = recent_posts
        _debug('没有新的正文媒体帖子，使用最近候选避免空结果')

    random.shuffle(candidates)
    for post in candidates:
        shuffled_media = list(post.media)
        random.shuffle(shuffled_media)
        selected = KuroPost(
            post_id=post.post_id,
            title=post.title,
            summary=post.summary,
            author=post.author,
            url=post.url,
            media=tuple(shuffled_media),
        )
        _debug(f'候选帖子 post_id={selected.post_id} media={len(selected.media)}')
        return [selected]

    _debug('本轮没有可用正文媒体帖子')
    return []


async def _fetch_search_posts(keyword: str) -> list[KuroPost]:
    timeout = float(_cfg('request_timeout', 12.0))
    url = _api_url('search_endpoint', '/forum/searchPost')
    page_size = max(1, int(_cfg('search_page_size', 10)))
    search_rounds = max(1, int(_cfg('search_rounds', 3)))
    game_id = int(_cfg('game_id', 3))
    forum_id = int(_cfg('forum_id', 17))
    search_type = int(_cfg('search_type', 3))
    search_keywords = _make_search_keywords(keyword)
    if not search_keywords:
        return []

    posts: list[KuroPost] = []
    relaxed_posts: list[KuroPost] = []
    recent_posts: list[KuroPost] = []
    seen: set[str] = set()

    def collect_posts(payload: Any, request_keyword: str, strict_cos: bool):
        nodes = _extract_post_list(payload)
        if not nodes:
            _debug(f'搜索接口为空 keyword={request_keyword}')
            return
        accepted_count = 0
        for node in nodes:
            if not _is_search_result_relevant(node, keyword, strict_cos=strict_cos):
                continue
            post = _post_from_node(node, allow_cover_fallback=True)
            if not post:
                continue
            key = post.post_id or post.url or post.title
            if key in seen:
                continue
            seen.add(key)
            if key in _RECENT_POST_IDS:
                recent_posts.append(post)
            elif strict_cos:
                posts.append(post)
            else:
                relaxed_posts.append(post)
            accepted_count += 1
        mode = '严格' if strict_cos else '宽松'
        _debug(f'搜索接口完成 keyword={request_keyword} mode={mode} posts={len(nodes)} candidates={accepted_count}')

    async def fetch_keyword(client: httpx.AsyncClient, request_keyword: str, strict_cos: bool):
        for page_index in range(1, search_rounds + 1):
            body = {
                'gameId': game_id,
                'forumId': forum_id,
                'searchType': search_type,
                'pageIndex': page_index,
                'pageSize': page_size,
                'keyword': request_keyword,
            }
            try:
                response = await client.post(url, data=body)
                response.raise_for_status()
                collect_posts(response.json(), request_keyword, strict_cos)
            except Exception as exc:
                _debug(f'搜索接口失败 url={url} keyword={request_keyword} pageIndex={page_index} error={exc!r}')
                break

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=_build_headers()) as client:
        for request_keyword in search_keywords:
            strict_cos = request_keyword != keyword
            await fetch_keyword(client, request_keyword, strict_cos)
            if len(posts) >= 8:
                break

    candidates = posts or relaxed_posts or recent_posts
    if not posts and not relaxed_posts and recent_posts:
        _debug('搜索结果均为最近发送过的帖子，使用最近候选避免空结果')
    random.shuffle(candidates)
    for post in candidates:
        shuffled_media = list(post.media)
        random.shuffle(shuffled_media)
        selected = KuroPost(
            post_id=post.post_id,
            title=post.title,
            summary=post.summary,
            author=post.author,
            url=post.url,
            media=tuple(shuffled_media),
        )
        _debug(f'搜索候选帖子 keyword={keyword} post_id={selected.post_id} media={len(selected.media)}')
        return [selected]

    _debug(f'未找到搜索候选 keyword={keyword}')
    return []


async def _download_media(media: MediaItem, post_id: str, index: int) -> str | None:
    timeout = float(_cfg('download_timeout', 20.0))
    suffix = _url_suffix(media.url)
    if suffix not in MEDIA_EXTENSIONS:
        suffix = '.jpg' if media.kind == 'image' else '.mp4'
    safe_post_id = re.sub(r'[^a-zA-Z0-9_.-]+', '_', post_id)[:80] or 'post'
    target_dir = MEDIA_DIR / time.strftime('%Y%m%d_%H%M%S')
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f'{safe_post_id}_{index}_{random.randint(1000, 9999)}{suffix}'

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={'User-Agent': DEFAULT_USER_AGENT}) as client:
            response = await client.get(media.url)
            response.raise_for_status()
            target.write_bytes(response.content)
        return str(target)
    except Exception as exc:
        logger.warning(f'[gs_kuro_cos] 下载媒体失败：{media.url} {exc!r}')
        return None


def _segment_from_local(path: str, kind: str) -> Any:
    if kind == 'image':
        return MessageSegment.image(path)
    return MessageSegment.video(path)


def _segment_from_url(url: str, kind: str) -> Any:
    if kind == 'image':
        return MessageSegment.image(url)
    return f'\n视频：{url}'


def _cleanup_local_files(paths: list[str]):
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


def _remember_post(post: KuroPost):
    key = post.post_id or post.url or post.title
    if key:
        _RECENT_POST_IDS.append(key)


async def _build_message(post: KuroPost) -> tuple[list[Any], list[str]]:
    max_media = int(_cfg('max_media_per_post', 6))
    download_media = bool(_cfg('download_media', True))
    use_forward = bool(_cfg('use_forward', True))
    text = f'鸣潮 COS\n{post.title}\n作者：{post.author}\n{post.url}'
    if post.summary:
        text += f'\n{post.summary}'

    message: list[Any] = [text]
    forward_items: list[Any] = [text]
    local_paths: list[str] = []
    for index, media in enumerate(post.media[:max_media], start=1):
        item: Any | None = None
        if download_media:
            local_path = await _download_media(media, post.post_id or 'post', index)
            if local_path:
                local_paths.append(local_path)
                item = _segment_from_local(local_path, media.kind)

        if item is None:
            item = _segment_from_url(media.url, media.kind)
        message.append(item)
        forward_items.append(item)

    if use_forward and len(forward_items) > 1:
        return [MessageSegment.node(forward_items)], local_paths
    return message, local_paths


def _extract_search_keyword(raw_text: Any) -> str | None:
    message = re.sub(r'\s+', ' ', str(raw_text or '')).strip()
    if not message:
        return None
    for command_name in ('鸣潮cos', 'wwcos'):
        if message == command_name:
            return ''
        if message.startswith(f'{command_name} '):
            return _clean_text(message[len(command_name):].strip(), 40)
    return None


@sv.on_regex(r'^(?:鸣潮cos|wwcos)(?:\s+.+)?$', block=True, prefix=False)
async def send_kuro_cos(bot: Bot, ev: Event):
    keyword = _extract_search_keyword(getattr(ev, 'raw_text', ''))
    if keyword is None:
        return

    async with _FETCH_LOCK:
        posts = await _fetch_search_posts(keyword) if keyword else await _fetch_random_posts()
        if not posts:
            if keyword:
                return await bot.send(f'没找到包含「{keyword}」的 COS 正文图片/视频。')
            return await bot.send('没找到包含 COS 图片/视频的库街区内容。')

        post = posts[0]
        _remember_post(post)
        message, local_paths = await _build_message(post)
        try:
            await bot.send(message)
        finally:
            if bool(_cfg('delete_after_send', True)):
                _cleanup_local_files(local_paths)
