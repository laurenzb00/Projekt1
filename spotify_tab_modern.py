cd "c:\Users\laure\OneDrive\Studium-SBG\SoS 25\Datenerfassung\eigenes projekt\Projekt1-1" ; python -c "
import re
with open('spotify_tab_modern.py', 'r') as f:
    content = f.read()
# Replace all font=('Segoe UI' with font=_font('Arial'
content = re.sub(r'font=\(\"Segoe UI\"', 'font=_font(\"Arial\"', content)
with open('spotify_tab_modern.py', 'w') as f:
    f.write(content)
print('Replacements done!')
"
cd "c:\Users\laure\OneDrive\Studium-SBG\SoS 25\Datenerfassung\eigenes projekt\Projekt1-1" ; python fix_fonts.py
cd "c:\Users\laure\OneDrive\Studium-SBG\SoS 25\Datenerfassung\eigenes projekt\Projekt1-1" ; python fix_fonts.py
cd "c:\Users\laure\OneDrive\Studium-SBG\SoS 25\Datenerfassung\eigenes projekt\Projekt1-1" ; python -c "
with open('spotify_tab_modern.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
