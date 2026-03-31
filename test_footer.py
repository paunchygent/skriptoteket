from weasyprint import HTML

html = """
<!doctype html>
<html>
  <head>
    <style>
      @page {
        size: A4 portrait;
        margin: 14mm 12mm 16mm 12mm;
        @bottom-right {
          content: "skriptoteket.hule.education";
          font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
          font-size: 7.5pt;
          color: #94a3b8;
        }
      }
      body { font-family: sans-serif; }
    </style>
  </head>
  <body>
    <h1>Hello World</h1>
    <p>Testing footer.</p>
  </body>
</html>
"""

HTML(string=html).write_pdf("test-footer.pdf")
print("Done")
