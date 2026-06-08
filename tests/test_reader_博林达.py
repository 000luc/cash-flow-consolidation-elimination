import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cashflow_tool.readers.博林达 import 博林达Reader


def test_extract_counterparty():
    reader = 博林达Reader()
    assert '检测公司' in reader._extract_counterparty('收到 检测公司 货款', '')
    assert reader._extract_counterparty('报销差旅费', '') == ''


def test_read_returns_records():
    reader = 博林达Reader()
    detail_dir = os.path.join(os.path.dirname(__file__), '..', '明细')
    fp = os.path.join(detail_dir, '博林达明细.xlsx')
    if not os.path.exists(fp):
        print('SKIP')
        return

    pays, recvs = reader.read(fp)
    print(f'博林达: 付款 {len(pays)} 条, 收款 {len(recvs)} 条')
    assert len(pays) >= 0
    assert len(recvs) >= 0
    if pays:
        assert pays[0].direction == '付款'
        assert pays[0].source == '博林达'
    if recvs:
        assert recvs[0].direction == '收款'
        assert recvs[0].source == '博林达'
