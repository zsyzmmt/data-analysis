# -*- coding: utf-8 -*-
"""
Step 3: 可视化
读取 output/tables/*.csv (SQL 分析结果) -> 生成中文图表 output/figures/*.png
图表规范: matplotlib / 中文字体 / 浅色主题
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.bbox"] = "tight"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "output", "figures")
os.makedirs(FIG, exist_ok=True)

# 配色
C_BLUE = "#3572C6"; C_ORANGE = "#F28B30"; C_GREEN = "#4CAF7D"; C_RED = "#D64545"
C_PURPLE = "#8E7CC3"; C_GRAY = "#8C9BAB"; BG = "#FFFFFF"


def load(name):
    return pd.read_csv(os.path.join(TAB, f"{name}.csv"))


def style_ax(ax, title, xlabel="", ylabel=""):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)


# ============================================================
# 模块一: 淘宝用户行为
# ============================================================
def fig_taobao():
    # 1) 漏斗
    f = load("tb_funnel")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    stages, vals = f["漏斗层级"].tolist(), f["用户数"].tolist()
    colors = [C_BLUE, C_PURPLE, C_ORANGE, C_GREEN]
    bars = ax.barh(stages[::-1], vals[::-1], color=colors[::-1], height=0.62)
    base = vals[0]
    for i, v in enumerate(vals[::-1]):
        ax.text(v * 1.01, i, f"{v:,} ({v / base * 100:.1f}%)", va="center", fontsize=10)
    style_ax(ax, "图1  用户行为漏斗（用户级转化率）", "用户数")
    ax.set_xlim(0, max(vals) * 1.25)
    fig.savefig(os.path.join(FIG, "fig_tb_funnel.png"), facecolor=BG); plt.close(fig)

    # 2) 分时段行为
    h = load("tb_hourly")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = h["小时"].astype(int)
    ax.bar(x - 0.2, h["pv量"], width=0.4, color=C_BLUE, label="浏览pv")
    ax.bar(x + 0.2, h["购买量"] * 50, width=0.4, color=C_GREEN, label="购买量(放大50倍显示)")
    ax2 = ax.twinx()
    conv = (h["购买量"] / h["pv量"] * 100).fillna(0)
    ax2.plot(x, conv, color=C_RED, marker="o", lw=2, label="购买转化率(右轴)")
    ax2.set_ylabel("购买转化率 %", fontsize=10)
    style_ax(ax, "图2  分时段浏览/购买分布与转化率", "小时", "行为量")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, frameon=False)
    fig.savefig(os.path.join(FIG, "fig_tb_hourly.png"), facecolor=BG); plt.close(fig)

    # 3) 类目四象限
    c = load("tb_category")
    med_pv, med_cv = c["浏览量"].median(), c["购买转化率pct"].median()
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.scatter(c["浏览量"], c["购买转化率pct"], s=c["购买量"].clip(lower=4) * 1.6,
               alpha=0.55, color=C_BLUE, edgecolors="white", linewidths=0.4)
    ax.axvline(med_pv, color=C_GRAY, linestyle="--", lw=1)
    ax.axhline(med_cv, color=C_GRAY, linestyle="--", lw=1)
    ax.set_xscale("log")
    ax.text(med_pv * 1.15, c["购买转化率pct"].max() * 0.95, "明星类目\n(高流量高转化)", fontsize=9, color=C_GREEN)
    ax.text(med_pv * 1.15, med_cv * 0.35, "流量洼地\n(高转化低流量)", fontsize=9, color=C_ORANGE)
    ax.text(c["浏览量"].min() * 1.1, c["购买转化率pct"].max() * 0.95, "潜力待挖掘", fontsize=9, color=C_GRAY)
    ax.text(c["浏览量"].min() * 1.1, med_cv * 0.35, "低效类目", fontsize=9, color=C_RED)
    style_ax(ax, "图3  类目流量-转化四象限（气泡=购买量, 浏览量对数轴, 样本≥200浏览）",
             "浏览量(log)", "购买转化率 %")
    fig.savefig(os.path.join(FIG, "fig_tb_category.png"), facecolor=BG); plt.close(fig)

    # 4) 购买频次分层
    r = load("tb_repurchase")
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [C_GREEN, C_BLUE, C_ORANGE, C_RED][:len(r)]
    bars = ax.bar(r["购买频次分层"], r["用户数"], color=colors, width=0.55)
    for b, pct in zip(bars, r["占比pct"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.01, f"{pct}%", ha="center", fontsize=10)
    style_ax(ax, "图4  购买用户复购频次分层", "", "用户数")
    fig.savefig(os.path.join(FIG, "fig_tb_repurchase.png"), facecolor=BG); plt.close(fig)

    # 5) 活跃度分层（二八法则）
    a = load("tb_user_activity_tier")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars = ax.bar(a["活跃度分层"], a["行为量占比pct"], color=[C_GRAY, C_BLUE, C_ORANGE, C_RED], width=0.55)
    for b, n, v in zip(bars, a["用户数"], a["行为量占比pct"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.2,
                f"{v}%\n({n:,}人)", ha="center", fontsize=9)
    style_ax(ax, "图5  用户活跃度分层：头部用户贡献的行为量（二八法则验证）", "用户活跃度十分位", "行为量占比 %")
    ax.set_ylim(0, a["行为量占比pct"].max() * 1.3)
    fig.savefig(os.path.join(FIG, "fig_tb_activity.png"), facecolor=BG); plt.close(fig)

    # 6) 每日趋势（若数据覆盖多天）
    d = load("tb_daily")
    if len(d) > 1:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(d["日期"], d["活跃用户数"], color=C_BLUE, marker="o", label="活跃用户数")
        ax.plot(d["日期"], d["pv量"], color=C_ORANGE, marker="s", label="浏览量")
        ax2 = ax.twinx()
        ax2.bar(d["日期"], d["购买转化率pct"], alpha=0.25, color=C_GREEN, label="购买转化率(右轴)")
        ax2.set_ylabel("购买转化率 %", fontsize=10)
        style_ax(ax, "图6  每日活跃与转化趋势", "日期", "用户数/浏览量")
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, frameon=False)
        plt.xticks(rotation=45)
        fig.savefig(os.path.join(FIG, "fig_tb_daily.png"), facecolor=BG); plt.close(fig)


# ============================================================
# 模块二: 香港Airbnb
# ============================================================
def fig_airbnb():
    # 1) 区域供给与均价
    n = load("ab_neighbourhood").head(12)
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(n))
    bars = ax.bar(x, n["房源数"], color=C_BLUE, width=0.6)
    for b, v in zip(bars, n["房源数"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 3, str(v), ha="center", fontsize=8.5)
    ax2 = ax.twinx()
    ax2.plot(x, n["均价"], color=C_RED, marker="D", lw=1.8, label="区域均价")
    ax2.set_ylabel("均价 (HK$/晚)", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(n["区域"], rotation=38, ha="right", fontsize=8.5)
    style_ax(ax, "图6  香港各区域房源供给量与均价", "", "房源数")
    ax2.legend(fontsize=9, frameon=False, loc="upper right")
    fig.savefig(os.path.join(FIG, "fig_ab_neighbourhood.png"), facecolor=BG); plt.close(fig)

    # 2) 房型结构
    rt = load("ab_room_type")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    top = rt[rt["房源数"] / rt["房源数"].sum() > 0.01]
    axes[0].pie(top["房源数"], labels=top["房型"], autopct="%1.1f%%",
                colors=[C_BLUE, C_ORANGE, C_GREEN, C_PURPLE][:len(top)],
                startangle=90, wedgeprops={"width": 0.42, "edgecolor": "white"})
    axes[0].set_title("房型供给占比", fontsize=12, fontweight="bold")
    bars = axes[1].bar(top["房型"], top["均价"], color=[C_BLUE, C_ORANGE, C_GREEN, C_PURPLE][:len(top)], width=0.5)
    for b, v, n_ in zip(bars, top["均价"], top["房源数"]):
        axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() * 1.01, f"${v:,.0f}",
                    ha="center", fontsize=9)
    style_ax(axes[1], "各房型平均定价", "", "均价 (HK$/晚)")
    fig.suptitle("图7  香港Airbnb房型供给结构与定价", fontsize=13, fontweight="bold")
    fig.savefig(os.path.join(FIG, "fig_ab_roomtype.png"), facecolor=BG); plt.close(fig)

    # 3) 定价因素
    pr = load("ab_price_by_rating")
    pv = load("ab_price_by_reviews")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    order1 = ["无评分", "4.0以下", "4.0-4.5", "4.5-4.8", "4.8-5.0"]
    pr["o"] = pr["评分档"].map({k: i for i, k in enumerate(order1)})
    pr = pr.sort_values("o")
    axes[0].bar(pr["评分档"], pr["均价"], color=C_BLUE, width=0.55)
    for i, (v, cnt) in enumerate(zip(pr["均价"], pr["房源数"])):
        axes[0].text(i, v + 15, f"${v:,.0f}\n(n={cnt})", ha="center", fontsize=8.5)
    style_ax(axes[0], "评分档位 vs 均价", "综合评分档", "均价 (HK$/晚)")
    axes[1].bar(pv["评论数档"], pv["均价"], color=C_ORANGE, width=0.55)
    for i, (v, cnt) in enumerate(zip(pv["均价"], pv["房源数"])):
        axes[1].text(i, v + 15, f"${v:,.0f}\n(n={cnt})", ha="center", fontsize=8.5)
    style_ax(axes[1], "评论数档位 vs 均价", "历史评论数档", "均价 (HK$/晚)")
    fig.suptitle("图8  定价影响因素：口碑与房源定价的关系", fontsize=13, fontweight="bold")
    fig.savefig(os.path.join(FIG, "fig_ab_price_factors.png"), facecolor=BG); plt.close(fig)

    # 4) 房东生态
    hs = load("ab_host_scale")
    if len(hs) > 1:
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
        bars = axes[0].bar(hs["房东规模"], hs["房源占比pct"],
                           color=[C_GRAY, C_BLUE, C_ORANGE, C_RED][:len(hs)], width=0.55)
        for b, v, hnum in zip(bars, hs["房源占比pct"], hs["房东数"]):
            axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
                         f"{v}%\n({hnum}位房东)", ha="center", fontsize=8.5)
        style_ax(axes[0], "房东规模 vs 房源供给占比", "", "房源占比 %")
        axes[0].set_ylim(0, hs["房源占比pct"].max() * 1.35)
        bars = axes[1].bar(hs["房东规模"], hs["房均年化收入"], color=C_PURPLE, width=0.55)
        for b, v in zip(bars, hs["房均年化收入"]):
            axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02,
                         f"${v:,.0f}", ha="center", fontsize=8.5)
        style_ax(axes[1], "房东规模 vs 房均年化收入", "", "房均年化收入 (HK$)")
        fig.suptitle("图9  房东生态：供给集中度与经营效率", fontsize=13, fontweight="bold")
        fig.savefig(os.path.join(FIG, "fig_ab_hostscale.png"), facecolor=BG); plt.close(fig)

    # 5) 需求季节性（全年第N月平均评论量）
    s = load("ab_review_month_of_year")
    fig, ax = plt.subplots(figsize=(8.5, 4))
    bars = ax.bar(s["月份"], s["年均月评论量"], color=C_GREEN, width=0.6)
    mx = s["年均月评论量"].max()
    for b, v in zip(bars, s["年均月评论量"]):
        ax.text(b.get_x() + b.get_width() / 2, v + mx * 0.02, f"{v:,.0f}", ha="center", fontsize=8.5)
    style_ax(ax, "图10  香港Airbnb需求季节性（跨年月均评论量, 2019起）", "月份", "月均评论量")
    fig.savefig(os.path.join(FIG, "fig_ab_season.png"), facecolor=BG); plt.close(fig)

    # 6) 超级房东溢价
    sh = load("ab_superhost_premium")
    fig, ax = plt.subplots(figsize=(6.5, 4))
    x = np.arange(len(sh))
    w = 0.35
    ax.bar(x - w / 2, sh["均价"], width=w, color=C_BLUE, label="均价")
    ax.bar(x + w / 2, sh["年化预估收入"], width=w, color=C_ORANGE, label="年化预估收入")
    ax.set_xticks(x)
    ax.set_xticklabels(["普通房东" if not v else "超级房东" for v in sh["超级房东"]])
    style_ax(ax, "图11  超级房东溢价：定价与收入对比", "", "HK$")
    ax.legend(fontsize=9, frameon=False)
    fig.savefig(os.path.join(FIG, "fig_ab_superhost.png"), facecolor=BG); plt.close(fig)


# ============================================================
# 模块三: Yelp + Reddit 舆情
# ============================================================
def fig_text():
    # 1) Yelp评分分布
    y = load("yp_rating_dist")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    bars = axes[0].bar(y["星级"], y["评论数"], color=[C_RED, C_ORANGE, C_GRAY, C_BLUE, C_GREEN], width=0.6)
    for b, v, p in zip(bars, y["评论数"], y["占比pct"]):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{v}\n({p}%)",
                     ha="center", fontsize=9)
    style_ax(axes[0], "Yelp评论星级分布", "星级", "评论数")
    axes[0].set_ylim(0, y["评论数"].max() * 1.25)
    axes[1].plot(y["星级"], y["平均情感得分"], marker="o", color=C_PURPLE, lw=2)
    axes[1].axhline(0, color=C_GRAY, linestyle="--", lw=1)
    style_ax(axes[1], "星级与文本情感得分的关系", "星级", "VADER平均情感得分")
    fig.suptitle("图12  Yelp用户满意度结构（N=1,000条评论）", fontsize=13, fontweight="bold")
    fig.savefig(os.path.join(FIG, "fig_yp_rating.png"), facecolor=BG); plt.close(fig)

    # 2) Reddit情感
    r = load("rd_sentiment_dist")
    lv = load("rd_len_vs_sentiment")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    colors = {"正面": C_GREEN, "中性": C_GRAY, "负面": C_RED}
    bars = axes[0].bar(r["情感标签"], r["评论数"], color=[colors.get(x, C_BLUE) for x in r["情感标签"]], width=0.5)
    for b, v, p in zip(bars, r["评论数"], r["占比pct"]):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() * 1.01, f"{v:,}\n({p}%)",
                     ha="center", fontsize=9)
    style_ax(axes[0], "r/ChatGPT社区评论情感分布(N=49,541)", "", "评论数")
    axes[0].set_ylim(0, r["评论数"].max() * 1.22)
    axes[1].bar(lv["评论长度档"], lv["负面占比pct"], color=C_RED, width=0.55, alpha=0.85)
    for i, v in enumerate(lv["负面占比pct"]):
        axes[1].text(i, v + 0.6, f"{v}%", ha="center", fontsize=9)
    style_ax(axes[1], "评论长度 vs 负面情绪占比", "评论长度档", "负面占比 %")
    axes[1].set_ylim(0, lv["负面占比pct"].max() * 1.25)
    fig.suptitle("图13  Reddit社区舆情温度计（r/ChatGPT）", fontsize=13, fontweight="bold")
    fig.savefig(os.path.join(FIG, "fig_rd_sentiment.png"), facecolor=BG); plt.close(fig)

    # 3) 痛点主题
    p = load("rd_pain_points").sort_values("提及数")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    colors2 = [C_GREEN if "惊艳" in t or "好用" in t else (C_BLUE if "替代" in t or "工作" in t else C_RED)
               for t in p["痛点主题"]]
    bars = ax.barh(p["痛点主题"], p["提及数"], color=colors2, height=0.6)
    for b, v in zip(bars, p["提及数"]):
        ax.text(v + max(p["提及数"]) * 0.01, b.get_y() + b.get_height() / 2, f"{v:,}", va="center", fontsize=9)
    ax.set_title("图14  AI产品用户之声：核心议题提及频次（关键词匹配）",
                 fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.set_xlim(0, max(p["提及数"]) * 1.15)
    fig.savefig(os.path.join(FIG, "fig_rd_painpoints.png"), facecolor=BG); plt.close(fig)

    # 4) Yelp精英 vs 普通
    e = load("yp_elite_vs_normal")
    if len(e) > 1:
        fig, ax = plt.subplots(figsize=(7, 4))
        x = np.arange(len(e))
        w = 0.28
        ax.bar(x - w, e["平均星级"], width=w, color=C_BLUE, label="平均星级")
        ax.bar(x, e["平均词数"] / 100, width=w, color=C_ORANGE, label="平均词数(÷100)")
        ax.bar(x + w, e["平均情感得分"], width=w, color=C_GREEN, label="平均情感得分")
        ax.set_xticks(x)
        ax.set_xticklabels(e["用户类型"])
        style_ax(ax, "图15  Yelp精英用户 vs 普通用户评论特征", "", "指标值")
        ax.legend(fontsize=9, frameon=False)
        fig.savefig(os.path.join(FIG, "fig_yp_elite.png"), facecolor=BG); plt.close(fig)


if __name__ == "__main__":
    fig_taobao()
    fig_airbnb()
    fig_text()
    print("=== 图表生成完成 ===")
    for f in sorted(os.listdir(FIG)):
        print(" -", f)
