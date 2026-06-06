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

def make_schema_organization():
    """生成 Organization JSON-LD（首页与 Article publisher 共用）"""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "钱智汇",
        "url": SITE_URL + "/",
        "description": "专注保险测评、理财规划、个人养老。帮你用最少的钱，配最好的保障。",
        "logo": SITE_URL + "/favicon.ico",
        "sameAs": []
    }, ensure_ascii=False, separators=(',', ':'))

def make_schema_faq(faq_pairs, page_url):
    """生成 FAQPage JSON-LD，faq_pairs = [(question, answer), ...]"""
    if not faq_pairs:
        return ""
    main_entity = []
    for q, a in faq_pairs:
        main_entity.append({
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": a
            }
        })
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": main_entity
    }, ensure_ascii=False, separators=(',', ':'))

def extract_faq_pairs(md_content):
    """从 Markdown 正文中提取 FAQ 问答对，返回 [(q, a), ...]"""
    pairs = []
    # 找 FAQ 章节
    faq_match = re.search(r'^#{2,3}\s*(?:FAQ|常见问题)', md_content, re.MULTILINE)
    if not faq_match:
        return pairs

    faq_section = md_content[faq_match.start():]
    # 匹配 Q/A 对：**Q：...** 跟 A：...
    qa_blocks = re.findall(
        r'\*\*Q[：:](.*?)\*\*\s*\n\s*A[：:](.*?)(?=\n\s*\*\*Q[：:]|\n\s*---|\Z)',
        faq_section, re.DOTALL
    )

    for q, a in qa_blocks:
        q_clean = re.sub(r'[*_]+', '', q).strip()
        a_clean = re.sub(r'[*_]+', '', a).strip()
        a_clean = re.sub(r'\n+', ' ', a_clean)
        if q_clean and a_clean:
            pairs.append((q_clean, a_clean))

    return pairs

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

def render_html_article(title, date, categories, tags, description, body_html, slug, prev_article=None, next_article=None, faq_pairs=None):
    """渲染单篇文章的 HTML 页面（含 SEO 优化：Article + FAQPage + BreadcrumbList）"""
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

    # JSON-LD FAQPage（仅当有 FAQ 内容时）
    json_ld_faq = ""
    if faq_pairs:
        faq_schema = make_schema_faq(faq_pairs, page_url)
        if faq_schema:
            json_ld_faq = f'<script type="application/ld+json">{faq_schema}</script>'

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
  {json_ld_faq}
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
      <p><a href="../index.html">首页</a> - <a href="../about.html">关于</a> - <a href="../privacy">隐私政策</a> - <a href="../contact">联系我们</a> - <a href="../terms">服务条款</a></p>
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
    json_ld_org = f'<script type="application/ld+json">{make_schema_organization()}</script>'

    og_tags = f'''
  <meta property="og:title" content="{SITE_TITLE}">
  <meta property="og:description" content="专注保险测评、理财规划、个人养老。帮你用最少的钱，配最好的保障。">
  <meta property="og:url" content="{SITE_URL}/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="钱智汇">
  <meta property="og:locale" content="zh_CN">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{SITE_TITLE}">
  <meta name="twitter:description" content="专注保险测评、理财规划、个人养老。">
  <meta name="google-site-verification" content="googleff27169294274065">'''

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
  {json_ld_org}
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
      <p><a href="./index.html">首页</a> - <a href="./about.html">关于</a> - <a href="./privacy">隐私政策</a> - <a href="./contact">联系我们</a> - <a href="./terms">服务条款</a></p>
    </div>
  </footer>
