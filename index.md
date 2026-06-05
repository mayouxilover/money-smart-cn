# Welcome to 钱智汇 · 保险理财指南

> 专注保险测评、理财规划、个人养老，帮你用最少的钱，配最好的保障。

---

## 🔥 最新文章

<ul>
{% for post in site.posts limit:10 %}
  <li>
    <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
    <small>（{{ post.date | date: "%Y-%m-%d" }}）</small>
  </li>
{% endfor %}
</ul>

---

## 📂 文章分类

{% for category in site.categories %}
### {{ category[0] }}（{{ category[1].size }}篇）
<ul>
{% for post in category[1] limit:5 %}
  <li><a href="{{ post.url | relative_url }}">{{ post.title }}</a></li>
{% endfor %}
{% if category[1].size > 5 %}
  <li><a href="/categories/{{ category[0] | slugify }}">查看全部{{ category[1].size }}篇 →</a></li>
{% endif %}
</ul>
{% endfor %}

---

## 🏷️ 热门标签

{% assign tags = site.tags | sort %}
{% for tag in tags %}
  <a href="/tags/{{ tag[0] | slugify }}" class="tag">{{ tag[0] }}（{{ tag[1].size }}）</a>
{% endfor %}

---

## 📌 关于本站

钱智汇（Money Smart CN）致力于让保险和理财知识变得通俗易懂。我们用心测评每一款产品，帮你避开营销陷阱，选对不选贵。

- 📧 合作联系：[your-email@example.com]
- 🔗 GitHub：[https://github.com/yourusername/money-smart-cn]

---

<sub>本站内容仅供科普参考，不构成投保或投资建议。购买前请仔细阅读保险条款或咨询专业顾问。</sub>
