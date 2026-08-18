const state = { stories: [], filter: 'Alle' };
const dialog = document.querySelector('#storyDialog');
const LIVE_DATA_URL = 'https://raw.githubusercontent.com/pedersenalexsander-gif/narvik-brief/main/data/news.json';
const LAST_VISIT_KEY = 'alexBriefLastVisit';
const lastVisit = Number(localStorage.getItem(LAST_VISIT_KEY) || 0);

const hour = new Date().getHours();
document.querySelector('#greeting').textContent = hour < 11 ? 'GOD MORGEN' : hour < 17 ? 'GOD ETTERMIDDAG' : 'GOD KVELD';

function relativeTime(iso, fallback = '') {
  if (!iso) return fallback;
  const mins = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return mins <= 1 ? 'Nå' : `${mins} min siden`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} t siden`;
  return `${Math.floor(hours / 24)} d siden`;
}
function readTime(story) {
  const words = `${story.summary || ''} ${(story.keyPoints || []).join(' ')}`.trim().split(/\s+/).length;
  return `${Math.max(1, Math.ceil(words / 180))} min oversikt`;
}
function isNew(story) { return lastVisit > 0 && new Date(story.publishedISO || 0).getTime() > lastVisit; }
function imageUrl(story) { return story.localImage || story.image || ''; }
function setImage(img, fallback, url, title) {
  if (!img || !fallback) return;
  if (!url) { img.style.display = 'none'; fallback.style.display = 'grid'; return; }
  img.alt = title ? `Bilde fra saken: ${title}` : 'Artikkelbilde';
  img.onload = () => { img.style.display = 'block'; fallback.style.display = 'none'; };
  img.onerror = () => { img.style.display = 'none'; fallback.style.display = 'grid'; };
  img.src = url;
}
function openStory(story) {
  document.querySelector('#dialogTag').textContent = story.category;
  document.querySelector('#dialogTime').textContent = `${relativeTime(story.publishedISO, story.published)} · ${readTime(story)}`;
  document.querySelector('#dialogTitle').textContent = story.title;
  document.querySelector('#dialogSummary').textContent = story.summary || 'Ingen oppsummering tilgjengelig ennå.';
  document.querySelector('#dialogWhy').textContent = story.whyItMatters || '';
  document.querySelector('#dialogSource').textContent = story.source || 'nyhetskilden';
  const image = document.querySelector('#dialogImage');
  const url = imageUrl(story);
  if (url) { image.src = url; image.alt = `Bilde fra saken: ${story.title}`; image.style.display = 'block'; image.onerror = () => image.style.display = 'none'; }
  else { image.removeAttribute('src'); image.style.display = 'none'; }
  const list = document.querySelector('#dialogPoints'); list.innerHTML = '';
  (story.keyPoints || []).forEach(point => { const li = document.createElement('li'); li.textContent = point; list.appendChild(li); });
  const original = document.querySelector('#dialogOriginal'); original.href = story.url || '#'; original.style.display = story.url ? 'inline-flex' : 'none';
  dialog.showModal(); document.body.classList.add('modal-open');
}
function render() {
  const grid = document.querySelector('#newsGrid'); const template = document.querySelector('#storyTemplate');
  const stories = state.filter === 'Alle' ? state.stories : state.stories.filter(s => s.category === state.filter);
  grid.innerHTML = ''; document.querySelector('#storyCount').textContent = `${stories.length} ${stories.length === 1 ? 'sak' : 'saker'}`;
  if (!stories.length) { grid.innerHTML = '<div class="empty">Ingen ferske kvalitetssaker i denne kategorien akkurat nå.</div>'; return; }
  stories.forEach((story, index) => {
    const node = template.content.cloneNode(true); const card = node.querySelector('.story-card');
    if (index === 0 && state.filter === 'Alle') card.classList.add('lead');
    if (isNew(story)) { card.classList.add('is-new'); const badge = document.createElement('span'); badge.className = 'new-badge'; badge.textContent = 'NY SIDEN SIST'; node.querySelector('.story-topline').prepend(badge); }
    node.querySelector('.tag').textContent = story.category;
    node.querySelector('.time').textContent = `${relativeTime(story.publishedISO, story.published)} · ${readTime(story)}`;
    node.querySelector('.story-title').textContent = story.title; node.querySelector('.story-summary').textContent = story.summary;
    node.querySelector('.source').textContent = story.source ? `Kilde: ${story.source} · artikkeltekst kontrollert` : 'Artikkeltekst kontrollert';
    setImage(node.querySelector('.story-image'), node.querySelector('.image-fallback'), imageUrl(story), story.title);
    node.querySelector('.story-more').addEventListener('click', () => openStory(story)); grid.appendChild(node);
  });
}
async function loadNews() {
  try {
    const response = await fetch(`${LIVE_DATA_URL}?v=${Date.now()}`, { cache: 'no-store' }); if (!response.ok) throw new Error('Kunne ikke hente nyhetsdata');
    const data = await response.json(); state.stories = data.stories || [];
    document.querySelector('#lastUpdated').textContent = data.updatedAt ? `Sist oppdatert ${data.updatedAt} · gratis fulltekstmodus` : 'Briefen er oppdatert';
    const count = document.querySelector('.hero-note strong'); if (count) count.textContent = state.stories.length;
    const fresh = state.stories.filter(isNew).length; const note = document.querySelector('.hero-note p');
    if (note) note.textContent = fresh ? `${fresh} nye siden sist. Ferske saker fra Narvik til verden, økonomi og AI.` : 'Ferske saker fra Narvik til verden, økonomi og AI.';
    render(); localStorage.setItem(LAST_VISIT_KEY, String(Date.now()));
  } catch (error) { console.error(error); document.querySelector('#lastUpdated').textContent = 'Kunne ikke hente siste oppdatering'; document.querySelector('#newsGrid').innerHTML = '<div class="empty">Prøv å laste siden på nytt om et øyeblikk.</div>'; }
}
document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('.filter').forEach(x => x.classList.remove('active')); button.classList.add('active'); state.filter = button.dataset.filter; render(); }));
document.querySelector('.close').addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => document.body.classList.remove('modal-open'));
dialog.addEventListener('click', event => { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); });
loadNews(); setInterval(loadNews, 2 * 60 * 1000);