</body>
</html>"""

def render_about():
    """渲染关于页面"""
    page_url = SITE_URL + "/about.html"
    json_ld_org = f'<script type="application/ld+json">{make_schema_organization()}</script>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>关于钱智汇 | 保险理财指南</title>
  <meta name="description" content="了解钱智汇的使命、内容标准和联系方式。钱智汇专注保险测评、理财规划、个人养老。">
  <link rel="stylesheet" href="./style.css">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="关于钱智汇 | 保险理财指南">
  <meta property="og:description" content="了解钱智汇的使命、内容标准和联系方式。">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="钱智汇">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="关于钱智汇">
  <meta name="twitter:description" content="了解钱智汇的使命、内容标准和联系方式。">
  {json_ld_org}
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="./index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 - 选对不选贵</p>
      {render_nav(0)}
    </div>
  </header>
  <main class="container">
    <article>
      <h2>关于钱智汇</h2>
      <p>钱智汇(Money Smart CN)是一个独立的保险与理财内容指南网站，致力于帮助普通家庭用最少的钱，配最好的保障。</p>
      <h3>我们的使命</h3>
      <p>保险和理财产品种类繁多、条款复杂，普通人很难判断哪款真正适合自己。钱智汇通过客观测评、横向对比和通俗易懂的解读，让读者能够独立做出明智的财务决策。</p>
      <h3>内容领域</h3>
      <ul>
        <li><strong>保险测评</strong>：重疾险、医疗险、寿险、意外险横向对比，不偏袒任何一家保险公司</li>
        <li><strong>理财规划</strong>：基金定投、银行存款、理财产品排行，兼顾收益与风险</li>
        <li><strong>养老规划</strong>：个人养老金、商业养老保险、延迟退休应对方案</li>
        <li><strong>投保攻略</strong>：核保技巧、理赔流程、受益人指定、保单管理</li>
      </ul>
      <h3>编辑准则</h3>
      <ul>
        <li>所有测评均基于公开条款和产品说明书，不接受保险公司投稿或付费推荐</li>
        <li>文章中如出现 affiliate 链接，会明确标注"推广"，不影响测评结论</li>
        <li>医疗与法律相关内容仅供参考，不构成专业建议，请务必咨询持牌专业人士</li>
        <li>如发现内容有误，请联系我们，我们会及时更正并注明更新日期</li>
      </ul>
      <h3>网站所有者</h3>
      <p>钱智汇由独立内容团队运营，联系邮箱：mayouxilover@gmail.com</p>
      <h3>免责声明</h3>
      <p>本站所有内容仅供参考，不构成保险、理财、投资建议。购买保险产品或做出财务决策前，请咨询持牌专业人士。因依赖本站内容而产生的任何损失，本站概不负责。</p>
    </article>
  </main>
  <footer class="site-footer">
    <div class="container">
      <p>&copy; 2025 钱智汇 - 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="./index.html">首页</a> - <a href="./about.html">关于</a> - <a href="./privacy">隐私政策</a> - <a href="./contact">联系我们</a> - <a href="./terms">服务条款</a></p>
    </div>
  </footer>
</body>
</html>"""

