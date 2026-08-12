"""Inventory every FastAPI mutation and require an explicit experiment policy."""
from __future__ import annotations
import json,re,tempfile
from pathlib import Path
from app.config import settings
_INVENTORY_DB = Path(tempfile.gettempdir()) / "ai-db-creator-route-inventory.sqlite"
settings.database_url = f"sqlite:///{_INVENTORY_DB.as_posix()}"
settings.enable_auth = False
from app.main import app
from app.api.dependencies import endpoint_capability
from app.services.experiment_service import CAPABILITIES

PROJECT_EXPECTED={
 "generate":{"ai_only","ai_interface"},"generate-async":{"ai_only","ai_interface"},"populate":{"ai_only","ai_interface"},"populate-async":{"ai_only","ai_interface"},
 "chat":{"ai_interface"},"chat-accept":{"ai_interface"},"schema":{"manual","ai_interface"},"import-sql":{"manual","ai_interface"},"data":{"manual","ai_interface"},
 "query":{"manual","ai_interface"},"execute-query":{"manual","ai_interface"},"documents":{"manual","ai_only","ai_interface"},"interactions":{"manual","ai_only","ai_interface"},
 "export-interactions":{"manual","ai_only","ai_interface"},"backup":{"manual","ai_only","ai_interface"},"restore":{"manual","ai_interface"},"export-async":{"manual","ai_only","ai_interface"},
 "project_delete":{"manual","ai_only","ai_interface"},
}
GLOBAL_POLICY={
 "POST /api/projects":"pre_session_authenticated","POST /api/experiments/compare":"experiment_ai_generate_gate","POST /api/surveys/nasa-tlx":"experiment_survey_gate",
 "POST /api/surveys/sus":"experiment_survey_gate","POST /api/experiments/sessions":"experiment_mode_authenticated_owned_project",
 "POST /api/experiments/sessions/current/{transition}":"experiment_mode_authenticated_transition","POST /api/progress/{project_id}":"authenticated_owned_project_server_state",
 "POST /api/settings/ollama-test":"admin_only","PUT /api/settings":"admin_only","POST /api/benchmark/run":"authenticated_research_tool",
 "POST /api/surveys/vote":"authenticated_owned_project",
}
GET_SIDE_EFFECT_AUDIT={"GET /api/projects/{project_id}/export":"read_only_serialization","GET /api/projects/{project_id}/export-full":"read_only_serialization"}

def application_routes():
 routes=[]
 for item in app.routes:
  included=getattr(item,"original_router",None)
  routes.extend(included.routes if included is not None else [item])
 return routes

def _inventory():
 return sorted({(method,route.path) for route in application_routes() for method in getattr(route,"methods",set()) if route.path.startswith('/api') and method in {'POST','PUT','PATCH','DELETE'}})
def validate():
 failures=[]; inventory=[]
 for method,path in _inventory():
  key=f"{method} {path}"; policy=None
  if path.startswith('/api/projects/{project_id}'):
   tail=path.split('/api/projects/{project_id}',1)[1].strip('/'); action=tail.split('/',1)[0] if tail else 'project_delete'
   expected=PROJECT_EXPECTED.get(action); sample=re.sub(r'\{[^}]+\}','sample',path)
   capability=endpoint_capability(sample,method); actual={arm for arm,caps in CAPABILITIES.items() if capability in caps}; policy=f"capability:{capability}"
   if expected is None: failures.append({"route":key,"reason":"missing_explicit_project_policy"})
   elif actual!=expected: failures.append({"route":key,"reason":"arm_matrix_mismatch","expected":sorted(expected),"actual":sorted(actual)})
  else:
   policy=GLOBAL_POLICY.get(key)
   if not policy: failures.append({"route":key,"reason":"missing_explicit_global_policy"})
  inventory.append({"method":method,"path":path,"policy":policy})
 for key in GET_SIDE_EFFECT_AUDIT:
  if not any(f"{method} {path}"==key for method,path in {(m,r.path) for r in application_routes() for m in getattr(r,'methods',set())}): failures.append({"route":key,"reason":"audited_get_missing"})
 return {"status":"pass" if not failures else "fail","inventory":inventory,"audited_gets":GET_SIDE_EFFECT_AUDIT,"failures":failures}
if __name__=='__main__':
 r=validate();print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='pass' else 1)
