import openpyxl
from cashflow_tool.readers.base import BaseReader
from cashflow_tool.models import CFRecord
from cashflow_tool.constants import CF_CODE_MAP


class 中安Reader(BaseReader):
    """中安明细读取器

    内部标记为"内部单位"的行，借方=付款，贷方=收款。
    """

    SHEET_NAME = 'Sheet1'

    COL_COMPANY = 0
    COL_VOUCHER = 4
    COL_DEBIT = 12
    COL_CREDIT = 13
    COL_CF = 14
    COL_INTERNAL_FLAG = 18
    COL_CP = 19

    def read(self, filepath: str, dedup_set: set[tuple] | None = None
             ) -> tuple[list[CFRecord], list[CFRecord]]:
        wb = openpyxl.load_workbook(filepath)
        ws = wb[self.SHEET_NAME]
        pays: list[CFRecord] = []
        recvs: list[CFRecord] = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(v is not None for v in row):
                continue
            flag = str(row[self.COL_INTERNAL_FLAG] or '').strip()
            if flag not in ('内部', '内部单位'):
                continue

            company = self.clean_name(row[self.COL_COMPANY])
            vno = str(row[self.COL_VOUCHER] or '').strip()
            cf_raw = str(row[self.COL_CF] or '').strip()
            cf_full = self.normalize_cf(cf_raw, CF_CODE_MAP)
            debit = row[self.COL_DEBIT] or 0
            credit = row[self.COL_CREDIT] or 0
            amount = abs(debit or credit)
            cp = self.clean_name(str(row[self.COL_CP] or ''))

            # 曼哈格已覆盖的跳过
            if dedup_set and self.make_dedup_key(company, cp, amount) in dedup_set:
                continue

            rec = CFRecord(
                company=company, counterparty=cp,
                cf_full=cf_full, amount=amount,
                voucher_no=vno, source='中安', direction=''
            )
            if debit:
                rec.direction = '付款'
                pays.append(rec)
            if credit:
                rec.direction = '收款'
                recvs.append(rec)

        wb.close()
        return pays, recvs
