# gs_kuro_cos

<p align="center">
  <a href="https://github.com/nnlmc/gs_kuro_cos"><img src="ICON.png" width="160" alt="gs_kuro_cos ICON"></a>
</p>
<h1 align="center">gs_kuro_cos v0.2.4</h1>
<h4 align="center">库街区 COS / 同人搬运插件，适用于 GsCore / GsUID Core</h4>
<div align="center">
  <a href="https://github.com/nnlmc/gs_kuro_cos" target="_blank">GitHub</a> &nbsp; · &nbsp;
  <a href="https://cnb.cool/nnlmc/gs_kuro_cos" target="_blank">CNB</a> &nbsp; · &nbsp;
  <a href="https://github.com/Genshin-bots/gsuid_core" target="_blank">gsuid_core</a>
</div>

## 丨安装提醒

> **注意：该插件为 [早柚核心(gsuid_core)](https://github.com/Genshin-bots/gsuid_core) 的扩展，需要先安装好 GsCore 才能使用**
>
> **本插件已上架 GsCore 插件商店，可直接对 bot 发送 `core安装插件cos`，然后重启 Core 以应用安装**
>
> **如果从 CNB 拉取，需要手动克隆到 GsCore 插件目录后重启 Core：**
>
> ```bash
> cd /path/to/gsuid_core/gsuid_core/plugins
> git clone https://cnb.cool/nnlmc/gs_kuro_cos.git
> ```
>
> 插件依赖已写入 `pyproject.toml`，插件市场或新版 GsCore 会自动检查安装；如果你的 GsCore 版本不会自动处理依赖，请在同一 Python 环境中手动安装：
>
> ```bash
> pip install "httpx>=0.24.0" "pillow>=10.0.0"
> ```
>
> 插件交流、图库账号密码获取请加群：`798949533`

## 丨功能

- 随机获取库街区鸣潮 COS、鸣潮同人、战双同人帖子
- 支持关键词搜索，例如指定角色名或作品关键词
- 支持图片发送，图片默认下载后发送以减少直链失效问题
- 自动跳过带有禁止搬运、禁止转载、禁止二传等限制说明的帖子
- 使用 GsCore 强制前缀区分游戏：`ww` 为鸣潮，`zs` 为战双

## 丨命令

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

## 丨常用配置

配置项可在 GsCore 控制台中修改，一般只需要关注下面几项：

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| 图片合并转发 | 开启 | 图片帖是否使用合并转发 |
| 单帖图片上限 | 6 | 单条帖子最多发送多少张图片 |
| 发送后清理缓存 | 开启 | 发送完成后是否清理临时图片缓存 |
| 调试日志 | 关闭 | 输出更详细的抓取与解析日志，排查问题时打开 |

其余抓取相关配置（请求页数、并发数等）保持默认即可，随机内容重复较多时可适当调大「随机请求页数」或「随机页码上限」。图片默认下载后发送，减少直链失效导致的发送失败。

## 丨故障排查

经常提示没有找到内容：开启「调试日志」查看接口页码、候选帖子数量和过滤原因。

部分帖子被跳过：帖子可能没有正文图片，或正文包含禁止搬运、禁止转载、禁止二传等限制词。

## 丨其他

- 本项目仅供学习使用，请勿用于商业用途
- 本项目采用 **GNU General Public License v3.0（GPLv3）** 开源。你可以使用、修改和分发，但必须保留许可证与版权声明；分发修改版时，需要按 GPLv3 继续开放对应源码
- [GPL-3.0 License](LICENSE)
