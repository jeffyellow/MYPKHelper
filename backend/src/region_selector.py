"""全屏区域选择器：使用 Tkinter 在屏幕上拖拽选区。"""

import tkinter as tk
from typing import Optional, Callable
from screenshot import Region


class FullscreenRegionSelector:
    """创建一个覆盖全屏的半透明窗口，让用户拖拽选择区域。"""

    def __init__(self, on_selected: Callable[[Region], None]):
        self.on_selected = on_selected
        self.result: Optional[Region] = None
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.rect_id: Optional[int] = None
        self.start_x = 0
        self.start_y = 0

    def run(self) -> Optional[Region]:
        """阻塞运行选区窗口，返回选中的 Region 或 None。"""
        self.root = tk.Tk()
        self.root.title("选择监控区域")
        self.root.attributes("-topmost", True)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3)
        self.root.configure(bg="black")
        self.root.overrideredirect(True)

        self.canvas = tk.Canvas(self.root, cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(bg="black")

        # 提示文字
        self.canvas.create_text(
            self.root.winfo_screenwidth() // 2,
            self.root.winfo_screenheight() // 2 - 40,
            text="拖拽鼠标选择游戏画面区域，按 Esc 取消",
            fill="white",
            font=("Microsoft YaHei", 24, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", self._on_cancel)

        self.root.mainloop()
        return self.result

    def _on_press(self, event: tk.Event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#1b61c9", width=2, dash=(4, 4),
        )

    def _on_drag(self, event: tk.Event):
        if self.rect_id is not None:
            self.canvas.coords(
                self.rect_id,
                self.start_x, self.start_y, event.x, event.y,
            )

    def _on_release(self, event: tk.Event):
        left = min(self.start_x, event.x)
        top = min(self.start_y, event.y)
        width = abs(event.x - self.start_x)
        height = abs(event.y - self.start_y)

        if width >= 10 and height >= 10:
            self.result = Region(
                x=int(left),
                y=int(top),
                width=int(width),
                height=int(height),
            )
            if self.on_selected:
                self.on_selected(self.result)

        self._close()

    def _on_cancel(self, event: tk.Event):
        self.result = None
        self._close()

    def _close(self):
        if self.root:
            self.root.destroy()
            self.root = None


def select_region_sync() -> Optional[Region]:
    """同步调用，阻塞直到用户完成选区。"""
    selector = FullscreenRegionSelector(on_selected=lambda r: None)
    return selector.run()
