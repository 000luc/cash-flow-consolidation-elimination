import openpyxl
from cashflow_tool.readers.base import BaseReader, CFHelper
from cashflow_tool.models import CFRecord, MatchedPair
from cashflow_tool.constants import CF_CODE_MAP, CF_PAIR_MAP


class 曼哈格Reader(BaseReader):
    """曼哈格明细读取器

    曼哈格的明细是预先配好对的格式：
      付款方 | 收款方 | 现金流指标 | 金额 | 处理日期
    直接转为 MatchedPair，同时返回空付款/收款列表（已配对的不参与匹配）。
    """

    SHEET_NAME = '3'

    @staticmethod
    def build_dedup_set(pairs: list[MatchedPair]) -> set[tuple]:
        """从已配对数据构建去重集合

        返回 {(公司, 对方公司, 四舍五入金额)}，用于在读取其他明细时跳过曼哈格已覆盖的记录。
        """
        keys: set[tuple] = set()
        for p in pairs:
            keys.add(BaseReader.make_dedup_key(p.payer, p.receiver, p.pay_amount))
            keys.add(BaseReader.make_dedup_key(p.receiver, p.payer, p.pay_amount))
        return keys

    def read(self, filepath: str, dedup_set: set[tuple] | None = None
             ) -> tuple[list[CFRecord], list[CFRecord]]:
        """曼哈格不产生独立的付款/收款记录，返回空列表"""
        return [], []

    def read_pairs(self, filepath: str) -> list[MatchedPair]:
        """读取曼哈格已配对数据"""
        wb = openpyxl.load_workbook(filepath)
        ws = wb[self.SHEET_NAME]
        pairs: list[MatchedPair] = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(v is not None for v in row):
                continue
            payer = self.clean_name(row[0])
            receiver = self.clean_name(row[1])
            cf_raw = str(row[2]).strip() if row[2] else ''
            amount = abs(row[3] or 0)

            cf_full = self.normalize_cf(cf_raw, CF_CODE_MAP)
            cf_code = self.extract_cf_code(cf_full)

            pay_cf, recv_cf = self._determine_cf_pair(cf_full, cf_code)

            pairs.append(MatchedPair(
                pay_voucher='', payer=payer, pay_cf=pay_cf, pay_amount=amount,
                recv_voucher='', receiver=receiver, recv_cf=recv_cf, recv_amount=amount,
                match_type='曼哈格'
            ))

        wb.close()
        return pairs

    def _determine_cf_pair(self, cf_full: str, cf_code: str) -> tuple[str, str]:
        """根据CF指标确定付款侧和收款侧的指标文本"""
        if CFHelper.is_payment(cf_full, cf_code):
            mapped = CF_PAIR_MAP.get(cf_code, '')
            recv_cf = f'{mapped} {CF_CODE_MAP.get(mapped, "")}' if mapped else cf_full
            return cf_full, recv_cf
        else:
            mapped = CF_PAIR_MAP.get(cf_code, '')
            pay_cf = f'{mapped} {CF_CODE_MAP.get(mapped, "")}' if mapped else cf_full
            return pay_cf, cf_full
