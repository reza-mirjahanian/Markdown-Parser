import os
import markdown
from bs4 import BeautifulSoup
from html2image import Html2Image
from pygments import highlight
from pygments.lexers import GoLexer
from pygments.formatters import HtmlFormatter
from PIL import Image

# ==========================================
# CONFIGURATION
# ==========================================
INPUT_FILE = "input.md"
OUTPUT_DIR = "output_images"

# 3.0 = Ultra Sharp 4K
SCALE_FACTOR = 3

# ------------------------------------------
# STYLES
# ------------------------------------------
TABLE_CSS = """
body { 
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    background-color: transparent; /* White bg for clean cropping */
    margin: 0; padding: 0;
    display: inline-block;
    width: fit-content;
}
.table-container {
    padding: 40px; 
    display: inline-block;
}
table {
    border-collapse: collapse;
    min-width: 1800px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    border-radius: 12px;
    overflow: hidden;
    background-color: #ffffff;
}
th {
    background-color: #009879;
    color: #ffffff;
    text-align: left;
    font-weight: bolder;
    padding: 20px 30px;
    font-size: 2.4em;
}
td {
    padding: 18px 30px;
    border-bottom: 1px solid #dddddd;
    color: #333;
    font-size: 2.2em;
    font-weight: bold;
}
tr:nth-of-type(even) { background-color: #f3f3f3; }
tr:last-of-type td { border-bottom: 2px solid #009879; }
"""

CODE_CONTAINER_CSS = """
body {
    font-family: 'Consolas', 'Monaco', monospace;
    margin: 0; padding: 0;
    display: inline-block;
    background-color: transparent;
    width: fit-content;
}
.window {
    margin: 40px; 
    background-color: #1e1e1e;
    border-radius: 16px;
    box-shadow: 0 30px 60px rgba(0,0,0,0.5);
    min-width: 3000px; /* Wider for 4K */
    overflow: hidden;
}
.title-bar {
    background-color: #252526;
    padding: 15px 20px;
    display: flex;
    gap: 12px;
}
.dot { width: 16px; height: 16px; border-radius: 50%; }
.red { background-color: #ff5f56; }
.yellow { background-color: #ffbd2e; }
.green { background-color: #27c93f; }

.code-content {
    padding: 30px;
    color: #d4d4d4;
    font-size: 28px; /* Larger font for 4K visibility */
    line-height: 1.6;
}
pre { margin: 0; white-space: pre-wrap; padding: 40px; }
"""

class MarkdownRenderer:
    def __init__(self, input_path, output_dir):
        self.input_path = input_path
        self.output_dir = output_dir

        # We start with a default size, but we will change this dynamically per image
        self.hti = Html2Image(output_path=output_dir, size=(3840, 2160))

        self.hti.browser_args = [
            f'--force-device-scale-factor={SCALE_FACTOR}',
            '--hide-scrollbars',
            '--font-render-hinting=none'
        ]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def trim_whitespace(self, filename):
        full_path = os.path.join(self.output_dir, filename)
        try:
            with Image.open(full_path) as im:
                bbox = im.getbbox()
                if bbox:
                    im_cropped = im.crop(bbox)
                    im_cropped.save(full_path)
                    print(f"  └── Cropped to {im_cropped.size}")
        except Exception as e:
            print(f"Error trimming {filename}: {e}")

    def read_markdown(self):
        with open(self.input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return markdown.markdown(text, extensions=['tables', 'fenced_code'])

    def render_tables(self, soup):
        print("--- Processing Tables ---")
        tables = soup.find_all('table')

        for idx, table in enumerate(tables):
            filename = f"{idx + 1}_table.png"

            # --- DYNAMIC HEIGHT CALCULATION ---
            # Count rows (tr) to estimate height
            rows = table.find_all('tr')
            num_rows = len(rows) if rows else 10
            # Estimate: 100px per row + 500px padding (overestimate is safe due to cropping)
            estimated_height = (num_rows * 100) + 1000

            # Update browser window size
            self.hti.size = (3840, estimated_height)

            html_str = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><style>{TABLE_CSS}</style></head>
            <body><div class="table-container">{str(table)}</div></body>
            </html>
            """

            print(f"Generating {filename} (Height buffer: {estimated_height}px)...")
            self.hti.screenshot(html_str=html_str, save_as=filename)
            self.trim_whitespace(filename)

    def render_code_blocks(self, soup):
        print("--- Processing Code Blocks ---")
        code_blocks = soup.find_all('code')

        count = 1
        for code in code_blocks:
            if code.parent.name != 'pre':
                continue

            code_text = code.get_text()

            # --- DYNAMIC HEIGHT CALCULATION ---
            # Count newlines to determine code length
            num_lines = code_text.count('\n') + 1

            # Math: (Lines * LineHeight * Scale) + Header + Padding
            # 24px font * 1.6 line-height * 3 scale ≈ 115px per line physically
            # We use 130px to be safe.
            estimated_height = (num_lines * 130) + 1500

            # Set the browser window height specifically for this image
            self.hti.size = (3840, estimated_height)

            formatter = HtmlFormatter(style='monokai', noclasses=True)
            highlighted_html = highlight(code_text, GoLexer(), formatter)

            filename = f"{count}_code.png"

            html_str = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><style>{CODE_CONTAINER_CSS}</style></head>
            <body>
                <div class="window">
                    <div class="title-bar">
                        <div class="dot red"></div>
                        <div class="dot yellow"></div>
                        <div class="dot green"></div>
                    </div>
                    <div class="code-content">
                        {highlighted_html}
                    </div>
                </div>
            </body>
            </html>
            """

            print(f"Generating {filename} (Lines: {num_lines}, Height buffer: {estimated_height}px)...")
            self.hti.screenshot(html_str=html_str, save_as=filename)
            self.trim_whitespace(filename)
            count += 1

    def run(self):
        html_content = self.read_markdown()
        soup = BeautifulSoup(html_content, 'html.parser')
        self.render_tables(soup)
        self.render_code_blocks(soup)
        print("\n✅ Processing Complete!")

if __name__ == "__main__":
    # Create a test file with very long code
    if not os.path.exists(INPUT_FILE):
        long_code = 'fmt.Println("This is a long line")\n' * 50
        with open(INPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"""
# Long Code Test

```go
package main

import "fmt"

func main() {{
    // This loops 50 times to test vertical scrolling
{long_code}
}}
""")
renderer = MarkdownRenderer(INPUT_FILE, OUTPUT_DIR)
renderer.run()