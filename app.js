let publications = []
let filtered = []

const resultsList = document.getElementById("results-list")
const searchInput = document.getElementById("search-input")
const yearFilter = document.getElementById("year-filter")
const languageFilter = document.getElementById("language-filter")
const resultsCount = document.getElementById("results-count")

// Fetch data
fetch("publications_archive.json")
  .then(res => res.json())
  .then(data => {
    publications = data
    filtered = data

    populateFilters()
    render()
  })

// Populate filter dropdowns
function populateFilters() {

  const years = [...new Set(publications.map(p => p.year).filter(Boolean))].sort((a,b)=>b-a)
  const languages = [...new Set(publications.flatMap(p => p.languages))]

  years.forEach(year => {
    const opt = document.createElement("option")
    opt.value = year
    opt.textContent = year
    yearFilter.appendChild(opt)
  })

  languages.forEach(lang => {
    const opt = document.createElement("option")
    opt.value = lang
    opt.textContent = lang.toUpperCase()
    languageFilter.appendChild(opt)
  })
}

// Filtering logic
function applyFilters() {

  const search = searchInput.value.toLowerCase()
  const year = yearFilter.value
  const lang = languageFilter.value

  filtered = publications.filter(p => {

    const matchesSearch =
      !search ||
      p.title.toLowerCase().includes(search) ||
      p.series.toLowerCase().includes(search)

    const matchesYear =
      !year || String(p.year) === year

    const matchesLang =
      !lang || p.languages.includes(lang)

    return matchesSearch && matchesYear && matchesLang
  })

  render()
}

// Render results
function render() {

  resultsList.innerHTML = ""

  resultsCount.textContent = `${filtered.length} publications found`

  filtered.forEach(pub => {

    const li = document.createElement("li")
    li.className = "result-item"

    li.innerHTML = `
      <h3>
        <a href="${pub.translations[0].url}" target="_blank" rel="noopener">
          ${pub.title}
        </a>
      </h3>
      <p>${pub.series} • ${pub.year}</p>
      <div>
        ${pub.languages.map(l => `<span class="badge">${l.toUpperCase()}</span>`).join("")}
      </div>
    `

    resultsList.appendChild(li)
  })
}

// Event listeners
searchInput.addEventListener("input", applyFilters)
yearFilter.addEventListener("change", applyFilters)
languageFilter.addEventListener("change", applyFilters)