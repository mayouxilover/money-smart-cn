#!/usr/bin/env python3
"""
将 _posts/ 目录下的 Markdown 文章批量转换成 HTML 静态文件
生成：html/*.html + html/index.html + html/style.css
"""

import os
import re
import json
import glob
import urllib.parse
from datetime import datetime, date as date_cls
from html import escape

# ============ 简单 Markdown 转 HTML（不依赖外部库）============
def simple_markdown_to_html(text):
    """简单的 Markdown 转 HTML，支持常用语法"""
    lines = text.split('\n')
    html_lines = []
    in_ul = False
    in_ol = False
    in_table = False
    table_rows = []

    for line in lines:
        # 表格
        if line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(line)
            continue
        else:
            if in_table:
                html_lines.append(convert_table(table_rows))
                table_rows = []
                in_table = False

        # 代码块（保持原样）
        if line.strip().startswith('```'):
            html_lines.append(line)
            continue

        # 标题
        if line.strip().startswith('# '):
            html_lines.append(f'<h2>{line.strip()[2:]}</h2>')
            continue
        if line.strip().startswith('## '):
            html_lines.append(f'<h3>{line.strip()[3:]}</h3>')
            continue
        if line.strip().startswith('### '):
            html_lines.append(f'<h4>{line.strip()[4:]}</h4>')
            continue

        # 分隔线
        if line.strip() == '---':
            html_lines.append('<hr />')
            continue

        # 列表
        if line.strip().startswith('- '):
            if not in_ul:
                html_lines.append('<ul>')
                in_ul = True
            html_lines.append(f'<li>{line.strip()[2:]}</li>')
            continue
        else:
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False

        if re.match(r'^\d+\.\s', line.strip()):
            if not in_ol:
                html_lines.append('<ol>')
                in_ol = True
            content = re.sub(r'^\d+\.\s', '', line.strip())
            html_lines.append(f'<li>{content}</li>')
            continue
        else:
            if in_ol:
                html_lines.append('</ol>')
                in_ol = False

        # 引用
        if line.strip().startswith('> '):
            html_lines.append(f'<blockquote><p>{line.strip()[2:]}</p></blockquote>')
            continue

        # 空行
        if not line.strip():
            continue

        # 普通段落
        html_lines.append(f'<p>{line}</p>')

    # 关闭未关闭的标签
    if in_ul:
        html_lines.append('</ul>')
    if in_ol:
        html_lines.append('</ol>')
    if in_table:
        html_lines.append(convert_table(table_rows))

    return '\n'.join(html_lines)

def convert_table(table_rows):
    """转换 Markdown 表格为 HTML 表格"""
    if not table_rows:
        return ''

    # 跳过分隔行（|---|---|）
    rows = [r for r in table_rows if not re.match(r'^\|[\s\-:|]+\|$', r)]

    if not rows:
        return ''

    html = '<table>\n<thead>\n<tr>\n'
    # 表头
    headers = [c.strip() for c in rows[0].strip('|').split('|')]
    for h in headers:
        html += f'<th>{h}</th>\n'
    html += '</tr>\n</thead>\n<tbody>\n'

    # 表格内容
    for row in rows[1:]:
        cells = [c.strip() for c in row.strip('|').split('|')]
        html += '<tr>\n'
        for cell in cells:
            html += f'<td>{cell}</td>\n'
        html += '</tr>\n'

    html += '</tbody>\n</table>'
    return html

# ============ SEO 辅助函数 ============
def make_schema_breadcrumb(items):
    """生成 BreadcrumbList JSON-LD，items = [("名称", "url"), ...]，最后一项url可为空"""
    elements = []
    for i, (name, url) in enumerate(items, 1):
        if url:
            elements.append({"@type": "ListItem", "position": i, "name": name, "item": url})
        else:
            elements.append({"@type": "ListItem", "position": i, "name": name})
    return json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": elements}, ensure_ascii=False, separators=(',', ':'))

