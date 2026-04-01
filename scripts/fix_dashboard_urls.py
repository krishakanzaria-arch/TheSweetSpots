from pathlib import Path
root = Path(__file__).resolve().parents[1]
count = 0
changed_files = []
for p in root.glob('templates/dashboard/admin/**/*.html'):
    s = p.read_text(encoding='utf-8')
    ns = s.replace("{% url 'page'","{% url 'dashboard:page'")
    ns = ns.replace('% }','%}')
    if ns != s:
        p.write_text(ns, encoding='utf-8')
        changed_files.append(str(p))
        count += 1
print(f'Updated {count} files')
for f in changed_files:
    print(f)
