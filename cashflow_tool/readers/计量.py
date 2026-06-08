import openpyxl
from cashflow_tool.readers.base import BaseReader
from cashflow_tool.models import CFRecord
from cashflow_tool.constants import CF_CODE_MAP


class 计量Reader(BaseReader):
    """计量明细读取器

    只读标记为"内部"的行，借方=付款，贷方=收款。
    """

    SHEET_NAME = '1'

    # 列索引（0-based）
    COL_COMPANY = 0
    COL_VOUCHER = 4
    COL_DEBIT = 12
    COL_CREDIT = 13
    COL_CF = 14
    COL_INTERNAL_FLAG = 18
    COL_CP1 = 19
    COL_CP2 = 20

    def read(self, filepath: str) -> tuple[list[CFRecord], list[CFRecord]]:
        wb = openpyxl.load_workbook(filepath)
        ws = wb[self.SHEET_NAME]
        pays: list[CFRecord] = []
        recvs: list[CFRecord] = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(v is not None for v in row):
                continue
            if str(row[self.COL_INTERNAL_FLAG]).strip() != '内部':
                continue

            company = self.clean_name(row[self.COL_COMPANY])
            vno = str(row[self.COL_VOUCHER] or '').strip()
            cf_raw = str(row[self.COL_CF] or '').strip()
            cf_full = self.normalize_cf(cf_raw, CF_CODE_MAP)
            debit = row[self.COL_DEBIT] or 0
            credit = row[self.COL_CREDIT] or 0
            amount = abs(debit or credit)
            cp_raw = str(row[self.COL_CP1] or '')
            if len(row) > self.COL_CP2 and row[self.COL_CP2]:
                cp_raw = str(row[self.COL_CP2])
            cp = self.clean_name(cp_raw)

            rec = CFRecord(
                company=company, counterparty=cp,
                cf_full=cf_full, amount=amount,
                voucher_no=vno, source='计量',
                direction=''
            )
            if debit:
                rec.direction = '付款'
                pays.append(rec)
            if credit:
                rec.direction = '收款'
                recvs.append(rec)

        wb.close()
        return pays, recvs
