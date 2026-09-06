import urllib.request
import json
from app.db.session import SessionLocal
from app.models.user import UserModel, SessionModel

db = SessionLocal()
admin_user = db.query(UserModel).filter(UserModel.role == 'super_admin').first()
sess = db.query(SessionModel).filter(SessionModel.user_email == admin_user.email).first()

# 1. Test GET /api/admin/models
req = urllib.request.Request('http://localhost:8000/api/admin/models', headers={'Cookie': f'sovereign_session={sess.token}'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print('GET /api/admin/models Status:', resp.status)
    print('Total Models returned:', len(data.get('models', [])))
    for m in data.get('models', []):
        print(' -', m.get('id'), m.get('name'), m.get('assignedRole'), 'Enabled:', m.get('isEnabled'))

# 2. Test POST /api/admin/models
post_payload = {
    'name': 'Claude 3.5 Sonnet',
    'provider': 'anthropic',
    'modelId': 'claude-3-5-sonnet-20241022',
    'assignedRole': 'coding-model',
    'apiKey': 'sk-ant-api03-testkey-1234567890',
    'contextWindow': 200000,
    'isEnabled': True
}
post_req = urllib.request.Request(
    'http://localhost:8000/api/admin/models',
    data=json.dumps(post_payload).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'Cookie': f'sovereign_session={sess.token}'}
)
with urllib.request.urlopen(post_req) as post_resp:
    created = json.loads(post_resp.read().decode('utf-8'))
    print('\nPOST /api/admin/models Created:', created.get('id'), created.get('name'), 'Key:', created.get('apiKey'))

created_id = created['id']

# 3. Test PATCH /api/admin/models/{id}/toggle
patch_req = urllib.request.Request(
    f'http://localhost:8000/api/admin/models/{created_id}/toggle',
    data=json.dumps({'isEnabled': False}).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'Cookie': f'sovereign_session={sess.token}'},
    method='PATCH'
)
with urllib.request.urlopen(patch_req) as patch_resp:
    toggled = json.loads(patch_resp.read().decode('utf-8'))
    print('PATCH Toggle Status:', toggled.get('id'), 'isEnabled:', toggled.get('isEnabled'))

# 4. Test DELETE /api/admin/models/{id}
del_req = urllib.request.Request(
    f'http://localhost:8000/api/admin/models/{created_id}',
    headers={'Cookie': f'sovereign_session={sess.token}'},
    method='DELETE'
)
with urllib.request.urlopen(del_req) as del_resp:
    deleted = json.loads(del_resp.read().decode('utf-8'))
    print('DELETE Status:', deleted)
