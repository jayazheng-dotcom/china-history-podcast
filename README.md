# 📚 每日中国通史播客

**每天20分钟，从西汉到北洋，160集完整中国通史。**

> 原视频由B站UP主 [安州牧](https://space.bilibili.com/7481602) 制作，本播客仅提取音频供个人学习使用。

## 订阅方式

**RSS 链接**（复制到播客 App 中订阅）：
```
https://jayazheng-dotcom.github.io/china-history-podcast/rss/podcast.xml
```

### iPhone (Apple Podcasts)
1. 打开 Apple Podcasts
2. 资料库 → 右上角 ⋯ → 「通过 URL 关注节目」
3. 粘贴上面的 RSS 链接 → 关注

### 其他播客 App
支持「通过 URL 订阅」的 App（如 Overcast、Pocket Casts、小宇宙等）均可使用。

## 内容概览

| 系列 | 集数范围 | 集数 |
|------|---------|------|
| 西汉 | 1-3 | 3 |
| 汉末三国 | 4-8 | 5 |
| 两晋十六国 | 9-42 | 34 |
| 风云南北朝 | 43-88 | 46 |
| 开皇大业 | 89-100 | 12 |
| 大唐创业 | 101-110 | 10 |
| 贞观 | 111-119 | 9 |
| 从初唐走向盛唐 | 120-142 | 23 |
| 安史之乱 | 143-153 | 11 |
| 北洋时代 | 154-160 | 7 |
| **合计** | | **160** |

## 项目结构

```
china-history-podcast/
├── episodes.json       # 160集完整列表（B站API抓取）
├── config.yaml         # 配置文件
├── scripts/
│   ├── daily_push.py   # 主脚本：下载→上传→更新RSS
│   └── setup_github_pages.sh  # 初始化
├── audio/              # 本地音频缓存（gitignore）
├── rss/
│   ├── podcast.xml     # RSS feed（GitHub Pages 托管）
│   ├── cover.jpg       # 播客封面
│   └── index.html      # 订阅引导页
└── state.json          # 运行状态（gitignore）
```

## 运行

```bash
# 安装依赖
pip3 install -r requirements.txt

# 初始化项目 + 启用 GitHub Pages
bash scripts/setup_github_pages.sh

# 查看状态
python3 scripts/daily_push.py status

# 发布当天集数
python3 scripts/daily_push.py today

# 批量预下载（如：下载前10集）
python3 scripts/daily_push.py batch 1 10

# 发布指定集数
python3 scripts/daily_push.py publish 5

# 重新生成 RSS
python3 scripts/daily_push.py rss
```

## 每日定时发布（Mac crontab）

```bash
# 每天 21:30 执行
crontab -e
# 添加以下行：
30 21 * * * cd /Users/jaya/CodeBuddy/work_github/projects/china-history-podcast && /usr/bin/python3 scripts/daily_push.py today >> /tmp/china-history-podcast.log 2>&1
```

## 技术栈

- **音频下载**：yt-dlp + ffmpeg
- **音频托管**：GitHub Releases（免费、无流量限制）
- **RSS 托管**：GitHub Pages
- **定时任务**：Mac crontab
- **播客客户端**：Apple Podcasts / 任意支持 RSS 订阅的 App