def make_schema_article(title, date_str, description, url, categories):
    """生成 Article JSON-LD"""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "datePublished": date_str,
        "dateModified": date_str,
        "description": description or title,
        "author": {"@type": "Organization", "name": "钱智汇"},
        "publisher": {
            "@type": "Organization",
            "name": "钱智汇",
            "logo": {"@type": "ImageObject", "url": SITE_URL + "/favicon.ico"}
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url}
    }, ensure_ascii=False, separators=(',', ':'))

def make_schema_website():
    """生成 WebSite JSON-LD（首页用）"""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "钱智汇",
        "url": SITE_URL + "/",
        "description": "专注保险测评、理财规划、个人养老。帮你用最少的钱，配最好的保障。",
        "potentialAction": {
            "@type": "SearchAction",
            "target": SITE_URL + "/index.html?s={search_term_string}",
            "query-input": "required name=search_term_string"
        }
    }, ensure_ascii=False, separators=(',', ':'))

def make_schema_collection_page(title, description, url):
    """生成 CollectionPage JSON-LD（分类/标签页用）"""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": url
    }, ensure_ascii=False, separators=(',', ':'))

def render_breadcrumb_html(depth, items):
    """
    生成面包屑 HTML（纯文字导航）
    items = [("名称", "相对路径url"), ...]，最后一项url=None表示当前页
    depth: 0=根目录, 1=文章目录, 2=分类/标签目录
    """
    prefix = '../' * depth
    parts = []
    for name, url in items:
        if url:
            parts.append(f'<a href="{url}">{escape(name)}</a>')
        else:
            parts.append(f'<span class="breadcrumb-current">{escape(name)}</span>')
    inner = ' <span class="breadcrumb-sep">›</span> '.join(parts)
    return f'<nav class="breadcrumb" aria-label="面包屑导航">位置：{inner}</nav>'

def render_prev_next(prev_article, next_article, depth):
    """生成上一篇/下一篇导航，prev_article/next_article 为 dict 或 None"""
    prefix = '../' * depth
    parts = []
    if prev_article:
        parts.append(f'<a href="{prefix}{prev_article["slug"]}/index.html" rel="prev">← {escape(prev_article["title"])}</a>')
    if next_article:
        parts.append(f'<a href="{prefix}{next_article["slug"]}/index.html" rel="next">{escape(next_article["title"])} →</a>')
    if not parts:
        return ""
    return f'<div class="post-prev-next">{" | ".join(parts)}</div>'

# ============ 配置 ============
OUTPUT_DIR = "html"
POSTS_DIR = "_posts"
SITE_TITLE = "钱智汇 · 保险理财指南"
SITE_URL = "https://mayouxilover.github.io/money-smart-cn"

# ============ 工具函数 ============
def parse_front_matter(text):
    """解析 Jekyll Front Matter（--- 包裹的 YAML）"""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_text = parts[1].strip()
    content = parts[2].strip()
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm, content

def get_slug_from_filename(md_path):
    """从 Markdown 文件名提取 slug（如 2025-01-15-xxx.md → xxx）"""
    basename = os.path.basename(md_path)
    # 去掉 .md 后缀
    name = basename.replace(".md", "")
    # 去掉日期前缀（YYYY-MM-DD-）
    parts = name.split("-", 3)
    if len(parts) >= 4:
        return parts[3]
    return name  # 如果格式不对，返回原始名称

