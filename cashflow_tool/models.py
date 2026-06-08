from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CFRecord:
    """一条现金流明细记录"""
    company: str          # 本企业名称
    counterparty: str     # 对方企业名称（空字符串 = 未识别）
    cf_full: str          # 完整现金流指标，如 "CI1.02.04.01 支付的其他..._内部"
    amount: float         # 金额（正数）
    voucher_no: str       # 凭证号
    direction: str        # "付款" or "收款"
    source: str           # 来源公司简称：计量/中安/曼哈格/博林达


@dataclass
class MatchedPair:
    """一对匹配成功的内部交易"""
    pay_voucher: str      # 付款方凭证号
    payer: str            # 付款方公司名
    pay_cf: str           # 付款方现金流指标
    pay_amount: float     # 付款额
    recv_voucher: str     # 收款方凭证号
    receiver: str         # 收款方公司名
    recv_cf: str          # 收款方现金流指标
    recv_amount: float    # 收款额（正=购销流入，负=代付）
    match_type: str       # "曼哈格" / "精确匹配" / "宽松匹配" / "聚合匹配" / "互付抵消"


@dataclass
class MatchResult:
    """一次处理的完整结果"""
    matched: list[MatchedPair] = field(default_factory=list)
    unmatched_pay: list[CFRecord] = field(default_factory=list)
    unmatched_recv: list[CFRecord] = field(default_factory=list)
