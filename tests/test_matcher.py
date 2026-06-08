"""测试核心匹配引擎"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cashflow_tool.matcher import CFMatcher
from cashflow_tool.models import CFRecord, MatchedPair


def test_exact_match():
    """两条金额相同的记录，公司对匹配"""
    matcher = CFMatcher()
    pays = [
        CFRecord(company='A公司', counterparty='B公司', cf_full='CI1.02.04.01 支付其他',
                 amount=10000, voucher_no='P001', direction='付款', source='计量'),
    ]
    recvs = [
        CFRecord(company='B公司', counterparty='A公司', cf_full='CI1.01.03.01 收到其他',
                 amount=10000, voucher_no='R001', direction='收款', source='中安'),
    ]

    result = matcher.match(pays, recvs)
    assert len(result.matched) == 1
    assert result.matched[0].match_type == '精确匹配'
    assert result.matched[0].payer == 'A公司'
    assert result.matched[0].receiver == 'B公司'
    assert len(result.unmatched_pay) == 0
    assert len(result.unmatched_recv) == 0


def test_no_match_different_amount():
    """金额不同不匹配"""
    matcher = CFMatcher()
    pays = [CFRecord(company='A', counterparty='B', cf_full='CI1.02.04.01 支付',
                     amount=10000, voucher_no='P1', direction='付款', source='A')]
    recvs = [CFRecord(company='B', counterparty='A', cf_full='CI1.01.03.01 收到',
                      amount=9999, voucher_no='R1', direction='收款', source='B')]
    result = matcher.match(pays, recvs)
    assert len(result.matched) == 0
    assert len(result.unmatched_pay) == 1
    assert len(result.unmatched_recv) == 1


def test_dedup_with_prematched():
    """曼哈格已配对的不会被重复匹配"""
    matcher = CFMatcher()
    prematched = [MatchedPair(pay_voucher='', payer='A公司', pay_cf='', pay_amount=5000,
                              recv_voucher='', receiver='B公司', recv_cf='', recv_amount=5000,
                              match_type='曼哈格')]
    pays = [CFRecord(company='A公司', counterparty='B公司', cf_full='',
                     amount=5000, voucher_no='', direction='付款', source='计量')]
    recvs = [CFRecord(company='B公司', counterparty='A公司', cf_full='',
                      amount=5000, voucher_no='', direction='收款', source='中安')]
    result = matcher.match(pays, recvs, prematched)
    assert len(result.matched) == 1  # 只有曼哈格那对


def test_aggregate_match():
    """多条小额合并匹配"""
    matcher = CFMatcher()
    pays = [
        CFRecord(company='A', counterparty='B', cf_full='', amount=3000,
                 voucher_no='P1', direction='付款', source='A'),
        CFRecord(company='A', counterparty='B', cf_full='', amount=2000,
                 voucher_no='P2', direction='付款', source='A'),
    ]
    recvs = [
        CFRecord(company='B', counterparty='A', cf_full='', amount=5000,
                 voucher_no='R1', direction='收款', source='B'),
    ]
    result = matcher.match(pays, recvs)
    assert len(result.matched) == 1
    assert result.matched[0].match_type == '聚合匹配'
