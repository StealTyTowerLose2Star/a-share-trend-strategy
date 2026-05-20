#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大盘市场状态分析模块

基于多重指标评估 A 股整体市场状态，输出趋势仓位建议。
用于趋势策略系统的顶层仓位决策——"当下应该用几成仓"。

分析维度 (综合评分 0-100):
  1. 指数趋势 (40%) — 三大指数均线排列 + 斜率
  2. 指数位置 (20%) — 指数相对于 MA20/MA60 的位置
  3. 市场情绪 (20%) — 涨跌家数比、涨停跌停比
  4. 成交量 (20%) — 全市场量能 vs 均量

数据源: AKShare (免费)
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


# ─── 市场状态定义 ────────────────────────────────────────────────

MARKET_STATES = {
    "strong_bull": {
        "name": "强势牛市",
        "icon": "🚀",
        "desc": "指数多头排列，量价齐升，赚钱效应极强",
        "position_range": (80, 100),  # 趋势仓位使用比例 (%)
    },
    "bull": {
        "name": "牛市",
        "icon": "📈",
        "desc": "指数趋势向上，市场活跃，主线清晰",
        "position_range": (65, 80),
    },
    "mild_bull": {
        "name": "震荡偏多",
        "icon": "↗️",
        "desc": "指数震荡上行，局部机会，适合精选个股",
        "position_range": (45, 65),
    },
    "ranging": {
        "name": "震荡市",
        "icon": "➡️",
        "desc": "指数横盘整理，方向不明，控制仓位",
        "position_range": (25, 45),
    },
    "mild_bear": {
        "name": "震荡偏空",
        "icon": "↘️",
        "desc": "指数重心下移，宜轻仓防守",
        "position_range": (10, 25),
    },
    "bear": {
        "name": "熊市",
        "icon": "📉",
        "desc": "指数空头排列，普跌行情，空仓为主",
        "position_range": (0, 10),
    },
    "crisis": {
        "name": "危机模式",
        "icon": "⚠️",
        "desc": "市场恐慌，系统性风险，空仓观望",
        "position_range": (0, 5),
    },
}

# 仓位映射详细表 (供报告使用)
POSITION_MAP = [
    (90, "强烈重仓",   "全仓出击，顺势加仓"),
    (75, "重仓",       "积极做多，精选主线"),
    (55, "中等偏重",   "谨慎做多，控制单票仓位"),
    (35, "中等",       "平衡仓位，高抛低吸"),
    (20, "轻仓",       "防守为主，快进快出"),
    (8,  "极轻仓",     "多看少动，只做超跌反弹"),
    (3,  "空仓观望",   "空仓等待，现金为王"),
]