def render_html_article(title, date, categories, tags, description, body_html, slug, prev_article=None, next_article=None):
    """渲染单篇文章的 HTML 页面（含 SEO 优化）"""
    cats = "".join(f'<a href="../category/{c}/index.html">{c}</a>' for c in (categories or []))
    tag_list = ", ".join(f'<a href="../tag/{t}/index.html">{t}</a>' for t in (tags or []))
    datetime_str = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date)[:10]
    page_url = f"{SITE_URL}/{slug}/index.html"
    first_cat = categories[0] if categories else None

    # 面包屑数据
    bc_items_html = [("首页", "../index.html")]
    if first_cat:
        bc_items_html.append((first_cat, f"../category/{first_cat}/index.html"))
    bc_items_html.append((title, None))
    breadcrumb_html = render_breadcrumb_html(1, bc_items_html)

    # JSON-LD BreadcrumbList
    bc_items_schema = [("首页", SITE_URL + "/")]
    if first_cat:
        bc_items_schema.append((first_cat, SITE_URL + f"/category/{first_cat}/"))
    bc_items_schema.append((title, page_url))
    json_ld_breadcrumb = f'<script type="application/ld+json">{make_schema_breadcrumb(bc_items_schema)}</script>'

    # JSON-LD Article
    json_ld_article = f'<script type="application/ld+json">{make_schema_article(title, datetime_str, description, page_url, categories)}</script>'

    # 上一篇/下一篇
    prev_next_html = render_prev_next(prev_article, next_article, 1)

    # Open Graph + Twitter Card
    og_tags = f'''
    <meta property="og:title" content="{escape(title)}">
    <meta property="og:description" content="{escape(description or title)}">
    <meta property="og:url" content="{page_url}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="钱智汇">
    <meta property="og:locale" content="zh_CN">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape(title)}">
    <meta name="twitter:description" content="{escape(description or title)}">'''

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)} | 钱智汇</title>
  <meta name="description" content="{escape(description or title)}">
  <link rel="stylesheet" href="../style.css">
  <link rel="canonical" href="{page_url}">
  {og_tags}
  {json_ld_article}
  {json_ld_breadcrumb}
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="../index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 · 选对不选贵</p>
      {render_nav(1)}
    </div>
  </header>

  <main class="container">
    {breadcrumb_html}
    <article class="post">
      <header class="post-header">
        <h2 class="post-title">{escape(title)}</h2>
        <div class="post-meta">
          <time datetime="{datetime_str}">{datetime_str}</time>
          {" · 分类: " + cats if cats else ""}
        </div>
        {f'<p class="post-description">{escape(description)}</p>' if description else ''}
      </header>
      <div class="post-content">
        {body_html}
      </div>
      {"<footer class=\"post-footer\"><p>标签: " + tag_list + "</p></footer>" if tag_list else ""}
    </article>
    {prev_next_html}
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>© 2025 钱智汇 · 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="../index.html">首页</a> · <a href="../about.html">关于</a></p>
    </div>
  </footer>
</body>
</html>"""

def render_index(articles):
    """渲染首页文章列表（含 SEO 优化）"""
    items = ""
    for a in articles:
        date_str = a["date"].strftime("%Y-%m-%d") if isinstance(a["date"], datetime) else str(a["date"])[:10]
        items += f"""
      <article class="post-card">
        <time class="post-card-date">{date_str}</time>
        <h3 class="post-card-title"><a href="./{a['slug']}/index.html">{escape(a['title'])}</a></h3>
        <p class="post-card-desc">{escape(a.get('description', ''))}</p>
      </article>"""

    json_ld_website = f'<script type="application/ld+json">{make_schema_website()}</script>'

    og_tags = f'''
  <meta property="og:title" content="{SITE_TITLE}">
  <meta property="og:description" content="专注保险测评、理财规划、个人养老。帮你用最少的钱，配最好的保障。">
  <meta property="og:url" content="{SITE_URL}/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="钱智汇">
  <meta property="og:locale" content="zh_CN">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{SITE_TITLE}">
  <meta name="twitter:description" content="专注保险测评、理财规划、个人养老。">'''

    # 面包屑仅首页不需要，但可加结构化数据
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{SITE_TITLE}</title>
  <meta name="description" content="专注保险测评、理财规划、个人养老。帮你用最少的钱，配最好的保障。">
  <link rel="stylesheet" href="./style.css">
  <link rel="canonical" href="{SITE_URL}/">
  {og_tags}
  {json_ld_website}
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="./index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 · 选对不选贵</p>
      {render_nav(0)}
    </div>
  </header>

  <main class="container">
    <section class="posts-list">
      <h2>最新文章</h2>
      {items}
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>© 2025 钱智汇 · 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="./index.html">首页</a> · <a href="./about.html">关于</a></p>
    </div>
  </footer>
</body>
</html>"""

