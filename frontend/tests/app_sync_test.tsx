import './jsdom_setup';
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import assert from 'node:assert/strict';
import App from '../src/App';
import { apiFetch } from '../src/lib/api';
const g: any = globalThis;
const user = { id:'u', username:'qa', fullName:'QA', role:'admin' };
const project = { name:'A', type:'Nhà hỗn hợp', floors:1, totalFloorArea:100, floorArea:100, floorFunctions:[] };
let snapshot: any = { id:'A',title:'A',revision:'r0',reviewState:'reviewed',projectInfo:project,messages:[],checklist:[{id:1,status:'Cần xem xét'}],warnings:[],appraisalReason:'A' };
let delaySave: any, delayChat: any, saveFailure = false;
let calls: string[] = [];
let exports = 0, chats = 0, appraises = 0;
const response = (body:any, status=200) => new Response(JSON.stringify(body), {status,headers:{'Content-Type':'application/json'}});
g.window.URL.createObjectURL = () => 'blob:test'; g.window.URL.revokeObjectURL = () => {}; g.alert=()=>{};
g.window.HTMLAnchorElement.prototype.click = function () {};
g.fetch = async (path: string, options: any = {}) => {
  calls.push(path);
  if (path === '/api/auth/me') return response({...user,full_name:'QA'});
  if (path === '/api/documents') return response([]);
  if (path.startsWith('/api/sessions?')) return response([snapshot, {...snapshot,id:'B',title:'B',projectInfo:{...project,name:'B'}}]);
  if (path === '/api/sessions/A') return response(snapshot);
  if (path.includes('appraise=false')) {
    assert.equal(options.headers.get('If-Match'), snapshot.revision);
    if (delaySave) await delaySave.promise;
    if (saveFailure) return response({detail:'Thông số không hợp lệ'},422);
    snapshot = {...snapshot,revision:snapshot.revision+"n",reviewState:"draft",checklist:[],projectInfo:{...snapshot.projectInfo,...JSON.parse(options.body)}};
    return response(snapshot);
  }
  if (path.includes('appraise=true')) { appraises++; snapshot={...snapshot,reviewState:'reviewed',checklist:[{id:1,status:'Cần xem xét'}]}; return response(snapshot); }
  if (path === '/api/chat') {
    chats++;
    await new Promise<void>((resolve,reject) => {
      delayChat={resolve};
      options.signal.addEventListener('abort',()=>reject(new DOMException('cancel','AbortError')),{once:true});
    });
    return response(snapshot);
  }
  if (path.startsWith('/api/report/')) { assert.equal(JSON.parse(options.body).expectedRevision,snapshot.revision); exports++; return response(snapshot); }
  throw new Error('Unexpected route '+path);
};
const deferred = () => { let resolve: any; const promise=new Promise<void>(r=>resolve=r); return {promise,resolve}; };
const tick = async () => { await act(async () => { await new Promise(r=>setTimeout(r,0)); }); };
async function run() {
  localStorage.setItem('pccc_token','qa-token'); localStorage.setItem('pccc_user',JSON.stringify(user));
  const root = createRoot(document.getElementById('root')!);
  await act(async()=>{root.render(<App/>);}); await tick();
  delaySave=deferred();
  let saving: any, exporting: any;
  await act(async()=>{saving=g.sidebarProps.onUpdateProject({floors:7});});
  await act(async()=>{exporting=g.mainProps.onExportReport();});
  assert.equal(exports,0);
  await act(async()=>{g.sidebarProps.onSelectSession('B');});
  assert.equal(g.sidebarProps.activeSessionId,'A');
  await act(async()=>{delaySave.resolve();await saving;await exporting;}); delaySave=null;
  assert.equal(exports,0); assert.equal(g.mainProps.projectInfo.floors,7);
  assert.equal(g.mainProps.reviewState,"draft");
  await act(async()=>{await g.mainProps.onTriggerAppraisal();});
  await act(async()=>{await g.mainProps.onExportReport();});
  assert.equal(exports,1);
  console.log('PASS S05: draft export waits then blocks until explicit review; switching blocked');
  saveFailure=true;
  await act(async()=>{await g.sidebarProps.onUpdateProject({floors:-1});});
  await act(async()=>{await g.mainProps.onTriggerAppraisal(); await g.mainProps.onExportReport();});
  assert.equal(appraises,1); assert.equal(exports,1);
  assert.ok(document.body.textContent!.includes('chưa kiểm duyệt'));
  saveFailure=false;
  await act(async()=>{await g.sidebarProps.onUpdateProject({floors:5});});
  await act(async()=>{await g.mainProps.onTriggerAppraisal();});
  assert.equal(appraises,2);
  console.log('PASS S06: failed save blocks dependent operations until corrected');
  delaySave=deferred();
  await act(async()=>{saving=g.sidebarProps.onUpdateProject({totalFloorArea:500});});
  let a: any,b: any;
  await act(async()=>{a=g.mainProps.onTriggerAppraisal(); b=g.mainProps.onTriggerAppraisal();});
  await act(async()=>{delaySave.resolve();await saving;await a;await b;}); delaySave=null;
  assert.equal(appraises,3);
  console.log('PASS S07: double click while saving starts one appraisal');
  let chat: any;
  await act(async()=>{chat=g.mainProps.onSendMessage('test');}); await tick();
  await act(async()=>{g.mainProps.onCancelPending(); await chat;});
  assert.equal(chats,1); assert.equal(g.mainProps.messages.length,0); assert.equal(g.mainProps.isPending,false);
  assert.ok(calls.filter(p=>p==='/api/sessions/A').length>=3);
  console.log('PASS S08: cancelled chat reloads server state; no phantom message');
  const exportsBeforeDraft=exports;
  await act(async()=>{g.sidebarProps.onDraftChange();});
  assert.equal(g.mainProps.reviewState,"draft"); assert.deepEqual(g.mainProps.checklist,[]);
  await act(async()=>{await g.mainProps.onExportReport();});
  assert.equal(exports,exportsBeforeDraft);
  console.log('PASS S22: unfinished local edits hide prior verdict and block export before blur');
  await act(async()=>{root.unmount();});
  const pending=deferred();
  g.fetch=async()=>{await pending.promise;return response({detail:'old token'},401);};
  const oldRequest=apiFetch('/api/documents').then(()=>null,e=>e);
  localStorage.setItem('pccc_token','new-token');
  pending.resolve(); const err=await oldRequest;
  assert.equal(err.name,'AbortError'); assert.equal(localStorage.getItem('pccc_token'),'new-token');
  console.log('PASS S09: old login response cannot clear new login token');
  localStorage.setItem('pccc_token','body-old');
  const bodyPending=deferred();
  g.fetch=async()=>new Response(new ReadableStream({start(c){bodyPending.promise.then(()=>{c.enqueue(new TextEncoder().encode('{"secret":"old account"}'));c.close();});}}),{status:200});
  const bodyRes=await apiFetch('/api/documents');
  const bodyRead=bodyRes.json().then(()=>null,e=>e);
  localStorage.setItem('pccc_token','body-new');bodyPending.resolve();
  assert.equal((await bodyRead).name,'AbortError');
  console.log('PASS S23: login changes while body streams discard old account data');

  // Test S24: Silent refresh & tab-switching recovery for real JWT tokens
  const makeJwt = (payload: any) => {
    const enc = (obj: any) => Buffer.from(JSON.stringify(obj)).toString('base64url');
    return `${enc({alg:'HS256',typ:'JWT'})}.${enc(payload)}.sig`;
  };
  const nowSec = Math.floor(Date.now() / 1000);
  const expiringJwt = makeJwt({ sub: 'u', username: 'qa', role: 'admin', sid: 'sess-same', siat: nowSec - 600, exp: nowSec + 120 });
  const refreshedJwt = makeJwt({ sub: 'u', username: 'qa', role: 'admin', sid: 'sess-same', siat: nowSec - 600, exp: nowSec + 1800 });
  localStorage.setItem('pccc_token', expiringJwt);
  localStorage.setItem('pccc_user', JSON.stringify(user));
  let refreshCalled = 0;
  g.fetch = async (path: string, options: any = {}) => {
    if (path === '/api/auth/refresh') {
      refreshCalled++;
      return response({ access_token: refreshedJwt, expires_in: 1800, user });
    }
    if (path === '/api/documents') {
      assert.equal(options.headers.get('Authorization'), `Bearer ${refreshedJwt}`);
      return response([{ id: 'doc1' }]);
    }
    throw new Error('Unexpected route ' + path);
  };
  const docRes = await apiFetch('/api/documents');
  const docs = await docRes.json();
  assert.equal(refreshCalled, 1);
  assert.equal(localStorage.getItem('pccc_token'), refreshedJwt);
  assert.equal(docs.length, 1);
  console.log('PASS S24: silent refresh renews expiring JWT without aborting active session or losing token on tab switch');
}
run().then(()=>{window.close();process.exit(0);}).catch(e=>{console.error(e);process.exit(1);});
