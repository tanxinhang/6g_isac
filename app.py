#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISAC 文献综述 Web 可视化平台
"""

from flask import Flask, jsonify, render_template, request
import json
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = Flask(__name__)
DATA_DIR = Path(__file__).parent / "data"

# ============================================================================
# 常量
# ============================================================================

CATEGORY_LABELS = {
    "Waveform_Design": "波形设计",
    "Beamforming_and_Precoding": "波束赋形与预编码",
    "Resource_Allocation": "资源分配",
    "Channel_Estimation_and_CSI": "信道估计与CSI获取",
    "Machine_Learning_for_ISAC": "机器学习驱动的ISAC",
    "RIS_Metasurface_ISAC": "RIS/智能超表面ISAC",
    "Security_and_Privacy": "安全与隐私",
    "Localization_and_Tracking": "定位与跟踪",
    "Full_Duplex_and_NOMA_ISAC": "全双工与NOMA-ISAC",
    "Standardization_and_Architecture": "标准化与系统架构",
}

INNOVATION_LABELS = {
    "novel_approach": "全新方法",
    "theoretical_contribution": "理论贡献",
    "unified_framework": "统一框架",
    "integration": "融合整合",
    "extension": "扩展延伸",
    "incremental_improvement": "增量改进",
    "benchmark_study": "基准研究",
    "survey_or_review": "综述/调研",
}

CATEGORY_COLORS = [
    "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
    "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc", "#48b8d0",
]

CONFIDENCE_COLORS = {"high": "#91cc75", "medium": "#fac858", "low": "#ee6666"}


# ============================================================================
# 数据加载
# ============================================================================

def load_cards():
    cards = []
    path = DATA_DIR / "paper_cards.jsonl"
    if not path.exists():
        print(f"[WARN] 数据文件不存在: {path}")
        return cards
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    cards.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    print(f"[INFO] 已加载 {len(cards)} 条论文卡片")
    return cards


# 预加载
cards_data = load_cards()


def compute_overview():
    n = len(cards_data)
    categories_count = Counter(c.get("best_fit_category", "未分类") for c in cards_data)
    confidence_count = Counter(c.get("confidence_level", "low") for c in cards_data)
    innovation_count = Counter(c.get("innovation_type", "未分类") for c in cards_data)

    dates = [c.get("published_date", "") for c in cards_data if c.get("published_date")]
    dates.sort()

    monthly = defaultdict(int)
    for d in dates:
        monthly[d[:7]] += 1

    avg_completeness = sum(
        sum(1 for k in ["problem","key_idea","method","dataset_or_scenario","metrics",
                         "results_summary","innovation_type","limitations","best_fit_category",
                         "confidence_level"]
            if c.get(k) and c.get(k) != "[未能从摘要中提取]")
        / 10.0 for c in cards_data
    ) / max(n, 1) * 100

    return {
        "total_papers": n,
        "categories_count": len([v for v in categories_count.values() if v > 0]),
        "date_range": f"{dates[0]} ~ {dates[-1]}" if dates else "N/A",
        "avg_completeness": round(avg_completeness, 1),
        "high_confidence": confidence_count.get("high", 0),
        "medium_confidence": confidence_count.get("medium", 0),
        "low_confidence": confidence_count.get("low", 0),
        "categories": dict(categories_count.most_common()),
        "innovation": dict(innovation_count.most_common()),
        "monthly": dict(sorted(monthly.items())),
    }


def compute_category_stats():
    result = {}
    for cat_key, cat_label in CATEGORY_LABELS.items():
        cat_cards = [c for c in cards_data if c.get("best_fit_category") == cat_key]
        if not cat_cards:
            continue
        innovation = Counter(c.get("innovation_type", "未分类") for c in cat_cards)
        confidence = Counter(c.get("confidence_level", "low") for c in cat_cards)
        result[cat_label] = {
            "key": cat_key,
            "count": len(cat_cards),
            "innovation": {INNOVATION_LABELS.get(k, k): v for k, v in innovation.most_common()},
            "confidence": dict(confidence),
            "top_papers": sorted(
                cat_cards,
                key=lambda c: (
                    (2 if c.get("confidence_level") == "high" else 1 if c.get("confidence_level") == "medium" else 0),
                    sum(1 for k in ["problem","key_idea","method","dataset_or_scenario","metrics",
                                     "results_summary","innovation_type","limitations","best_fit_category",
                                     "confidence_level"]
                        if c.get(k) and c.get(k) != "[未能从摘要中提取]")
                ),
                reverse=True
            )[:5],
        }
    return result


def detect_trend_keywords():
    all_abstracts = " ".join(c.get("abstract_raw", "") for c in cards_data).lower()
    keywords = [
        "near-field", "cell-free", "transformer", "diffusion model",
        "semantic communication", "foundation model", "digital twin",
        "federated learning", "reinforcement learning", "deep learning",
        "generative ai", "large language model", "quantum", "terahertz",
        "orthogonal time frequency", "otfs", "non-terrestrial", "uav",
        "reconfigurable intelligent", "star-ris", "intelligent omni-surface",
        "multi-functional", "joint communication", "coexistence",
        "beamforming", "mimo", "waveform", "optimization",
        "energy efficiency", "security", "privacy", "localization",
        "channel estimation", "resource allocation", "noma", "full duplex",
        "compressed sensing", "sparse", "hybrid", "analog beamforming",
        "mmwave", "sub-terahertz", "6g", "beyond 5g", "next generation",
        "network slicing", "edge computing", "edge intelligence",
        "explainable", "interpretable", "robust", "scalable",
    ]
    result = {}
    for kw in keywords:
        count = all_abstracts.count(kw)
        if count > 0:
            result[kw] = count
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True)[:30])


def compute_category_timeline():
    timeline = defaultdict(lambda: defaultdict(int))
    for c in cards_data:
        date = c.get("published_date", "")
        if date and len(date) >= 7:
            month = date[:7]
            cat = CATEGORY_LABELS.get(c.get("best_fit_category", ""), "其他")
            timeline[month][cat] += 1
    return dict(sorted(timeline.items()))


def sort_cards(cards, sort_by, sort_order):
    if sort_by == "date":
        return sorted(cards, key=lambda c: c.get("published_date", ""), reverse=sort_order == "desc")
    elif sort_by == "title":
        return sorted(cards, key=lambda c: c.get("title", "").lower(), reverse=sort_order == "desc")
    elif sort_by == "confidence":
        order = {"high": 3, "medium": 2, "low": 1}
        return sorted(cards, key=lambda c: order.get(c.get("confidence_level", "low"), 0), reverse=sort_order == "desc")
    elif sort_by == "category":
        return sorted(cards, key=lambda c: CATEGORY_LABELS.get(c.get("best_fit_category", ""), "其他"), reverse=sort_order == "desc")
    return cards


# ============================================================================
# API 路由
# ============================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/overview")
def api_overview():
    return jsonify(compute_overview())


@app.route("/api/cards")
def api_cards():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort_by = request.args.get("sort_by", "date")
    sort_order = request.args.get("sort_order", "desc")
    search = request.args.get("search", "").strip().lower()
    category = request.args.get("category", "").strip()
    confidence = request.args.get("confidence", "").strip()
    innovation = request.args.get("innovation", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    filtered = list(cards_data)

    if search:
        filtered = [
            c for c in filtered
            if search in c.get("title", "").lower()
            or search in c.get("abstract_raw", "").lower()
            or search in c.get("key_idea", "").lower()
            or search in c.get("method", "").lower()
            or any(search in a.lower() for a in c.get("authors", []))
        ]
    if category:
        filtered = [c for c in filtered if c.get("best_fit_category") == category]
    if confidence:
        filtered = [c for c in filtered if c.get("confidence_level") == confidence]
    if innovation:
        filtered = [c for c in filtered if c.get("innovation_type") == innovation]
    if date_from:
        filtered = [c for c in filtered if c.get("published_date", "") >= date_from]
    if date_to:
        filtered = [c for c in filtered if c.get("published_date", "") <= date_to]

    filtered = sort_cards(filtered, sort_by, sort_order)

    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    paged = filtered[start:end]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "data": paged,
    })


@app.route("/api/cards/<arxiv_id>")
def api_card_detail(arxiv_id):
    for c in cards_data:
        if c.get("arxiv_id") == arxiv_id:
            return jsonify(c)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/categories")
def api_categories():
    return jsonify(compute_category_stats())


@app.route("/api/trends")
def api_trends():
    return jsonify({
        "keywords": detect_trend_keywords(),
        "category_timeline": compute_category_timeline(),
    })


@app.route("/api/filters")
def api_filters():
    """返回前端筛选器可选项"""
    cats = list(set(c.get("best_fit_category", "") for c in cards_data if c.get("best_fit_category")))
    cats = [{"value": c, "label": CATEGORY_LABELS.get(c, c)} for c in sorted(cats)]
    innos = list(set(c.get("innovation_type", "") for c in cards_data if c.get("innovation_type")))
    innos = [{"value": i, "label": INNOVATION_LABELS.get(i, i)} for i in sorted(innos)]
    confs = [{"value": c, "label": c} for c in ["high", "medium", "low"]]
    return jsonify({"categories": cats, "innovations": innos, "confidences": confs})


# ============================================================================
# 启动
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ISAC 文献综述 Web 可视化平台")
    print("  面向 6G 的通信感知一体化")
    print("=" * 60)
    print(f"  论文数量: {len(cards_data)}")
    print(f"  访问地址: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
