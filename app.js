let publications = [];
let filtered = [];

const resultsList = document.getElementById("results-list");
const searchInput = document.getElementById("search-input");
const yearFilter = document.getElementById("year-filter");
const languageFilter = document.getElementById("language-filter");
const keywordFilter = document.getElementById("keyword-filter");
const subjectFilter = document.getElementById("subject-filter");
const resultsCount = document.getElementById("results-count");
const paginationContainer = document.getElementById("pagination");

const RESULTS_PER_PAGE = 12;
let currentPage = 1;


// --------------------------------------------------
// FETCH
// --------------------------------------------------

fetch("publications_archive.json")
  .then(res => res.json())
  .then(data => {
    publications = data || [];
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
    ...(pub.topics || []),
    ...(pub.keywords || []),
    pub.pdf_metadata?.pdf_subject,
    pub.pdf_metadata?.pdf_keywords
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}


// --------------------------------------------------
// FILTER POPULATION (NO KEYWORD DROPDOWN)
// --------------------------------------------------

function populateFilters() {

  const years = [...new Set(publications.map(p => p.year).filter(Boolean))]
    .sort((a,b)=>b-a);

  const languages = [...new Set(publications.flatMap(p => p.languages || []))];

  const subjects = [...new Set(
    publications.map(p => p.pdf_metadata?.pdf_subject).filter(Boolean)
  )].sort();

  years.forEach(year => {
    const opt = new Option(year, year);
    yearFilter.appendChild(opt);
  });

  languages.forEach(lang => {
    const opt = new Option(lang.toUpperCase(), lang);
    languageFilter.appendChild(opt);
  });

  subjects.forEach(subject => {
    const opt = new Option(subject, subject);
    subjectFilter.appendChild(opt);
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
      !search || index.includes(search);

    const matchesYear =
      !year || String(pub.year) === year;

    const matchesLang =
      !lang || (pub.languages || []).includes(lang);

    const matchesKeyword =
      !keywordQuery ||
      (pub.keywords || []).some(k =>
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

  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");
    btn.textContent = i;
    btn.className = i === currentPage ? "active-page" : "";
    btn.addEventListener("click", () => {
      currentPage = i;
      render();
    });
    paginationContainer.appendChild(btn);
  }
}


// --------------------------------------------------
// RENDER
// --------------------------------------------------

function render() {

  resultsList.innerHTML = "";

  const totalPages =
    Math.ceil(filtered.length / RESULTS_PER_PAGE);

  const start =
    (currentPage - 1) * RESULTS_PER_PAGE;

  const end =
    start + RESULTS_PER_PAGE;

  const pageResults =
    filtered.slice(start, end);

  resultsCount.textContent =
    `${filtered.length} publication${filtered.length !== 1 ? "s" : ""} found`;

  pageResults.forEach(pub => {

    const li = document.createElement("li");
    li.className = "result-item";

    const primaryUrl =
      pub.translations?.[0]?.url || "#";

    li.innerHTML = `
      <h3>
        <a href="${primaryUrl}" target="_blank" rel="noopener">
          ${pub.title}
        </a>
      </h3>

      <p>
        ${pub.series || ""} 
        ${pub.year ? "• " + pub.year : ""}
        ${pub.type ? " • " + pub.type : ""}
      </p>

      ${pub.description ? `<p>${pub.description}</p>` : ""}

      <div>
        ${(pub.topics || []).map(t =>
          `<span class="badge">${t}</span>`
        ).join("")}
      </div>

      <div>
        ${(pub.languages || []).map(l =>
          `<span class="badge">${l.toUpperCase()}</span>`
        ).join("")}
      </div>
    `;

    resultsList.appendChild(li);
  });

  renderPagination(totalPages);
}


// --------------------------------------------------
// EVENT LISTENERS
// --------------------------------------------------

searchInput.addEventListener("input", applyFilters);
yearFilter.addEventListener("change", applyFilters);
languageFilter.addEventListener("change", applyFilters);
keywordFilter.addEventListener("input", applyFilters);
subjectFilter.addEventListener("change", applyFilters);