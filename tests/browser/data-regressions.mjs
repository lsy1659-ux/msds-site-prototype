import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve, join} from 'node:path';
import vm from 'node:vm';

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const products = JSON.parse(readFileSync(join(ROOT, 'data/msds.public.json'), 'utf8'));
const context = vm.createContext({window:{location:{search:'',hostname:'localhost'}},
  document:{addEventListener(){}}, URLSearchParams, URL, console});
vm.runInContext(readFileSync(join(ROOT,'js/guide.js'),'utf8'),context);
const guide = vm.runInContext('({cleanList,getEmergencyItems})',context);
let groups = 0;
for(const product of products){
  for(const [key, values] of Object.entries(product.firstAid || {})){
    const expected = [...new Set(values.map(s=>String(s || '').replace(/^[-•○\s]+/,'').trim()).filter(Boolean))];
    assert.equal(Array.from(guide.cleanList(values,0)).join('\n'),expected.join('\n'),`${product.id} ${key}: 원문 문구가 누락·축약됨`);
    groups++;
  }
}
const known = ['msds-131','msds-138','msds-078','msds-085','msds-087','msds-pdf-37736004f8e3d7b1','msds-pdf-25117e7770dfe7d6'];
for(const id of known){
  const product = products.find(p=>p.id===id);
  const items = Array.from(guide.getEmergencyItems(product,new Set()));
  for(const [key,label] of [['eye','눈에 들어갔을 때'],['skin','피부에 닿았을 때'],['inhalation','흡입했을 때'],['ingestion','삼켰을 때']]){
    const first = product.firstAid?.[key]?.[0];
    if(!first) continue;
    assert.ok(items.some(x=>x.label===label && x.text===first),`${id} ${key}: 채워진 응급조치가 비어 있음`);
  }
}
console.log(`응급조치 ${groups}개 등록 그룹의 문구 보존 / 누락 7개 제품 경로: PASS`);

const substanceContext=vm.createContext({window:{location:{search:'',hostname:'localhost'}},document:{addEventListener(){}},URLSearchParams,URL,console});
vm.runInContext(readFileSync(join(ROOT,'js/substance.js'),'utf8'),substanceContext);
const substance=vm.runInContext('({cleanCas,buildSubstances})',substanceContext);
assert.equal(substance.cleanCas('67-64-1'),'67-64-1');
for(const invalid of ['2028-08-3','2028-08-30','67-64-10','T-2023-00604'])assert.equal(substance.cleanCas(invalid),'');
const grouping=substance.buildSubstances(products);
assert.ok(!grouping.substances.some(s=>s.cas==='2028-08-3'));
for(const id of ['msds-004','msds-005','msds-012'])assert.ok(grouping.orphans.some(x=>x.productId===id && x.sourceIdentifier==='T-2023-00604(2028-08-30)'));
console.log('CAS 전체 토큰·체크 숫자 / T식별자 보존 / 가짜 물질 그룹 제외: PASS');

function handoffEnvironment(storage){
  const links=['index.html','label.html','guide.html','index.html?offline=1'].map(href=>({href,getAttribute(){return this.href},setAttribute(k,v){this.href=v}}));
  const win={location:{pathname:'/label.html',search:'?dataMode=public'},sessionStorage:storage};
  const ctx=vm.createContext({window:win,document:{querySelectorAll(){return links}},URLSearchParams,console});
  vm.runInContext(readFileSync(join(ROOT,'js/handoff.js'),'utf8'),ctx);
  return {win,links};
}
const memory=new Map();
const storage={setItem(k,v){memory.set(k,v)},getItem(k){return memory.get(k)??null}};
for(const backend of [storage,{setItem(){throw new Error('quota')},getItem(){throw new Error('blocked')}}]){
  const e=handoffEnvironment(backend), ids=products.map(p=>p.id);
  e.win.MsdsHandoff.carry(ids);
  const target=e.links.find(x=>x.href.startsWith('guide.html'));
  if(backend===storage)assert.ok(target.href.length<1800 && target.href.includes('selection='));
  else assert.ok(target.href.includes('product='));
  e.win.location.pathname='/guide.html'; e.win.location.search=target.href.slice(target.href.indexOf('?'));
  assert.deepEqual(Array.from(e.win.MsdsHandoff.requested()),ids);
  assert.equal(e.links[0].href,'index.html?dataMode=public');
  assert.equal(e.links[3].href,'index.html?offline=1');
  e.win.MsdsHandoff.carry([ids[0]]);
  assert.ok(e.links[0].href.includes(`product=${ids[0]}`));
  e.win.location.search='?selection=broken';
  assert.deepEqual(Array.from(e.win.MsdsHandoff.requested()),[]);
}
console.log(`${products.length}개 선택 전달 / URL 길이 / 저장소 차단 fallback / 한 제품·오프라인 링크: PASS`);
