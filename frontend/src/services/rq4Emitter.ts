import { api } from '../api/client'
export type Rq4Type='rename_column'|'add_constraint'|'remove_constraint'|'ignore_suggestion'|'accept_suggestion'|'navigation'|'schema_save'|'population_start'|'population_complete'|'validation_error'|'task_abandon'|'task_complete'
export type Rq4Action='open'|'close'|'add'|'remove'|'rename'|'accept'|'ignore'|'start'|'complete'|'retry'
export type Rq4Phase='onboarding'|'schema'|'population'|'validation'|'survey'|'completion'
type Event={type:Rq4Type;target_type:'project'|'table'|'column'|'relationship'|'suggestion';target_name:string;action?:Rq4Action;phase?:Rq4Phase;outcome?:'success'|'failure'|'cancelled'|'ignored';error_code?:string;operation_id:string;duration_ms?:number}
let scope='legacy'; let project='';
const storage=()=>typeof window==='undefined'?null:window.sessionStorage
const key=()=>`rq4-sequence:${project}:${scope}`
export function configureRq4Scope(projectId:string,sessionId:string,nextSequence:number){project=projectId;scope=sessionId;const current=Number(storage()?.getItem(key())||'0');storage()?.setItem(key(),String(Math.max(current,nextSequence-1)))}
function reserve(){const next=Number(storage()?.getItem(key())||'0')+1;storage()?.setItem(key(),String(next));return next}
export async function emitRq4(projectId:string,event:Event){
 if(project!==projectId){
  if(typeof (api as any).get==='function'){const state=await api.get(`/projects/${projectId}/interactions-next-sequence`);configureRq4Scope(projectId,state.session_id,state.next_sequence)}
  else configureRq4Scope(projectId,'legacy',1)
 }
 let sequence=reserve(); const operationToken=`${event.operation_id}:${sequence}`
 const send=()=>api.post(`/projects/${projectId}/interactions`,{...event,event_id:`${scope}:${operationToken}`,sequence_no:sequence,monotonic_ms:performance.now(),duration_ms:event.duration_ms||0,app_revision:import.meta.env.VITE_APP_REVISION||'development',payload_schema_version:'rq4-envelope-v1'})
 try{return await send()}catch(error:any){if(error?.status!==409)throw error;const state=await api.get(`/projects/${projectId}/interactions-next-sequence`);configureRq4Scope(projectId,state.session_id,state.next_sequence);sequence=reserve();return send()}
}
export function resetRq4ModuleForTest(){scope='legacy';project=''}
