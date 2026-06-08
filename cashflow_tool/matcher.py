"""现金流内部抵消匹配引擎

四轮匹配策略：
1. 曼哈格已配对数据直接纳入
2. 精确匹配（公司对+金额四舍五入）
3. 宽松匹配（公司名包含+金额）
4. 聚合匹配（同公司对多条小额合并）
5. 内部互付/互收抵消
"""

from collections import defaultdict
from cashflow_tool.models import CFRecord, MatchedPair, MatchResult
from cashflow_tool.readers.base import CFHelper


class CFMatcher:
    """现金流内部抵消匹配引擎"""

    def __init__(self):
        self._dedup_keys: set[tuple] = set()

    def _dedup_key(self, company: str, cp: str, amount: float) -> tuple:
        return (company.strip(), cp.strip(), round(amount))

    def _build_dedup_set(self, prematched: list[MatchedPair]) -> set[tuple]:
        """从曼哈格已配对数据构建去重集合"""
        keys = set()
        for p in prematched:
            keys.add(self._dedup_key(p.payer, p.receiver, p.pay_amount))
            keys.add(self._dedup_key(p.receiver, p.payer, p.pay_amount))
        return keys

    def _round1_exact(self, pays: list, recvs: list, used_pay: set, used_recv: set,
                      dedup_set: set) -> list[MatchedPair]:
        """第1轮: 精确匹配"""
        matched = []

        pay_idx = sorted(enumerate(pays), key=lambda x: x[1].amount, reverse=True)
        recv_idx = sorted(enumerate(recvs), key=lambda x: x[1].amount, reverse=True)

        for pi, pay in pay_idx:
            if pi in used_pay:
                continue
            for rj, recv in recv_idx:
                if rj in used_recv:
                    continue
                if round(pay.amount) != round(recv.amount):
                    continue

                dk = self._dedup_key(pay.company, recv.company, pay.amount)
                if dk in dedup_set:
                    continue

                pay_cp = pay.counterparty.strip()
                recv_cp = recv.counterparty.strip()

                matched_pair = False
                if pay_cp and pay_cp == recv.company.strip():
                    matched_pair = True
                elif recv_cp and recv_cp == pay.company.strip():
                    matched_pair = True

                if not matched_pair:
                    continue

                used_pay.add(pi)
                used_recv.add(rj)

                same_cf = (CFHelper.extract_cf_code(pay.cf_full)
                           == CFHelper.extract_cf_code(recv.cf_full))
                recv_amount = -recv.amount if same_cf else recv.amount

                matched.append(MatchedPair(
                    pay_voucher=pay.voucher_no, payer=pay.company,
                    pay_cf=pay.cf_full, pay_amount=pay.amount,
                    recv_voucher=recv.voucher_no, receiver=recv.company,
                    recv_cf=recv.cf_full, recv_amount=recv_amount,
                    match_type='精确匹配'
                ))
                break

        return matched

    def _round2_loose(self, pays: list, recvs: list, used_pay: set, used_recv: set,
                      dedup_set: set) -> list[MatchedPair]:
        """第2轮: 宽松匹配"""
        matched = []
        pay_idx = sorted(enumerate(pays), key=lambda x: x[1].amount, reverse=True)
        recv_idx = sorted(enumerate(recvs), key=lambda x: x[1].amount, reverse=True)

        for pi, pay in pay_idx:
            if pi in used_pay:
                continue
            for rj, recv in recv_idx:
                if rj in used_recv:
                    continue
                if round(pay.amount) != round(recv.amount):
                    continue

                dk = self._dedup_key(pay.company, recv.company, pay.amount)
                if dk in dedup_set:
                    continue

                pay_cp = pay.counterparty.strip()
                recv_cp = recv.counterparty.strip()

                matched_pair = False
                if pay_cp and recv.company.strip():
                    if pay_cp in recv.company or recv.company in pay_cp:
                        matched_pair = True
                if not matched_pair and recv_cp and pay.company.strip():
                    if recv_cp in pay.company or pay.company in recv_cp:
                        matched_pair = True
                if not matched_pair:
                    continue

                used_pay.add(pi)
                used_recv.add(rj)
                same_cf = (CFHelper.extract_cf_code(pay.cf_full)
                           == CFHelper.extract_cf_code(recv.cf_full))
                recv_amount = -recv.amount if same_cf else recv.amount

                matched.append(MatchedPair(
                    pay_voucher=pay.voucher_no, payer=pay.company,
                    pay_cf=pay.cf_full, pay_amount=pay.amount,
                    recv_voucher=recv.voucher_no, receiver=recv.company,
                    recv_cf=recv.cf_full, recv_amount=recv_amount,
                    match_type='宽松匹配'
                ))
                break
        return matched

    def _round3_aggregate(self, pays: list, recvs: list, used_pay: set,
                          used_recv: set, dedup_set: set = set()) -> list[MatchedPair]:
        """第3轮: 聚合匹配"""
        matched = []
        pay_groups: dict[tuple, list] = defaultdict(list)
        recv_groups: dict[tuple, list] = defaultdict(list)

        for pi, pay in enumerate(pays):
            if pi in used_pay:
                continue
            key = (pay.company.strip(), pay.counterparty.strip())
            pay_groups[key].append((pi, pay))

        for rj, recv in enumerate(recvs):
            if rj in used_recv:
                continue
            key = (recv.counterparty.strip(), recv.company.strip())
            recv_groups[key].append((rj, recv))

        for pay_key, pay_items in pay_groups.items():
            if not pay_items or pay_key not in recv_groups:
                continue
            recv_items = recv_groups[pay_key]
            if not recv_items:
                continue

            # 检查聚合组中是否有已被曼哈格预配对的记录
            has_deduped = any(
                self._dedup_key(p.company, p.counterparty, p.amount) in dedup_set
                for _, p in pay_items
            ) or any(
                self._dedup_key(r.company, r.counterparty, r.amount) in dedup_set
                for _, r in recv_items
            )
            if has_deduped:
                continue

            pay_total = round(sum(p.amount for _, p in pay_items))
            recv_total = round(sum(r.amount for _, r in recv_items))

            # 单对单聚合要求完全相等，多对多/多对一允许1元舍入差异
            if len(pay_items) == 1 and len(recv_items) == 1:
                if pay_total != recv_total:
                    continue
            elif abs(pay_total - recv_total) > 1:
                continue

            for pi, _ in pay_items:
                used_pay.add(pi)
            for rj, _ in recv_items:
                used_recv.add(rj)

            pay_vnos = '; '.join(p.voucher_no for _, p in pay_items if p.voucher_no)
            recv_vnos = '; '.join(r.voucher_no for _, r in recv_items if r.voucher_no)
            pay_amt = sum(p.amount for _, p in pay_items)
            recv_amt = sum(r.amount for _, r in recv_items)

            first_pay = pay_items[0][1]
            first_recv = recv_items[0][1]
            same_cf = (CFHelper.extract_cf_code(first_pay.cf_full)
                       == CFHelper.extract_cf_code(first_recv.cf_full))

            matched.append(MatchedPair(
                pay_voucher=pay_vnos, payer=first_pay.company,
                pay_cf=first_pay.cf_full, pay_amount=pay_amt,
                recv_voucher=recv_vnos, receiver=first_recv.company,
                recv_cf=first_recv.cf_full, recv_amount=-recv_amt if same_cf else recv_amt,
                match_type='聚合匹配'
            ))

        return matched

    def _round4_mutual(self, pays: list, recvs: list, used_pay: set,
                       used_recv: set) -> list[MatchedPair]:
        """第4轮: 内部互付/互收抵消"""
        matched = []

        # 互付: 同一对公司在付款侧互相欠款
        pay_unused = [(i, p) for i, p in enumerate(pays) if i not in used_pay]
        extra = set()

        for i in range(len(pay_unused)):
            if pay_unused[i][0] in extra:
                continue
            for j in range(i + 1, len(pay_unused)):
                if pay_unused[j][0] in extra:
                    continue
                pi, pay = pay_unused[i]
                pj, pay2 = pay_unused[j]

                if (pay.counterparty.strip() == pay2.company.strip() and
                        pay2.counterparty.strip() == pay.company.strip() and
                        round(pay.amount) == round(pay2.amount)):
                    extra.add(pi)
                    extra.add(pj)
                    used_pay.add(pi)
                    used_pay.add(pj)

                    matched.append(MatchedPair(
                        pay_voucher=pay.voucher_no, payer=pay.company,
                        pay_cf=pay.cf_full, pay_amount=pay.amount,
                        recv_voucher=pay2.voucher_no, receiver=pay2.company,
                        recv_cf=pay2.cf_full, recv_amount=-pay2.amount,
                        match_type='互付抵消'
                    ))
                    break

        # 互收: 类似逻辑但发生在收款侧
        recv_unused = [(i, r) for i, r in enumerate(recvs) if i not in used_recv]

        for i in range(len(recv_unused)):
            if recv_unused[i][0] in extra:
                continue
            for j in range(i + 1, len(recv_unused)):
                if recv_unused[j][0] in extra:
                    continue
                ri, recv = recv_unused[i]
                rj, recv2 = recv_unused[j]

                if (recv.counterparty.strip() == recv2.company.strip() and
                        recv2.counterparty.strip() == recv.company.strip() and
                        round(recv.amount) == round(recv2.amount)):
                    extra.add(ri)
                    extra.add(rj)
                    used_recv.add(ri)
                    used_recv.add(rj)

                    matched.append(MatchedPair(
                        pay_voucher=recv.voucher_no, payer=recv.counterparty,
                        pay_cf=recv.cf_full, pay_amount=recv.amount,
                        recv_voucher=recv2.voucher_no, receiver=recv2.company,
                        recv_cf=recv2.cf_full, recv_amount=-recv2.amount,
                        match_type='互收抵消'
                    ))
                    break

        return matched

    def match(self, pays: list[CFRecord], recvs: list[CFRecord],
              prematched: list[MatchedPair] | None = None) -> MatchResult:
        """执行全部匹配流程"""
        result = MatchResult()
        if prematched is None:
            prematched = []

        result.matched = list(prematched)
        dedup_set = self._build_dedup_set(prematched)

        used_pay: set[int] = set()
        used_recv: set[int] = set()

        r1 = self._round1_exact(pays, recvs, used_pay, used_recv, dedup_set)
        result.matched.extend(r1)

        r2 = self._round2_loose(pays, recvs, used_pay, used_recv, dedup_set)
        result.matched.extend(r2)

        r3 = self._round3_aggregate(pays, recvs, used_pay, used_recv, dedup_set)
        result.matched.extend(r3)

        r4 = self._round4_mutual(pays, recvs, used_pay, used_recv)
        result.matched.extend(r4)

        result.unmatched_pay = [p for i, p in enumerate(pays) if i not in used_pay]
        result.unmatched_recv = [r for i, r in enumerate(recvs) if i not in used_recv]

        # 从未匹配中过滤掉曼哈格已覆盖的记录（这些本就不应进入匹配池）
        result.unmatched_pay = [p for p in result.unmatched_pay
                                if self._dedup_key(p.company, p.counterparty, p.amount) not in dedup_set]
        result.unmatched_recv = [r for r in result.unmatched_recv
                                 if self._dedup_key(r.company, r.counterparty, r.amount) not in dedup_set]

        return result
