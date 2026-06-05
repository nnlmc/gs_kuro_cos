> 本项目采用 **GNU General Public License v3.0（GPLv3）** 开源。
>
> 你可以使用、修改和分发，但必须遵守 GPLv3：保留许可证与版权声明，分发修改版时按 GPLv3 继续开放对应源码。

# gs_kuro_cos

<p align="center">
  <img src="./ICON.png" width="160" alt="插件 ICON">
</p>

GSCore / GsUID 版鸣潮库街区 COS 搬运插件，按 AstrBot 版同步改写。

功能：从鸣潮库街区 COS 板块随机获取帖子，只提取帖子正文里的 COS 图片/视频，然后由机器人发送到当前聊天。

## 使用方法

固定命令：

```text
鸣潮cos
wwcos
鸣潮cos 长离
wwcos 长离
鸣潮cos 守岸人
```

不带参数时随机获取 COS 板块内容；带角色名/人物名时，会调用库街区搜索接口组合搜索 `角色名 cos`、`角色名 正片` 等关键词，比随机抽帖子后搜正文更容易命中。

本版保留 AstrBot 版固定命令：`鸣潮cos`、`wwcos`。群聊直接发送即可触发，无需 `/`，不再提供旧版 GScore 自定义触发词配置。

## 当前策略

- 只请求库街区 COS 板块：`gameId=3`、`forumId=17`、`searchType=3`；
- `鸣潮cos` 不带参数时走随机模式：默认从 `1~80` 页里抽 `30` 页，并固定混入前段页来减少抽到空页的概率；
- `鸣潮cos 角色名` 带参数时走搜索模式：使用 `/forum/searchPost` 组合搜索 `角色名 cos`、`角色名 正片`、`角色名 cos正片` 等关键词，并排除攻略、养成、配队、抽卡、活动等明显非 COS 结果；
- 每页默认取 `20` 条，组合成候选池后随机挑选；
- 如果随机页没有可用候选，会自动回退检查前段页，尽量避免直接返回“没找到”；
- 单条帖子默认最多发送 `6` 个正文媒体；
- 记住最近发过的帖子，降低连续重复概率；
- 只读取帖子正文媒体字段：`imgContent`、图片列表、视频字段、正文直链；搜索模式下如果帖子正文媒体为空，会额外尝试使用帖子封面图作为兜底；
- 命中“禁止搬运/禁止转载/禁止二传/Do not repost”等限制转载关键词时会跳过该帖子；
- 默认下载到本地后发送，发送后自动删除本地图片/视频；
- 默认使用合并转发发送整条帖子，可在控制台关闭。

## GScore 版未移植项

- `recall_after_send` / `recall_delay_seconds`：GScore 的通用发送接口不稳定暴露可撤回的消息 ID，未移植自动撤回；
- `forward_sender_name` / `forward_sender_id`：GScore 的 `MessageSegment.node` 不支持自定义合并转发节点昵称和 QQ，未移植。

## 推荐默认配置

当前内置默认值偏向稳定可用：`request_rounds=30`、`random_page_max=80`、`default_page_size=20`、`search_page_size=10`、`search_rounds=3`、`max_media_per_post=6`、`request_timeout=12.0`、`download_timeout=20.0`。

## 配置重点

- `request_rounds`：一次随机请求多少页，越大越不容易重复；
- `random_page_max`：随机页码上限，过大可能抽到较多空页；
- `default_page_size`：每页取多少条帖子；
- `max_media_per_post`：单条帖子最多发送多少个正文媒体；
- `download_media`：是否先下载媒体再发；
- `use_forward`：是否使用合并转发发送帖子内容，默认开启；
- `delete_after_send`：发送后是否自动删除本地媒体；
- `search_endpoint`：库街区帖子搜索接口，默认 `/forum/searchPost`；
- `search_page_size`：角色搜索模式每页取多少条搜索结果；
- `search_rounds`：角色搜索模式每个搜索词请求多少页；
- `forum_id`：鸣潮 COS 板块 ID，默认 `17`。

如果还是重复，把 `request_rounds` 和 `default_page_size` 调大。

## 安装

把 `gs_kuro_cos` 文件夹放到 GSCore 插件目录，然后重载插件或重启机器人。
