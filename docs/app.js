const query = document.getElementById("query");
const mode = document.getElementById("mode");
const results = document.getElementById("results");
const status = document.getElementById("status");
const pageStatus = document.getElementById("pageStatus");
const previousButton = document.getElementById("previous");
const nextButton = document.getElementById("next");
let records = [];
let source = "archive snapshot";
let matches = [];
let page = 0;
const pageSize = 50;

function flattenArchive(fonds) {
  if (!Array.isArray(fonds)) throw new Error("Archive JSON must be a list of fonds.");
  const rows = [];
  for (const fund of fonds) {
    if (!fund || typeof fund !== "object") continue;
    const base = {
      fund_id: fund.id,
      fund_number: fund.number,
      fund_title: fund.title
    };
    rows.push({
      ...base,
      level: "Fond",
      title: fund.title,
      date_start: fund.date_start,
      date_end: fund.date_end
    });
    for (const opis of fund.opisi || []) {
      if (!opis || typeof opis !== "object") continue;
      rows.push({
        ...base,
        level: "Opis",
        opis_id: opis.id,
        opis_number: opis.number,
        opis_title: opis.title,
        title: opis.title,
        date_start: opis.date_start,
        date_end: opis.date_end
      });
    }
  }
  return rows;
}

function parseJsonl(text) {
  const rows = [];
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    if (!line.trim()) continue;
    try {
      const row = JSON.parse(line);
      if (row && typeof row === "object" && !Array.isArray(row)) rows.push(row);
    } catch (error) {
      throw new Error("Invalid JSON on line " + (index + 1) + ".");
    }
  }
  return rows;
}

function field(row, ...names) {
  for (const name of names) {
    if (row[name] !== undefined && row[name] !== null) return String(row[name]);
  }
  return "";
}

function searchableText(row) {
  return Object.values(row).map(value => typeof value === "string" || typeof value === "number" ? String(value) : "").join(" ").toLocaleLowerCase();
}

function makeResult(row) {
  const article = document.createElement("article");
  const meta = document.createElement("div");
  meta.className = "meta";
  const parts = [];
  const fundNumber = field(row, "fund_number", "fund_no", "fund");
  const opisNumber = field(row, "opis_number", "inventory_number", "inventory_no", "inventory");
  const deloNumber = field(row, "delo_number", "file_number", "file_no");
  if (fundNumber) parts.push("Fond " + fundNumber);
  if (opisNumber) parts.push("Opis " + opisNumber);
  if (deloNumber) parts.push("Delo " + deloNumber);
  meta.textContent = parts.join(" · ") || "Catalogue record";
  const title = document.createElement("h3");
  title.textContent = field(row, "delo_title", "title", "file_title", "name", "opis_title", "fund_title") || "Untitled record";
  const details = document.createElement("p");
  details.textContent = [row.level === "Opis" ? field(row, "fund_title") : "", field(row, "description", "text", "notes")].filter(Boolean).join(" · ");
  const date = document.createElement("p");
  date.className = "meta";
  date.textContent = [field(row, "date_start", "date", "dates", "year"), field(row, "date_end")].filter(Boolean).join(" – ");
  article.append(meta, title, details, date);
  return article;
}

function renderPage() {
  const pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
  results.replaceChildren();
  for (const row of matches.slice(page * pageSize, (page + 1) * pageSize)) results.append(makeResult(row));
  if (!matches.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No matches. Try another term or switch to Any term.";
    results.append(empty);
  }
  status.textContent = matches.length + " match" + (matches.length === 1 ? "" : "es") + " in " + records.length + " records (" + source + ").";
  pageStatus.textContent = "Page " + (page + 1) + " of " + pageCount;
  previousButton.disabled = page === 0;
  nextButton.disabled = page + 1 >= pageCount;
}

function search() {
  const terms = query.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  matches = records.filter(row => {
    if (!terms.length) return true;
    const text = searchableText(row);
    return mode.value === "any" ? terms.some(term => text.includes(term)) : terms.every(term => text.includes(term));
  });
  page = 0;
  renderPage();
}

async function loadArchive() {
  try {
    status.textContent = "Loading archive snapshot…";
    const response = await fetch("./archive_full.json");
    if (!response.ok) throw new Error("Could not load the archive snapshot.");
    records = flattenArchive(await response.json());
    source = "archive snapshot";
    search();
  } catch (error) {
    status.textContent = error.message;
  }
}

document.getElementById("search").addEventListener("click", search);
previousButton.addEventListener("click", () => { if (page > 0) { page -= 1; renderPage(); } });
nextButton.addEventListener("click", () => { if ((page + 1) * pageSize < matches.length) { page += 1; renderPage(); } });
query.addEventListener("keydown", event => { if (event.key === "Enter") search(); });
mode.addEventListener("change", search);
document.getElementById("sample").addEventListener("click", loadArchive);
document.getElementById("upload").addEventListener("change", async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    const parsed = parseJsonl(await file.text());
    if (!parsed.length) throw new Error("The file contains no JSONL records.");
    records = parsed;
    source = file.name;
    search();
  } catch (error) {
    status.textContent = error.message;
  }
});

loadArchive();
