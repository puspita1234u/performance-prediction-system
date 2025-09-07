// Add/replace this in static/js/main.js
// Predict an individual student's performance
async function predictStudent(studentId) {
  try {
    const res = await fetch(`/students/${studentId}/predict`, { method: 'POST' });
    if (!res.ok) throw new Error('Prediction failed');
    const data = await res.json();

    if (!data || (!data.prediction && typeof data.probability !== 'number')) {
      throw new Error('Invalid prediction response');
    }

    // Update prediction cell
    const predCell = document.getElementById(`pred-${studentId}`);
    if (predCell) {
      predCell.textContent = data.prediction || 'N/A';
    }

    // Update probability cell (always ensure it's in percentage format)
    const probCell = document.getElementById(`prob-${studentId}`);
    if (probCell) {
      const prob = data.probability > 1 ? data.probability : data.probability * 100;
      probCell.textContent = `${prob.toFixed(1)}%`;
    }

    // Refresh chart
    if (typeof window.loadStats === 'function') {
      window.loadStats();
    }
  } catch (e) {
    console.error('Prediction failed for student', studentId, e);
    alert('Prediction failed for student ID: ' + studentId);
  }
}


// Predict all students for the logged-in teacher (or admin if applicable)
async function predictAll() {
  try {
    const res = await fetch('/students/predict_all', { method: 'POST' });
    if (!res.ok) throw new Error('Predict All request failed');

    const data = await res.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    const updatedCount = data.updated || 0;
    if (updatedCount === 0) {
      alert('No students were predicted. Either no students found or prediction failed.');
      return;
    }

    alert(`${updatedCount} students predicted successfully.`);

    // Update each row in the table
    if (Array.isArray(data.students)) {
      data.students.forEach(st => {
        const predCell = document.getElementById(`pred-${st.id}`);
        if (predCell) {
          predCell.textContent = st.prediction || 'N/A';
        }

        const probCell = document.getElementById(`prob-${st.id}`);
        if (probCell) {
          const prob = st.probability > 1 ? st.probability : st.probability * 100;
          probCell.textContent = `${prob.toFixed(1)}%`;
        }
      });
    }

    // Refresh chart after all updates
    if (typeof window.loadStats === 'function') {
      window.loadStats();
    }
  } catch (e) {
    console.error('Predict All failed', e);
    alert('Prediction failed.');
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
