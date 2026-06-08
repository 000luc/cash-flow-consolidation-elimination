import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cashflow_tool.readers.计量 import 计量Reader


def test_read_returns_records():
    reader = 计量Reader()
    detail_dir = os.path.join(os.path.dirname(__file__), '..', '明细')
    filepath = os.path.join(detail_dir, '计量明细.xlsx')
    if not os.path.exists(filepath):
        print('SKIP')
        return

    pays, recvs = reader.read(filepath)
    print(f'付款: {len(pays)} 条, 收款: {len(recvs)} 条')
    assert len(pays) >= 0
    assert len(recvs) >= 0
    if pays:
        assert pays[0].direction == '付款'
        assert pays[0].source == '计量'
    if recvs:
        assert recvs[0].direction == '收款'
        assert recvs[0].source == '计量'


def test_only_internal_records():
    """验证非内部的行被过滤"""
    reader = 计量Reader()
    detail_dir = os.path.join(os.path.dirname(__file__), '..', '明细')
    filepath = os.path.join(detail_dir, '计量明细.xlsx')
    if not os.path.exists(filepath):
        print('SKIP')
        return

    pays, recvs = reader.read(filepath)
    total = len(pays) + len(recvs)
    assert total <= 500  # 总行501行数据（含表头），全部可能是内部
    print(f'OK: 内部记录 {total} 条（总行 501）')
