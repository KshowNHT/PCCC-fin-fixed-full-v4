import React, { useEffect, useRef, useState } from 'react';
import { BuildingComponent, ProjectInfo } from '../types';

export function BuildingEditor({project, onUpdate}: {project: ProjectInfo; onUpdate: (info: Partial<ProjectInfo>) => void}) {
  const [items, setItems] = useState<BuildingComponent[]>(project.components || []);
  const dirty = useRef(false);
  useEffect(() => { if (!dirty.current) setItems(project.components || []); }, [project.components]);
  const commit = (next: BuildingComponent[]) => { dirty.current = false; setItems(next); onUpdate({components: next, componentsComplete: false}); };
  const change = (id: string, key: keyof BuildingComponent, value: string | number) => {
    dirty.current = true;
    setItems(prev => prev.map(c => c.id === id ? {...c, [key]: value} : c));
  };
  const fields: Array<[keyof BuildingComponent,string]> = [['floors','Tầng nổi'],['height','Cao công trình (m)'],['pcccHeight','Cao PCCC (m)'],['floorArea','Diện tích một tầng (m²)'],['totalFloorArea','Tổng sàn của nhà (m²)'],['volume','Khối tích (m³)']];
  const choices = (key: 'hazardClass' | 'industrialSubtype', current: string, callback: (value:string) => void) => <label className="block text-xs my-2">{key === 'hazardClass' ? 'Hạng nguy hiểm cháy/nổ' : 'Phân loại sản xuất'}<select aria-label={key === 'hazardClass' ? 'Hạng nguy hiểm cháy' : 'Phân loại sản xuất'} className="w-full border p-1 rounded" value={current} onChange={e=>callback(e.target.value)}><option value="">Chưa xác định</option>{key === 'hazardClass' ? ['A','B','C','D','E'].map(x=><option key={x}>{x}</option>) : <><option value="other">Sản xuất công nghiệp khác — mục 9(d)</option><option value="special">Loại chuyên ngành — cần rà soát riêng</option></>}</select></label>;
  return <section className="border rounded p-2 space-y-2 bg-slate-50">
    <strong className="text-sm">Nhà xưởng, kho và hồ sơ nhiều hạng mục</strong>
    <p className="text-xs">Mỗi nhà giữ riêng số liệu. Không cộng các nhà thành một nhà hỗn hợp. Số 0 là chưa xác định; không suy khối tích từ diện tích × chiều cao.</p>
    {!items.length && <>
      {choices('hazardClass', project.hazardClass || '', value=>onUpdate({hazardClass:value}))}
      {choices('industrialSubtype', project.industrialSubtype || '', value=>onUpdate({industrialSubtype:value}))}
      <label className="block text-xs">Khối tích nhà (m³)<input aria-label="Khối tích nhà" type="number" min="0" max="1000000000" step="any" className="w-full border p-1" defaultValue={project.volume || ''} onBlur={e=>onUpdate({volume:Number(e.target.value)})}/></label>
    </>}
    {items.map(c=><article key={c.id} className="border bg-white p-2 rounded" onBlur={e=>{if (dirty.current && !e.currentTarget.contains(e.relatedTarget as Node)) commit(items);}}>
      <label className="text-xs">Tên hạng mục<input aria-label="Tên hạng mục" className="w-full border p-1" value={c.name} onChange={e=>change(c.id,'name',e.target.value)}/></label>
      <label className="text-xs">Loại/công năng<input aria-label={`Loại ${c.name}`} className="w-full border p-1" value={c.type} onChange={e=>change(c.id,'type',e.target.value)} placeholder="Nhà xưởng / Nhà kho / Văn phòng"/></label>
      <div className="grid grid-cols-2 gap-1">{fields.map(([key,label])=><label key={key} className="text-xs">{label}<input aria-label={`${label} ${c.name}`} type="number" min="0" step={key==='floors'?'1':'any'} className="w-full border p-1" value={Number(c[key]) || ''} onChange={e=>change(c.id,key,Number(e.target.value))}/></label>)}</div>
      {choices('hazardClass',c.hazardClass,v=>change(c.id,'hazardClass',v))}
      {choices('industrialSubtype',c.industrialSubtype,v=>change(c.id,'industrialSubtype',v))}
      <label className="text-xs">Bậc chịu lửa<input aria-label={`Bậc chịu lửa ${c.name}`} className="w-full border p-1" value={c.fireRating} onChange={e=>change(c.id,'fireRating',e.target.value)}/></label>
      {c.sourceText && <p className="text-xs whitespace-pre-wrap text-slate-600">Nguồn trang {c.sourcePages.join(', ')}: {c.sourceText}</p>}
      <button type="button" className="text-xs text-red-700" onClick={()=>commit(items.filter(x=>x.id!==c.id))}>Xóa hạng mục {c.name}</button>
    </article>)}
    <button type="button" className="text-xs border rounded p-1" onClick={()=>commit([...items,{id:crypto.randomUUID(),name:`Hạng mục ${items.length+1}`,type:'',floors:0,basements:0,height:0,pcccHeight:0,floorArea:0,totalFloorArea:0,volume:0,hazardClass:'',industrialSubtype:'',fireRating:'',commercialDetails:'',sourcePages:[],sourceText:''}])}>Thêm hạng mục độc lập</button>
    {items.length>0 && <>
      <label className="block text-xs"><input type="checkbox" checked={project.componentsComplete === true} onChange={e=>onUpdate({componentsComplete:e.target.checked})}/> Tôi đã kiểm tra và xác nhận danh sách đầy đủ</label>
      {(['sharedSystems','concurrentDesign'] as const).map(key=><label key={key} className="block text-xs">{key==='sharedSystems'?'Có dùng chung hệ thống báo cháy/chữa cháy?':'Các hạng mục thiết kế đồng thời?'}<select className="w-full border p-1" value={project[key]===true?'yes':project[key]===false?'no':''} onChange={e=>{if(e.target.value)onUpdate({[key]:e.target.value==='yes'});}}><option value="" disabled>Chưa xác nhận</option><option value="yes">Có</option><option value="no">Không</option></select></label>)}
      <p className="text-xs font-semibold">Kiểm duyệt sẽ xét danh sách hạng mục ở đây; số liệu nhà đơn lẻ phía trên không thay thế các hạng mục.</p>
    </>}
  </section>;
}
