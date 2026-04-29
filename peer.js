let publications = [];
let filtered = [];

const resultsList = document.getElementById("results-list");
const searchInput = document.getElementById("search-input");
const yearFilter = document.getElementById("year-filter");
const journalFilter = document.getElementById("journal-filter");
const keywordFilter = document.getElementById("keyword-filter");
const clearBtn = document.getElementById("clear-filters");
const resultsCount = document.getElementById("results-count");
const paginationContainer = document.getElementById("pagination");

const RESULTS_PER_PAGE = 12;
let currentPage = 1;


// --------------------------------------------------
// FETCH AND PARSE CSV
// --------------------------------------------------

function parseCSV(csvText) {
  const lines = csvText.split('\n').filter(line => line.trim());
  const headers = lines[0].split(',').map(h => h.replace(/"/g, '').trim());
  const rows = lines.slice(1).map(line => {
    const values = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        values.push(current.replace(/"/g, '').trim());
        current = '';
      } else {
        current += char;
      }
    }
    values.push(current.replace(/"/g, '').trim());
    return values;
  });
  return rows.map(row => {
    const obj = {};
    headers.forEach((header, i) => {
      obj[header.toLowerCase()] = row[i] || '';
    });
    return obj;
  });
}

fetch("peer-2010-2026.csv")
  .then(res => res.text())
  .then(csvText => {
    const data = parseCSV(csvText);
    publications = data.map(p => ({
      title: p.title,
      authors: p.authors,
      year: parseInt(p.year) || 0,
      date: p.date,
      link: p.link,
      journal: p.journal,
      doi: p.doi,
      keywords: p.keywords ? p.keywords.split(';').map(k => k.trim()).filter(k => k) : []
    }));

    filtered = publications;

    populateFilters();
    applyFilters();
  });


// --------------------------------------------------
// SEARCH INDEX
// --------------------------------------------------

function buildSearchIndex(pub) {
  return [
    pub.title,
    pub.authors,
    pub.journal,
    ...pub.keywords
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}


// --------------------------------------------------
// FILTER POPULATION
// --------------------------------------------------

function populateFilters() {

  const years = [...new Set(publications.map(p => p.year).filter(Boolean))]
    .sort((a,b)=>b-a);

  const journals = [...new Set(publications.map(p => p.journal).filter(Boolean))].sort();

  years.forEach(year => {
    yearFilter.appendChild(new Option(year, year));
  });

  journals.forEach(journal => {
    journalFilter.appendChild(new Option(journal, journal));
  });
}


// --------------------------------------------------
// FILTERING
// --------------------------------------------------

function applyFilters() {

  const search = searchInput.value.toLowerCase().trim();
  const year = yearFilter.value;
  const journal = journalFilter.value;
  const keywordQuery = keywordFilter.value.toLowerCase().trim();

  filtered = publications.filter(pub => {

    const index = buildSearchIndex(pub);

    const matchesSearch =
      !search ||
      search.split(" ").every(token =>
        index.includes(token)
      );

    const matchesYear =
      !year || String(pub.year) === year;

    const matchesJournal =
      !journal || pub.journal === journal;

    const matchesKeyword =
      !keywordQuery ||
      pub.keywords.some(k =>
        k.toLowerCase().includes(keywordQuery)
      );

    return (
      matchesSearch &&
      matchesYear &&
      matchesJournal &&
      matchesKeyword
    );
  });

  currentPage = 1;
  render();
}


// --------------------------------------------------
// PAGINATION
// --------------------------------------------------

function renderPagination(totalPages) {
  paginationContainer.innerHTML = "";

  if (totalPages <= 1) return;

  const MAX_VISIBLE = 10;

  // Determine current page group (1–10, 11–20, etc.)
  const groupStart = Math.floor((currentPage - 1) / MAX_VISIBLE) * MAX_VISIBLE + 1;
  const groupEnd = Math.min(groupStart + MAX_VISIBLE - 1, totalPages);

  // Helper to create button
  function createButton(label, page, isActive = false) {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.className = isActive ? "active-page" : "";
    btn.setAttribute("aria-label", `Go to page ${page}`);
    btn.addEventListener("click", () => {
      currentPage = page;
      render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    return btn;
  }

  // Previous group button
  if (groupStart > 1) {
    const prevGroupBtn = createButton("« Prev 10", groupStart - 1);
    paginationContainer.appendChild(prevGroupBtn);
  }

  // Page numbers within current group
  for (let i = groupStart; i <= groupEnd; i++) {
    paginationContainer.appendChild(
      createButton(i, i, i === currentPage)
    );
  }

  // Ellipsis + jump to last page
  if (groupEnd < totalPages) {

    const ellipsis = document.createElement("span");
    ellipsis.textContent = "…";
    ellipsis.style.padding = "0.6rem 0.75rem";
    paginationContainer.appendChild(ellipsis);

    const lastBtn = createButton("Last", totalPages);
    paginationContainer.appendChild(lastBtn);

    const nextGroupBtn = createButton("Next 10 »", groupEnd + 1);
    paginationContainer.appendChild(nextGroupBtn);
  }
}


// --------------------------------------------------
// RENDER
// --------------------------------------------------

function render() {

  resultsList.innerHTML = "";

  const total = filtered.length;
  const totalPages = Math.ceil(total / RESULTS_PER_PAGE);

  const start = (currentPage - 1) * RESULTS_PER_PAGE;
  const end = start + RESULTS_PER_PAGE;

  const pageResults = filtered.slice(start, end);

  const startNum = total === 0 ? 0 : start + 1;
  const endNum = Math.min(end, total);

  resultsCount.textContent =
    total === 0
      ? "No publications found"
      : `Showing ${startNum}–${endNum} of ${total} article${total !== 1 ? "s" : ""} published in peer-reviewed journals since 2010.`;

  pageResults.forEach(pub => {

    const li = document.createElement("li");
    li.className = "result-item";

    let href = pub.link;
    if (!href) {
      const encodedTitle = encodeURIComponent(pub.title);
      href = `https://scholar.google.com/scholar?hl=en&as_sdt=0%2C33&q=${encodedTitle}&btnG=`;
    }
    const titleHTML = href ? `<a href="${href}" target="_blank" rel="noopener">${pub.title}</a>` : pub.title;

    li.innerHTML = `
      <h3>${titleHTML}</h3>

      <p><strong>${pub.journal ? pub.journal : ""}</strong></p>
    
      <p>${pub.authors} 
        ${pub.year ? pub.year : ""}
      </p>

      ${pub.date ? `<p>Published: ${pub.date}</p>` : ""}

      <div>
        ${pub.keywords.map(k =>
          `<span class="badge">${k}</span>`
        ).join("")}
      </div>
    `;

    resultsList.appendChild(li);
  });

  renderPagination(totalPages);
}


// --------------------------------------------------
// UTIL
// --------------------------------------------------

function debounce(fn, delay = 250) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}


// --------------------------------------------------
// EVENT LISTENERS
// --------------------------------------------------

searchInput.addEventListener("input", debounce(applyFilters));
keywordFilter.addEventListener("input", debounce(applyFilters));
yearFilter.addEventListener("change", applyFilters);
journalFilter.addEventListener("change", applyFilters);

clearBtn.addEventListener("click", () => {
  searchInput.value = "";
  yearFilter.value = "";
  journalFilter.value = "";
  keywordFilter.value = "";
  applyFilters();
});