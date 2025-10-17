#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_live_site.py
作者: REDDUCK (2025)
功能：
- 实时生成访问日志（随时间推移，间隔随机几秒到几分钟）
- 每条日志时间为真实当前时间 (CST)
- 实时更新 index.html（点赞、收藏、分享、评论）
- 自动加载当前目录下的 a.* 图片
- 可手动 Ctrl+C 停止
"""

import os
import random
import re
import shutil
import time
import ipaddress
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Tuple

# ----------------------------
# 全局常量
# ----------------------------
DEFAULT_OUTPUT_DIR = "site_out"
DEFAULT_TITLE = "“森”的约定"
DEFAULT_DESC = (
    "在上海恒隆广场，我们不止于树立宫崎骏风格的可爱雕像——它们全部由可回收材料制作，"
    "本身就是环保理念的宣言。我们更设置了一个完整的环保叙事空间：<br>"
    "▪️ 环保产品展区，展示E公司对可持续材料的探索与应用；<br>"
    "▪️ 旧物改造艺术展，重新审视“价值”，启迪公众的环保意识。<br>"
    "感谢F公司的专业指导与小红书平台的记录，让“森计划”的种子通过线上内容，在更多人心中生根发芽。<br>"
    "未来，E公司将继续在这条路上深耕。因为守护我们共同的森林，是一场永不结束的计划。"
)
DEFAULT_COMMENT_PDF = "评论文件.pdf"
DEFAULT_URL_PATH = "/index.html"   # ✅ 修复 NameError
CST = timezone(timedelta(hours=8), name="CST")

# ----------------------------
# 实用函数
# ----------------------------
def random_realistic_ipv4() -> str:
    """生成较真实公网 IPv4 地址"""
    first_octet_candidates = [
        (3, 5), (13, 3), (18, 2), (34, 2), (35, 2), (52, 8),
        (54, 4), (66, 2), (69, 3), (70, 2), (99, 1),
        (104, 4), (107, 2), (128, 1), (130, 1), (139, 1),
        (144, 1), (151, 1), (154, 1), (162, 1), (167, 1),
        (184, 1), (185, 1), (193, 1), (195, 1), (199, 1),
        (204, 1), (205, 1), (206, 1), (207, 1), (208, 1),
        (209, 1), (216, 1)
    ]
    firsts, weights = zip(*first_octet_candidates)
    reserved_nets = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("224.0.0.0/4"),
        ipaddress.ip_network("240.0.0.0/4"),
    ]
    while True:
        first = random.choices(firsts, weights=weights, k=1)[0]
        ip = f"{first}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        if not any(ipaddress.ip_address(ip) in n for n in reserved_nets):
            return ip


def random_user_code4() -> str:
    import string
    return "".join(random.choice(string.ascii_uppercase) for _ in range(4))


def read_comments_from_pdf(pdf_path: Path) -> List[str]:
    """从 PDF 读取评论文本"""
    try:
        import PyPDF2
    except Exception:
        return []
    if not pdf_path.exists():
        return []
    texts = []
    try:
        with pdf_path.open("rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text() or ""
                if t:
                    texts.append(t)
    except Exception:
        return []
    raw = "\n".join(texts)
    lines = [re.sub(r"[0-9\.]", "", ln).strip() for ln in raw.splitlines()]
    return [ln for ln in lines if ln]


def find_local_image_candidate(root: Path) -> Path | None:
    """自动识别 a.png/jpg/jpeg/svg/webp"""
    for ext in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        p = root / f"a{ext}"
        if p.exists():
            return p
    return None


def ensure_assets(output_dir: Path, image_path: Path | None) -> Path:
    """复制图片到输出目录"""
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    img_out = assets / "image_a"
    if image_path and image_path.exists():
        ext = image_path.suffix
        img_out = img_out.with_suffix(ext)
        shutil.copyfile(image_path, img_out)
        return img_out
    else:
        print("⚠️ 未找到 a.*，生成占位图。")
        img_out = img_out.with_suffix(".svg")
        img_out.write_text(
            "<svg width='800' height='400'><rect width='800' height='400' fill='#eee'/>"
            "<text x='50%' y='50%' text-anchor='middle' dy='.3em'>Placeholder</text></svg>",
            encoding="utf-8"
        )
        return img_out


def build_html(out_dir: Path, title: str, desc_html: str, image_rel_path: str,
               totals: Tuple[int, int, int, int], comments_render: List[Tuple[str, str, str]]):
    """构建 HTML 页面"""
    likes, bookmarks, shares, comments = totals
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{title}</title>
<meta http-equiv="refresh" content="15"> <!-- ✅ 页面每15秒自动刷新 -->
<style>
  body{{font-family:Arial,"PingFang SC";margin:0;padding:0;background:#fff;color:#222;}}
  .container{{max-width:860px;margin:40px auto;padding:0 20px;}}
  .chip{{background:#f3f3f3;border-radius:30px;padding:8px 14px;margin:4px;display:inline-block;}}
  .comment{{border:1px solid #ddd;border-radius:10px;padding:10px;margin-bottom:8px;}}
  .meta{{font-size:12px;color:#777;margin-bottom:4px;}}
</style></head>
<body><div class="container">
<h1>{title}</h1>
<img src="{image_rel_path}" style="width:100%;border-radius:12px;">
<p>{desc_html}</p>
<div>
<span class="chip">👍 Likes: <b>{likes}</b></span>
<span class="chip">📌 Bookmarks: <b>{bookmarks}</b></span>
<span class="chip">🔁 Shares: <b>{shares}</b></span>
<span class="chip">💬 Comments: <b>{comments}</b></span>
</div>
<h2>Comments ({comments})</h2>
{"".join(f'<div class="comment"><div class="meta">{t}</div><div>{u}: {c}</div></div>' for t,u,c in comments_render)}
</div></body></html>"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")


# ----------------------------
# 主程序
# ----------------------------
def main():
    out_dir = Path(DEFAULT_OUTPUT_DIR)
    out_dir.mkdir(exist_ok=True)
    cwd = Path.cwd()

    img_src = find_local_image_candidate(cwd)
    img_out = ensure_assets(out_dir, img_src)
    img_rel = os.path.relpath(img_out, out_dir).replace("\\", "/")

    pdf_path = cwd / DEFAULT_COMMENT_PDF
    pool = read_comments_from_pdf(pdf_path)
    if not pool:
        pool = ["Great eco concept!", "Love this design!", "So inspiring!", "Miyazaki vibes!", "Very creative!"]

    access_log = out_dir / "access.log"
    cmts_used = out_dir / "comments_used.txt"

    likes = bookmarks = shares = comments_cnt = 0
    comments_render = []

    print("🌿 实时生成已启动（Ctrl + C 停止）...")
    print("   每隔随机几秒~几分钟生成一条访问记录。")

    try:
        while True:
            ts = datetime.now(CST)
            ip = random_realistic_ipv4()
            ua = random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (Linux; Android 14; Pixel 7) Chrome/124.0.0.0 Mobile Safari/537.36"
            ])
            ref = random.choice(["-", "https://www.xiaohongshu.com/", "https://weibo.com/"])
            tstr = ts.strftime("%d/%b/%Y:%H:%M:%S %z")

            with access_log.open("a", encoding="utf-8") as flog:
                flog.write(f'{ip} - - [{tstr}] "GET {DEFAULT_URL_PATH} HTTP/1.1" 200 5123 "{ref}" "{ua}"\n')

            # 随机行为
            if random.random() < 0.55: likes += 1
            if random.random() < 0.40: bookmarks += 1
            if random.random() < 0.35: shares += 1
            if random.random() < 0.5:
                comments_cnt += 1
                content = random.choice(pool)
                user = random_user_code4()
                human_t = ts.strftime("%Y-%m-%d %H:%M")
                comments_render.append((human_t, user, content))
                with cmts_used.open("a", encoding="utf-8") as fcmts:
                    fcmts.write(f"[{human_t}] {user}: {content}\n")

            build_html(out_dir, DEFAULT_TITLE, DEFAULT_DESC, img_rel,
                       (likes, bookmarks, shares, comments_cnt), comments_render)

            # ⏰ 等待随机时间（几秒~几分钟）
            wait = random.randint(5, 300)  # 5秒到5分钟之间
            print(f"🕒 {ts.strftime('%H:%M:%S')} 生成新访问记录，等待 {wait}s...")
            time.sleep(wait)

    except KeyboardInterrupt:
        print("\n✅ 停止实时生成。")
        print(f"日志文件位置: {access_log.resolve()}")
        print(f"网页输出: {out_dir.resolve()}/index.html")


if __name__ == "__main__":
    main()
