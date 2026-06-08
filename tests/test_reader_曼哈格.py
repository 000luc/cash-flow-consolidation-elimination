import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cashflow_tool.readers.曼哈格 import 曼哈格Reader


def test_read_pairs_returns_list():
    reader = 曼哈格Reader()
    detail_dir = os.path.join(os.path.dirname(__file__), '..', '明细')
    filepath = os.path.join(detail_dir, '曼哈格明细.xlsx')

    if not os.path.exists(filepath):
        print(f'SKIP: 明细文件不存在: {filepath}')
        return

    pairs = reader.read_pairs(filepath)
    assert len(pairs) > 0, '应有匹配对'
    assert all(p.match_type == '曼哈格' for p in pairs)
    assert all(p.pay_amount > 0 for p in pairs)
    print(f'OK: {len(pairs)} 对曼哈格匹配')


def test_read_returns_empty():
    """曼哈格的 read() 应返回空列表"""
    reader = 曼哈格Reader()
    pays, recvs = reader.read('dummy.xlsx')
    assert pays == []
    assert recvs == []
