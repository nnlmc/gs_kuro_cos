# gs_kuro_cos

<p align="center">
  <img src="./ICON.png" width="160" alt="gs_kuro_cos ICON">
</p>

<p align="center">库街区 COS / 同人搬运插件，适用于 GsCore / GsUID Core。</p>

<p align="center">当前版本：v0.2.3</p>

## 功能

- 随机获取库街区鸣潮 COS、鸣潮同人、战双同人帖子。
- 支持关键词搜索，例如指定角色名或作品关键词。
- 支持图片发送，图片默认下载后发送以减少直链失效问题。
- 自动跳过带有禁止搬运、禁止转载、禁止二传等限制说明的帖子。
- 使用 GsCore 强制前缀区分游戏：`ww` 为鸣潮，`zs` 为战双。

## 安装

### 插件市场安装

插件上架后，可在 GsCore 控制台插件市场安装，或向机器人发送：

```text
core安装插件cos
```

安装完成后重启 GsCore，或使用 GsCore 的插件重载功能。

### 手动安装

进入 GsCore 插件目录：

```bash
cd /path/to/gsuid_core/gsuid_core/plugins
git clone https://github.com/nnlmc/gs_kuro_cos.git
```

然后重启 GsCore。

## 命令

帮助：

```text
wwcos帮助
zscos帮助
```

鸣潮 COS：

```text
wwcos
wwcos 长离
```

鸣潮同人：

```text
ww同人
ww同人 今汐
```

战双同人：

```text
zs同人
zs同人 露西亚
```

命令也兼容前缀和命令之间带空格的写法，例如：

```text
ww cos
ww 同人 今汐
zs 同人 露西亚
```

不带关键词时，插件会从对应分区随机抽取帖子；带关键词时，会优先使用库街区搜索接口查找相关内容。

## 常用配置

配置项可在 GsCore 控制台中修改。一般用户只需要关注下面几项：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `use_forward` | `true` | 图片帖是否使用合并转发。 |
| `max_media_per_post` | `6` | 单个帖子最多发送多少张图片。 |
| `delete_cache_after_send` | `true` | 发送完成后是否清理临时图片缓存。 |
| `debug_log` | `false` | 输出更详细的抓取与解析日志。 |

高级抓取相关配置保持默认即可。随机内容重复较多时，可以适当调大 `request_rounds` 或 `random_page_max`。

## 发送规则

图片默认下载后发送，减少图片直链失效导致的发送失败。

## 故障排查

经常提示没有找到内容：开启 `debug_log` 查看接口页码、候选帖子数量和过滤原因。

部分帖子被跳过：帖子可能没有正文图片，或正文包含禁止搬运、禁止转载、禁止二传等限制词。

## 开源协议

本项目采用 **GNU General Public License v3.0（GPLv3）** 开源。你可以使用、修改和分发，但必须保留许可证与版权声明；分发修改版时，需要按 GPLv3 继续开放对应源码。
