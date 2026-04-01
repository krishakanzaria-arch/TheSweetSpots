from pathlib import Path
root = Path(__file__).resolve().parents[1]
count = 0
changed = []
old_href = "href=\"{% url 'dashboard:page' page_name='auth-signin' %}\""
new_href = "href=\"{% url 'dashboard:logout' %}\""
for p in root.glob('templates/dashboard/admin/**/*.html'):
    s = p.read_text(encoding='utf-8')
    if 'class="dropdown-item text-danger"' in s and old_href in s:
        ns = s.replace(old_href, new_href)
        p.write_text(ns, encoding='utf-8')
        changed.append(str(p))
        count += 1
print(f'Updated {count} files')
for f in changed:
    print(f)
