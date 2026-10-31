/* Progressive enhancement: existing HTML content and API schema remain compatible. */
(() => {
  const panel = document.getElementById('panel-blog');
  if (!panel) return;
  const byId = id => document.getElementById(id);
  const source = byId('postContent');
  source.previousElementSibling.textContent = 'Nội dung bài viết';
  const fields = ['editPostId','postIcon','postTitle','postExcerpt','postContent','postImage','postGallery'];
  const draftKey = 'owen_blog_editor_draft_v1';
  let dirty = false, saving = false, mode = 'visual', timer;
  const listCard = panel.querySelector('.section-card');
  const card = source.closest('.section-card');
  listCard.querySelector('.section-title').textContent = 'Bài viết';
  card.querySelector('.section-title').textContent = 'Soạn bài viết';
  const tools = document.createElement('div');
  tools.className = 'blog-tools';
  tools.innerHTML = '<input class="form-input" id="blogSearch" aria-label="Tìm bài viết" placeholder="Tìm bài viết…"><select class="form-select" id="blogFilter" aria-label="Lọc trạng thái"><option value="all">Tất cả bài viết</option><option value="visible">Đang hiển thị</option><option value="hidden">Đang ẩn</option></select><button class="form-btn" id="blogNew">＋ Viết bài mới</button>';
  listCard.insertBefore(tools, byId('blogList'));
  const toolbar = document.createElement('div');
  toolbar.className = 'blog-tools';
  toolbar.setAttribute('aria-label', 'Công cụ soạn thảo');
  toolbar.innerHTML = '<button type="button" class="form-btn" data-command="bold" aria-label="In đậm"><b>B</b></button><button type="button" class="form-btn" data-command="italic" aria-label="In nghiêng"><i>I</i></button><button type="button" class="form-btn" data-command="formatBlock" data-value="h2">Tiêu đề</button><button type="button" class="form-btn" data-command="formatBlock" data-value="p">Đoạn văn</button><button type="button" class="form-btn" data-command="insertUnorderedList">• Danh sách</button><button type="button" class="form-btn" id="blogLink">Liên kết</button><button type="button" class="form-btn" id="blogHtml">HTML</button><button type="button" class="form-btn" id="blogPreviewToggle">Xem trước</button>';
  source.before(toolbar);
  const editor = document.createElement('div');
  editor.id = 'blogRichEditor'; editor.className = 'blog-writing';
  editor.contentEditable = 'true'; editor.setAttribute('role','textbox');
  editor.setAttribute('aria-label','Nội dung bài viết'); editor.setAttribute('aria-multiline','true');
  editor.dataset.placeholder = 'Bắt đầu câu chuyện của bạn…';
  source.before(editor); source.hidden = true;
  const preview = document.createElement('iframe');
  preview.className = 'blog-preview'; preview.title = 'Xem trước bài viết';
  preview.setAttribute('sandbox',''); preview.hidden = true; source.after(preview);
  const status = document.createElement('div');
  status.className = 'blog-editor-status'; status.setAttribute('role','status'); card.append(status);
  const restore = document.createElement('button'); restore.className='form-btn';
  restore.textContent='Khôi phục bản nháp trên máy'; restore.hidden=!localStorage.getItem(draftKey); card.append(restore);
  const drop = document.createElement('div'); drop.className='blog-cover-drop';
  drop.textContent='Kéo ảnh bìa vào đây hoặc dùng nút chọn ảnh bên trên.';
  byId('postImagePreview').after(drop);
  const gallery = document.createElement('div'); gallery.className='blog-media-grid';
  byId('postGallery').after(gallery);
  const escape = value => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function values(){return Object.fromEntries(fields.map(id => [id,byId(id).value]));}
  function updateStatus(message){
    const text = editor.textContent.trim();
    status.textContent = message || `${text ? text.split(/\s+/).length : 0} từ · ${dirty ? 'Chưa lưu bài viết' : 'Sẵn sàng'}`;
  }
  function changed(){
    dirty=true; updateStatus(); clearTimeout(timer);
    timer=setTimeout(() => {localStorage.setItem(draftKey,JSON.stringify(values()));restore.hidden=false;updateStatus('Đã giữ bản nháp trên máy · Chưa lưu vào kho');},500);
  }
  function media(){
    const cover = byId('postImage').value.trim();
    const box=byId('postImagePreview'); box.replaceChildren(); box.className='blog-media-grid';
    function image(url,parent,remove){
      if(!/^(https?:\/\/|\.?\/?assets\/|\/assets\/)/i.test(url))return;
      const figure=document.createElement('figure'), img=document.createElement('img'), button=document.createElement('button');
      img.src=url; img.alt='Ảnh bài viết'; button.type='button'; button.className='box-btn-sm';button.textContent='Xóa ảnh';
      button.onclick=remove;figure.append(img,button);parent.append(figure);
    }
    if(cover)image(cover,box,()=>{byId('postImage').value='';media();changed();});
    gallery.replaceChildren();
    byId('postGallery').value.split('\n').filter(Boolean).forEach((url,index)=>image(url,gallery,()=>{
      const urls=byId('postGallery').value.split('\n').filter(Boolean);urls.splice(index,1);byId('postGallery').value=urls.join('\n');media();changed();
    }));
  }
  function sync(){editor.innerHTML=source.value;media();updateStatus();}
  editor.addEventListener('input',()=>{source.value=editor.innerHTML;changed();});
  source.addEventListener('input',()=>{editor.innerHTML=source.value;changed();});
  panel.addEventListener('input',e=>{if(fields.includes(e.target.id)&&e.target!==source){media();changed();}});
  toolbar.querySelectorAll('[data-command]').forEach(button=>{
    button.onmousedown=e=>e.preventDefault();
    button.onclick=()=>{editor.focus();document.execCommand(button.dataset.command,false,button.dataset.value||null);source.value=editor.innerHTML;changed();};
  });
  byId('blogLink').onmousedown=e=>e.preventDefault();
  byId('blogLink').onclick=()=>{const url=prompt('Địa chỉ liên kết (https://…)');if(!url)return;if(!/^https?:\/\//i.test(url)){showNotif('Hãy nhập liên kết HTTP hoặc HTTPS.','danger');return;}editor.focus();document.execCommand('createLink',false,url);source.value=editor.innerHTML;changed();};
  byId('blogHtml').onclick=()=>{mode=mode==='visual'?'html':'visual';preview.hidden=true;editor.hidden=mode!=='visual';source.hidden=mode!=='html';byId('blogHtml').textContent=mode==='html'?'Soạn trực quan':'HTML';};
  byId('blogPreviewToggle').onclick=()=>{
    preview.hidden=!preview.hidden;
    if(!preview.hidden){
      const cover=byId('postImage').value;
      preview.srcdoc=`<!doctype html><meta charset="utf-8"><base href="${escape(location.origin+'/')}"><style>body{font:16px/1.8 system-ui;max-width:720px;padding:28px;margin:auto;color:#1e293b}img{max-width:100%;border-radius:10px}h1{line-height:1.3}blockquote{border-left:3px solid #94a3b8;padding-left:16px}a{color:#2563eb}</style><h1>${escape(byId('postTitle').value||'Bài viết chưa có tiêu đề')}</h1><p>${escape(byId('postExcerpt').value)}</p>${cover?`<img src="${escape(cover)}" alt="Ảnh bìa">`:''}<article>${source.value}</article>`;
    }
    editor.hidden=!preview.hidden||mode!=='visual';source.hidden=!preview.hidden||mode!=='html';
  };
  function filter(){const query=byId('blogSearch').value.toLocaleLowerCase(),state=byId('blogFilter').value;
    byId('blogList').querySelectorAll('[data-id]').forEach(row=>{const post=blogPosts.find(p=>String(p.id)===row.dataset.id);row.hidden=!post||!String(post.title).toLocaleLowerCase().includes(query)||(state==='hidden'&&!post.hidden)||(state==='visible'&&post.hidden);});}
  const originalRender=window.renderBlogList;
  window.renderBlogList=function(){originalRender();filter();};
  byId('blogSearch').oninput=filter;byId('blogFilter').onchange=filter;
  const originalEdit=window.editPost, originalClear=window.clearPostForm;
  window.editPost=function(id){if(dirty&&!confirm('Bỏ thay đổi chưa lưu để mở bài khác?'))return;originalEdit(id);dirty=false;sync();};
  window.clearPostForm=function(){if(dirty&&!confirm('Bỏ thay đổi chưa lưu?'))return;originalClear();dirty=false;clearTimeout(timer);localStorage.removeItem(draftKey);restore.hidden=true;sync();};
  byId('blogNew').onclick=()=>window.clearPostForm();
  restore.onclick=()=>{if(dirty&&!confirm('Thay nội dung hiện tại bằng bản nháp?'))return;try{const data=JSON.parse(localStorage.getItem(draftKey));fields.forEach(id=>byId(id).value=data[id]||'');sync();changed();}catch(e){showNotif('Không đọc được bản nháp.','danger');}};
  const originalUpload=window.uploadBlogImage;
  window.uploadBlogImage=async function(...args){await originalUpload(...args);media();changed();};
  drop.ondragover=e=>{e.preventDefault();drop.classList.add('dragover');};drop.ondragleave=()=>drop.classList.remove('dragover');
  drop.ondrop=e=>{e.preventDefault();drop.classList.remove('dragover');const files=[...e.dataTransfer.files].filter(f=>f.type.startsWith('image/'));if(files.length)window.uploadBlogImage('cover',{files:[files[0]],value:''});};
  window.savePost=async function(){
    if(saving)return;
    const title=byId('postTitle').value.trim();if(!title){showNotif('Vui lòng nhập tiêu đề!','danger');byId('postTitle').focus();return;}
    const submitted=JSON.stringify(values());
    const id=Number(byId('editPostId').value)||Math.max(0,...blogPosts.map(p=>Number(p.id)||0))+1;
    const old=blogPosts.find(p=>p.id===id)||{};
    const post={...old,id,title,icon:byId('postIcon').value||'📝',excerpt:byId('postExcerpt').value,content:source.value,image:byId('postImage').value,images:byId('postGallery').value.split('\n').map(x=>x.trim()).filter(Boolean),date:new Date().toLocaleDateString('vi-VN')};
    const next=blogPosts.some(p=>p.id===id)?blogPosts.map(p=>p.id===id?post:p):[...blogPosts,post];
    saving=true;updateStatus('Đang lưu bài viết…');
    try{
      const response=await fetch('/api/blog/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({posts:next})});
      const data=await response.json();if(!response.ok||!data.ok)throw new Error(data.error||'Không thể lưu bài viết');
      blogPosts=next;window.renderBlogList();localStorage.setItem('repo_blogPosts',JSON.stringify(next));localStorage.setItem('repo_blog_updated',String(Date.now()));
      if(JSON.stringify(values())===submitted){dirty=false;clearTimeout(timer);localStorage.removeItem(draftKey);restore.hidden=true;byId('editPostId').value=id;updateStatus('Đã lưu bài viết vào kho');}else{changed();}
      showNotif('Đã lưu bài viết!');
    }catch(e){dirty=true;updateStatus('Lưu thất bại · Nội dung vẫn được giữ lại');showNotif(e.message,'danger');}
    finally{saving=false;}
  };
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  sync();filter();
})();
