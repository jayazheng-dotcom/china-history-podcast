#!/usr/bin/env python3
"""
每日中国通史播客 - 主脚本
功能：下载B站视频 → 提取音频 → 上传GitHub Release → 更新RSS
"""

import json
import os
import re
import subprocess
import sys
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import yaml

# ─── 项目根目录 ───
PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "audio"
RSS_DIR = PROJECT_DIR / "docs"
EPISODES_FILE = PROJECT_DIR / "episodes.json"
STATE_FILE = PROJECT_DIR / "state.json"
CONFIG_FILE = PROJECT_DIR / "config.yaml"

SHANGHAI_TZ = timezone(timedelta(hours=8))


def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def load_episodes():
    with open(EPISODES_FILE) as f:
        return json.load(f)


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"current_episode": 1, "published": [], "last_updated": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def download_audio(bvid, output_path, config):
    """用 yt-dlp 下载B站视频音频轨道，再用 ffmpeg 转为 m4a"""
    url = f"https://www.bilibili.com/video/{bvid}"
    tmp_path = str(output_path) + ".tmp"

    # yt-dlp 下载最佳音频
    cmd = [
        "yt-dlp",
        "-f", config["download"]["yt_dlp_format"],
        "-x",  # 提取音频
        "--audio-format", "m4a",
        "--audio-quality", "0",
        "-o", tmp_path,
        "--no-playlist",
        "--retries", str(config["download"]["max_retries"]),
        "--no-check-certificates",
        url,
    ]
    print(f"  [下载] {url}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [错误] yt-dlp 下载失败: {result.stderr[-500:]}")
        return False

    # 如果 yt-dlp 没直接输出 m4a，用 ffmpeg 转换
    tmp_files = list(Path(str(output_path) + ".tmp*").parent.glob(
        Path(str(output_path) + ".tmp*").name
    ))
    # yt-dlp 可能自动加了扩展名
    actual_tmp = None
    for ext in [".tmp.m4a", ".tmp.opus", ".tmp.webm", ".tmp.mp4", ".tmp"]:
        candidate = Path(str(output_path) + ext)
        if candidate.exists():
            actual_tmp = candidate
            break

    if actual_tmp is None:
        # 也可能 yt-dlp 直接输出了目标文件
        if output_path.exists():
            actual_tmp = None  # 已经是最终文件
        else:
            print(f"  [错误] 未找到下载的临时文件")
            return False

    if actual_tmp and str(actual_tmp) != str(output_path):
        # 用 ffmpeg 转换
        print(f"  [转换] {actual_tmp.name} → {output_path.name}")
        cmd = [
            "ffmpeg", "-y", "-i", str(actual_tmp),
            "-vn",  # 不要视频
            "-c:a", "aac",
            "-b:a", config["download"]["bitrate"],
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        actual_tmp.unlink(missing_ok=True)
        if result.returncode != 0:
            print(f"  [错误] ffmpeg 转换失败: {result.stderr[-300:]}")
            return False

    # 清理可能的残留临时文件
    for ext in [".tmp.m4a", ".tmp.opus", ".tmp.webm", ".tmp.mp4", ".tmp"]:
        Path(str(output_path) + ext).unlink(missing_ok=True)
    Path(str(output_path) + ".tmp").unlink(missing_ok=True)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  [完成] {output_path.name} ({size_mb:.1f} MB)")
    return True


def get_audio_duration(path):
    """用 ffprobe 获取音频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return float(result.stdout.strip())
    return 0


def upload_to_github_pages(audio_path, episode_idx, config):
    """将音频文件复制到 docs/audio/ 目录，通过 GitHub Pages 提供直链"""
    owner = config["github"]["owner"]
    repo = config["github"]["repo"]
    pages_audio_dir = RSS_DIR / "audio"
    pages_audio_dir.mkdir(exist_ok=True)

    dest = pages_audio_dir / audio_path.name
    if dest.exists() and dest.stat().st_size == audio_path.stat().st_size:
        print(f"  [跳过] {dest.name} 已在 Pages 目录")
    else:
        import shutil
        shutil.copy2(str(audio_path), str(dest))
        print(f"  [复制] {audio_path.name} → docs/audio/")

    # GitHub Pages 直链 URL（无重定向，正确的 MIME type）
    return f"https://{owner}.github.io/{repo}/audio/{audio_path.name}"


def generate_rss(published_episodes, config):
    """生成播客 RSS XML"""
    owner = config["github"]["owner"]
    repo = config["github"]["repo"]
    pc = config["podcast"]
    base_url = f"https://{owner}.github.io/{repo}"

    rss = Element("rss", version="2.0",
                  **{"xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
                     "xmlns:atom": "http://www.w3.org/2005/Atom"})

    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = pc["title"]
    SubElement(channel, "link").text = f"https://github.com/{owner}/{repo}"
    SubElement(channel, "language").text = pc["language"]
    SubElement(channel, "description").text = pc["description"]
    SubElement(channel, "itunes:subtitle").text = pc["subtitle"]
    SubElement(channel, "itunes:author").text = pc["author"]
    SubElement(channel, "itunes:owner").append(
        _make_owner(pc["author"], pc["email"])
    )
    SubElement(channel, "itunes:explicit").text = "no"
    SubElement(channel, "itunes:category").text = pc["category"]
    SubElement(channel, "itunes:image", href=f"{base_url}/{pc['image']}")

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", f"{base_url}/podcast.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # 按发布日期倒序（最新的在前）
    for ep in sorted(published_episodes, key=lambda x: x["pub_date"], reverse=True):
        item = SubElement(channel, "item")
        SubElement(item, "title").text = ep["title"]
        SubElement(item, "itunes:subtitle").text = ep.get("series", "")
        SubElement(item, "description").text = (
            f"安州牧《中国通史》第{ep['idx']}集 - {ep['title']}\n"
            f"系列：{ep.get('series', '')}\n"
            f"时长：{ep.get('duration_min', 0):.0f}分钟\n"
            f"原视频：https://www.bilibili.com/video/{ep['bvid']}"
        )
        SubElement(item, "enclosure").set("url", ep["audio_url"])
        item.find("enclosure").set("length", str(ep.get("file_size", 0)))
        item.find("enclosure").set("type", "audio/mp4")

        SubElement(item, "guid").text = ep["audio_url"]
        SubElement(item, "pubDate").text = ep["pub_date"]
        SubElement(item, "itunes:duration").text = str(ep.get("duration_sec", 0))
        SubElement(item, "itunes:explicit").text = "no"

    # 美化输出
    xml_str = minidom.parseString(tostring(rss)).toprettyxml(indent="  ", encoding="utf-8")
    rss_path = RSS_DIR / "podcast.xml"
    rss_path.write_bytes(xml_str)
    print(f"[RSS] 已生成 {rss_path}")
    return rss_path


def _make_owner(name, email):
    owner = Element("itunes:owner")
    SubElement(owner, "itunes:name").text = name
    SubElement(owner, "itunes:email").text = email
    return owner


def deploy_rss_to_github_pages(config):
    """将 RSS 和 cover 部署到 GitHub Pages"""
    owner = config["github"]["owner"]
    repo = config["github"]["repo"]

    # 提交 docs 目录到 main 分支
    subprocess.run(["git", "add", "docs/"], cwd=str(PROJECT_DIR), capture_output=True)
    subprocess.run(["git", "commit", "-m", "update RSS feed"], cwd=str(PROJECT_DIR), capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=str(PROJECT_DIR), capture_output=True)

    print("[部署] RSS 已推送到 GitHub Pages")


def publish_episode(episode_idx, config, episodes, state, skip_download=False):
    """发布单集：下载 → 上传 → 更新RSS"""
    ep = None
    for e in episodes:
        if e["idx"] == episode_idx:
            ep = e
            break
    if ep is None:
        print(f"[错误] 未找到第 {episode_idx} 集")
        return False

    print(f"\n{'='*60}")
    print(f"第 {ep['idx']} 集 | {ep['series']} | {ep['title']}")
    print(f"{'='*60}")

    # 1. 下载音频
    audio_filename = f"ep{ep['idx']:03d}.m4a"
    audio_path = AUDIO_DIR / audio_filename

    if not skip_download:
        if audio_path.exists():
            print(f"  [跳过] 音频已存在 {audio_path.name}")
        else:
            success = download_audio(ep["bvid"], audio_path, config)
            if not success:
                return False
    elif not audio_path.exists():
        print(f"  [错误] skip_download 但文件不存在: {audio_path}")
        return False

    # 2. 获取音频信息
    duration_sec = int(get_audio_duration(audio_path))
    if duration_sec == 0:
        duration_sec = ep["duration"]  # 回退到 API 数据
    file_size = audio_path.stat().st_size

    # 3. 复制到 GitHub Pages 音频目录
    audio_url = upload_to_github_pages(audio_path, ep["idx"], config)
    if audio_url is None:
        return False

    # 4. 记录发布信息
    now = datetime.now(SHANGHAI_TZ)
    pub_entry = {
        "idx": ep["idx"],
        "bvid": ep["bvid"],
        "title": ep["title"],
        "series": ep["series"],
        "duration_sec": duration_sec,
        "duration_min": duration_sec / 60,
        "file_size": file_size,
        "audio_url": audio_url,
        "pub_date": now.strftime("%a, %d %b %Y %H:%M:%S +0800"),
        "pub_date_iso": now.isoformat(),
    }

    state["published"].append(pub_entry)
    state["current_episode"] = ep["idx"] + 1
    state["last_updated"] = now.isoformat()
    save_state(state)

    # 5. 更新 RSS
    generate_rss(state["published"], config)

    # 6. 自动推送到 GitHub Pages
    deploy_rss_to_github_pages(config)

    print(f"  [发布] 第{ep['idx']}集发布成功!")
    return True


def batch_download(start_idx, count, config, episodes):
    """批量下载音频（不发布）"""
    AUDIO_DIR.mkdir(exist_ok=True)
    success_count = 0
    for ep in episodes:
        if ep["idx"] < start_idx or ep["idx"] >= start_idx + count:
            continue
        audio_filename = f"ep{ep['idx']:03d}.m4a"
        audio_path = AUDIO_DIR / audio_filename
        if audio_path.exists():
            print(f"  [跳过] ep{ep['idx']:03d} 已存在")
            success_count += 1
            continue
        if download_audio(ep["bvid"], audio_path, config):
            success_count += 1
        else:
            print(f"  [失败] 第{ep['idx']}集下载失败")
    print(f"\n[统计] 成功 {success_count}/{count}")


def main():
    config = load_config()
    episodes = load_episodes()
    state = load_state()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python daily_push.py today       # 发布今天的集数")
        print("  python daily_push.py publish N    # 发布第N集")
        print("  python daily_push.py batch N M    # 批量下载第N到N+M-1集")
        print("  python daily_push.py rss          # 重新生成RSS")
        print("  python daily_push.py status       # 查看状态")
        return

    cmd = sys.argv[1]
    AUDIO_DIR.mkdir(exist_ok=True)
    RSS_DIR.mkdir(exist_ok=True)

    if cmd == "today":
        # 发布当天集数
        ep_idx = state["current_episode"]
        if ep_idx > len(episodes):
            print("[完成] 所有 160 集已发布完毕！")
            return
        publish_episode(ep_idx, config, episodes, state)

    elif cmd == "publish" and len(sys.argv) >= 3:
        ep_idx = int(sys.argv[2])
        publish_episode(ep_idx, config, episodes, state)

    elif cmd == "batch" and len(sys.argv) >= 4:
        start_idx = int(sys.argv[2])
        count = int(sys.argv[3])
        batch_download(start_idx, count, config, episodes)

    elif cmd == "rss":
        generate_rss(state["published"], config)

    elif cmd == "status":
        current = state["current_episode"]
        published = len(state["published"])
        total = len(episodes)
        print(f"当前进度: 第 {current}/{total} 集")
        print(f"已发布: {published} 集")
        if state.get("last_updated"):
            print(f"最后更新: {state['last_updated']}")
        # 显示最近 3 集
        for ep in state["published"][-3:]:
            print(f"  第{ep['idx']:3d}集 | {ep['series']} | {ep['title'][:30]}")

    else:
        print(f"未知命令: {cmd}")
        main()  # 显示帮助


if __name__ == "__main__":
    main()
