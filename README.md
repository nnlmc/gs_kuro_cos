> 本项目采用 **GNU General Public License v3.0（GPLv3）** 开源。
>
> 你可以使用、修改和分发，但必须遵守 GPLv3：保留许可证与版权声明，分发修改版时按 GPLv3 继续开放对应源码。

# gs_kuro_cos

<p align="center">
  <img src="./ICON.png" width="160" alt="插件 ICON">
</p>

GSCore / GsUID Core 版库街区 COS/同人搬运插件。

插件使用 GsCore 强制前缀区分游戏：`ww` 是鸣潮，`zs` 是战双。命令本体保持简短，例如 `wwcos`、`ww同人`、`zs同人`。

## 安装

把 `gs_kuro_cos` 文件夹放到 GsCore 插件目录，重启 GsCore 或执行插件重载。

视频命令需要服务器能调用 `ffmpeg`，否则 `.m3u8` 视频无法转成可发送的 MP4。Linux 可以用系统包管理器安装，Windows 可以把 `ffmpeg.exe` 放进 `PATH`。

## 命令

鸣潮：

```text
wwcos
ww cos
wwcos 长离
wwcos视频
ww cos视频 长离
ww同人
ww 同人 今汐
ww同人视频
ww 同人视频 椿
```

战双：

```text
zs同人
zs 同人 露西亚
zs同人视频
zs 同人视频 露西亚
```

不带关键词时随机从对应板块抽取帖子。带关键词时走库街区搜索接口。

## 发送策略

- 图片帖默认使用合并转发。
- 视频帖默认普通消息发送，避免合并转发视频在不同 OneBot 端兼容性不一致。
- 图片默认下载后发送，减少直链失效问题。
- 视频默认下载后发送；`.m3u8` 会先用 `ffmpeg` 转成 MP4。
- 命中“禁止搬运、禁止转载、禁止二传、do not repost”等限制词的帖子会跳过。

## 配置

常用配置在 GsCore 控制台里改：

| 配置 | 默认 | 说明 |
| --- | --- | --- |
| `use_forward` | `true` | 图片帖是否合并转发，视频帖不使用合并转发 |
| `max_media_per_post` | `6` | 单帖最多发送的媒体数量 |
| `download_images` | `true` | 图片是否下载后发送 |
| `download_videos` | `true` | 视频是否下载后发送 |
| `video_send_mode` | `video` | `video` 发视频消息，`file` 发文件消息 |
| `video_definition` | `HD` | 视频清晰度优先级，可填 `HD`、`SD`、`LD`、`FD` |
| `video_max_mb` | `80` | 视频超过该大小会跳过发送 |
| `delete_cache_after_send` | `true` | 发送后删除 `media_cache` 临时文件 |
| `request_rounds` | `30` | 随机模式请求页数 |
| `random_page_max` | `80` | 随机模式页码上限 |
| `debug_log` | `false` | 输出详细抓取日志 |

一般只需要调整 `max_media_per_post`、`video_send_mode`、`video_max_mb`。如果随机重复多，再调大 `request_rounds`。

## 故障排查

视频解析成功但发不出去：把 `video_send_mode` 改成 `file` 测试，或调低 `video_max_mb`。

日志提示找不到 `ffmpeg`：安装 `ffmpeg` 并确认命令行能直接执行 `ffmpeg`。

经常提示没找到内容：开启 `debug_log` 看接口页码和候选数量，也可以增加 `request_rounds`。

部分帖子没有媒体：库街区接口可能只返回封面或隐藏正文资源，插件会跳过没有正文媒体的帖子。