def render_about():
    """渲染关于页面"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>关于本站 | 钱智汇</title>
  <link rel="stylesheet" href="./style.css">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="./index.html">钱智汇</a></h1>
      {render_nav(0)}
    </div>
  </header>
  <main class="container">
    <article>
      <h2>关于钱智汇</h2>
      <p>钱智汇（Money Smart CN）专注于保险测评、理财规划、个人养老规划。</p>
      <p>我们的使命：帮你用最少的钱，配最好的保障。</p>
      <h3>内容领域</h3>
      <ul>
        <li><strong>保险测评</strong>：重疾险、医疗险、寿险、意外险横向对比</li>
        <li><strong>理财规划</strong>：基金定投、银行存款、理财产品排行</li>
        <li><strong>养老规划</strong>：个人养老金、商业养老保险、延迟退休应对</li>
      </ul>
      <h3>联系方式</h3>
      <p>Email: contact@moneysmart.cn</p>
    </article>
  </main>
</body>
</html>"""

def render_category_index(category_name, articles):
    """渲染分类汇总页面（含 SEO 优化）"""
    items = ""
    for a in articles:
        date_str = a["date"].strftime("%Y-%m-%d") if isinstance(a["date"], datetime) else str(a["date"])[:10]
        items += f"""
      <article class="post-card">
        <time class="post-card-date">{date_str}</time>
        <h3 class="post-card-title"><a href="../../{a['slug']}/index.html">{escape(a['title'])}</a></h3>
        <p class="post-card-desc">{escape(a.get('description', ''))}</p>
      </article>"""

    page_url = f"{SITE_URL}/category/{urllib.parse.quote(category_name)}/index.html"
    breadcrumb_html = render_breadcrumb_html(2, [("首页", "../../index.html"), ("分类", None), (category_name, None)])
    json_ld_bc = f'<script type="application/ld+json">{make_schema_breadcrumb([("首页", SITE_URL + "/"), ("分类:" + category_name, page_url)])}</script>'
    json_ld_col = f'<script type="application/ld+json">{make_schema_collection_page("分类：" + category_name, "钱智汇 - " + category_name + "相关文章汇总", page_url)}</script>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>分类：{escape(category_name)} | 钱智汇</title>
  <meta name="description" content="钱智汇 - {escape(category_name)}相关文章汇总">
  <link rel="stylesheet" href="../../style.css">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="分类：{escape(category_name)} | 钱智汇">
  <meta property="og:description" content="钱智汇 - {escape(category_name)}相关文章汇总">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="钱智汇">
  {json_ld_bc}
  {json_ld_col}
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="../../index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 · 选对不选贵</p>
      {render_nav(2)}
    </div>
  </header>

  <main class="container">
    {breadcrumb_html}
    <section class="posts-list">
      <h2>分类：{escape(category_name)}</h2>
      {items}
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>© 2025 钱智汇 · 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="../../index.html">首页</a> · <a href="../../about.html">关于</a></p>
    </div>
  </footer>