def render_privacy_policy():
    """渲染隐私政策页面"""
    page_url = SITE_URL + "/privacy"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>隐私政策 | 钱智汇</title>
  <meta name="description" content="钱智汇隐私政策：我们如何收集、使用和保护您的个人信息。">
  <link rel="stylesheet" href="./style.css">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="隐私政策 | 钱智汇">
  <meta property="og:description" content="钱智汇隐私政策">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="./index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 - 选对不选贵</p>
      {render_nav(0)}
    </div>
  </header>
  <main class="container">
    <article>
      <h2>隐私政策</h2>
      <p><strong>生效日期：2025年1月1日</strong></p>
      <h3>1. 信息收集</h3>
      <p>当您访问钱智汇时，我们可能通过以下方式收集信息：</p>
      <ul>
        <li><strong>自动收集</strong>：IP地址、浏览器类型、访问时间、访问页面</li>
        <li><strong>广告服务</strong>：Google AdSense 可能通过 Cookie 收集您的信息，用于展示相关广告</li>
        <li><strong>主动提供</strong>：当您通过邮件联系我们时，我们会收到您提供的邮箱地址</li>
      </ul>
      <h3>2. Cookie 使用</h3>
      <p>本网站使用 Cookie 用于：Google AdSense 广告投放和效果衡量、基础访问统计。</p>
      <p>您可以通过浏览器设置拒绝 Cookie，但可能导致部分功能无法正常使用。</p>
      <h3>3. 广告服务(Google AdSense)</h3>
      <p>本网站使用 Google AdSense 展示广告。Google 可能使用 Cookie 向用户展示基于兴趣的广告。您可以通过 <a href="https://adssettings.google.com" target="_blank" rel="noopener">Google 广告设置</a> 管理您的广告偏好。</p>
      <h3>4. 信息共享</h3>
      <p>我们不会出售、出租或交换您的个人信息。仅在法律要求时披露信息。</p>
      <h3>5. 数据安全</h3>
      <p>我们采取合理的技术措施保护您的信息安全。但请注意，互联网传输无法保证100%安全。</p>
      <h3>6. 第三方链接</h3>
      <p>本网站可能包含指向第三方网站的链接。这些网站有独立的隐私政策，我们对其内容和安全不承担责任。</p>
      <h3>7. 儿童隐私</h3>
      <p>本网站不面向13岁以下儿童，我们不会故意收集儿童的个人信息。</p>
      <h3>8. 政策更新</h3>
      <p>本隐私政策可能不时更新，更新后的版本将发布在本页面。</p>
      <h3>9. 联系我们</h3>
      <p>如有任何关于本隐私政策的问题，请通过 <a href="./contact">联系我们</a> 页面与我们联系。</p>
    </article>
  </main>
  <footer class="site-footer">
    <div class="container">
      <p>&copy; 2025 钱智汇 - 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="./index.html">首页</a> - <a href="./about.html">关于</a> - <a href="./privacy">隐私政策</a> - <a href="./contact">联系我们</a> - <a href="./terms">服务条款</a></p>
    </div>
  </footer>
</body>
</html>"""


def render_contact():
    """渲染联系我们页面"""
    page_url = SITE_URL + "/contact"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>联系我们 | 钱智汇</title>
  <meta name="description" content="钱智汇联系方式：邮箱、内容纠错、广告合作。">
  <link rel="stylesheet" href="./style.css">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="联系我们 | 钱智汇">
  <meta property="og:description" content="钱智汇联系方式">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="./index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 - 选对不选贵</p>
      {render_nav(0)}
    </div>
  </header>
  <main class="container">
    <article>
      <h2>联系我们</h2>
      <p>如果您对网站内容有疑问、发现错误、或有合作建议，欢迎通过以下方式联系我们。</p>
      <h3>电子邮箱</h3>
      <p>商务合作与内容反馈：<strong>mayouxilover@gmail.com</strong></p>
      <p>我们会在3个工作日内回复您的邮件。</p>
      <h3>内容纠错</h3>
      <p>如果您发现文章中有事实错误、过时信息或表述不当，请邮件告知，我们会核实后及时更正，并在文章末尾注明更新记录。</p>
      <h3>广告合作</h3>
      <p>本网站使用 Google AdSense 自动投放广告。如需广告合作，请直接联系 Google AdSense 团队。我们不参与广告内容的审核或干预。</p>
      <h3>社交媒体</h3>
      <p>暂无官方社交媒体账号。所有以钱智汇名义运营的社媒账号均与本站无关，请注意甄别。</p>
    </article>
  </main>
  <footer class="site-footer">
    <div class="container">
      <p>&copy; 2025 钱智汇 - 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="./index.html">首页</a> - <a href="./about.html">关于</a> - <a href="./privacy">隐私政策</a> - <a href="./contact">联系我们</a> - <a href="./terms">服务条款</a></p>
    </div>
  </footer>
</body>
</html>"""


