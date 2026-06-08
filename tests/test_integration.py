"""集成测试：从真实明细文件读取 -> 匹配 -> 输出全流程"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cashflow_tool.readers.计量 import 计量Reader
from cashflow_tool.readers.中安 import 中安Reader
from cashflow_tool.readers.曼哈格 import 曼哈格Reader
from cashflow_tool.readers.博林达 import 博林达Reader
from cashflow_tool.matcher import CFMatcher
from cashflow_tool.exporter import ExcelExporter


def test_full_pipeline():
    """从真实明细文件读取 -> 匹配 -> 输出"""
    detail_dir = os.path.join(os.path.dirname(__file__), '..', '明细')

    if not os.path.exists(detail_dir):
        print('SKIP: 明细目录不存在')
        return

    pays, recvs = [], []
    prematched = []

    fp = os.path.join(detail_dir, '计量明细.xlsx')
    if os.path.exists(fp):
        p, r = 计量Reader().read(fp)
        pays.extend(p)
        recvs.extend(r)
        print(f'计量: {len(p)} 付, {len(r)} 收')

    fp = os.path.join(detail_dir, '中安明细.xlsx')
    if os.path.exists(fp):
        p, r = 中安Reader().read(fp)
        pays.extend(p)
        recvs.extend(r)
        print(f'中安: {len(p)} 付, {len(r)} 收')

    fp = os.path.join(detail_dir, '曼哈格明细.xlsx')
    if os.path.exists(fp):
        prematched = 曼哈格Reader().read_pairs(fp)
        print(f'曼哈格: {len(prematched)} 对')

    fp = os.path.join(detail_dir, '博林达明细.xlsx')
    if os.path.exists(fp):
        p, r = 博林达Reader().read(fp)
        pays.extend(p)
        recvs.extend(r)
        print(f'博林达: {len(p)} 付, {len(r)} 收')

    matcher = CFMatcher()
    result = matcher.match(pays, recvs, prematched)

    print(f'\n匹配结果: {len(result.matched)} 对')
    print(f'未匹配付款: {len(result.unmatched_pay)} 条')
    print(f'未匹配收款: {len(result.unmatched_recv)} 条')

    # 至少应有匹配结果（曼哈格配对 + 自动匹配）
    assert len(result.matched) >= 1, '至少应有一对匹配'

    # 输出到临时文件验证
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        out_path = f.name
    try:
        exporter = ExcelExporter()
        exporter.export(result, out_path)
        file_size = os.path.getsize(out_path)
        assert file_size > 0, '输出文件不应为空'
        print(f'\nOK: 输出文件 {file_size} bytes')
    finally:
        try:
            os.unlink(out_path)
        except Exception:
            pass