</body>
</html>"""

def render_tag_index(tag_name, articles):
    """渲染标签汇总页面（含 SEO 优化）"""
    items = ""
    for a in articles:
        date_str = a["date"].strftime("%Y-%m-%d") if isinstance(a["date"], datetime) else str(a["date"])[:10]
        items += f"""
      <article class="post-card">
        <time class="post-card-date">{date_str}</time>
        <h3 class="post-card-title"><a href="../../{a['slug']}/index.html">{escape(a['title'])}</a></h3>
        <p class="post-card-desc">{escape(a.get('description', ''))}</p>
      </article>"""

    page_url = f"{SITE_URL}/tag/{urllib.parse.quote(tag_name)}/index.html"
    breadcrumb_html = render_breadcrumb_html(2, [("首页", "../../index.html"), ("标签", None), (tag_name, None)])
    json_ld_bc = f'<script type="application/ld+json">{make_schema_breadcrumb([("首页", SITE_URL + "/"), ("标签:" + tag_name, page_url)])}</script>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>标签：{escape(tag_name)} | 钱智汇</title>
  <meta name="description" content="钱智汇 - {escape(tag_name)}相关文章汇总">
  <link rel="stylesheet" href="../../style.css">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="标签：{escape(tag_name)} | 钱智汇">
  <meta property="og:description" content="钱智汇 - {escape(tag_name)}相关文章汇总">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="钱智汇">
  {json_ld_bc}
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="../../index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 · 选对不选贵</p>
      {render_nav(2)}
    </div>
  </header>

  <main class="container">
    {breadcrumb_html}
    <section class="posts-list">
      <h2>标签：{escape(tag_name)}</h2>
      {items}
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>© 2025 钱智汇 · 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="../../index.html">首页</a> · <a href="../../about.html">关于</a></p>
    </div>
  </footer>
</body>
</html>"""


def render_nav(depth):
    """渲染页眉导航，depth=相对路径深度（0=根目录，1=文章目录，2=分类/标签目录）"""
    prefix = '../' * depth  # depth=0 -> '', depth=1 -> '../', depth=2 -> '../../'
    return f'''      <nav class="site-nav">
        <a href="{prefix}index.html">首页</a>
        <a href="{prefix}category/保险测评/index.html">保险测评</a>
        <a href="{prefix}category/投资理财/index.html">投资理财</a>
        <a href="{prefix}category/投保攻略/index.html">投保攻略</a>
        <a href="{prefix}category/理财规划/index.html">理财规划</a>
        <a href="{prefix}about.html">关于</a>
      </nav>'''

def render_css():
    """渲染全局 CSS 样式"""
    return """/* 钱智汇 · 全局样式 */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --primary: #1a3a6e;
  --primary-dark: #0d2345;
  --accent: #d4a017;
  --accent-light: #fdf3d0;
  --bg: #ffffff;
  --bg-warm: #f8f9fa;
  --text: #1f2937;
  --text-light: #6b7280;
  --border: #e5e7eb;
  --radius: 8px;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--text);
  background: var(--bg-warm);
  line-height: 1.8;
  font-size: 16px;
}
.container { max-width: 720px; margin: 0 auto; padding: 0 20px; }

/* Header */
.site-header {
  background: var(--primary);
  color: #fff;
  padding: 24px 0 16px;
  margin-bottom: 32px;
}
.site-title { font-size: 28px; font-weight: 700; }
.site-title a { color: #fff; text-decoration: none; }
.site-subtitle { font-size: 14px; opacity: 0.85; margin-top: 4px; }
.site-nav { margin-top: 12px; }
.site-nav a {
  color: rgba(255,255,255,0.9);
  text-decoration: none;
  margin-right: 20px;
  font-size: 14px;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: border-color 0.2s;
}
.site-nav a:hover { border-bottom-color: var(--accent); }

/* Posts List */
.posts-list h2 {
  font-size: 20px;
  margin-bottom: 20px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent);
}
.post-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 16px;
  transition: box-shadow 0.2s;
}
.post-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.post-card-date { font-size: 13px; color: var(--text-light); }
.post-card-title { font-size: 18px; margin: 6px 0 8px; }
.post-card-title a { color: var(--text); text-decoration: none; }
.post-card-title a:hover { color: var(--accent); }
.post-card-desc { font-size: 14px; color: var(--text-light); line-height: 1.6; }

/* Single Post */
.post-header { margin-bottom: 28px; }
.post-title { font-size: 26px; line-height: 1.4; margin-bottom: 8px; }
.post-meta { font-size: 14px; color: var(--text-light); margin-bottom: 12px; }
.post-meta a { color: var(--accent); text-decoration: none; }
.post-description { font-size: 15px; color: var(--text-light); font-style: italic; }
.post-content h2 { font-size: 22px; margin: 32px 0 14px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
.post-content h3 { font-size: 18px; margin: 24px 0 10px; }
.post-content p { margin-bottom: 16px; }
.post-content ul, .post-content ol { margin: 0 0 16px 24px; }
.post-content li { margin-bottom: 6px; }
.post-content table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
.post-content th, .post-content td { border: 1px solid var(--border); padding: 10px 12px; text-align: left; }
.post-content th { background: var(--bg-warm); font-weight: 600; }
.post-content blockquote {
  border-left: 4px solid var(--accent);
  background: var(--bg-warm);
  padding: 12px 16px;
  margin: 16px 0;
  color: var(--text-light);
}
.post-content code {
  background: var(--bg-warm);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14px;
}
.post-footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 14px; color: var(--text-light); }
.post-nav { margin: 24px 0; }
.post-nav a { color: var(--accent); text-decoration: none; font-size: 15px; }

/* Breadcrumb */
.breadcrumb {
  font-size: 13px;
  color: var(--text-light);
  margin: -16px 0 20px;
  padding: 8px 12px;
  background: var(--bg-warm);
  border-radius: var(--radius);
  border: 1px solid var(--border);
}
.breadcrumb a { color: var(--accent); text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb-sep { margin: 0 4px; color: var(--border); }
.breadcrumb-current { color: var(--text); }

/* Prev / Next Navigation */
.post-prev-next {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 32px 0 16px;
  padding: 16px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
}
.post-prev-next a {
  color: var(--accent);
  text-decoration: none;
  flex: 1;
  line-height: 1.5;
}
.post-prev-next a:hover { text-decoration: underline; }
.post-prev-next a[rel="next"] { text-align: right; }

/* Footer */
.site-footer {
  background: #0d1a2e;
  color: rgba(255,255,255,0.8);
  padding: 24px 0;
  margin-top: 64px;
  font-size: 14px;
  text-align: center;
}
.site-footer a { color: rgba(255,255,255,0.9); }

/* Responsive */
@media (max-width: 600px) {
  .site-title { font-size: 22px; }
  .post-title { font-size: 22px; }
  .container { padding: 0 16px; }
}
"""

