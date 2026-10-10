import "./jsdom_setup";
import fs from "fs";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MainArea } from "../src/components/MainArea";
import { resolveStatus, verdictHeading } from "../src/components/LegalBasisPanel";
const fixtures = JSON.parse(fs.readFileSync(require("path").join(__dirname,"fixtures.json"),"utf-8"));
const noop = () => {};
function assert(value: unknown, message: string) { if (!value) throw new Error(message); }
(async () => {
  let tested = 0;
  for (const [name, fx] of Object.entries(fixtures) as [string,any][]) {
    document.body.innerHTML = "<div id='root'></div>";
    const root=createRoot(document.getElementById("root")!);
    await act(async()=>{root.render(<MainArea sessionTitle="QA" messages={[]} onSendMessage={noop}
      onTriggerAppraisal={noop} isPending={false} checklist={fx.checklist} isSubjectToAppraisal={fx.isSubject}
      appraisalReason={fx.reason} appraisalBasis={fx.basis} warnings={fx.warnings}
      projectInfo={{name:"QA",basements:0,location:"",investor:"",designer:"",stage:"",length:0,width:0,height:0,commercialDetails:"",...fx.project}}
      onExportReport={noop} isExporting={false} onExportReportPdf={noop} isExportingPdf={false}
      isSidebarOpen={false} onToggleSidebar={noop}/>);});
    assert(document.body.textContent?.includes("Chưa có hạng mục được xác nhận"),name+": no false compliance percentage");
    const btn=Array.from(document.querySelectorAll("button")).find(b=>b.textContent?.includes("Kết luận Pháp lý PCCC"));
    assert(btn,name+": verdict navigation");
    await act(async()=>{(btn as HTMLElement).click();});
    const card=document.getElementById("verdict-badge-card");
    if (card) await act(async()=>{card.click();});
    const text=document.body.textContent || "";
    assert(text.includes(verdictHeading(fx.basis.status,fx.basis)),name+": authoritative heading");
    assert(text.includes(fx.basis.conclusion),name+": authoritative conclusion");
    assert(!text.includes("BỞI CƠ QUAN CÔNG AN"),name+": no blanket authority statement");
    assert(!text.includes("bất kể quy mô"),name+": no unsupported karaoke exemption from thresholds");
    for (const row of fx.basis.thresholds) assert(text.includes(row.limitText),name+": threshold text");
    await act(async()=>{root.unmount();});
    tested++;
  }
  assert(resolveStatus(null,false)==="insufficient_data","missing basis must never imply exemption");
  console.log(`PASS: ${tested} React verdict fixtures, missing-basis fallback, unsupported legal claims and unverified compliance labels.`);
})().then(()=>{window.close(); process.exit(0);}).catch(error=>{console.error(error);window.close();process.exit(1);});
