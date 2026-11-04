import './jsdom_setup';
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import assert from 'node:assert/strict';
import { AppHeader } from '../src/layouts/AppHeader';
import { EMPTY_PROJECT } from '../src/types';

const g: any = globalThis;
const tick = async () => {
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0));
  });
};
const response = (body: any, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

async function run() {
  localStorage.setItem('pccc_token', 'qa-token');
  const root = createRoot(document.getElementById('root')!);
  const noop = () => {};

  const baseHeaderProps: any = {
    onToggleSidebar: noop,
    project: EMPTY_PROJECT,
    reviewState: 'draft',
    activeTab: 'chat',
    onChangeTab: noop,
    onOpenSpecsDrawer: noop,
    onOpenOcrUpload: noop,
    onTriggerAppraisal: noop,
    isPending: false,
    hasAreaContradiction: false,
    hasChecklist: false,
    theme: 'light',
    onToggleTheme: noop,
    onExportDocx: noop,
    onExportPdf: noop,
    onExportJson: noop,
    isExportingDocx: false,
    isExportingPdf: false,
    isExportingJson: false,
  };

  let aiCalls: string[] = [];

  // 1. Staff role must NOT see AI Health Indicator and must NOT call /api/health/ai
  g.fetch = async (url: string) => {
    aiCalls.push(url);
    return response({ geminiApiKeyConfigured: true, status: 'unknown', detail: 'OK' });
  };
  await act(async () => {
    root.render(
      <AppHeader
        {...baseHeaderProps}
        currentUser={{ id: 's1', username: 'staff1', fullName: 'Nhân viên 1', role: 'staff' }}
      />
    );
  });
  await tick();
  assert.equal(document.getElementById('ai-health-indicator'), null, 'Staff must NOT see AI health indicator');
  assert.equal(aiCalls.length, 0, 'Staff must NOT trigger /api/health/ai request');
  console.log('PASS Pkg4.1: Staff account does not render AI health indicator or call /api/health/ai');

  // 2. Admin role with unconfigured GEMINI_API_KEY
  g.fetch = async (url: string) => {
    aiCalls.push(url);
    return response({
      geminiApiKeyConfigured: false,
      status: 'unknown',
      detail: 'Chưa cấu hình GEMINI_API_KEY trên máy chủ.',
    });
  };
  await act(async () => {
    root.render(
      <AppHeader
        {...baseHeaderProps}
        currentUser={{ id: 'a1', username: 'admin', fullName: 'Quản trị viên', role: 'admin' }}
      />
    );
  });
  await tick();
  const indicatorUnconf = document.getElementById('ai-health-indicator');
  assert.notEqual(indicatorUnconf, null, 'Admin MUST see AI health indicator');
  assert.equal(indicatorUnconf?.getAttribute('data-status'), 'unconfigured');
  assert.ok(indicatorUnconf?.textContent?.includes('Gemini AI: Chưa cấu hình'));
  console.log('PASS Pkg4.2: Admin sees unconfigured Gemini AI status when key is missing');

  // 3. Admin role with configured GEMINI_API_KEY -> Click to live ping -> OK
  await act(async () => {
    root.unmount();
  });
  document.body.innerHTML = '<div id="root"></div>';
  const root2 = createRoot(document.getElementById('root')!);
  aiCalls = [];
  g.fetch = async (url: string) => {
    aiCalls.push(url);
    if (url.includes('ping=true')) {
      return response({
        geminiApiKeyConfigured: true,
        status: 'ok',
        detail: 'Gọi Gemini API thành công.',
      });
    }
    return response({
      geminiApiKeyConfigured: true,
      status: 'unknown',
      detail: 'Đã cấu hình, chưa kiểm tra kết nối thật (dùng ?ping=true để kiểm tra).',
    });
  };
  await act(async () => {
    root2.render(
      <AppHeader
        {...baseHeaderProps}
        currentUser={{ id: 'a1', username: 'admin', fullName: 'Quản trị viên', role: 'admin' }}
      />
    );
  });
  await tick();
  const indicatorConf = document.getElementById('ai-health-indicator')!;
  assert.equal(indicatorConf.getAttribute('data-status'), 'configured');
  assert.ok(indicatorConf.textContent?.includes('Gemini AI: Sẵn sàng'));

  // Click indicator to trigger live ping
  await act(async () => {
    indicatorConf.click();
  });
  await tick();
  assert.ok(aiCalls.some((u) => u.includes('/api/health/ai?ping=true')), 'Clicking indicator triggers ?ping=true');
  assert.equal(indicatorConf.getAttribute('data-status'), 'ok');
  assert.ok(indicatorConf.textContent?.includes('Gemini AI: Hoạt động'));
  console.log('PASS Pkg4.3: Admin sees configured status and live ping transitions to Hoạt động (ok)');

  // 4. Live ping failure transitions to error state
  g.fetch = async () =>
    response({
      geminiApiKeyConfigured: true,
      status: 'error',
      detail: 'Không gọi được Gemini API: Quota exceeded',
    });
  await act(async () => {
    indicatorConf.click();
  });
  await tick();
  assert.equal(indicatorConf.getAttribute('data-status'), 'error');
  assert.ok(indicatorConf.textContent?.includes('Gemini AI: Lỗi kết nối'));
  console.log('PASS Pkg4.4: Admin live ping failure transitions to Lỗi kết nối (error)');

  // 5. Recover to ok, then network exception during live ping must transition to error (not stay ok)
  g.fetch = async () =>
    response({
      geminiApiKeyConfigured: true,
      status: 'ok',
      detail: 'Gọi Gemini API thành công.',
    });
  await act(async () => {
    indicatorConf.click();
  });
  await tick();
  assert.equal(indicatorConf.getAttribute('data-status'), 'ok');

  g.fetch = async () => {
    throw new Error('Network disconnected');
  };
  await act(async () => {
    indicatorConf.click();
  });
  await tick();
  assert.equal(indicatorConf.getAttribute('data-status'), 'error');
  assert.ok(indicatorConf.getAttribute('title')?.includes('Không thể kết nối tới máy chủ'));
  console.log('PASS Pkg4.5: Network exception on live ping transitions from Hoạt động (ok) to Lỗi kết nối (error)');

  await act(async () => {
    root2.unmount();
  });
}

run()
  .then(() => {
    window.close();
    process.exit(0);
  })
  .catch((e) => {
    console.error(e);
    process.exit(1);
  });
