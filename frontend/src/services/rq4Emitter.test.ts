import { beforeEach, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import { configureRq4Scope, emitRq4, resetRq4ModuleForTest } from './rq4Emitter'

beforeEach(()=>{sessionStorage.clear();resetRq4ModuleForTest();vi.restoreAllMocks()})
it('keeps contiguous session/project sequence across simulated module reload',async()=>{
 const payloads:any[]=[];vi.spyOn(api,'post').mockImplementation(async(_path,data)=>{payloads.push(data);return {status:'logged'}})
 configureRq4Scope('p','s',1);await emitRq4('p',{type:'navigation',target_type:'project',target_name:'workspace',operation_id:'open'})
 resetRq4ModuleForTest();vi.spyOn(api,'get').mockResolvedValue({session_id:'s',next_sequence:2})
 await emitRq4('p',{type:'schema_save',target_type:'project',target_name:'schema',operation_id:'save'})
 expect(payloads.map(item=>item.sequence_no)).toEqual([1,2]);expect(new Set(payloads.map(item=>item.event_id)).size).toBe(2)
})
it('recovers expected sequence after 409 without raw payload',async()=>{
 vi.spyOn(api,'get').mockResolvedValue({session_id:'s',next_sequence:4});let calls=0;const payloads:any[]=[]
 vi.spyOn(api,'post').mockImplementation(async(_path,data)=>{payloads.push(data);if(calls++===0){const error:any=new Error('sequence');error.status=409;throw error}return {status:'logged'}})
 configureRq4Scope('p','s',1);await emitRq4('p',{type:'navigation',target_type:'project',target_name:'workspace',operation_id:'open'})
 expect(payloads.map(item=>item.sequence_no)).toEqual([1,4]);expect(JSON.stringify(payloads)).not.toContain('content')
})
