from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

client = MongoClient(os.environ['MONGO_URL'])
db = client['legal_aid']

print('=== CORPUS COUNTS ===')
hindu_count = db.legal_sections.count_documents({"act_name": {"$regex": "Hindu Marriage", "$options": "i"}})
special_count = db.legal_sections.count_documents({"act_name": {"$regex": "Special Marriage", "$options": "i"}})
ji_count = db.judicial_invalidations.count_documents({})
rq_count = db.review_queue.count_documents({})

print(f'Hindu Marriage Act sections:    {hindu_count}  (expect 37)')
print(f'Special Marriage Act sections:  {special_count}  (expect 57)')
print(f'judicial_invalidations total:   {ji_count}  (expect 16)')
print(f'review_queue total:             {rq_count}  (expect 650)')

print()
print('=== JUDICIAL INVALIDATIONS (all) ===')
for doc in db.judicial_invalidations.find({}, {'act_name':1, 'section_number':1, 'status':1, 'verified_by':1, 'user_warning':1}):
    print(f"  act={doc.get('act_name')}, sec={doc.get('section_number')}, status={doc.get('status')}, verified_by={doc.get('verified_by')}")

print()
print('=== IT Act 66A in legal_sections ===')
sec66a = db.legal_sections.find_one({
    "act_name": {"$regex": "Information Technology", "$options": "i"},
    "section_number": {"$regex": "66A", "$options": "i"}
})
if sec66a:
    print(f'  act_name:       {sec66a.get("act_name")}')
    print(f'  section_number: {sec66a.get("section_number")}')
    print(f'  is_dead_law:    {sec66a.get("is_dead_law")}')
    print(f'  serve_warning:  {sec66a.get("serve_warning")}')
    print(f'  jurisdiction:   {sec66a.get("jurisdiction")}')
    text = str(sec66a.get("section_text", ""))
    print(f'  section_text (first 300): {text[:300]}')
else:
    print('  IT Act 66A NOT FOUND in legal_sections')

print()
print('=== IPC 377 in legal_sections ===')
ipc377 = db.legal_sections.find_one({
    "act_name": {"$regex": "Indian Penal", "$options": "i"},
    "section_number": {"$regex": "377", "$options": "i"}
})
if ipc377:
    print(f'  FOUND: {ipc377}')
else:
    print('  IPC 377 NOT FOUND (expected - IPC replaced by BNS)')

ipc_total = db.legal_sections.count_documents({"act_name": {"$regex": "Indian Penal", "$options": "i"}})
print(f'  Total IPC sections in DB: {ipc_total}')

print()
print('=== judicial_invalidations for IT Act 66A ===')
ji_66a = db.judicial_invalidations.find_one({
    "act_name": {"$regex": "Information Technology", "$options": "i"},
    "section_number": {"$regex": "66A", "$options": "i"}
})
if ji_66a:
    print(f'  Found JI for 66A: status={ji_66a.get("status")}, user_warning={ji_66a.get("user_warning")}')
else:
    print('  No judicial_invalidations entry for IT Act 66A')

client.close()
