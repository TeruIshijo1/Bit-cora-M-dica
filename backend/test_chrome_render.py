import subprocess
import os

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

def get_browser_path():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None

def render_html_to_pdf(html_content, output_pdf_path):
    browser = get_browser_path()
    if not browser:
        raise RuntimeError("No Chromium browser found")
        
    temp_html = output_pdf_path.replace(".pdf", "_temp.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf_path}",
        temp_html
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if os.path.exists(temp_html):
        try:
            os.remove(temp_html)
        except:
            pass
            
    if res.returncode != 0:
        raise RuntimeError(f"PDF generation failed: {res.stderr}")
    return output_pdf_path

if __name__ == "__main__":
    html_test = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: letter portrait; margin: 0; }
  body { margin: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
  .page { width: 8.5in; height: 11in; position: relative; box-sizing: border-box; padding: 15mm; border: 1px solid red; }
</style>
</head>
<body>
  <div class="page">
    <h1 style="color: #0056b3;">Hospital Escandón</h1>
    <p>Renderizado nativo Chromium perfecto.</p>
  </div>
</body>
</html>"""
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "pdfs", "chrome_test.pdf"))
    res = render_html_to_pdf(html_test, out)
    print("Generated successfully:", res, "Size:", os.path.getsize(res))
