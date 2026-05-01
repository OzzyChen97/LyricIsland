<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS-blueviolet?style=for-the-badge&logo=apple" alt="macOS">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/version-1.0.0-orange?style=for-the-badge" alt="Version">
</p>

<h1 align="center">LyricIsland</h1>

<p align="center">
  <b>macOS 桌面浮动歌词工具 — 为 Apple Music 带来实时同步歌词体验</b>
</p>

<p align="center">
  一款轻量级 macOS 菜单栏应用，自动获取 Apple Music 歌词并通过浮动窗口实时同步显示，支持迷你胶囊模式与展开歌词面板。
</p>

---

## 目录

- [功能特性](#功能特性)
- [演示](#演示)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [系统要求](#系统要求)
- [安装与运行](#安装与运行)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [工作原理](#工作原理)
- [常见问题](#常见问题)
- [贡献规范](#贡献规范)
- [许可证](#许可证)
- [致谢](#致谢)

---

## 功能特性

- **实时歌词同步** — 基于 LRC 时间戳精准匹配当前播放位置，逐行高亮显示
- **浮动窗口** — 始终置顶、无边框、半透明毛玻璃风格，不影响其他操作
- **双模式切换**
  - **迷你胶囊模式** — 紧凑的药丸形面板，仅显示当前歌词行与歌曲信息
  - **展开面板模式** — 完整歌词列表，支持滚动浏览，当前行加粗高亮
- **自动歌词获取** — 通过 LRCLIB API 自动搜索并匹配歌词，支持同步与纯文本歌词
- **Apple Music 深度集成** — 通过 ScriptingBridge 与分布式通知实时监听播放状态
- **播放状态动画** — 迷你模式下的音频条动画指示播放状态
- **菜单栏常驻** — 系统托盘图标，一键显示/隐藏歌词面板

---

## 演示

```
┌─────────────────────────────────────┐
│  ♪  Song Title - Artist     ▋ ▊ ▋ ⌄ │   ← 迷你胶囊模式
│     当前歌词行                       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Song Title                    ⌃    │
│  Artist Name                        │
│ ─────────────────────────────────── │
│                                     │
│  已经播放过的歌词（低透明度）         │
│  ▐ 当前正在播放的歌词行（加粗高亮）   │
│  即将播放的歌词行                    │
│  后续歌词行                          │
│  ...                                │
└─────────────────────────────────────┘
```

---

## 技术栈

| 技术 | 用途 | 说明 |
|------|------|------|
| **Python 3.10+** | 主语言 | 核心运行时 |
| **PyObjC** | macOS 原生桥接 | 将 Apple Objective-C 框架绑定到 Python |
| **AppKit (NSWindow/NSView)** | UI 渲染 | 无边框浮动窗口与自定义绘图 |
| **ScriptingBridge** | Apple Music 通信 | 获取播放状态、当前曲目、播放进度 |
| **NSDistributedNotificationCenter** | 事件监听 | 实时监听 Music.app 播放状态变更通知 |
| **LRCLIB API** | 歌词数据源 | 免费开源的同步歌词 API |
| **Quartz (Core Graphics)** | 图形绘制 | 圆角路径、矩形填充等底层绘图 |
| **requests** | HTTP 客户端 | 调用 LRCLIB REST API |

---

## 项目结构

```
LyricIsland-Python/
├── app.py              # 应用入口，主控制器，菜单栏与窗口协调
├── config.py           # 全局配置常量（窗口尺寸、颜色、API 地址等）
├── floating_window.py  # 浮动窗口与歌词自定义绘图视图
├── lyrics_fetcher.py   # LRCLIB API 歌词获取与 LRC 解析
├── music_monitor.py    # Apple Music 播放状态监控与曲目信息获取
├── sync_engine.py      # 歌词同步引擎，二分查找匹配当前播放行
└── run.sh              # 快捷启动脚本
```

**模块职责：**

| 模块 | 核心类/函数 | 职责 |
|------|-------------|------|
| [app.py](app.py) | `LyricIslandController`, `AppDelegate` | 应用生命周期、模块间协调、定时器管理 |
| [config.py](config.py) | 常量定义 | 统一管理窗口尺寸、颜色、字体、API 配置 |
| [floating_window.py](floating_window.py) | `FloatingWindow`, `LyricsContentView` | NSPanel 浮动窗口与 Core Graphics 歌词渲染 |
| [lyrics_fetcher.py](lyrics_fetcher.py) | `fetch_lyrics()`, `parse_lrc()` | HTTP 请求歌词 API、LRC 格式解析 |
| [music_monitor.py](music_monitor.py) | `MusicMonitor`, `SongInfo` | ScriptingBridge 通信、分布式通知监听 |
| [sync_engine.py](sync_engine.py) | `SyncEngine` | 二分查找定位当前歌词行、计算行内进度 |

---

## 系统要求

- **操作系统**: macOS 12 Monterey 或更高版本
- **Python**: 3.10+
- **音乐应用**: Apple Music（macOS 版）
- **网络**: 首次获取歌词需要网络连接（歌词会缓存在内存中）

---

## 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/your-username/LyricIsland-Python.git
cd LyricIsland-Python
```

### 2. 安装依赖

```bash
pip3 install pyobjc-framework-Cocoa pyobjc-framework-ScriptingBridge pyobjc-framework-Quartz requests
```

> **注意**: PyObjC 仅在 macOS 上可用，安装过程可能需要几分钟。

### 3. 运行应用

**方式一：直接运行**

```bash
python3 app.py
```

**方式二：使用启动脚本**

```bash
chmod +x run.sh
./run.sh
```

### 4. 授权提示

首次运行时，macOS 可能会提示授予辅助功能权限，以允许应用监听 Apple Music 状态。请前往 **系统设置 → 隐私与安全性 → 辅助功能** 中授权。

---

## 使用指南

### 基本操作

1. **启动应用** — 运行后，LyricIsland 图标会出现在菜单栏
2. **播放音乐** — 在 Apple Music 中播放任意歌曲，歌词将自动获取并显示
3. **展开/收起面板** — 点击浮动窗口即可在迷你胶囊和完整歌词面板之间切换
4. **快捷键** — `⌘L` 显示/隐藏歌词面板
5. **退出应用** — 点击菜单栏图标 → Quit LyricIsland，或使用 `⌘Q`

### 界面说明

**迷你胶囊模式（默认）：**
- 左侧 `♪` 图标标识应用
- 顶部显示歌曲名称
- 底部显示当前歌词行
- 右侧音频条动画表示播放状态
- 右下角 `⌄` 提示可展开

**展开面板模式：**
- 顶部显示歌曲名称与艺术家
- 歌词列表中，当前行以粗体 + 蓝色左侧指示条高亮
- 已播放行降低透明度
- 点击 `⌃` 或面板任意位置收起

---

## 配置说明

所有可配置项位于 [config.py](config.py)：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `COMPACT_WIDTH` | 400 | 迷你模式窗口宽度 (px) |
| `COMPACT_HEIGHT` | 48 | 迷你模式窗口高度 (px) |
| `EXPANDED_WIDTH` | 400 | 展开模式窗口宽度 (px) |
| `EXPANDED_HEIGHT` | 500 | 展开模式窗口高度 (px) |
| `CORNER_RADIUS` | 24 | 迷你模式圆角半径 |
| `EXPANDED_CORNER_RADIUS` | 16 | 展开模式圆角半径 |
| `POLL_INTERVAL` | 0.1 | 播放位置轮询间隔 (秒) |
| `LRCLIB_BASE_URL` | `https://lrclib.net/api` | 歌词 API 地址 |
| `BG_COLOR` | `(0,0,0,0.75)` | 背景色 (RGBA) |
| `TEXT_COLOR` | `(1,1,1,1)` | 文字颜色 |
| `ACCENT_COLOR` | `(0.3,0.5,1.0,1.0)` | 强调色（高亮行指示条） |

---

## 工作原理

```
Apple Music.app
      │
      ├── ScriptingBridge ──→ MusicMonitor (播放状态 + 曲目信息)
      │                              │
      │                              ▼
      │                        SongInfo (title, artist, album, duration)
      │                              │
      ├── DistributedNotification ──→┘ (即时播放/暂停事件)
      │
      ▼
LyricsFetcher ──→ LRCLIB API ──→ [LyricLine(time, text), ...]
                                       │
                                       ▼
                               SyncEngine.set_lyrics()
                                       │
                            MusicMonitor.playback_time
                                       │
                                       ▼
                               SyncEngine.update(time)
                                       │
                              二分查找当前行 index
                                       │
                                       ▼
                          LyricsContentView 渲染高亮
                                       │
                                       ▼
                          FloatingWindow 桌面显示
```

**核心算法 — 歌词同步 ([sync_engine.py](sync_engine.py)):**

SyncEngine 使用二分查找在已排序的 LRC 时间戳列表中定位当前播放位置对应的歌词行，时间复杂度 O(log n)。同时计算当前行的播放进度（0.0 ~ 1.0），为潜在的进度动画提供数据支持。

---

## 常见问题

### Q: 歌词没有显示？
- 确认 Apple Music 正在播放歌曲
- 检查网络连接（歌词需要从 LRCLIB API 获取）
- 部分小众歌曲可能不在 LRCLIB 数据库中

### Q: 歌词不同步？
- LRCLIB 提供的 LRC 时间戳质量因歌曲而异
- 如果仅有纯文本歌词（无时间戳），会默认显示在第一行

### Q: 窗口被其他窗口遮挡？
- 浮动窗口设置为 `NSFloatingWindowLevel`，应始终在普通窗口之上
- 如果进入全屏应用，窗口会在所有桌面空间中显示

### Q: Apple Music 未被检测到？
- 确认使用的是 macOS 原生 Apple Music 应用（非 Spotify 等第三方播放器）
- 确认已在系统设置中授予辅助功能权限

---

## 贡献规范

欢迎贡献代码、报告问题或提出功能建议！

### 开发流程

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

| 前缀 | 说明 |
|------|------|
| `feat:` | 新功能 |
| `fix:` | Bug 修复 |
| `refactor:` | 代码重构 |
| `docs:` | 文档更新 |
| `style:` | 代码格式调整 |
| `perf:` | 性能优化 |

### 开发建议

- 遵循现有代码风格（type hints、docstring）
- UI 相关修改请确保在 macOS 12+ 上测试
- 新增依赖前请在 Issue 中讨论

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

```
MIT License

Copyright (c) 2025 LyricIsland

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## 致谢

- [LRCLIB](https://lrclib.net) — 提供免费开源的同步歌词 API
- [PyObjC](https://pyobjc.readthedocs.io) — Python 与 macOS 原生框架的桥梁
- Apple Music — 优秀的音乐播放体验

---

<p align="center">
  Made with ♪ for music lovers
</p>
