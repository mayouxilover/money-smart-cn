# 钱智汇 (Money Smart CN) — 项目长期记忆

## 项目概况
- 名称：钱智汇 · 保险理财指南
- 域名：`https://mayouxilover.github.io`（仓库：mayouxilover/mayouxilover.github.io）
- 旧域名：`https://mayouxilover.github.io/money-smart-cn`（仓库：mayouxilover/money-smart-cn，保持同步）
- 变现方式：Google AdSense（ca-pub-3698112179300810）
- 审核状态：正在准备（2026-06-06）

## 技术架构
- 静态 HTML 生成：Python 脚本 `convert_md_to_html.py`
- Markdown 源文件：`_posts/` 目录
- HTML 输出：`html/` 目录（本地）→ 根目录（GitHub Pages）
- GitHub Pages：使用 `.nojekyll` 禁用 Jekyll 处理
- 构建命令：`python convert_md_to_html.py`
- 部署：手动 cp html/* → 根目录 → git push 到两个仓库

## 关键配置文件
- `convert_md_to_html.py`：唯一的内容生成脚本
  - `SITE_URL` = `"https://mayouxilover.github.io"`
  - `POSTS_DIR` = `"_posts"`
  - `OUTPUT_DIR` = `"html"`
- `_config.yml`：Jekyll 主题配置（已不生效，因 .nojekyll）
- `.nojekyll`：禁用 Jekyll，提供纯静态文件

## 关键集成
- Google AdSense：`ca-pub-3698112179300810`（脚本 + meta 双标签）
- Google CMP：GDPR 消息已发布（同意+管理选项）
- Consent Mode v2：全站嵌入，在 AdSense 脚本之前
- 联系邮箱：mayouxilover@gmail.com
- Google Search Console：已验证

## 文章格式规范
- Markdown frontmatter：layout, title, date, categories, tags, description
- 文章结构：摘要 → 3-5个章节（##标题+正文） → FAQ → 免责声明
- 每篇文章含4-5个SEO标签

## 当前内容规模
- 40 篇原创文章
- 44 个分类页面
- 202 个标签页面
- 5 个静态页面：index, about, privacy, contact, terms
