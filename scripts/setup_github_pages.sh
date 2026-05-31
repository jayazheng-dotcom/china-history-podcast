#!/bin/bash
# 初始化 GitHub Pages 和项目基础文件
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="jayazheng-dotcom"
REPO="china-history-podcast"

echo "=== 初始化每日中国通史播客 ==="

cd "$PROJECT_DIR"

# 1. 创建 GitHub Pages 所需的 index.html
mkdir -p rss

cat > rss/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日中国通史 - 播客</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.6; }
        h1 { color: #1a1a1a; }
        .rss-link { display: inline-block; background: #8B4513; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-size: 16px; margin: 16px 0; }
        .rss-link:hover { background: #6B3410; }
        .info { color: #666; font-size: 14px; margin-top: 24px; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 14px; }
    </style>
</head>
<body>
    <h1>📚 每日中国通史</h1>
    <p>安州牧《中国通史》音频版 · 每天20分钟听懂中国历史</p>
    <p>从西汉到北洋，160集完整中国通史。每日更新一集。</p>

    <a class="rss-link" href="podcast.xml">📥 订阅播客 RSS</a>

    <div class="info">
        <p><strong>如何在 iPhone 播客 App 订阅：</strong></p>
        <ol>
            <li>复制 RSS 链接：<code>https://jayazheng-dotcom.github.io/china-history-podcast/rss/podcast.xml</code></li>
            <li>打开 Apple Podcasts → 资料库 → 右上角⋯ → 通过 URL 关注节目</li>
            <li>粘贴链接 → 关注</li>
        </ol>
        <p><strong>其他播客 App：</strong>支持"通过 URL 订阅"的 App 均可使用上述 RSS 链接。</p>
    </div>
</body>
</html>
HTMLEOF

echo "[完成] 创建 rss/index.html"

# 2. 生成默认播客封面（纯色占位）
python3 -c "
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (3000, 3000), color='#8B4513')
draw = ImageDraw.Draw(img)
# 简单文字
try:
    font = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 200)
except:
    font = ImageFont.load_default()
draw.text((600, 1200), '中国通史', fill='white', font=font)
draw.text((600, 1600), '每日20分钟', fill='#FFD700', font=font)
img.save('rss/cover.jpg', quality=90)
print('[完成] 生成封面 rss/cover.jpg')
" 2>/dev/null || echo "[跳过] 封面生成（PIL 未安装，请手动放置 3000x3000 的 cover.jpg 到 rss/ 目录）"

# 3. 提交到 git
git add -A
git commit -m "init: 每日中国通史播客项目" || echo "[跳过] 无新变更"
git branch -M main
git push -u origin main

echo ""
echo "=== 下一步 ==="
echo "1. 启用 GitHub Pages:"
echo "   gh api repos/$OWNER/$REPO/pages -X POST -f source.branch=main -f source.path=/rss"
echo ""
echo "2. 下载第1集测试:"
echo "   python3 scripts/daily_push.py batch 1 1"
echo ""
echo "3. 发布第1集:"
echo "   python3 scripts/daily_push.py today"
