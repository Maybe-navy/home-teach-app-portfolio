from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit


def get_font_name():
    """既存の _register_jp_font を呼び出してフォント名を取得"""
    from .views import _register_jp_font  # 遅延インポートで循環参照回避
    return _register_jp_font()


def draw_header(canvas, title, meta_lines, font):
    """共通ヘッダ描画。タイトルとメタ情報を表示し、次の描画Y座標を返す"""
    width, height = A4
    left = 15 * mm
    top = height - 20 * mm
    canvas.setFont(font, 14)
    canvas.drawString(left, top, title)
    canvas.setFont(font, 11)
    y = top - 8 * mm
    for line in meta_lines:
        canvas.drawString(left, y, line)
        y -= 6 * mm
    # テーブル開始位置を返す
    return y - 2 * mm


def draw_table(canvas, x, y, col_defs, rows, font, size, line_h, page_right, page_bottom, header=True):
    """
    共通テーブル描画。折返しや改ページを処理し、描画後のY座標を返す。
    col_defs: [(header, width), ...]
    rows: [[col1, col2, ...], ...]
    page_right: ページの右端座標
    page_bottom: ページ下端のマージン座標
    """
    start_y = y
    canvas.setFont(font, size)

    def draw_header_row(y_pos):
        x_pos = x
        for header_text, w in col_defs:
            canvas.drawString(x_pos, y_pos, header_text)
            x_pos += w
        canvas.line(x, y_pos - 2, page_right, y_pos - 2)
        return y_pos - line_h

    if header:
        y = draw_header_row(y)

    for row in rows:
        # 行の高さを計算
        row_lines = 1
        for text, (_h, w) in zip(row, col_defs):
            wrapped = simpleSplit(str(text), font, size, w)
            row_lines = max(row_lines, len(wrapped))
        row_height = row_lines * line_h
        if y - row_height < page_bottom:
            canvas.showPage()
            canvas.setFont(font, size)
            y = start_y
            if header:
                y = draw_header_row(y)
        x_pos = x
        for text, (_h, w) in zip(row, col_defs):
            wrapped = simpleSplit(str(text), font, size, w)
            for i, line in enumerate(wrapped):
                canvas.drawString(x_pos, y - i * line_h, line)
            x_pos += w
        y -= row_height
    return y
