import win32gui
import re

"""All you should have to do is initialize a WindowHandler object by passing it some identifiers, you can pass as many
as you want and it basically just sees if the window title contains all of those words. Then mess around with the
methods I made and add any if you need"""


class WindowHandler:
    def __init__(self, identifiers: list):
        """This calls that EnumWindows in order to set the value of the window handle given those identifiers

            Parameters:
                identifiers: list - This is a list of strings that the window title would have.
                (Ex. WindowName="Some Awesome Window" You could pass a list like ["Awesome", "window"] or ["some"])
        """
        self.hwnd = None
        win32gui.EnumWindows(self._get_window_hwnd, identifiers)

    def _get_window_hwnd(self, hwnd, ctx):
        """Sets the window handle for this object given some context."""
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):
            pattern = re.compile(r' | '.join(ctx), flags=re.I | re.X)
            words_found = set(pattern.findall(win32gui.GetWindowText(hwnd)))
            if len(ctx) == 1 and ctx[0].lower() in win32gui.GetWindowText(hwnd).lower():
                self.hwnd = hwnd
            elif len(ctx) > 1 and len(words_found) == len(ctx):
                self.hwnd = hwnd

    def move(self, x: int, y: int, width: int, height: int, redraw: bool = True):
        win32gui.MoveWindow(self.hwnd, x - 7, y, width, height, redraw)  # The -7 on the x is to deal with weird offset

    def unminize(self, redraw: bool = True):
        """This will unminimize the window, note that it will only work if the window literally was minized by clicking
        the -
        """
        win32gui.ShowWindow(self.hwnd, redraw)

    def foreground(self):
        """Moves the window to the very top of the stack wherever it is (little better than unminimize)"""
        win32gui.SetForegroundWindow(self.hwnd)


WINDOW_IDENTIFIERS = ["Notepad"]
window = WindowHandler(WINDOW_IDENTIFIERS)

window.move(0, 0, 200, 200)
window.foreground()
