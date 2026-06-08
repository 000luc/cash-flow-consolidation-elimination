# cashflow_tool/gui.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import threading

from cashflow_tool.readers.计量 import 计量Reader
from cashflow_tool.readers.中安 import 中安Reader
from cashflow_tool.readers.曼哈格 import 曼哈格Reader
from cashflow_tool.readers.博林达 import 博林达Reader
from cashflow_tool.matcher import CFMatcher
from cashflow_tool.exporter import ExcelExporter


class App:
    """现金流内部抵消工具 GUI"""

    FILE_CONFIGS = [
        ('计量明细', '计量明细.xlsx'),
        ('中安明细', '中安明细.xlsx'),
        ('曼哈格明细', '曼哈格明细.xlsx'),
        ('博林达明细', '博林达明细.xlsx'),
    ]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('现金流内部抵消工具 v2')
        self.root.geometry('620x520')
        self.root.resizable(False, False)

        self._file_vars: list[tk.StringVar] = []
        self._status_labels: list[tk.Label] = []
        self._output_var = tk.StringVar()
        self._result_text = tk.StringVar(value='')

        self._setup_ui()

    def _setup_ui(self):
        # 标题
        tk.Label(self.root, text='现金流内部抵消工具', font=('微软雅黑', 16, 'bold'),
                 fg='#1a1a2e').pack(pady=(15, 5))
        tk.Label(self.root, text='选择4家子公司明细文件，自动生成内部抵消结果',
                 font=('微软雅黑', 9), fg='#888').pack()

        # 文件选择区域
        frame = tk.Frame(self.root, padx=20)
        frame.pack(fill='x', pady=10)

        for label, default_name in self.FILE_CONFIGS:
            row = tk.Frame(frame)
            row.pack(fill='x', pady=3)

            tk.Label(row, text=f'📂 {label}', width=12, anchor='w',
                     font=('微软雅黑', 10)).pack(side='left')

            var = tk.StringVar()
            self._file_vars.append(var)
            path_var = tk.StringVar(value=default_name)

            entry = tk.Entry(row, textvariable=path_var, width=35,
                             font=('微软雅黑', 9), state='readonly')
            entry.pack(side='left', padx=5)

            tk.Button(row, text='浏览...', font=('微软雅黑', 9),
                      command=lambda v=var, pv=path_var: self._browse_file(v, pv))\
                .pack(side='left', padx=2)

            status = tk.Label(row, text='✗ 未选择', fg='#999', width=10,
                              font=('微软雅黑', 9))
            status.pack(side='left')
            self._status_labels.append(status)

        # 输出路径
        out_frame = tk.Frame(self.root, padx=20)
        out_frame.pack(fill='x', pady=5)

        tk.Label(out_frame, text='📥 输出路径', width=12, anchor='w',
                 font=('微软雅黑', 10)).pack(side='left')

        self._output_var = tk.StringVar(
            value=os.path.join(os.getcwd(), '现金流内部抵消结果.xlsx')
        )

        output_entry = tk.Entry(out_frame, textvariable=self._output_var,
                                 width=35, font=('微软雅黑', 9))
        output_entry.pack(side='left', padx=5)

        tk.Button(out_frame, text='浏览...', font=('微软雅黑', 9),
                  command=self._browse_output).pack(side='left', padx=2)

        # 处理按钮
        self._btn = tk.Button(self.root, text='▶ 开始处理',
                              font=('微软雅黑', 12, 'bold'),
                              bg='#4a90d9', fg='white',
                              padx=30, pady=8,
                              command=self._start_process)
        self._btn.pack(pady=12)

        # 结果区域
        sep = ttk.Separator(self.root, orient='horizontal')
        sep.pack(fill='x', padx=20, pady=5)

        tk.Label(self.root, textvariable=self._result_text,
                 font=('微软雅黑', 10), fg='#333', wraplength=550).pack(pady=5)

        self._open_btn = tk.Button(self.root, text='📂 打开结果文件',
                                    font=('微软雅黑', 10),
                                    command=self._open_result,
                                    state='disabled')
        self._open_btn.pack(pady=2)
        self._result_path = None

    def _browse_file(self, var, path_var):
        fp = filedialog.askopenfilename(
            title='选择文件',
            filetypes=[('Excel 文件', '*.xlsx *.xls')]
        )
        if fp:
            var.set(fp)
            path_var.set(os.path.basename(fp))
            idx = self._file_vars.index(var)
            self._status_labels[idx].config(text='✓ 已选择', fg='#28a745')

    def _browse_output(self):
        fp = filedialog.asksaveasfilename(
            title='选择输出位置',
            defaultextension='.xlsx',
            filetypes=[('Excel 文件', '*.xlsx')],
            initialfile='现金流内部抵消结果.xlsx'
        )
        if fp:
            self._output_var.set(fp)

    def _resolve_data_path(self, relative_path):
        """获取数据文件路径（兼容 PyInstaller 打包）"""
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, relative_path)

    def _start_process(self):
        self._btn.config(state='disabled', text='⏳ 处理中...')
        self._result_text.set('')
        self._open_btn.config(state='disabled')

        t = threading.Thread(target=self._process, daemon=True)
        t.start()

    def _process(self):
        try:
            readers = {
                '计量明细': 计量Reader(),
                '中安明细': 中安Reader(),
                '曼哈格明细': 曼哈格Reader(),
                '博林达明细': 博林达Reader(),
            }

            pays, recvs = [], []
            prematched = []

            for i, (label, default_name) in enumerate(self.FILE_CONFIGS):
                fp = self._file_vars[i].get()
                if not fp:
                    default_path = self._resolve_data_path(os.path.join('明细', default_name))
                    if os.path.exists(default_path):
                        fp = default_path
                    else:
                        raise FileNotFoundError(f'请选择 {label} 文件')

                reader = readers[label]
                if label == '曼哈格明细':
                    prematched = reader.read_pairs(fp)
                else:
                    p, r = reader.read(fp)
                    pays.extend(p)
                    recvs.extend(r)

            matcher = CFMatcher()
            result = matcher.match(pays, recvs, prematched)

            exporter = ExcelExporter()
            output_path = self._output_var.get()
            exporter.export(result, output_path)

            self.root.after(0, self._on_success, result, output_path)

        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _on_success(self, result, output_path):
        self._result_path = output_path
        msg = (f'处理完成\n'
               f'抵消明细: {len(result.matched)} 对 | '
               f'未匹配付款: {len(result.unmatched_pay)} 条 | '
               f'未匹配收款: {len(result.unmatched_recv)} 条')
        self._result_text.set(msg)
        self._open_btn.config(state='normal')
        self._btn.config(state='normal', text='▶ 开始处理')

    def _on_error(self, msg):
        self._result_text.set(f'❌ 处理失败: {msg}')
        self._btn.config(state='normal', text='▶ 重新处理')
        messagebox.showerror('处理失败', msg)

    def _open_result(self):
        if self._result_path and os.path.exists(self._result_path):
            os.startfile(self._result_path)

    def run(self):
        self.root.mainloop()


def launch_gui():
    app = App()
    app.run()


if __name__ == '__main__':
    launch_gui()
