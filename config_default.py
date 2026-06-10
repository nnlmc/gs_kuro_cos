from __future__ import annotations

from typing import Dict

from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsBoolConfig,
    GsFloatConfig,
    GsIntConfig,
)

CONFIG_DEFAULT: Dict[str, GSC] = {
    'use_forward': GsBoolConfig(
        '图片合并转发',
        '图片帖使用合并转发。',
        True,
    ),
    'default_page_size': GsIntConfig(
        '列表每页数量',
        '随机模式每页取多少条帖子。',
        20,
        max_value=50,
    ),
    'request_rounds': GsIntConfig(
        '随机请求页数',
        '随机模式一次请求多少页。',
        30,
        max_value=120,
    ),
    'random_page_max': GsIntConfig(
        '随机页码上限',
        '随机模式抽取的最大页码。',
        80,
        max_value=2000,
    ),
    'request_concurrency': GsIntConfig(
        '请求并发数',
        '列表接口同时请求的页数。',
        5,
        max_value=10,
    ),
    'search_page_size': GsIntConfig(
        '搜索每页数量',
        '关键词搜索每页取多少条结果。',
        10,
        max_value=30,
    ),
    'search_rounds': GsIntConfig(
        '搜索请求页数',
        '每个关键词最多搜索多少页。',
        3,
        max_value=10,
    ),
    'max_media_per_post': GsIntConfig(
        '单帖图片上限',
        '单条帖子最多发送多少张图片。',
        6,
        max_value=20,
    ),
    'download_images': GsBoolConfig(
        '下载图片发送',
        '开启后图片转为本地/base64发送。',
        True,
    ),
    'delete_cache_after_send': GsBoolConfig(
        '发送后清理缓存',
        '发送完成后删除 media_cache 临时文件。',
        True,
    ),
    'request_timeout': GsFloatConfig(
        '接口超时秒数',
        '请求库街区接口的超时时间。',
        12.0,
        min_value=3.0,
        max_value=60.0,
    ),
    'download_timeout': GsFloatConfig(
        '下载超时秒数',
        '下载单张图片的超时时间。',
        120.0,
        min_value=5.0,
        max_value=300.0,
    ),
    'search_type': GsIntConfig(
        '列表排序类型',
        '库街区列表接口 searchType。',
        3,
    ),
    'debug_log': GsBoolConfig(
        '调试日志',
        '输出接口页码、候选帖子和过滤日志。',
        False,
    ),
}
