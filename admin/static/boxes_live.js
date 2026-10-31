/* Live page and starter layouts operate only inside the dashboard preview. */
(() => {
  const panel=document.getElementById('panel-boxes'),frame=document.getElementById('previewIframe');
  if(!panel||!frame)return;
  let live=false,ready=false,queued=false,frameObserver;
  const tools=document.createElement('div');tools.className='boxes-live-tools';
  tools.innerHTML='<button class="form-btn" id="boxesLiveToggle" aria-pressed="false">Trang thật</button><button class="form-btn" id="boxesTemplatesToggle" aria-expanded="false">Chọn bố cục mẫu</button><span id="boxesLiveStatus" role="status">Chỉnh trong bản xem trước · Bấm Áp dụng lên trang khi hoàn tất</span>';
  document.getElementById('boxesToolbar').before(tools);
  const templates=document.createElement('div');templates.className='boxes-templates';templates.hidden=true;
  for(const [key,title,description,diagram] of [
    ['sidebar','Nội dung + cột bên','Bài viết và gói bên trái, tiện ích bên phải.','▰▰▰\n▰▰ ▪\n▰▰ ▪'],
    ['stack','Một cột','Dễ đọc, nội dung xếp lần lượt từ trên xuống.','▰▰▰\n▰▰▰\n▰▰▰'],
    ['grid','Hai cột cân đối','Các khung chia đều, phù hợp trang tổng hợp.','▰▰▰\n▰ ▰\n▰ ▰']]){
    const button=document.createElement('button');button.className='boxes-template';button.innerHTML=`<span class="boxes-template-diagram" aria-hidden="true">${diagram}</span><strong>${title}</strong><span>${description}</span>`;
    button.onclick=()=>applyTemplate(key);templates.append(button);
  }
  tools.after(templates);
  const status=document.getElementById('boxesLiveStatus');
  const toggle=document.getElementById('boxesLiveToggle');
  const templateToggle=document.getElementById('boxesTemplatesToggle');
  templateToggle.onclick=()=>{templates.hidden=!templates.hidden;templateToggle.setAttribute('aria-expanded',String(!templates.hidden));};
  function init(){
    const doc=frame.contentDocument;if(!doc||!doc.body||doc.readyState!=='complete')return false;
    const nodes=[...doc.querySelectorAll('[data-box]')].filter(n=>!n.parentElement.closest('[data-box]'));
    if(!nodes.length)return false;
    if(!document.querySelector('#previewStage .prev-box')){
      nodes.forEach(node=>{const rect=node.getBoundingClientRect();if(rect.width&&rect.height)createBoxOnCanvas({key:node.dataset.box,title:node.querySelector('h1,h2,h3')?.textContent||node.dataset.box,x:Math.max(0,rect.x),y:Math.max(0,rect.y+frame.contentWindow.scrollY),w:rect.width,h:rect.height,type:'content'});});
    }
    if(!doc.getElementById('boxes-live-style')){
      const style=doc.createElement('style');style.id='boxes-live-style';
      style.textContent='html{min-width:0!important;overflow:hidden!important}body{display:block!important;transform:none!important;margin:0!important;padding:0!important;min-width:0!important;position:relative!important}[data-preview-wrapper]{display:contents!important}[data-preview-exclude]{display:none!important}[data-box]{position:absolute!important;margin:0!important;box-sizing:border-box!important;max-width:none!important;min-width:0!important;overflow:auto!important}';
      nodes.forEach(node=>{
        node.dataset.previewDisplay=frame.contentWindow.getComputedStyle(node).display;
        let parent=node.parentElement;
        while(parent&&parent!==doc.body){parent.setAttribute('data-preview-wrapper','');parent=parent.parentElement;}
      });
      [doc.body,...doc.querySelectorAll('[data-preview-wrapper]')].forEach(parent=>{
        [...parent.children].forEach(child=>{if(!child.hasAttribute('data-box')&&!child.hasAttribute('data-preview-wrapper')&&!['SCRIPT','STYLE','LINK'].includes(child.tagName))child.setAttribute('data-preview-exclude','');});
      });
      doc.head.append(style);
    }
    if(frameObserver)frameObserver.disconnect();
    frameObserver=new MutationObserver(records=>{if(records.some(record=>record.target.matches?.('[data-box]')))schedule();});
    frameObserver.observe(doc.body,{subtree:true,attributes:true,attributeFilter:['style']});
    ready=true;return true;
  }
  function mirror(){
    queued=false;if(!live)return;if(!ready&&!init()){status.textContent='Đang tải nội dung trang…';return;}
    const doc=frame.contentDocument;
    doc.querySelectorAll('[data-box]').forEach(element=>{if(!previewBoxesData[element.dataset.box])element.style.setProperty('display','none','important');});
    Object.entries(previewBoxesData).forEach(([key,data])=>{
      const element=[...doc.querySelectorAll('[data-box]')].find(n=>n.dataset.box===key);
      const overlay=[...document.querySelectorAll('#previewStage [data-box]')].find(n=>n.dataset.box===key);
      if(overlay)overlay.classList.toggle('has-live-source',!!element);
      if(!element)return;
      const properties={left:(data.x||0)+'px',top:(data.y||0)+'px',width:(data.w||300)+'px',height:(data.h||200)+'px',right:'auto',bottom:'auto','min-height':'0px','max-height':'none',display:data.hidden?'none':(element.dataset.previewDisplay==='none'?'block':element.dataset.previewDisplay||'block'),transform:`rotate(${data.rotation||0}deg) scale(${data.scale||1})`,'z-index':String(data.zIndex||0)};
      for(const [field,prop] of [['paddingT','padding-top'],['paddingR','padding-right'],['paddingB','padding-bottom'],['paddingL','padding-left']])if(data[field]!==undefined)properties[prop]=data[field]+'px';
      if(data.opacity!==undefined)properties.opacity=String(data.opacity/100);
      for(const [prop,value] of Object.entries(properties)){
        if(element.style.getPropertyValue(prop)!==value||element.style.getPropertyPriority(prop)!=='important')element.style.setProperty(prop,value,'important');
      }
    });
    frame.style.height=previewCanvasH+'px';frame.style.width=previewCanvasW+'px';
    status.textContent='Trang thật · Chọn khung, bật chỉnh sửa rồi kéo hoặc đổi kích thước';
  }
  function schedule(){if(!queued){queued=true;requestAnimationFrame(mirror);}}
  toggle.onclick=()=>{live=!live;panel.classList.toggle('boxes-live',live);toggle.setAttribute('aria-pressed',String(live));toggle.textContent=live?'Xem sơ đồ khung':'Xem giao diện trang';if(live){schedule();requestAnimationFrame(()=>zoomFit());}else status.textContent='Sơ đồ vị trí các khung · Chuyển sang giao diện trang để xem nội dung';};
  frame.addEventListener('load',()=>{ready=false;if(live)schedule();});
  new MutationObserver(schedule).observe(document.getElementById('previewStage'),{subtree:true,attributes:true,childList:true,attributeFilter:['style','class']});
  function applyTemplate(kind){
    if(!document.querySelector('#previewStage .prev-box')&&!init()){status.textContent='Trang chưa tải xong. Hãy thử lại sau vài giây.';return;}
    if(!confirm('Sắp xếp các khung theo mẫu này? Bạn có thể hoàn tác bằng Ctrl Z.'))return;
    saveUndoSnapshot();
    const entries=Object.entries(previewBoxesData).filter(([,d])=>!d.hidden);
    const width=1200,gap=24,pad=24;
    const headers=entries.filter(([k])=>['masthead','hello-banner','meta'].includes(k))
      .sort((a,b)=>['masthead','hello-banner','meta'].indexOf(a[0])-['masthead','hello-banner','meta'].indexOf(b[0]));
    const footers=entries.filter(([k])=>k==='hint-box');
    const body=entries.filter(e=>!headers.includes(e)&&!footers.includes(e));
    let y=pad;
    function place([key,data],x,top,w,h){
      Object.assign(data,{x,y:top,w,h,rotation:0,scale:1,marginT:0,marginR:0,marginB:0,marginL:0});
      applyBoxStyle(key);
      const box=document.querySelector('#previewStage [data-box="'+CSS.escape(key)+'"]');
      if(box){box.dataset.naturalW=w;box.dataset.naturalH=h;const inner=box.querySelector('.prev-scale');if(inner){inner.style.width=w+'px';inner.style.height=h+'px';}}
    }
    const height=entry=>Math.max(120,Math.min(900,Number(entry[1].h)||240));
    headers.forEach(entry=>{const h=height(entry);place(entry,pad,y,width,h);y+=h+gap;});
    if(kind==='stack'){
      body.forEach(entry=>{const h=height(entry);place(entry,pad,y,width,h);y+=h+gap;});
    }else if(kind==='grid'){
      for(let i=0;i<body.length;i+=2){const pair=body.slice(i,i+2),h=Math.max(...pair.map(height));pair.forEach((entry,col)=>place(entry,pad+col*(width+gap)/2,y,pair.length===1?width:(width-gap)/2,h));y+=h+gap;}
    }else{
      const main=body.filter(([k])=>!/stars|music|moon|links|widget/.test(k));
      const side=body.filter(entry=>!main.includes(entry));
      const columns=main.length&&side.length?[main,side]:[body];
      const bottoms=columns.map((column,index)=>{
        let top=y;column.forEach(entry=>{const h=height(entry);place(entry,pad+(index?876:0),top,columns.length===1?width:index?324:852,h);top+=h+gap;});return top;
      });
      const bottom=Math.max(y,...bottoms);
      columns.forEach((column,index)=>{const last=column[column.length-1];if(last&&bottoms[index]<bottom){last[1].h+=bottom-bottoms[index];applyBoxStyle(last[0]);}});
      y=bottom;
    }
    footers.forEach(entry=>{const h=height(entry);place(entry,pad,y,width,h);y+=h+gap;});
    previewCanvasW=width+pad*2;previewCanvasH=Math.max(240,y);
    updateCanvasSize();renderLayers();renderInspector();
    if(!live)toggle.click();
    zoomFit();schedule();
    status.textContent='Đã xếp theo mẫu trong bản xem trước · Chưa áp dụng lên trang';
    templates.hidden=true;templateToggle.setAttribute('aria-expanded','false');
  }
  // The page itself is the default preview. Cloned markup is only a wireframe:
  // it cannot inherit the complete stylesheet and behavior of the source page.
  toggle.click();
})();
