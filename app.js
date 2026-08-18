const state = { stories: [], filter: 'Alle' };
const dialog = document.querySelector('#storyDialog');

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

function openStory(story) {
  document.querySelector('#dialogTag').textContent = story.category;
  document.querySelector('#dialogTime').textContent = relativeTime(story.publishedISO, story.published);
  document.querySelector('#dialogTitle').textContent = story.title;
  document.querySelector('#dialogSummary').textContent = story.summary || 'Ingen oppsummering tilgjengelig ennå.';
  document.querySelector('#dialogWhy').textContent = story.whyItMatters || '';
  document.querySelector('#dialogSource').textContent = story.source || 'nyhetskilden';
  const list = document.querySelector('#dialogPoints');
  list.innerHTML = '';
  (story.keyPoints || []).forEach(point => {
    const li = document.createElement('li'); li.textContent = point; list.appendChild(li);
  });
  const original = document.querySelector('#dialogOriginal');
  original.href = story.url || '#';
  original.style.display = story.url ? 'inline-flex' : 'none';
  dialog.showModal();
  document.body.classList.add('modal-open');
}

function render() {
  const grid = document.querySelector('#newsGrid');
  const template = document.querySelector('#storyTemplate');
  const stories = state.filter === 'Alle' ? state.stories : state.stories.filter(s => s.category === state.filter);
  grid.innerHTML = '';
  document.querySelector('#storyCount').textContent = `${stories.length} ${stories.length === 1 ? 'sak' : 'saker'}`;
  if (!stories.length) {
    grid.innerHTML = '<div class="empty">Ingen ferske saker i denne kategorien akkurat nå.</div>';
    return;
  }
  stories.forEach((story, index) => {
    const node = template.content.cloneNode(true);
    const card = node.querySelector('.story-card');
    if (index === 0 && state.filter === 'Alle') card.classList.add('lead');
    node.querySelector('.tag').textContent = story.category;
    node.querySelector('.time').textContent = relativeTime(story.publishedISO, story.published);
    node.querySelector('.story-title').textContent = story.title;
    node.querySelector('.story-summary').textContent = story.summary;
    node.querySelector('.source').textContent = story.source ? `Kilde: ${story.source}` : '';
    node.querySelector('.story-more').addEventListener('click', () => openStory(story));
    grid.appendChild(node);
  });
}

async function loadNews() {
  try {
    const response = await fetch(`data/news.json?v=${Date.now()}`);
    if (!response.ok) throw new Error('Kunne ikke hente nyhetsdata');
    const data = await response.json();
    state.stories = data.stories || [];
    document.querySelector('#lastUpdated').textContent = data.updatedAt ? `Sist oppdatert ${data.updatedAt}` : 'Briefen er oppdatert';
    render();
  } catch (error) {
    document.querySelector('#lastUpdated').textContent = 'Kunne ikke hente siste oppdatering';
    document.querySelector('#newsGrid').innerHTML = '<div class="empty">Prøv å laste siden på nytt om et øyeblikk.</div>';
  }
}

document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.filter').forEach(x => x.classList.remove('active'));
  button.classList.add('active'); state.filter = button.dataset.filter; render();
}));

document.querySelector('.close').addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => document.body.classList.remove('modal-open'));
dialog.addEventListener('click', event => {
  const r = dialog.getBoundingClientRect();
  if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
});

loadNews();
setInterval(loadNews, 5 * 60 * 1000);