class MarketStateAnalyzer:
    """
    大盘市场状态分析器

    用法:
        analyzer = MarketStateAnalyzer()
        result = analyzer.analyze()
        print(result['market_state_name'], result['position_ratio'])
    """

    # 三大指数代码
    INDEX_CODES = {
        "上证指数": "sh000001",
        "深证成指": "sz399001",
        "创业板指": "sz399006",
    }

    # 指数权重 (用于综合评分)
    INDEX_WEIGHTS = {
        "上证指数": 0.40,
        "深证成指": 0.35,
        "创业板指": 0.25,
    }

    def __init__(self):
        self.index_data: Dict[str, pd.DataFrame] = {}
        self.cache = {}

    # ─── 数据获取 ──────────────────────────────────────────────

    def _get_index_data(self, code: str, days: int = 120) -> Optional[pd.DataFrame]:
        """获取指数历史数据"""
        try:
            df = ak.stock_zh_index_daily_tx(symbol=code)
            if df is None or len(df) == 0:
                return None

            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'amount': 'amount',
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            # 取最近 days 天
            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)

            return df
        except Exception:
            return None

    def _load_index_data(self):
        """加载所有指数数据"""
        for name, code in self.INDEX_CODES.items():
            df = self._get_index_data(code)
            if df is not None:
                self.index_data[name] = df

    def _get_limit_up_down(self, date_str: Optional[str] = None) -> Dict:
        """获取涨停/跌停数据 (含降级)"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")

        result = {"limit_up": None, "limit_down": None, "up_count": 0, "down_count": 0}

        # 涨停池
        try:
            zt = ak.stock_zt_pool_em(date=date_str)
            if zt is not None and len(zt) > 0:
                result["limit_up"] = len(zt)
                result["up_count"] = len(zt)
        except Exception:
            pass

        # 跌停池
        try:
            dt = ak.stock_zt_pool_dtgc_em(date=date_str)
            if dt is not None and len(dt) > 0:
                result["limit_down"] = len(dt)
                result["down_count"] = len(dt)
        except Exception:
            pass

        return result

    def _get_market_breadth(self) -> Dict:
        """获取市场涨跌宽度 (涨跌家数) — 可选，失败不影响主流程"""
        result = {"up": None, "down": None, "total": None}
        try:
            spot = ak.stock_individual_spot_em()
            if spot is not None and len(spot) > 0:
                up = len(spot[spot['涨跌幅'] > 0])
                down = len(spot[spot['涨跌幅'] < 0])
                result["up"] = up
                result["down"] = down
                result["total"] = len(spot)
        except Exception:
            pass
        return result

    # ─── 指标计算 ──────────────────────────────────────────────

    @staticmethod
    def _calc_ma(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """计算均线"""
        if periods is None:
            periods = [5, 10, 20, 60]
        df = df.copy()
        for p in periods:
            df[f'ma{p}'] = df['close'].rolling(p).mean()
        return df

    @staticmethod
    def _calc_index_trend_score(df: pd.DataFrame) -> Dict:
        """
        计算单指数的趋势评分 (0-100)

        指标:
        - 均线排列 (50分): MA5>MA10>MA20>MA60=50, 逐级递减
        - MA20 斜率 (25分): 斜率越大分越高
        - 价格位置 (25分): 收盘在MA20上方得分
        """
        if df is None or len(df) < 60:
            return {"score": 0, "aligned": False, "slope": 0, "above_ma20": False,
                    "above_ma60": False, "ma_alignment_score": 0, "current_price": 0}

        df = MarketStateAnalyzer._calc_ma(df)
        latest = df.iloc[-1]

        price = latest['close']
        ma5 = latest.get('ma5', price)
        ma10 = latest.get('ma10', price)
        ma20 = latest.get('ma20', price)
        ma60 = latest.get('ma60', price)

        # ── 1. 均线排列评分 (50分) ──
        alignment_score = 0
        if ma5 > ma10:
            alignment_score += 12.5
        if ma10 > ma20:
            alignment_score += 12.5
        if ma20 > ma60:
            alignment_score += 12.5
        if ma5 > ma60:
            alignment_score += 12.5

        # 完美多头加分
        if ma5 > ma10 > ma20 > ma60:
            alignment_score = 50

        aligned = ma5 > ma10 > ma20 > ma60
        partially_aligned = ma20 > ma60

        # ── 2. MA20 斜率评分 (25分) ──
        if len(df) >= 25:
            ma20_current = df['ma20'].iloc[-1]
            ma20_5ago = df['ma20'].iloc[-5] if len(df) >= 5 else ma20_current
            ma20_20ago = df['ma20'].iloc[-20] if len(df) >= 20 else ma20_current

            slope_short = (ma20_current - ma20_5ago) / ma20_20ago * 100 if ma20_20ago > 0 else 0
            slope_score = min(25, max(0, slope_short * 10))
        else:
            slope_short = 0
            slope_score = 12.5  # 数据不足给中值

        # ── 3. 价格位置评分 (25分) ──
        price_score = 0
        above_ma20 = price > ma20
        above_ma60 = price > ma60

        if above_ma20 and above_ma60:
            # 在两条均线上方，乖离越大分越高，但过大要扣分 (过热)
            dist_ma20 = (price - ma20) / ma20 * 100
            if dist_ma20 > 15:
                price_score = 15  # 乖离过大，过热
            else:
                price_score = 25
        elif above_ma20 and not above_ma60:
            price_score = 15  # 站上20日线但未站上60日线
        elif not above_ma20 and above_ma60:
            price_score = 10  # 跌破20日线但在60日线上方
        else:
            # 全线下方
            dist_below = (ma60 - price) / ma60 * 100 if ma60 > 0 else 0
            if dist_below < 5:
                price_score = 5   # 在60日线附近
            else:
                price_score = 0   # 深度破位

        # 综合
        total = alignment_score + slope_score + price_score

        return {
            "score": round(total, 1),
            "aligned": aligned,
            "partially_aligned": partially_aligned,
            "slope": round(slope_short, 4),
            "above_ma20": above_ma20,
            "above_ma60": above_ma60,
            "ma_alignment_score": alignment_score,
            "slope_score": slope_score,
            "position_score": price_score,
            "current_price": round(float(price), 2),
            "ma5": round(float(ma5), 2),
            "ma10": round(float(ma10), 2),
            "ma20": round(float(ma20), 2),
            "ma60": round(float(ma60), 2),
        }

    def _calc_sentiment_score(self) -> Dict:
        """
        计算市场情绪评分 (0-100)

        基于涨停/跌停数据。
        如果数据不可用，使用指数近期的涨跌表现做降级。
        """
        # 方法1: 涨停跌停比
        limit_data = self._get_limit_up_down()
        up = limit_data.get("up_count", 0) or 0
        down = limit_data.get("down_count", 0) or 0

        if up > 0 or down > 0:
            # 涨停跌停比 -> 评分
            if down == 0:
                ratio = 10 + up  # 无跌停时，涨停越多越好
            else:
                ratio = up / down

            if ratio >= 5:
                sentiment = 90
            elif ratio >= 3:
                sentiment = 75
            elif ratio >= 1.5:
                sentiment = 60
            elif ratio >= 0.8:
                sentiment = 45
            elif ratio >= 0.3:
                sentiment = 25
            else:
                sentiment = 10

            return {
                "score": sentiment,
                "method": "limit_up_down",
                "limit_up": up,
                "limit_down": down,
                "ratio": round(ratio, 2),
            }

        # 方法2 (降级): 使用指数近期涨跌幅
        sh_data = self.index_data.get("上证指数")
        if sh_data is not None and len(sh_data) >= 20:
            recent = sh_data.tail(10)
            pct_changes = recent['close'].pct_change().dropna()
            positive_days = len(pct_changes[pct_changes > 0])
            ratio = positive_days / len(pct_changes)

            sentiment = ratio * 100  # 0-100

            return {
                "score": round(sentiment, 1),
                "method": "index_pct_fallback",
                "positive_days": positive_days,
                "total_days": len(pct_changes),
                "ratio": round(ratio, 2),
            }

        # 完全无数据
        return {"score": 50, "method": "unknown", "ratio": 1.0}

    def _calc_volume_score(self) -> Dict:
        """
        计算成交量评分 (0-100)
        """
        total_current = 0
        total_avg = 0

        for name in self.INDEX_CODES:
            df = self.index_data.get(name)
            if df is not None and len(df) >= 25:
                current = df.iloc[-1]['amount']
                avg_20 = df['amount'].tail(20).mean()
                # 不同指数量级不同，用比例加权
                if current > 0 and avg_20 > 0:
                    weight = self.INDEX_WEIGHTS.get(name, 0.33)
                    total_current += current * weight
                    total_avg += avg_20 * weight

        if total_avg == 0:
            return {"score": 50, "ratio": 1.0, "method": "unknown"}

        ratio = total_current / total_avg

        # 评分
        if ratio >= 2.0:
            score = 100  # 爆量
        elif ratio >= 1.5:
            score = 85   # 显著放量
        elif ratio >= 1.2:
            score = 70   # 温和放量
        elif ratio >= 0.8:
            score = 50   # 正常量能
        elif ratio >= 0.5:
            score = 30   # 缩量
        else:
            score = 10   # 极度缩量

        return {
            "score": score,
            "ratio": round(ratio, 2),
            "method": "index_volume",
        }

    # ─── 综合评估 ──────────────────────────────────────────────

    def analyze(self) -> Dict:
        """
        执行完整的市场状态分析

        Returns:
            dict: 包含所有分析结果
        """
        # 1. 加载数据
        self._load_index_data()

        if not self.index_data:
            return {
                "status": "error",
                "error": "无法获取指数数据，请检查网络或 AKShare",
                "market_state": "unknown",
                "market_state_name": "未知",
                "position_ratio": 50,  # 默认半仓
                "position_label": "未知（数据不可用，建议半仓）",
                "score": 50,
            }

        # 2. 各指数趋势评分
        index_scores = {}
        for name in self.INDEX_CODES:
            df = self.index_data.get(name)
            if df is not None:
                index_scores[name] = self._calc_index_trend_score(df)

        # 3. 综合指数趋势评分 (40%)
        trend_score = 0
        for name, weight in self.INDEX_WEIGHTS.items():
            if name in index_scores:
                trend_score += index_scores[name]["score"] * weight

        # 4. 指数位置评分 (20%)
        position_score = 0
        for name, weight in self.INDEX_WEIGHTS.items():
            if name in index_scores:
                ps = index_scores[name].get("position_score", 0)
                position_score += ps * weight

        # 5. 情绪评分 (20%)
        sentiment_result = self._calc_sentiment_score()
        sentiment_score = sentiment_result["score"]

        # 6. 成交量评分 (20%)
        volume_result = self._calc_volume_score()
        volume_score = volume_result["score"]

        # 7. 综合评分
        total_score = (
            trend_score * 0.40
            + position_score * 0.20
            + sentiment_score * 0.20
            + volume_score * 0.20
        )

        # 8. 映射到市场状态
        market_state, position_range = self._score_to_state(total_score)
        position_ratio = self._suggest_position(total_score, position_range)

        # 9. 构建详细结果
        detail = {
            "status": "ok",
            "analyze_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_date": self._get_latest_data_date(),

            # 综合
            "total_score": round(total_score, 1),
            "market_state": market_state,
            "market_state_name": MARKET_STATES[market_state]["name"],
            "market_state_icon": MARKET_STATES[market_state]["icon"],
            "market_state_desc": MARKET_STATES[market_state]["desc"],

            # 仓位建议 (趋势策略占80%总仓的百分比)
            "position_ratio": position_ratio,
            "position_label": self._get_position_label(position_ratio),
            "position_range": position_range,

            # 实际仓位计算（占整体资金）
            "actual_total_position_pct": round(position_ratio * 0.80, 1),
            "position_explanation": self._build_position_explanation(
                market_state, position_ratio
            ),

            # 各维度评分
            "dimensions": {
                "index_trend": {
                    "score": round(trend_score, 1),
                    "weight": "40%",
                    "detail": index_scores,
                },
                "index_position": {
                    "score": round(position_score, 1),
                    "weight": "20%",
                },
                "sentiment": {
                    "score": round(sentiment_score, 1),
                    "weight": "20%",
                    "detail": sentiment_result,
                },
                "volume": {
                    "score": round(volume_score, 1),
                    "weight": "20%",
                    "detail": volume_result,
                },
            },

            # 操作建议
            "advice": self._generate_advice(market_state, position_ratio, trend_score, sentiment_score),
        }

        return detail

    def _get_latest_data_date(self) -> str:
        """获取最新数据日期"""
        for df in self.index_data.values():
            if df is not None and len(df) > 0:
                return str(df.iloc[-1]['date'].strftime('%Y-%m-%d'))
        return "未知"

    @staticmethod
    def _score_to_state(score: float) -> Tuple[str, Tuple[int, int]]:
        """综合评分映射到市场状态"""
        if score >= 80:
            return "strong_bull", MARKET_STATES["strong_bull"]["position_range"]
        elif score >= 65:
            return "bull", MARKET_STATES["bull"]["position_range"]
        elif score >= 50:
            return "mild_bull", MARKET_STATES["mild_bull"]["position_range"]
        elif score >= 35:
            return "ranging", MARKET_STATES["ranging"]["position_range"]
        elif score >= 20:
            return "mild_bear", MARKET_STATES["mild_bear"]["position_range"]
        elif score >= 10:
            return "bear", MARKET_STATES["bear"]["position_range"]
        else:
            return "crisis", MARKET_STATES["crisis"]["position_range"]

    @staticmethod
    def _suggest_position(score: float, pos_range: Tuple[int, int]) -> int:
        """在仓位范围内给出建议值"""
        low, high = pos_range
        # 在范围内按评分线性插值
        ratio = score / 100.0
        position = low + (high - low) * ratio
        return round(position)

    @staticmethod
    def _get_position_label(position: int) -> str:
        """仓位数字 -> 文字描述"""
        for threshold, label, _ in POSITION_MAP:
            if position >= threshold:
                return label
        return "空仓"

    @staticmethod
    def _build_position_explanation(state: str, position: int) -> str:
        """仓位建议的详细说明"""
        if state == "crisis":
            return f"市场处于危机模式，建议趋势仓位使用 {position}%（占整体资金 {position*0.8:.1f}%），现金为王，等待系统性风险释放"
        elif state == "bear":
            return f"熊市行情，建议趋势仓位使用 {position}%（占整体资金 {position*0.8:.1f}%），仅做超跌反弹或保持空仓"
        elif state == "mild_bear":
            return f"市场偏弱，建议趋势仓位使用 {position}%（占整体资金 {position*0.8:.1f}%），轻仓防守，快进快出"
        elif state == "ranging":
            return f"震荡行情，建议趋势仓位使用 {position}%（占整体资金 {position*0.8:.1f}%），精选个股，高抛低吸"
        elif state == "mild_bull":
            return f"震荡偏多，建议趋势仓位使用 {position}%（占整体资金 {position*0.8:.1f}%），适度参与，做好风控"
        elif state == "bull":
            return f"牛市行情，建议趋势仓位使用 {position}%（占整体资金 {position*0.8:.1f}%），积极做多，持有主线"
        elif state == "strong_bull":
            return f"强势牛市！建议趋势仓位使用 {position}%（占整体资金 {position*0.8:.1f}%），全力做多，顺势加仓"

    @staticmethod
    def _generate_advice(state: str, position: int, trend_score: float, sentiment_score: float) -> str:
        """生成操作建议"""
        lines = []

        # 总体建议
        if position >= 65:
            lines.append("🟢 市场环境良好，可积极操作")
        elif position >= 35:
            lines.append("🟡 市场中性，精选个股，控制仓位")
        elif position >= 10:
            lines.append("🟠 市场偏弱，以防守为主")
        else:
            lines.append("🔴 市场风险高，建议空仓观望")

        # 趋势建议
        if trend_score >= 60:
            lines.append("📊 指数趋势向上，顺势而为")
        elif trend_score >= 30:
            lines.append("📊 指数趋势不明，等待方向确认")
        else:
            lines.append("📊 指数趋势向下，不宜重仓")

        # 情绪建议
        if sentiment_score >= 60:
            lines.append("🔥 市场情绪积极，赚钱效应较好")
        elif sentiment_score >= 35:
            lines.append("😐 市场情绪中性，分化明显")
        else:
            lines.append("❄️ 市场情绪低迷，注意风险")

        # 综合
        lines.append(f"💡 建议趋势策略仓位: {position}%（占整体资金 {position*0.8:.1f}%）")

        return "\n".join(lines)


# ─── 便捷函数 ──────────────────────────────────────────────────

def assess_market() -> Dict:
    """快速评估市场状态的便捷入口"""
    analyzer = MarketStateAnalyzer()
    return analyzer.analyze()


def get_position_advice() -> str:
    """快速获取仓位建议的文本"""
    result = assess_market()
    if result.get("status") == "error":
        return f"⚠️ {result.get('error')}"

    icon = result["market_state_icon"]
    state = result["market_state_name"]
    score = result["total_score"]
    pos = result["position_ratio"]
    advice = result["advice"]

    return (
        f"{icon} 当前市场状态: {state} (综合评分 {score}分)\n"
        f"  建议趋势仓位: {pos}%\n"
        f"  占整体资金: {result['actual_total_position_pct']}%\n"
        f"\n{advice}"
    )


def format_report(result: Optional[Dict] = None) -> str:
    """
    生成格式化的市场状态报告

    Args:
        result: analyze() 的输出，为 None 时自动运行

    Returns:
        str: 格式化的报告文本
    """
    if result is None:
        result = assess_market()

    if result.get("status") == "error":
        return f"⚠️ 市场状态分析失败: {result.get('error')}"

    lines = []
    lines.append("=" * 58)
    lines.append(f"  📊 A 股市场状态与仓位建议")
    lines.append(f"  分析时间: {result['analyze_time']}")
    lines.append(f"  数据日期: {result['data_date']}")
    lines.append("=" * 58)

    # 市场状态
    lines.append("")
    lines.append(f"  {result['market_state_icon']} 市场状态: {result['market_state_name']}")
    lines.append(f"  综合评分: {result['total_score']}/100")
    lines.append(f"  说明: {result['market_state_desc']}")
    lines.append("")

    # 仓位建议
    lines.append(f"  ┌── 仓位建议 ──────────────────────")
    lines.append(f"  │ 趋势策略仓位: {result['position_ratio']}%")
    lines.append(f"  │ (占趋势80%资金的 {result['position_ratio']}%)")
    lines.append(f"  │ 建议仓位水平: {result['position_label']}")
    lines.append(f"  │ 仓位范围: {result['position_range'][0]}%-{result['position_range'][1]}%")
    lines.append(f"  │ 占整体资金: {result['actual_total_position_pct']}%")
    lines.append(f"  └───────────────────────────────────")

    # 各维度评分
    lines.append("")
    lines.append(f"  ┌── 各维度评分 ──────────────────────")
    dims = result["dimensions"]
    lines.append(f"  │ 📐 指数趋势: {dims['index_trend']['score']}/100 (权重{dims['index_trend']['weight']})")
    lines.append(f"  │ 📍 指数位置: {dims['index_position']['score']}/100 (权重{dims['index_position']['weight']})")
    lines.append(f"  │ 🔥 市场情绪: {dims['sentiment']['score']}/100 (权重{dims['sentiment']['weight']})")
    lines.append(f"  │ 💰 成交量能: {dims['volume']['score']}/100 (权重{dims['volume']['weight']})")
    lines.append(f"  └───────────────────────────────────")

    # 详细指数数据
    lines.append("")
    lines.append(f"  ┌── 指数详情 ──────────────────────")
    for name, detail in dims['index_trend']['detail'].items():
        status = "✅" if detail.get('aligned') else ("🟡" if detail.get('partially_aligned') else "❌")
        lines.append(f"  │ {name} {status}")
        lines.append(f"  │   MA: {detail.get('ma5',0)} → {detail.get('ma10',0)} → {detail.get('ma20',0)} → {detail.get('ma60',0)}")
        lines.append(f"  │   趋势评分: {detail['score']} | 斜率: {detail.get('slope',0):.4f}")
        lines.append(f"  │   收盘: {detail['current_price']} | 在MA20{'上' if detail.get('above_ma20') else '下'} | 在MA60{'上' if detail.get('above_ma60') else '下'}")
    lines.append(f"  └───────────────────────────────────")

    # 操作建议
    lines.append("")
    lines.append(f"  ┌── 操作建议 ──────────────────────")
    for line in result["advice"].split("\n"):
        lines.append(f"  │ {line}")
    lines.append(f"  └───────────────────────────────────")
    lines.append("")
    lines.append("=" * 58)
    lines.append(f"  数据来源: AKShare")
    lines.append(f"  ⚠️ 本建议仅供参考，不构成投资建议")
    lines.append("=" * 58)

    return "\n".join(lines)


# ─── 主入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    print(format_report())
