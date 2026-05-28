from __future__ import annotations

from typing import Dict

from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsBoolConfig,
    GsFloatConfig,
    GsIntConfig,
    GsStrConfig,
)

CONFIG_DEFAULT: Dict[str, GSC] = {
    'use_forward': GsBoolConfig(
        '合并转发发送',
        '是否使用合并转发发送帖子内容；关闭后按普通消息发送。GScore 版不支持 AstrBot 的转发节点昵称/QQ 配置。',
        True,
    ),
    'default_page_size': GsIntConfig(
        '每页帖子数量',
        '每次从库街区列表接口取多少条帖子；越大随机池越大',
        20,
        max_value=50,
    ),
    'request_rounds': GsIntConfig(
        '随机请求页数',
        '一次命令随机请求多少页；越大越不容易重复',
        30,
        max_value=80,
    ),
    'random_page_max': GsIntConfig(
        '随机页码上限',
        '随机页码上限；建议不要过大，避免抽到大量空页',
        80,
        max_value=2000,
    ),
    'max_media_per_post': GsIntConfig(
        '单帖媒体上限',
        '单条帖子最多发送多少个正文图片/视频资源',
        6,
        max_value=30,
    ),
    'download_media': GsBoolConfig(
        '下载后发送',
        '是否下载媒体后从本地发送；关闭后图片尝试直链发送，视频回退为链接文本',
        True,
    ),
    'delete_after_send': GsBoolConfig(
        '发送后删除本地文件',
        '发送后自动删除下载到本地的图片/视频',
        True,
    ),
    'download_timeout': GsFloatConfig(
        '媒体下载超时秒数',
        '下载单个媒体的超时时间，单位秒',
        20.0,
        min_value=3.0,
        max_value=120.0,
    ),
    'request_timeout': GsFloatConfig(
        '接口请求超时秒数',
        '请求库街区接口的超时时间，单位秒',
        12.0,
        min_value=3.0,
        max_value=60.0,
    ),
    'api_base': GsStrConfig(
        '库街区 API 根地址',
        '库街区 API 根地址，通常不用改',
        'https://api.kurobbs.com',
    ),
    'list_endpoint': GsStrConfig(
        '库街区列表接口路径',
        '库街区列表接口路径，通常为 /forum/list',
        '/forum/list',
    ),
    'search_endpoint': GsStrConfig(
        '库街区帖子搜索接口路径',
        '用于 鸣潮cos 角色名 的搜索接口',
        '/forum/searchPost',
    ),
    'search_page_size': GsIntConfig(
        '搜索每页数量',
        '角色搜索模式每页取多少条搜索结果',
        10,
        max_value=50,
    ),
    'search_rounds': GsIntConfig(
        '搜索请求页数',
        '角色搜索模式每个搜索词请求多少页',
        3,
        max_value=20,
    ),
    'game_id': GsIntConfig(
        '鸣潮游戏 ID',
        '鸣潮游戏 ID，默认 3',
        3,
    ),
    'forum_id': GsIntConfig(
        '鸣潮 COS 板块 ID',
        '鸣潮 COS 板块 ID，默认 17',
        17,
    ),
    'search_type': GsIntConfig(
        '列表排序/筛选类型',
        '库街区列表排序/筛选类型，默认 3',
        3,
    ),
    'dev_code': GsStrConfig(
        '请求头 devCode',
        '库街区请求头 devCode；通常不用改',
        'H0O9l04JUG341k5UpUTMNpnGawC5Qt9p',
    ),
    'distinct_id': GsStrConfig(
        '请求头 distinct_id',
        '库街区请求头 distinct_id；通常不用改',
        '195be91535f592-0915a368d4173f-4c657b58-1327104-195be9153601740',
    ),
    'debug_log': GsBoolConfig(
        '调试日志',
        '开启后输出接口页码、候选帖子等调试日志',
        False,
    ),
}