def render_terms():
    """渲染服务条款页面"""
    page_url = SITE_URL + "/terms"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>服务条款 | 钱智汇</title>
  <meta name="description" content="钱智汇服务条款：使用本网站即表示您同意以下条款。">
  <link rel="stylesheet" href="./style.css">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="服务条款 | 钱智汇">
  <meta property="og:description" content="钱智汇服务条款">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="./index.html">钱智汇</a></h1>
      <p class="site-subtitle">保险理财指南 - 选对不选贵</p>
      {render_nav(0)}
    </div>
  </header>
  <main class="container">
    <article>
      <h2>服务条款</h2>
      <p><strong>生效日期：2025年1月1日</strong></p>
      <h3>1. 接受条款</h3>
      <p>访问和使用钱智汇网站，即表示您同意遵守本服务条款。如不同意，请立即停止使用本网站。</p>
      <h3>2. 网站内容</h3>
      <p>本网站所有内容仅供参考，不构成保险、理财、投资、法律或税务建议。在做出任何财务决策前，请咨询持牌专业人士。</p>
      <h3>3. 知识产权</h3>
      <p>本网站原创内容的知识产权归钱智汇所有，未经书面许可，不得转载、复制或用于商业用途。</p>
      <h3>4. 用户行为</h3>
      <p>您在使用本网站时，不得：上传或传播病毒、尝试未经授权访问本网站服务器、通过自动化工具大量抓取本网站内容。</p>
      <h3>5. 广告与联盟链接</h3>
      <p>本网站使用 Google AdSense 展示第三方广告，可能包含 affiliate 链接。点击广告或 affiliate 链接后，您将被引导至第三方网站，这些网站的内容和服务由第三方负责。</p>
      <h3>6. 免责声明</h3>
      <p>本网站按原样提供，不提供任何明示或暗示的担保。我们不对因使用本网站内容而产生的任何直接或间接损失负责。</p>
      <h3>7. 条款修改</h3>
      <p>我们保留随时修改本服务条款的权利。修改后的条款将发布在本页面。</p>
      <h3>8. 适用法律</h3>
      <p>本服务条款适用中华人民共和国法律。如因本条款产生争议，双方应友好协商；协商不成的，任何一方可向本站运营方所在地人民法院提起诉讼。</p>
      <h3>9. 联系我们</h3>
      <p>如有关于本服务条款的疑问，请通过 <a href="./contact">联系我们</a> 页面与我们联系。</p>
    </article>
  </main>
  <footer class="site-footer">
    <div class="container">
      <p>&copy; 2025 钱智汇 - 保险理财指南 | 本站内容仅供参考，不构成投资建议</p>
      <p><a href="./index.html">首页</a> - <a href="./about.html">关于</a> - <a href="./privacy">隐私政策</a> - <a href="./contact">联系我们</a> - <a href="./terms">服务条款</a></p>
    </div>
  </footer>
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
      <p><a href="../../index.html">首页</a> - <a href="../../about.html">关于</a> - <a href="../../privacy">隐私政策</a> - <a href="../../contact">联系我们</a> - <a href="../../terms">服务条款</a></p>
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
      <p><a href="../../index.html">首页</a> - <a href="../../about.html">关于</a> - <a href="../../privacy">隐私政策</a> - <a href="../../contact">联系我们</a> - <a href="../../terms">服务条款</a></p>
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
        <a href="{prefix}contact">联系</a>
        <a href="{prefix}privacy">隐私政策</a>
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
    # 静态页面
    add_url(SITE_URL + "/privacy", now_str, "monthly", "0.5")
    add_url(SITE_URL + "/contact", now_str, "monthly", "0.5")
    add_url(SITE_URL + "/terms",  now_str, "monthly", "0.5")

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
            "raw_content": text,
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
        faq_pairs = extract_faq_pairs(art["raw_content"])
        html_content = render_html_article(
            art["title"], art["date"], art["categories"], art["tags"],
            art["description"], art["body_html"], art["slug"],
            prev_article=prev_art, next_article=next_art,
            faq_pairs=faq_pairs
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

    # 生成 隐私政策页
    privacy_html = render_privacy_policy()
    with open(os.path.join(OUTPUT_DIR, "privacy.html"), "w", encoding="utf-8") as f:
        f.write(privacy_html)
    print("[OK] 已生成: privacy.html")

    # 生成 联系我们页
    contact_html = render_contact()
    with open(os.path.join(OUTPUT_DIR, "contact.html"), "w", encoding="utf-8") as f:
        f.write(contact_html)
    print("[OK] 已生成: contact.html")

    # 生成 服务条款页
    terms_html = render_terms()
    with open(os.path.join(OUTPUT_DIR, "terms.html"), "w", encoding="utf-8") as f:
        f.write(terms_html)
    print("[OK] 已生成: terms.html")

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
