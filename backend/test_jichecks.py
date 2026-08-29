from pymongo import MongoClient
import os, re
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

client = MongoClient(os.environ['MONGO_URL'])
dhara = client['dhara']

print('=== IPC 377 in judicial_invalidations ===')
ji_377 = dhara.judicial_invalidations.find_one({
    "section_number": "377",
    "act_name": {"$regex": "Indian Penal", "$options": "i"}
})
if ji_377:
    print(f'  Found: status={ji_377.get("status")}, user_warning={ji_377.get("user_warning")}')
else:
    print('  Not found')

print()
print('All IPC entries in judicial_invalidations:')
for doc in dhara.judicial_invalidations.find({"act_name": {"$regex": "Indian Penal", "$options": "i"}}):
    print(f'  sec={doc.get("section_number")}, status={doc.get("status")}, warning={str(doc.get("user_warning",""))[:80]}')

print()
print('=== IT Act 66A in judicial_invalidations ===')
ji_66a = dhara.judicial_invalidations.find_one({
    "section_number": "66A"
})
if ji_66a:
    print(f'  Found: status={ji_66a.get("status")}')
    print(f'  user_warning={ji_66a.get("user_warning")}')
    print(f'  act_name={ji_66a.get("act_name")}')

print()
print('=== Regex test for section extraction ===')
_SEC_RE = re.compile(r'(?:section|sections|sec|s\.|art(?:icle)?\.?)\s*(\d+[A-Za-z]{0,3})', re.IGNORECASE)
_ACT_HINTS = {
    "Indian Penal Code": re.compile(r'\bipc\b|indian\s+penal\s+code', re.I),
    "Information Technology": re.compile(r'\bit\s+act\b|information\s+technology', re.I),
}

tests = [
    'Tell me about IPC section 377',
    'What is IT Act section 66A',
    'section 377 of IPC',
    'IPC 377',
]
for t in tests:
    m = _SEC_RE.search(t)
    sec = m.group(1) if m else None
    act = None
    for act_name, pat in _ACT_HINTS.items():
        if pat.search(t):
            act = act_name
            break
    print(f'  query="{t}" -> sec={sec}, act_hint={act}')

client.close()