# ============ 主流程 ============
def generate_sitemap(articles, categories_map, tags_map):
    """生成 sitemap.xml（含 lastmod / changefreq / priority）"""
    from datetime import datetime as dt
    now_str = dt.now().strftime("%Y-%m-%d")
    urls = []

    def add_url(loc, lastmod, changefreq, priority):
       urls.append(f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>{changefreq}</changefreq>\n    <priority>{priority}</priority>\n  </url>")

    # 首页
    add_url(SITE_URL + "/", now_str, "daily", "1.0")
    # 关于页
    add_url(SITE_URL + "/about.html", now_str, "monthly", "0.5")

    # 文章页
    for art in articles:
        d = art["date"]
        ds = d.strftime("%Y-%m-%d") if isinstance(d, dt) else str(d)[:10]
        loc = SITE_URL + "/" + art["slug"] + "/index.html"
        add_url(loc, ds, "monthly", "0.8")

    # 分类页
    for cat_name in categories_map:
        loc = SITE_URL + "/category/" + urllib.parse.quote(cat_name) + "/index.html"
        add_url(loc, now_str, "weekly", "0.6")

    # 标签页
    for tag_name in tags_map:
        loc = SITE_URL + "/tag/" + urllib.parse.quote(tag_name) + "/index.html"
        add_url(loc, now_str, "weekly", "0.4")

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 收集所有文章
    md_files = sorted(glob.glob(os.path.join(POSTS_DIR, "*.md")))
    articles = []

    for md_path in md_files:
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()

        fm, content = parse_front_matter(text)
        title = fm.get("title", os.path.basename(md_path))
        date_str = fm.get("date", "2025-01-01")[:10]
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            date = datetime(2025, 1, 1)
        categories = [c.strip() for c in fm.get("categories", "").strip("[]").split(",") if c.strip()]
        tags = [t.strip() for t in fm.get("tags", "").strip("[]").split(",") if t.strip()]
        description = fm.get("description", "")
        slug = get_slug_from_filename(md_path)

        body_html = simple_markdown_to_html(content)

        articles.append({
            "title": title,
            "slug": slug,
            "date": date,
            "date_str": date_str,
            "categories": categories,
            "tags": tags,
            "description": description,
            "body_html": body_html,
            "fm": fm,
        })

    # 按日期排序（新的在前）
    articles.sort(key=lambda x: x["date"], reverse=True)

    # 生成单篇文章 HTML（带上一篇/下一篇）
    print("[文章] 开始生成文章页...")
    for i, art in enumerate(articles):
        prev_art = articles[i + 1] if i + 1 < len(articles) else None
        next_art = articles[i - 1] if i - 1 >= 0 else None

        out_dir = os.path.join(OUTPUT_DIR, art["slug"])
        os.makedirs(out_dir, exist_ok=True)
        html_path = os.path.join(out_dir, "index.html")
        html_content = render_html_article(
            art["title"], art["date"], art["categories"], art["tags"],
            art["description"], art["body_html"], art["slug"],
            prev_article=prev_art, next_article=next_art
        )
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  [OK] {art['slug']}/index.html")

    # 生成首页（含 JSON-LD WebSite）
    index_html = render_index(articles)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("[OK] 已生成: index.html")

    # 生成关于页（含面包屑）
    about_html = render_about()
    with open(os.path.join(OUTPUT_DIR, "about.html"), "w", encoding="utf-8") as f:
        f.write(about_html)
    print("[OK] 已生成: about.html")

    # 生成 CSS
    css = render_css()
    with open(os.path.join(OUTPUT_DIR, "style.css"), "w", encoding="utf-8") as f:
        f.write(css)
    print("[OK] 已生成: style.css")

    # 生成分类汇总页面
    print("\n[分类页面] 开始生成分类汇总页面...")
    categories_map = {}
    for article in articles:
        for cat in article.get("categories", []):
            categories_map.setdefault(cat, []).append(article)

    for cat_name, cat_articles in categories_map.items():
        cat_dir = os.path.join(OUTPUT_DIR, "category", cat_name)
        os.makedirs(cat_dir, exist_ok=True)
        cat_html = render_category_index(cat_name, cat_articles)
        cat_path = os.path.join(cat_dir, "index.html")
        with open(cat_path, "w", encoding="utf-8") as f:
            f.write(cat_html)
        print(f"  [OK] category/{cat_name}/index.html")

    # 生成标签汇总页面
    print("\n[标签页面] 开始生成标签汇总页面...")
    tags_map = {}
    for article in articles:
        for tag in article.get("tags", []):
            tags_map.setdefault(tag, []).append(article)

    for tag_name, tag_articles in tags_map.items():
        tag_dir = os.path.join(OUTPUT_DIR, "tag", tag_name)
        os.makedirs(tag_dir, exist_ok=True)
        tag_html = render_tag_index(tag_name, tag_articles)
        tag_path = os.path.join(tag_dir, "index.html")
        with open(tag_path, "w", encoding="utf-8") as f:
            f.write(tag_html)
        print(f"  [OK] tag/{tag_name}/index.html")

    # 生成 sitemap.xml
    print("\n[Sitemap] 生成 sitemap.xml...")
    sitemap = generate_sitemap(articles, categories_map, tags_map)
    with open(os.path.join(OUTPUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)
    print("  [OK] sitemap.xml")

    # 生成 robots.txt
    robots_txt = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    with open(os.path.join(OUTPUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots_txt)
    print("  [OK] robots.txt")

    print(f"\n[ALL DONE] 共生成 {len(articles)} 篇文章 + {len(categories_map)} 个分类页 + {len(tags_map)} 个标签页")
    print(f"[DIR] 输出目录: ./{OUTPUT_DIR}/")
    print(f"[NEXT] 推送 html/ 内容到 GitHub 即可上线")

if __name__ == "__main__":
    main()
