<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS-blueviolet?style=for-the-badge&logo=apple" alt="macOS">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/version-1.1.0-orange?style=for-the-badge" alt="Version">
</p>

<h1 align="center">LyricIsland</h1>

<p align="center">
  <b>macOS 桌面浮动歌词工具 — 为 Apple Music 带来实时同步歌词体验</b>
</p>

<p align="center">
  一款轻量级 macOS 菜单栏应用，自动获取 Apple Music 歌词并通过浮动窗口实时同步显示，支持黑胶唱片封面、迷你胶囊模式与展开歌词面板。
</p>

---

## 目录

- [目录](#目录)
- [功能特性](#功能特性)
- [演示](#演示)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [系统要求](#系统要求)
- [安装与运行](#安装与运行)
  - [方式一：下载 DMG 安装包（推荐）](#方式一下载-dmg-安装包推荐)
  - [方式二：源码运行](#方式二源码运行)
    - [1. 克隆项目](#1-克隆项目)
    - [2. 安装依赖](#2-安装依赖)
    - [3. 运行应用](#3-运行应用)
  - [首次授权提示](#首次授权提示)
- [使用指南](#使用指南)
  - [基本操作](#基本操作)
  - [界面说明](#界面说明)
  - [播放状态响应](#播放状态响应)
- [配置说明](#配置说明)
- [工作原理](#工作原理)
- [常见问题](#常见问题)
  - [Q: 歌词没有显示？](#q-歌词没有显示)
  - [Q: 歌词不同步？](#q-歌词不同步)
  - [Q: 窗口被其他窗口遮挡？](#q-窗口被其他窗口遮挡)
  - [Q: Apple Music 未被检测到？](#q-apple-music-未被检测到)
  - [Q: 无法拖拽窗口？](#q-无法拖拽窗口)
- [贡献规范](#贡献规范)
  - [开发流程](#开发流程)
  - [提交规范](#提交规范)
- [许可证](#许可证)
- [致谢](#致谢)

---

## 功能特性

- **实时歌词同步** — 基于 LRC 时间戳精准匹配当前播放位置，逐行高亮显示
- **浮动窗口** — 始终置顶、无边框、半透明毛玻璃风格，不影响其他操作
- **自由拖拽** — 按住窗口任意区域即可自由拖拽移动位置
- **黑胶唱片封面** — 迷你模式左侧显示旋转的黑胶唱片，自动加载当前歌曲封面，播放时顺时针旋转，暂停时停止
- **双模式切换**
  - **迷你胶囊模式** — 紧凑的药丸形面板，黑胶唱片 + 歌曲信息 + 当前歌词行 + 音频条动画
  - **展开面板模式** — 完整歌词列表，支持滚动浏览，当前行加粗高亮
  - **箭头按钮** — 点击 ▼/▲ 箭头按钮在两种模式间切换
- **多源歌词获取** — 优先从网易云音乐获取中文歌词，备选 LRCLIB API，支持同步与纯文本歌词
- **Apple Music 集成** — 通过 osascript 实时监听播放状态、曲目信息与播放进度
- **播放状态感知** — 播放/暂停状态变化时自动触发黑胶唱片启停、歌词冻结等响应
- **菜单栏常驻** — 系统托盘图标，右键菜单退出

---

## 演示

```
┌────────────────────────────────────────────┐
│  ╭──────────────────────────────────╮      │
│  │ ♬  黑胶  Song Title - Artist  ▼  │      │
│  │    当前歌词行                     │      │
│  ╰──────────────────────────────────╯      │
└────────────────────────────────────────────┘
            迷你胶囊模式（可自由拖拽）

┌────────────────────────────────────────────┐
│  ♬  Song Title                        ▲   │
│     Artist                                │
│  ─────────────────────────────────────── │
│                                           │
│     已经播放过的歌词（低透明度）            │
│   ▐ 当前正在播放的歌词行（加粗高亮）        │
│     即将播放的歌词行                        │
│     后续歌词行                              │
│     ...                                    │
└────────────────────────────────────────────┘
            展开面板模式（支持滚动）
```

---

## 技术栈

| 技术 | 用途 | 说明 |
|------|------|------|
| **Python 3.10+** | 主语言 | 核心运行时 |
| **PyObjC** | macOS 原生桥接 | 将 Apple Objective-C 框架绑定到 Python |
| **AppKit (NSWindow/NSView)** | UI 渲染 | 无边框浮动窗口与自定义绘图 |
| **osascript** | Apple Music 通信 | 通过 AppleScript 子进程获取播放状态、曲目信息 |
| **网易云音乐 API** | 主歌词数据源 | 优先使用，支持中文歌曲歌词 |
| **LRCLIB API** | 备选歌词数据源 | 免费开源的同步歌词 API |
| **AppKit (NSImage/NSBezierPath)** | 图形绘制 | 黑胶唱片封面、圆角路径、音频条动画 |
| **requests** | HTTP 客户端 | 调用歌词 REST API |

---

## 项目结构

```
LyricIsland/
├── app.py                    # 主入口（AppKit 原生 UI）
├── app_tkinter.py            # 备选入口（tkinter UI）
├── config.py                 # 全局配置常量
├── core/                     # 核心业务逻辑
│   ├── __init__.py
│   ├── music_monitor.py      # Apple Music 播放状态监控
│   ├── lyrics_fetcher.py     # 多源歌词获取与 LRC 解析
│   └── sync_engine.py        # 歌词同步引擎
├── ui/                       # UI 渲染模块
│   ├── __init__.py
│   └── floating_window.py    # 浮动窗口、黑胶唱片、歌词渲染
├── scripts/
│   └── run.sh                # 快捷启动脚本
├── setup.py                  # py2app 打包配置
├── requirements.txt          # Python 依赖清单
└── README.md
```

**模块职责：**

| 模块 | 核心类/函数 | 职责 |
|------|-------------|------|
| [app.py](app.py) | `LyricIslandController` | 应用生命周期、模块间协调、定时器管理、播放状态响应 |
| [config.py](config.py) | 常量定义 | 统一管理窗口尺寸、颜色、API 配置 |
| [core/music_monitor.py](core/music_monitor.py) | `MusicMonitor`, `SongInfo` | osascript 轮询播放状态、曲目信息、封面提取、播放/暂停状态回调 |
| [core/lyrics_fetcher.py](core/lyrics_fetcher.py) | `fetch_lyrics_async()`, `parse_lrc()` | 多源歌词获取（网易云优先 → LRCLIB 备选）、LRC 格式解析 |
| [core/sync_engine.py](core/sync_engine.py) | `SyncEngine` | 二分查找定位当前歌词行、计算行内进度 |
| [ui/floating_window.py](ui/floating_window.py) | `FloatingWindow`, `LyricsContentView` | NSWindow 浮动窗口、黑胶唱片旋转、箭头按钮、自由拖拽、歌词渲染 |

---

## 系统要求

- **操作系统**: macOS 12 Monterey 或更高版本
- **Python**: 3.10+（源码运行时需要，.app 已内嵌 Python）
- **音乐应用**: Apple Music（macOS 版）
- **网络**: 首次获取歌词需要网络连接（歌词会缓存在内存中）

---

## 安装与运行

### 方式一：下载 DMG 安装包（推荐）

1. 从 [Releases](https://github.com/OzzyChen97/LyricIsland/releases) 下载 `LyricIsland-v1.1.0-macOS.dmg`
2. 双击打开 DMG，将 `LyricIsland.app` 拖入 `Applications` 文件夹
3. 在启动台或应用程序文件夹中双击 `LyricIsland` 即可运行

> 无需安装 Python 或任何依赖，开箱即用。

### 方式二：源码运行

#### 1. 克隆项目

```bash
git clone https://github.com/OzzyChen97/LyricIsland.git
cd LyricIsland
```

#### 2. 安装依赖

```bash
pip3 install -r requirements.txt
```

> **注意**: PyObjC 仅在 macOS 上可用，安装过程可能需要几分钟。

#### 3. 运行应用

```bash
python3 app.py
```

### 首次授权提示

首次运行时，macOS 可能会提示授予辅助功能权限，以允许应用监听 Apple Music 状态。请前往 **系统设置 → 隐私与安全性 → 辅助功能** 中授权。

---

## 使用指南

### 基本操作

1. **启动应用** — 运行后，LyricIsland ♪ 图标会出现在菜单栏
2. **播放音乐** — 在 Apple Music 中播放任意歌曲，歌词将自动获取并显示
3. **展开/收起面板** — 点击窗口右侧的 ▼/▲ 箭头按钮切换模式
4. **拖拽移动** — 按住窗口任意非箭头区域，拖拽即可自由移动窗口位置
5. **退出应用** — 右键菜单栏图标 → Quit LyricIsland

### 界面说明

**迷你胶囊模式（默认）：**
- 左侧旋转黑胶唱片，自动加载当前歌曲专辑封面
- 中间显示歌曲名称、当前歌词行、下一句歌词预览
- 右侧音频条动画表示播放状态
- 右边缘 ▼ 箭头按钮点击可展开

**展开面板模式：**
- 顶部显示歌曲名称与艺术家
- 歌词列表中，当前行以粗体 + 蓝色左侧指示条高亮
- 已播放行降低透明度
- 支持鼠标滚轮滚动浏览完整歌词
- 右边缘 ▲ 箭头按钮点击可收起

### 播放状态响应

- **播放中** — 黑胶唱片顺时针旋转，歌词实时同步
- **暂停** — 黑胶唱片停止旋转，歌词冻结在当前行

---

## 配置说明

所有可配置项位于 [config.py](config.py)：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `COMPACT_WIDTH` | 400 | 迷你模式窗口宽度 (px) |
| `COMPACT_HEIGHT` | 68 | 迷你模式窗口高度 (px) |
| `EXPANDED_WIDTH` | 400 | 展开模式窗口宽度 (px) |
| `EXPANDED_HEIGHT` | 500 | 展开模式窗口高度 (px) |
| `CORNER_RADIUS` | 24 | 迷你模式圆角半径 |
| `EXPANDED_CORNER_RADIUS` | 16 | 展开模式圆角半径 |
| `POLL_INTERVAL` | 0.1 | 播放位置轮询间隔 (秒) |
| `LRCLIB_BASE_URL` | `https://lrclib.net/api` | LRCLIB 歌词 API 地址 |

---

## 工作原理

```
Apple Music.app
      │
      ├── osascript 轮询 ──→ MusicMonitor (播放状态 + 曲目信息 + 封面)
      │                              │
      │                              ▼
      │                        SongInfo (title, artist, album, duration, art_path)
      │                              │
      │                    ┌─────────┼─────────┐
      │                    ▼         ▼         ▼
      │              state_changed  song_changed  art_ready
      │                    │         │         │
      ▼                    ▼         ▼         ▼
LyricsFetcher ──→ 网易云 API    App Controller    Album Art
      │            (优先)           │          (黑胶唱片封面)
      │               │             │
      ├──→ LRCLIB ────┘             │
      │    (备选)                    │
      ▼                             ▼
[LyricLine(time, text), ...]  set_callbacks()
      │                             │
      ▼                             ▼
SyncEngine.set_lyrics()      LyricsContentView
      │                        ├─ 黑胶唱片旋转
      ▼                        ├─ 歌词渲染高亮
SyncEngine.update(time)       ├─ 箭头按钮交互
      │                        └─ 自由拖拽
      ▼
  二分查找当前行 index
      │
      ▼
  FloatingWindow 桌面显示
```

**核心算法 — 歌词同步 ([sync_engine.py](sync_engine.py)):**

SyncEngine 使用二分查找在已排序的 LRC 时间戳列表中定位当前播放位置对应的歌词行，时间复杂度 O(log n)。同时计算当前行的播放进度（0.0 ~ 1.0），为潜在的进度动画提供数据支持。

**歌词获取策略 ([lyrics_fetcher.py](lyrics_fetcher.py)):**

优先通过网易云音乐 API 搜索并获取中文歌词（在国内有更广泛的中文歌曲覆盖），失败后回退到 LRCLIB API。获取在后台线程中异步执行，不阻塞 UI。

---

## 常见问题

### Q: 歌词没有显示？
- 确认 Apple Music 正在播放歌曲
- 检查网络连接（歌词需要从网易云/LRCLIB API 获取）
- 部分小众歌曲可能不在歌词数据库中

### Q: 歌词不同步？
- LRC 时间戳质量因歌曲而异
- 如果仅有纯文本歌词（无时间戳），会默认显示在第一行

### Q: 窗口被其他窗口遮挡？
- 浮动窗口设置为 `NSFloatingWindowLevel`，应始终在普通窗口之上
- 窗口配置为在所有桌面空间中显示

### Q: Apple Music 未被检测到？
- 确认使用的是 macOS 原生 Apple Music 应用（非 Spotify 等第三方播放器）
- 确认已在系统设置中授予辅助功能权限

### Q: 无法拖拽窗口？
- 请确认使用的是原生 Apple Music 应用
- 尝试重新启动 LyricIsland

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

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 致谢

- [网易云音乐](https://music.163.com) — 中文歌词数据源
- [LRCLIB](https://lrclib.net) — 提供免费开源的同步歌词 API
- [PyObjC](https://pyobjc.readthedocs.io) — Python 与 macOS 原生框架的桥梁
- Apple Music — 优秀的音乐播放体验

---

<p align="center">
  Made with ♪ for music lovers
</p>
