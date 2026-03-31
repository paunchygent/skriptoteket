from weasyprint import HTML

html = """
<!doctype html>
<html>
  <head>
    <style>
      @page {
        size: A4 landscape;
        margin: 0;
      }
      body {
        margin: 0;
        width: 297mm;
        height: 210mm;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        font-family: sans-serif;
      }
      .poster {
        position: relative;
        width: 281mm;
        height: 194mm;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
      }
      .watermark {
        position: absolute;
        right: 0;
        bottom: -4.5mm;
        font-size: 7.5pt;
        color: #94a3b8;
        letter-spacing: 0.02em;
      }
    </style>
  </head>
  <body>
    <main class="poster">
      <h1>Poster Content</h1>
      <div class="watermark">skriptoteket.hule.education</div>
    </main>
  </body>
</html>
"""

HTML(string=html).write_pdf("test_watermark.pdf")
