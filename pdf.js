let publications = [];
let filtered = [];

const resultsList = document.getElementById("results-list");
const searchInput = document.getElementById("search-input");
const yearFilter = document.getElementById("year-filter");
const languageFilter = document.getElementById("language-filter");
const keywordFilter = document.getElementById("keyword-filter");
const subjectFilter = document.getElementById("subject-filter");
const clearBtn = document.getElementById("clear-filters");
const resultsCount = document.getElementById("results-count");
const paginationContainer = document.getElementById("pagination");

const RESULTS_PER_PAGE = 12;
let currentPage = 1;


// --------------------------------------------------
// FETCH
// --------------------------------------------------

fetch("pdf.json")
  .then(res => res.json())
  .then(data => {
    publications = (data || []).map(p => ({
      ...p,
      topics: Array.isArray(p.topics) ? p.topics : [],
      keywords: Array.isArray(p.keywords) ? p.keywords : [],
      languages: Array.isArray(p.languages) ? p.languages : [],
      translations: Array.isArray(p.translations) ? p.translations : []
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
    pub.series,
    pub.description,
    pub.type,
    ...pub.topics,
    ...pub.keywords,
    pub.pdf_metadata?.pdf_subject,
    pub.pdf_metadata?.pdf_keywords
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

  const languages = [...new Set(publications.flatMap(p => p.languages))];

  const subjects = [...new Set(
    publications.map(p => p.pdf_metadata?.pdf_subject).filter(Boolean)
  )].sort();

  years.forEach(year => {
    yearFilter.appendChild(new Option(year, year));
  });

  languages.forEach(lang => {
    languageFilter.appendChild(new Option(lang.toUpperCase(), lang));
  });

  subjects.forEach(subject => {
    subjectFilter.appendChild(new Option(subject, subject));
  });
}


// --------------------------------------------------
// FILTERING
// --------------------------------------------------

function applyFilters() {

  const search = searchInput.value.toLowerCase().trim();
  const year = yearFilter.value;
  const lang = languageFilter.value;
  const keywordQuery = keywordFilter.value.toLowerCase().trim();
  const subject = subjectFilter.value;

  filtered = publications.filter(pub => {

    const index = buildSearchIndex(pub);

    const matchesSearch =
      !search ||
      search.split(" ").every(token =>
        index.includes(token)
      );

    const matchesYear =
      !year || String(pub.year) === year;

    const matchesLang =
      !lang || pub.languages.includes(lang);

    const matchesKeyword =
      !keywordQuery ||
      pub.keywords.some(k =>
        k.toLowerCase().includes(keywordQuery)
      );

    const matchesSubject =
      !subject || pub.pdf_metadata?.pdf_subject === subject;

    return (
      matchesSearch &&
      matchesYear &&
      matchesLang &&
      matchesKeyword &&
      matchesSubject
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
      : `Showing ${startNum}–${endNum} of ${total} publication${total !== 1 ? "s" : ""}`;

  pageResults.forEach(pub => {

    const li = document.createElement("li");
    li.className = "result-item";

    const primaryUrl = pub.translations[0]?.url;

    const titleHTML = primaryUrl
      ? `<a href="${primaryUrl}" target="_blank" rel="noopener">${pub.title}</a>`
      : pub.title;

    li.innerHTML = `
      <h3>${titleHTML}</h3>

      <p>
        ${pub.series || ""} 
        ${pub.year ? "• " + pub.year : ""}
        ${pub.type ? " • " + pub.type : ""}
      </p>

      ${pub.description ? `<p>${pub.description}</p>` : ""}

      <div>
        ${pub.topics.map(t =>
          `<span class="badge">${t}</span>`
        ).join("")}
      </div>

      <div>
        ${pub.languages.map(l =>
          `<span class="badge">${l.toUpperCase()}</span>`
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
languageFilter.addEventListener("change", applyFilters);
subjectFilter.addEventListener("change", applyFilters);

clearBtn.addEventListener("click", () => {
  searchInput.value = "";
  yearFilter.value = "";
  languageFilter.value = "";
  keywordFilter.value = "";
  subjectFilter.value = "";
  applyFilters();
});