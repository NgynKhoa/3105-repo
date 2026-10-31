/* Same-document navigation. This module never creates, reloads or pauses media. */
(() => {
  if(!document.getElementById('shell')||window.__blogNavigation)return;
  const home=new URL(location.href),homeTitle=document.title;
  // History changes the address, but relative media URLs must keep their base.
  if(!document.querySelector('base')){
    const base=document.createElement('base');base.href=new URL('.',home).href;document.head.prepend(base);
  }
  const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const listURL=()=>window.PUBLIC_MODE?new URL('blog.html',home):new URL('/blog',home);
  const postURL=id=>{const url=listURL();if(window.PUBLIC_MODE)url.searchParams.set('id',id);else url.pathname='/blog-post/'+id;return url;};
  function blogRoute(value){
    const url=new URL(value,home);if(url.origin!==home.origin)return null;
    const match=url.pathname.match(/\/blog(?:-post)?\/(\d+)\/?$/);
    if(match)return {id:Number(match[1]),url:postURL(match[1])};
    if(/\/blog(?:\.html)?\/?$/.test(url.pathname)){
      const id=Number(url.searchParams.get('id'))||null;return {id,url:id?postURL(id):listURL()};
    }
    return null;
  }
  const reader=document.createElement('section');reader.id='blog-reader';reader.hidden=true;reader.setAttribute('aria-label','Blog');
  reader.innerHTML='<div class="reader-bar"><button type="button" data-home>← Trang Repo</button><span class="reader-track"></span><button type="button" data-player="mpPlay">Phát / Dừng</button><button type="button" data-player="mpNext" aria-label="Bài tiếp theo">Bài tiếp</button></div><main class="reader-scroll" tabindex="-1"><div class="reader-content"></div></main>';
  document.body.append(reader);
  const scroll=reader.querySelector('.reader-scroll'),content=reader.querySelector('.reader-content');
  let postsPromise,revision=0,active=false,previousFocus,previousOverflow;
  async function posts(){
    if(!postsPromise)postsPromise=(async()=>{
      if(window.PUBLIC_MODE){const value=window.PUBLIC_REPO_DATA?.blog;if(Array.isArray(value))return value;throw new Error('Không tìm thấy dữ liệu Blog');}
      const response=await fetch('/api/blog/posts');if(!response.ok)throw new Error('Không tải được bài viết');
      const data=await response.json();return Array.isArray(data)?data:(data.posts||[]);
    })().catch(error=>{postsPromise=null;throw error;});
    return postsPromise;
  }
  function bodyHTML(html){
    const doc=new DOMParser().parseFromString(String(html||''),'text/html');
    doc.querySelectorAll('script,style,link,meta,base,iframe,object,embed,audio,video,form').forEach(el=>el.remove());
    doc.body.querySelectorAll('*').forEach(el=>{for(const attr of [...el.attributes])if(/^on/i.test(attr.name)||['id','srcdoc','autofocus'].includes(attr.name)||(['href','src'].includes(attr.name)&&/^\s*(javascript|vbscript):/i.test(attr.value)))el.removeAttribute(attr.name);});
    return doc.body.innerHTML;
  }
  function updateTrack(){reader.querySelector('.reader-track').textContent=document.getElementById('mpTitle')?.textContent||'Nhạc và tiếng mưa tiếp tục từ trang Repo';}
  async function open(value,push=true){
    const route=blogRoute(value);if(!route)return;
    const ticket=++revision;
    if(!active){previousFocus=document.activeElement;previousOverflow=document.documentElement.style.overflow;}
    active=true;reader.hidden=false;document.documentElement.style.overflow='hidden';updateTrack();
    if(push&&location.href!==route.url.href)history.pushState({blogReader:true},'',route.url.href);
    content.innerHTML='<p role="status">Đang tải bài viết…</p>';scroll.scrollTop=0;
    try{
      const all=await posts();if(ticket!==revision)return;
      if(route.id){
        const post=all.find(p=>Number(p.id)===route.id);
        if(!post){content.innerHTML=`<h1>Không tìm thấy bài viết</h1><a href="${escape(listURL())}">Về danh sách Blog</a>`;return;}
        document.title=post.title+' — Blog';
        content.innerHTML=`<a class="reader-back" href="${escape(listURL())}">← Danh sách bài viết</a><article><header><div class="reader-icon">${escape(post.icon||'📝')}</div><h1>${escape(post.title)}</h1><p class="reader-meta">${escape(post.date)}</p>${post.image?`<img class="reader-cover" src="${escape(post.image)}" alt="Ảnh bìa">`:''}</header><div class="reader-body">${bodyHTML(post.content)}</div><div class="reader-gallery"></div></article>`;
        for(const url of Array.isArray(post.images)?post.images:[]){const img=document.createElement('img');img.src=url;img.alt='Ảnh bài viết';img.loading='lazy';content.querySelector('.reader-gallery').append(img);}
      }else{
        document.title='Blog — '+homeTitle;
        const visible=all.filter(p=>!p.hidden);
        content.innerHTML=`<header><span class="reader-eyebrow">OWEN REPO</span><h1>Blog</h1><p>Hướng dẫn, chia sẻ và cập nhật mới nhất.</p></header><div class="reader-list">${visible.map(p=>`<a class="reader-card" href="${escape(postURL(p.id))}"><span class="reader-icon">${escape(p.icon||'📝')}</span><div><h2>${escape(p.title)}</h2><p>${escape(p.excerpt||'')}</p><small>${escape(p.date)}</small></div><span aria-hidden="true">→</span></a>`).join('')||'<p>Chưa có bài viết.</p>'}</div>`;
      }
      scroll.focus({preventScroll:true});
    }catch(error){if(ticket===revision){content.replaceChildren();const text=document.createElement('p');text.textContent=error.message;const retry=document.createElement('button');retry.textContent='Thử lại';retry.onclick=()=>open(route.url,false);content.append(text,retry);}}
  }
  function close(push=true){
    ++revision;active=false;reader.hidden=true;document.documentElement.style.overflow=previousOverflow??'';document.title=homeTitle;
    if(push&&location.href!==home.href)history.pushState({blogReader:false},'',home.href);
    previousFocus?.focus({preventScroll:true});
  }
  reader.querySelector('[data-home]').onclick=()=>close();
  reader.querySelectorAll('[data-player]').forEach(button=>button.onclick=()=>{document.getElementById(button.dataset.player)?.click();updateTrack();});
  const title=document.getElementById('mpTitle');if(title)new MutationObserver(updateTrack).observe(title,{childList:true,subtree:true,characterData:true});
  document.addEventListener('click',event=>{
    const anchor=event.target.closest('a[href]');if(!anchor||event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||anchor.hasAttribute('download'))return;
    const route=blogRoute(anchor.href);if(route){event.preventDefault();open(route.url);}
  });
  window.addEventListener('popstate',()=>{if(blogRoute(location.href))open(location.href,false);else if(active)close(false);});
  window.__blogNavigation={open,close};
})();
