const state = { stories: [], filter: 'Alle' };

const norwegianDate = new Intl.DateTimeFormat('nb-NO', {
  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
}).format(new Date());
document.querySelector('#today').textContent = norwegianDate.charAt(0).toUpperCase() + norwegianDate.slice(1);

function render() {
  const grid = document.querySelector('#newsGrid');
  const template = document.querySelector('#storyTemplate');
  const stories = state.filter === 'Alle'
    ? state.stories
    : state.stories.filter(story => story.category === state.filter);

  grid.innerHTML = '';
  document.querySelector('#storyCount').textContent = `${stories.length} ${stories.length === 1 ? 'sak' : 'saker'}`;

  if (!stories.length) {
    grid.innerHTML = '<div class="empty">Ingen saker i denne kategorien ennå.</div>';
    return;
  }

  stories.forEach(story => {
    const node = template.content.cloneNode(true);
    node.querySelector('.tag').textContent = story.category;
    node.querySelector('.time').textContent = story.published || '';
    node.querySelector('.story-title').textContent = story.title;
    node.querySelector('.story-summary').textContent = story.summary;
    node.querySelector('.story-why').textContent = story.whyItMatters;
    const link = node.querySelector('.story-link');
    link.href = story.url;
    if (!story.url || story.url === '#') link.style.display = 'none';
    grid.appendChild(node);
  });
}

async function loadNews() {
  try {
    const response = await fetch(`data/news.json?v=${Date.now()}`);
    if (!response.ok) throw new Error('Kunne ikke hente nyhetsdata');
    const data = await response.json();
    state.stories = data.stories || [];
    document.querySelector('#lastUpdated').textContent = data.updatedAt
      ? `Sist oppdatert ${data.updatedAt}`
      : 'Klar for dagens oppdatering';
    render();
  } catch (error) {
    document.querySelector('#lastUpdated').textContent = 'Nyhetsfeeden er ikke oppdatert ennå';
    document.querySelector('#newsGrid').innerHTML = '<div class="empty">Morgenbriefen kommer her når første oppdatering er publisert.</div>';
  }
}

document.querySelectorAll('.filter').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.filter').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    state.filter = button.dataset.filter;
    render();
  });
});

loadNews();
