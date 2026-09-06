import urllib.request
import json
from app.db.session import SessionLocal
from app.models.user import UserModel, SessionModel
from app.services.managed_model_service import managed_model_service

db = SessionLocal()

# 1. Test listing models
res = managed_model_service.list_all(db)
print('--- Models in DB ---')
print('Total Models:', len(res['models']))
for m in res['models']:
    print(f"ID: {m['id']} | Name: {m['name']} | Role: {m['assignedRole']} | Enabled: {m['isEnabled']}")

# 2. Test creating a cloud model with API Key
new_m = managed_model_service.create_model(
    name='DeepSeek R1 Reasoner',
    provider='deepseek',
    model_id='deepseek-reasoner',
    assigned_role='reasoning-model',
    api_key='sk-test-deepseek-key-1234567890',
    api_base='https://api.deepseek.com',
    context_window=64000,
    is_enabled=True,
    db=db,
)
print('\n--- Created Model ---')
print(new_m)

# 3. Test toggling OFF
toggled_off = managed_model_service.toggle_model(new_m['id'], is_enabled=False, db=db)
print('\n--- Toggled Off ---', toggled_off['id'], 'isEnabled:', toggled_off['isEnabled'])

# 4. Test toggling ON
toggled_on = managed_model_service.toggle_model(new_m['id'], is_enabled=True, db=db)
print('--- Toggled On ---', toggled_on['id'], 'isEnabled:', toggled_on['isEnabled'])

# 5. Test deleting
deleted = managed_model_service.delete_model(new_m['id'], db=db)
print('--- Deleted ---', deleted)

# 6. Test HTTP endpoint with super_admin session
admin_user = db.query(UserModel).filter(UserModel.role == 'super_admin').first()
sess = db.query(SessionModel).filter(SessionModel.user_email == admin_user.email).first()
if not sess:
    sess = SessionModel(token='sess_test_admin', user_email=admin_user.email, created_at='2026-09-04T00:00:00Z', expires_at='2027-09-04T00:00:00Z')
    db.add(sess)
    db.commit()

req = urllib.request.Request('http://localhost:8000/api/admin/models', headers={'Cookie': f'sovereign_session={sess.token}'})
with urllib.request.urlopen(req) as resp:
    print('\n--- HTTP GET /api/admin/models --- Status:', resp.status)
    data = json.loads(resp.read().decode('utf-8'))
    print('HTTP Models Returned:', len(data.get('models', [])))
