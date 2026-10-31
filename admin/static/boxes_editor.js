/* Layout controls reuse the existing canvas engine and persistence. */
(() => {
  const panel=document.getElementById('panel-boxes');
  if(!panel)return;
  const byId=id=>document.getElementById(id);
  panel.dataset.pane='canvas';
  const card=panel.querySelector('.section-card');
  card.querySelector('.section-title').remove();
  card.querySelector('.info-note').remove();
  const heading=document.createElement('div');heading.className='boxes-heading';
  heading.innerHTML='<div><h2>Bố cục trang</h2><p>Chọn khung bên trái, chỉnh vị trí trên canvas và tùy chỉnh ở bên phải.</p></div><button class="form-btn" id="boxesFocus">Mở rộng</button>';
  card.prepend(heading);
  const toolbar=byId('boxesToolbar');
  const buttons=[...toolbar.querySelectorAll('button')];
  const editing=document.createElement('div');editing.className='boxes-tool-group';
  editing.append(buttons[1],buttons[2]);
  buttons[1].title='Bật hoặc tắt kéo thả và thay đổi kích thước';
  buttons[2].textContent='＋ Thêm khung';
  const zoom=document.createElement('div');zoom.className='boxes-tool-group';
  const zoomInput=byId('zoomLevel');
  zoom.append(buttons[3],zoomInput,document.createTextNode('%'),buttons[4],buttons[5]);
  buttons[5].textContent='Vừa màn hình';buttons[5].title='Hiển thị toàn bộ bố cục trong canvas';
  zoomInput.setAttribute('aria-label','Tỷ lệ thu phóng (%)');
  const options=document.createElement('details');options.className='boxes-options';
  const summary=document.createElement('summary');summary.textContent='Tùy chọn canvas';
  const advanced=document.createElement('div');
  [...toolbar.querySelectorAll('label')].forEach(label=>advanced.append(label));
  buttons[6].textContent='Đặt zoom về 50%';advanced.append(buttons[6]);
  buttons[0].textContent='Nạp bố cục từ trang';buttons[0].title='Quét lại bố cục hiện tại của trang Repo';
  advanced.append(buttons[0]);options.append(summary,advanced);
  const xy=byId('xy-display');
  toolbar.replaceChildren(editing,zoom,options,xy);
  byId('layersPanel').firstElementChild.classList.add('boxes-pane-title');
  byId('layersPanel').firstElementChild.textContent='Các khung';
  byId('inspectorPanel').firstElementChild.classList.add('boxes-pane-title');
  byId('inspectorPanel').firstElementChild.textContent='Thuộc tính khung';
  const search=document.createElement('input');search.id='boxesSearch';search.className='form-input boxes-search';
  search.placeholder='Tìm khung…';search.setAttribute('aria-label','Tìm khung');
  byId('layersList').before(search);
  const count=document.createElement('div');count.className='boxes-help';count.style.padding='6px 12px';
  search.before(count);
  function filter(){
    const rows=[...byId('layersList').querySelectorAll('.layer-row')];
    rows.forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase().includes(search.value.toLocaleLowerCase()));
    count.textContent=rows.length+' khung · Chọn để chỉnh sửa';
    rows.forEach(row=>{row.tabIndex=0;row.setAttribute('role','button');row.setAttribute('aria-label',row.textContent.trim());row.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();row.click();}};});
  }
  search.oninput=filter;
  new MutationObserver(filter).observe(byId('layersList'),{childList:true});filter();
  const nav=document.createElement('div');nav.className='boxes-mobile-nav';
  for(const [key,label] of [['layers','Các khung'],['canvas','Canvas'],['inspector','Thuộc tính']]){
    const button=document.createElement('button');button.className='form-btn';button.textContent=label;button.dataset.pane=key;
    button.onclick=()=>{panel.dataset.pane=key;nav.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));if(key==='canvas')requestAnimationFrame(()=>zoomFit());};
    button.setAttribute('aria-pressed',String(key==='canvas'));nav.append(button);
  }
  byId('boxesEditor').before(nav);
  const savebar=byId('saveStatus').parentElement;savebar.className='boxes-savebar';savebar.removeAttribute('style');
  const saves=savebar.querySelectorAll('button');saves[0].textContent='Lưu bố cục';saves[0].title='Lưu bản bố cục đang chỉnh';
  saves[1].textContent='Đặt lại bố cục';saves[2].textContent='Áp dụng lên trang';
  saves[2].title='Dùng bố cục này cho trang Repo';
  const help=document.createElement('div');help.className='boxes-help';
  help.innerHTML='Di chuyển canvas: giữ <kbd>Space</kbd> và kéo · Di chuyển khung: <kbd>↑ ↓ ← →</kbd> · Nhân đôi: <kbd>Ctrl D</kbd> · Bỏ chọn: <kbd>Esc</kbd>';
  savebar.after(help);
  const focus=byId('boxesFocus');
  function toggleFocus(){const active=panel.classList.toggle('boxes-focus');focus.textContent=active?'Thu gọn':'Mở rộng';focus.setAttribute('aria-pressed',String(active));requestAnimationFrame(()=>zoomFit());}
  focus.onclick=toggleFocus;
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&panel.classList.contains('boxes-focus'))toggleFocus();});
  document.querySelector('.dash-tab[data-tab="boxes"]').addEventListener('click',()=>requestAnimationFrame(()=>zoomFit()));
})();

