"""把宋体子集嵌进 index.html。

iPhone 没有自带中文宋体，网页里写的宋体在手机上都会变成苹方黑体。
这个脚本扫描 index.html 里实际用到的字，从思源宋体（Noto Serif CJK SC）里只取这些字，
压成 WOFF2 后以 base64 写进页面，放在 FONT:BEGIN 和 FONT:END 两行注释之间。
页面文字改了之后重新跑一遍即可：

    pip install fonttools brotli
    python3 tools/build_font.py [常规体 .ttc] [粗体 .ttc]

字体许可：SIL Open Font License 1.1（Noto Serif CJK）。子集保留了字体自带的版权和许可信息。
"""
import base64, re, subprocess, sys, tempfile
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / 'index.html'
REGULAR = sys.argv[1] if len(sys.argv) > 1 else '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'
BOLD = sys.argv[2] if len(sys.argv) > 2 else '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
FACE = 2  # .ttc 里第 3 个字体是简体中文（SC）
BOLD_TEXT = '看穿揭晓已检花佳'  # 印章、检票章、观展记录的章用粗体，只有这几个字
BEGIN, END = '/* FONT:BEGIN', '/* FONT:END */'

def page_text(html):
    # 去掉已经嵌进去的字体和所有注释，只看真正会显示的字
    a, b = html.find(BEGIN), html.find(END)
    if a >= 0 and b > a:
        html = html[:a] + html[b + len(END):]
    html = re.sub(r'/\*.*?\*/', '', html, flags=re.S)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    html = re.sub(r'(?m)^\s*//.*$', '', html)
    html = re.sub(r'(?m)\s//\s.*$', '', html)
    return html

def subset(src, text, out):
    with tempfile.NamedTemporaryFile('w', suffix='.txt', encoding='utf-8', delete=False) as f:
        f.write(text)
    subprocess.run(['pyftsubset', src, f'--font-number={FACE}', f'--text-file={f.name}', '--flavor=woff2',
                    f'--output-file={out}', '--layout-features=kern,vert,vrt2', '--no-hinting', "--name-IDs=*"], check=True)
    return base64.b64encode(Path(out).read_bytes()).decode()

def main():
    html = PAGE.read_text(encoding='utf-8')
    text = page_text(html)
    han = sorted(set(c for c in text if '　' <= c <= '鿿' or '＀' <= c <= '￯'))
    latin = ''.join(chr(i) for i in range(0x20, 0x7f)) + '·—…“”‘’'
    with tempfile.TemporaryDirectory() as d:
        reg = subset(REGULAR, ''.join(han) + latin, f'{d}/r.woff2')
        bold = subset(BOLD, BOLD_TEXT, f'{d}/b.woff2')
    ranges = ','.join(f'U+{ord(c):04X}' for c in sorted(set(BOLD_TEXT)))
    css = (f'{BEGIN} 宋体子集：思源宋体（Noto Serif CJK SC，SIL OFL 1.1），只含页面用到的 {len(han)} 个字；由 tools/build_font.py 生成 */\n'
           f'@font-face{{font-family:"ExpoSerif";font-weight:400;font-display:block;src:url(data:font/woff2;base64,{reg}) format("woff2")}}\n'
           f'@font-face{{font-family:"ExpoSerif";font-weight:700;font-display:block;unicode-range:{ranges};src:url(data:font/woff2;base64,{bold}) format("woff2")}}\n'
           f'{END}\n')
    a, b = html.find(BEGIN), html.find(END)
    if a >= 0 and b > a:
        html = html[:a] + css + html[b + len(END) + 1:]
    else:
        html = html.replace('<style>\n', '<style>\n' + css, 1)
    PAGE.write_text(html, encoding='utf-8')
    print(f'{len(han)} 个字，常规体 {len(reg) * 3 // 4 // 1024} KB，粗体 {len(bold) * 3 // 4 // 1024} KB')

main()
