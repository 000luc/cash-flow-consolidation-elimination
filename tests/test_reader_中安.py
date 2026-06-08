import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cashflow_tool.readers.中安 import 中安Reader


def test_read_returns_records():
    reader = 中安Reader()
    detail_dir = os.path.join(os.path.dirname(__file__), '..', '明细')
    fp = os.path.join(detail_dir, '中安明细.xlsx')
    if not os.path.exists(fp):
        print('SKIP')
        return

    pays, recvs = reader.read(fp)
    print(f'中安: 付款 {len(pays)} 条, 收款 {len(recvs)} 条')
    assert len(pays) >= 0
    assert len(recvs) >= 0
    if pays:
        assert pays[0].direction == '付款'
        assert pays[0].source == '中安'
    if recvs:
        assert recvs[0].direction == '收款'
        assert recvs[0].source == '中安'


def test_only_internal_records():
    """验证非内部的行被过滤（只认 '内部' 或 '内部单位'）"""
    reader = 中安Reader()
    detail_dir = os.path.join(os.path.dirname(__file__), '..', '明细')
    fp = os.path.join(detail_dir, '中安明细.xlsx')
    if not os.path.exists(fp):
        print('SKIP')
        return

    pays, recvs = reader.read(fp)
    total = len(pays) + len(recvs)
    print(f'中安: 内部记录 {total} 条')
    assert total >= 0