/* Keep the inspector readable at sidebar widths; reuse existing field bindings. */
(() => {
  const original=window.renderInspector;
  const opened=new Map(),ratios=new Map();
  const labels={x:'Vị trí ngang',y:'Vị trí dọc',w:'Chiều rộng',h:'Chiều cao',rotation:'Góc xoay',scale:'Tỷ lệ',opacity:'Độ hiện (%)',zIndex:'Thứ tự lớp',paddingT:'Trên',paddingR:'Phải',paddingB:'Dưới',paddingL:'Trái',marginT:'Trên',marginR:'Phải',marginB:'Dưới',marginL:'Trái'};
  window.renderInspector=function(){
    original();
    const root=document.getElementById('inspectorBody'),key=previewSelectedKey;
    if(!root||!key)return;
    root.classList.add('friendly-inspector');
    const tabbar=document.getElementById('inspTabBar');
    const select=document.createElement('select');select.className='form-select inspector-category';select.setAttribute('aria-label','Nhóm thuộc tính');
    for(const [value,label] of [['transform','Bố cục & kích thước'],['style','Viền & hình dáng'],['bg','Nền'],['typography','Chữ'],['effects','Hiệu ứng'],['children','Nội dung'],['css','CSS nâng cao']]){
      const option=new Option(label,value);select.append(option);
    }
    select.value=window._inspTab||'transform';select.onchange=()=>switchInspTab(select.value);tabbar.replaceWith(select);
    const header=root.firstElementChild;header.classList.add('inspector-selection');
    header.firstElementChild.textContent=previewTitles[key]?.title||key;
    header.firstElementChild.title=key;
    const actions=header.lastElementChild;actions.className='inspector-actions';
    for(const button of actions.querySelectorAll('button')){button.setAttribute('aria-label',button.title);button.textContent=button.title.replace('Khóa/Mở khóa',previewBoxesData[key].locked?'Mở khóa':'Khóa').replace('Ẩn/Hiện',previewBoxesData[key].hidden?'Hiện':'Ẩn');}
    const content=document.getElementById('inspTabContent');
    for(const input of content.querySelectorAll('input[data-prop]')){
      const prop=input.dataset.prop,label=input.parentElement.querySelector('label');
      if(label&&labels[prop])label.textContent=labels[prop];
      input.setAttribute('aria-label',labels[prop]||prop);
      if(['x','y','w','h',...Object.keys(labels).filter(p=>/padding|margin/.test(p))].includes(prop))input.step='1';
      if(['w','h'].includes(prop))input.min='20';
      input.addEventListener('focus',()=>saveUndoSnapshot(),{once:true});
      input.addEventListener('change',()=>{
        let value=Number(input.value);if(!Number.isFinite(value))return;
        if(input.min!=='')value=Math.max(Number(input.min),value);
        if(input.max!=='')value=Math.min(Number(input.max),value);
        input.value=value;previewBoxesData[key][prop]=value;
        const ratio=ratios.get(key);
        if(ratio&&['w','h'].includes(prop)){
          const other=prop==='w'?'h':'w';previewBoxesData[key][other]=Math.max(20,Math.round(prop==='w'?value/ratio:value*ratio));
          const field=content.querySelector(`[data-prop="${other}"]`);if(field)field.value=previewBoxesData[key][other];
        }
        applyBoxStyle(key);renderLayers();updateXYDisplay();
      });
    }
    const sections=[...content.querySelectorAll(':scope > .inspector-section')];
    sections.forEach((section,index)=>{
      const title=section.querySelector('.inspector-label');if(!title)return;
      const details=document.createElement('details'),summary=document.createElement('summary');
      details.className='inspector-group';summary.textContent=title.textContent;title.remove();
      const id=(window._inspTab||'transform')+':'+index;
      details.open=opened.has(id)?opened.get(id):index===0;
      details.ontoggle=()=>opened.set(id,details.open);
      section.before(details);details.append(summary,section);
    });
    if((window._inspTab||'transform')==='transform'){
      const first=sections[0];
      const align=first.querySelector('button[onclick^="alignBoxes"]')?.parentElement;
      if(align){align.className='inspector-align';const names=['Căn trái','Giữa ngang','Căn phải','Căn trên','Giữa dọc','Căn dưới'];[...align.children].forEach((button,i)=>{button.textContent=names[i];button.title=names[i]+' theo canvas';});}
      const quick=document.createElement('div');quick.className='inspector-quick';
      function action(label,fn){const button=document.createElement('button');button.className='form-btn';button.textContent=label;button.onclick=()=>{saveUndoSnapshot();fn(previewBoxesData[key]);applyBoxStyle(key);renderLayers();updateXYDisplay();window.renderInspector();};quick.append(button);}
      action('Rộng bằng trang',d=>{d.x=24;d.w=Math.max(20,previewCanvasW-48);});
      action('Vừa nội dung',d=>{const doc=document.getElementById('previewIframe').contentDocument;const node=[...doc.querySelectorAll('[data-box]')].find(n=>n.dataset.box===key);if(node)d.h=Math.max(20,node.scrollHeight+Math.ceil(parseFloat(getComputedStyle(node).borderTopWidth)||0)+Math.ceil(parseFloat(getComputedStyle(node).borderBottomWidth)||0));});
      const ratioLabel=document.createElement('label');ratioLabel.className='inspector-ratio';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=ratios.has(key);checkbox.onchange=()=>{if(checkbox.checked){const d=previewBoxesData[key];ratios.set(key,d.w/Math.max(1,d.h));}else ratios.delete(key);};ratioLabel.append(checkbox,document.createTextNode('Giữ tỷ lệ khi đổi kích thước'));
      first.append(quick,ratioLabel);
      const spacing=sections[1]?.querySelector('div[style*="grid"]');if(spacing)spacing.classList.add('inspector-spacing');
    }
  };
  window.renderInspector();
})();
