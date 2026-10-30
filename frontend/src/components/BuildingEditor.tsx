import React, { useEffect, useRef, useState } from 'react';
import { BuildingComponent, ProjectInfo } from '../types';

export function BuildingEditor({ project, onUpdate }: { project: ProjectInfo; onUpdate: (info: Partial<ProjectInfo>) => void }) {
  const [items, setItems] = useState<BuildingComponent[]>(project.components || []);
  const dirty = useRef(false);

  useEffect(() => {
    if (!dirty.current) setItems(project.components || []);
  }, [project.components]);

  const commit = (next: BuildingComponent[]) => {
    dirty.current = false;
    setItems(next);
    onUpdate({ components: next, componentsComplete: false });
  };

  const change = (id: string, key: keyof BuildingComponent, value: string | number) => {
    dirty.current = true;
    setItems((prev) => prev.map((c) => (c.id === id ? { ...c, [key]: value } : c)));
  };

  const fields: Array<[keyof BuildingComponent, string]> = [
    ['floors', 'Tầng nổi'], ['height', 'Cao công trình (m)'], ['pcccHeight', 'Cao PCCC (m)'],
    ['floorArea', 'Diện tích một tầng (m²)'], ['totalFloorArea', 'Tổng sàn của nhà (m²)'], ['volume', 'Khối tích (m³)'],
  ];

  const choices = (key: 'hazardClass' | 'industrialSubtype', current: string, callback: (value: string) => void) => (
    <label className="block text-xs font-bold text-black my-2">
      <span className="block mb-1 text-black font-bold">{key === 'hazardClass' ? 'Hạng nguy hiểm cháy/nổ' : 'Phân loại sản xuất'}</span>
      <select
        aria-label={key === 'hazardClass' ? 'Hạng nguy hiểm cháy' : 'Phân loại sản xuất'}
        className="w-full border border-slate-300 p-2 rounded-lg bg-white text-black font-semibold text-xs focus:border-brand-orange outline-none"
        value={current}
        onChange={(e) => callback(e.target.value)}
      >
        <option value="" className="text-black bg-white">Chưa xác định</option>
        {key === 'hazardClass'
          ? ['A', 'B', 'C', 'D', 'E'].map((x) => <option key={x} value={x} className="text-black bg-white">{x}</option>)
          : <>
              <option value="other" className="text-black bg-white">Sản xuất công nghiệp khác — mục 9(d)</option>
              <option value="special" className="text-black bg-white">Loại chuyên ngành — cần rà soát riêng</option>
            </>}
      </select>
    </label>
  );

  return (
    <section className="border border-slate-300 rounded-xl p-3.5 space-y-2.5 bg-white text-black shadow-xs">
      <strong className="text-sm font-bold text-black block">Nhà xưởng, kho và hồ sơ nhiều hạng mục</strong>
      <p className="text-xs text-black leading-relaxed font-medium">
        Mỗi nhà giữ riêng số liệu. Không cộng các nhà thành một nhà hỗn hợp. Số 0 là chưa xác định; không suy khối tích từ diện tích × chiều cao.
      </p>

      {!items.length && (
        <>
          {choices('hazardClass', project.hazardClass || '', (value) => onUpdate({ hazardClass: value }))}
          {choices('industrialSubtype', project.industrialSubtype || '', (value) => onUpdate({ industrialSubtype: value }))}
          <label className="block text-xs font-bold text-black">
            <span className="block mb-1 text-black font-bold">Khối tích nhà (m³)</span>
            <input
              aria-label="Khối tích nhà"
              type="number"
              min="0"
              max="1000000000"
              step="any"
              className="w-full border border-slate-300 p-2 rounded-lg bg-white text-black font-semibold text-xs focus:border-brand-orange outline-none"
              defaultValue={project.volume || ''}
              onFocus={(e) => e.target.select()}
              onBlur={(e) => onUpdate({ volume: Number(e.target.value) || 0 })}
            />
          </label>
        </>
      )}

      {items.map((c) => (
        <article key={c.id} className="border border-slate-300 bg-slate-50 p-2.5 rounded-lg space-y-2 text-black" onBlur={(e) => { if (dirty.current && !e.currentTarget.contains(e.relatedTarget as Node)) commit(items); }}>
          <label className="block text-xs font-bold text-black">
            <span className="block mb-1 text-black font-bold">Tên hạng mục</span>
            <input aria-label="Tên hạng mục" className="w-full border border-slate-300 p-1.5 rounded-lg bg-white text-black font-medium text-xs focus:border-brand-orange outline-none" value={c.name} onChange={(e) => change(c.id, 'name', e.target.value)} />
          </label>
          <label className="block text-xs font-bold text-black">
            <span className="block mb-1 text-black font-bold">Loại/công năng</span>
            <input aria-label={`Loại ${c.name}`} className="w-full border border-slate-300 p-1.5 rounded-lg bg-white text-black font-medium text-xs focus:border-brand-orange outline-none" value={c.type} onChange={(e) => change(c.id, 'type', e.target.value)} placeholder="Nhà xưởng / Nhà kho / Văn phòng" />
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            {fields.map(([key, label]) => (
              <label key={key} className="block text-xs font-bold text-black">
                <span className="block mb-0.5 text-black truncate">{label}</span>
                <input aria-label={`${label} ${c.name}`} type="number" min="0" step={key === 'floors' ? '1' : 'any'} className="w-full border border-slate-300 p-1.5 rounded-lg bg-white text-black font-medium text-xs focus:border-brand-orange outline-none" value={Number(c[key]) || ''} onChange={(e) => change(c.id, key, Number(e.target.value))} />
              </label>
            ))}
          </div>
          {choices('hazardClass', c.hazardClass, (v) => change(c.id, 'hazardClass', v))}
          {choices('industrialSubtype', c.industrialSubtype, (v) => change(c.id, 'industrialSubtype', v))}
          <label className="block text-xs font-bold text-black">
            <span className="block mb-1 text-black font-bold">Bậc chịu lửa</span>
            <input aria-label={`Bậc chịu lửa ${c.name}`} className="w-full border border-slate-300 p-1.5 rounded-lg bg-white text-black font-medium text-xs focus:border-brand-orange outline-none" value={c.fireRating} onChange={(e) => change(c.id, 'fireRating', e.target.value)} />
          </label>
          {c.sourceText && <p className="text-xs whitespace-pre-wrap text-black font-medium">Nguồn trang {c.sourcePages.join(', ')}: {c.sourceText}</p>}
          <button type="button" className="text-xs text-red-700 hover:text-red-900 font-bold cursor-pointer" onClick={() => commit(items.filter((x) => x.id !== c.id))}>Xóa hạng mục {c.name}</button>
        </article>
      ))}

      <button
        type="button"
        className="w-full py-2 px-3 text-xs font-bold border border-slate-300 rounded-lg bg-slate-100 hover:bg-slate-200 text-black transition-colors cursor-pointer"
        onClick={() => commit([...items, { id: crypto.randomUUID(), name: `Hạng mục ${items.length + 1}`, type: '', floors: 0, basements: 0, height: 0, pcccHeight: 0, floorArea: 0, totalFloorArea: 0, volume: 0, hazardClass: '', industrialSubtype: '', fireRating: '', commercialDetails: '', sourcePages: [], sourceText: '' }])}
      >
        Thêm hạng mục độc lập
      </button>

      {items.length > 0 && (
        <>
          <label className="block text-xs font-bold text-black">
            <input type="checkbox" className="mr-1.5 accent-brand-orange" checked={project.componentsComplete === true} onChange={(e) => onUpdate({ componentsComplete: e.target.checked })} />
            Tôi đã kiểm tra và xác nhận danh sách đầy đủ
          </label>
          {(['sharedSystems', 'concurrentDesign'] as const).map((key) => (
            <label key={key} className="block text-xs font-bold text-black">
              <span className="block mb-1 text-black font-bold">{key === 'sharedSystems' ? 'Có dùng chung hệ thống báo cháy/chữa cháy?' : 'Các hạng mục thiết kế đồng thời?'}</span>
              <select className="w-full border border-slate-300 p-2 rounded-lg bg-white text-black font-semibold text-xs focus:border-brand-orange outline-none" value={project[key] === true ? 'yes' : project[key] === false ? 'no' : ''} onChange={(e) => { if (e.target.value) onUpdate({ [key]: e.target.value === 'yes' }); }}>
                <option value="" disabled className="text-black bg-white">Chưa xác nhận</option>
                <option value="yes" className="text-black bg-white">Có</option>
                <option value="no" className="text-black bg-white">Không</option>
              </select>
            </label>
          ))}
          <p className="text-xs font-bold text-black">Kiểm duyệt sẽ xét danh sách hạng mục ở đây; số liệu nhà đơn lẻ phía trên không thay thế các hạng mục.</p>
        </>
      )}
    </section>
  );
}
