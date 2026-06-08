import openpyxl
import re
from cashflow_tool.readers.base import BaseReader
from cashflow_tool.models import CFRecord
from cashflow_tool.constants import CF_CODE_MAP


class 博林达Reader(BaseReader):
    """博林达明细读取器

    博林达没有明确的"内部"标记，通过摘要字段提取对方公司。
    公司名固定为"深圳市博林达科技有限公司"。
    """

    SHEET_NAME = '2'

    COL_SUMMARY = 4
    COL_ACCT_NAME = 6
    COL_DEBIT = 9
    COL_CREDIT = 10
    COL_CF = 12
    COL_CHARACTER = 2
    COL_VOUCHER_NUM = 3

    def read(self, filepath: str, dedup_set: set[tuple] | None = None
             ) -> tuple[list[CFRecord], list[CFRecord]]:
        wb = openpyxl.load_workbook(filepath)
        ws = wb[self.SHEET_NAME]
        pays: list[CFRecord] = []
        recvs: list[CFRecord] = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(v is not None for v in row):
                continue

            cf_raw = str(row[self.COL_CF] or '').strip()
            cf_full = self.normalize_cf(cf_raw, CF_CODE_MAP)
            debit = row[self.COL_DEBIT] or 0
            credit = row[self.COL_CREDIT] or 0
            char = str(row[self.COL_CHARACTER] or '').strip()
            vno_num = str(row[self.COL_VOUCHER_NUM] or '').strip()
            vno = char + vno_num
            summary = str(row[self.COL_SUMMARY] or '')
            acct_name = str(row[self.COL_ACCT_NAME] or '')
            amount = abs(debit or credit)

            cp = self._extract_counterparty(summary, acct_name)

            # 曼哈格已覆盖的跳过
            if dedup_set and self.make_dedup_key(
                '深圳市博林达科技有限公司', cp, amount
            ) in dedup_set:
                continue

            rec = CFRecord(
                company='深圳市博林达科技有限公司',
                counterparty=cp, cf_full=cf_full, amount=amount,
                voucher_no=vno, source='博林达', direction=''
            )
            if debit:
                rec.direction = '付款'
                pays.append(rec)
            if credit:
                rec.direction = '收款'
                recvs.append(rec)

        wb.close()
        return pays, recvs

    @staticmethod
    def _extract_counterparty(summary: str, acct_name: str) -> str:
        """从摘要或科目名提取对方公司"""
        m = re.search(r'收到\s*(.+?公司)', summary)
        if m:
            return m.group(1).strip()
        m = re.search(r'支付.+?给\s*(.+?公司)', summary)
        if m:
            return m.group(1).strip()
        if '公司' in acct_name:
            return acct_name.strip()
        return ''
