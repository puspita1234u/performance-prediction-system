// Add/replace this in static/js/main.js
async function predictStudent(studentId) {
  try {
    const res = await fetch(`/students/${studentId}/predict`, { method: 'POST' });
    if (!res.ok) throw new Error('Prediction failed');
    const data = await res.json();

    // Update prediction & probability cells if present
    const predCell = document.getElementById(`pred-${studentId}`);
    if (predCell) predCell.textContent = data.prediction || '';

    const probCell = document.getElementById(`prob-${studentId}`);
    if (probCell && typeof data.probability === 'number') {
      probCell.textContent = (data.probability * 100).toFixed(1) + '%';
    }

    // Refresh the chart (global function defined in dashboard template)
    if (typeof window.loadStats === 'function') {
      window.loadStats();
    }
  } catch (e) {
    console.error(e);
    alert('Prediction failed');
  }
}



// Simple table sort/search/filter
(function () {
  const table = document.querySelector('table.table');
  if (!table) return;

  const tbody = table.querySelector('tbody');
  const headers = table.querySelectorAll('th[data-sort]');
  let currentSort = { key: null, asc: true };

  headers.forEach((th, idx) => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      currentSort.asc = (currentSort.key === key) ? !currentSort.asc : true;
      currentSort.key = key;

      const rows = Array.from(tbody.querySelectorAll('tr')).filter(r => r.style.display !== 'none');
      rows.sort((a, b) => {
        const ta = a.children[idx].innerText.trim();
        const tb = b.children[idx].innerText.trim();
        const na = parseFloat(ta.replace(/[^0-9.]/g, ''));
        const nb = parseFloat(tb.replace(/[^0-9.]/g, ''));
        const bothNum = !isNaN(na) && !isNaN(nb);
        let cmp = 0;
        if (bothNum) cmp = na - nb; else cmp = ta.localeCompare(tb);
        return currentSort.asc ? cmp : -cmp;
      });
      rows.forEach(r => tbody.appendChild(r));
    });
  });

  function applyFilters() {
    const q = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const res = (document.getElementById('resultFilter')?.value || '').toLowerCase();
    Array.from(tbody.querySelectorAll('tr')).forEach(tr => {
      const name = tr.querySelector('td:nth-child(2)')?.innerText.toLowerCase() || '';
      const pred = tr.querySelector('[id^="pred-"]')?.innerText.toLowerCase() || '';
      const matchName = !q || name.includes(q);
      const matchRes = !res || pred.startsWith(res);
      tr.style.display = (matchName && matchRes) ? '' : 'none';
    });
  }

  document.getElementById('searchInput')?.addEventListener('input', applyFilters);
  document.getElementById('resultFilter')?.addEventListener('change', applyFilters);
})();
