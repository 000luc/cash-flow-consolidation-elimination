from abc import ABC, abstractmethod
import re
from cashflow_tool.models import CFRecord


class BaseReader(ABC):
    """所有明细读取器的基类"""

    @abstractmethod
    def read(self, filepath: str) -> tuple[list[CFRecord], list[CFRecord]]:
        """
        读取明细文件，返回 (付款记录列表, 收款记录列表)

        每个子类自行处理自家格式的列映射、清理逻辑。
        filepath 已由 GUI 校验过存在性。
        """
        ...

    @staticmethod
    def extract_cf_code(cf_text: str) -> str:
        """从CF文本中提取CI代码，如 'CI1.02.04.01 支付...' → 'CI1.02.04.01'"""
        if not cf_text:
            return ''
        m = re.match(r'(CI\d+\.\d+\.\d+\.\d+)', str(cf_text).strip())
        return m.group(1) if m else ''

    @staticmethod
    def normalize_cf(cf_text: str, code_map: dict[str, str]) -> str:
        """规范化CF文本：确保带有CI代码前缀"""
        if not cf_text:
            return ''
        cf_text = str(cf_text).strip()
        if re.match(r'CI\d+\.\d+\.\d+\.\d+', cf_text):
            return cf_text
        for desc, code in code_map.items():
            if cf_text in desc or desc in cf_text:
                return f'{code} {cf_text}'
        return cf_text

    @staticmethod
    def clean_name(name: str) -> str:
        """清理公司名称"""
        if not name:
            return ''
        name = str(name).strip()
        name = re.sub(r'内部单位:\d+\s*', '', name)
        name = re.sub(r';$', '', name)
        return name.strip()


class CFHelper:
    """现金流指标判断工具"""

    @staticmethod
    def is_payment(cf_text: str, cf_code: str = '') -> bool:
        """是否为付款类(流出)"""
        if cf_code:
            parts = cf_code.split('.')
            if len(parts) >= 2 and parts[1] == '02':
                return True
            if 'CI3.02.04' in cf_code:
                return True
        return '支付' in cf_text or '分配' in cf_text

    @staticmethod
    def is_receipt(cf_text: str, cf_code: str = '') -> bool:
        """是否为收款类(流入)"""
        if cf_code:
            parts = cf_code.split('.')
            if len(parts) >= 2 and parts[1] == '01':
                return True
        return '收到' in cf_text or '销售' in cf_text
