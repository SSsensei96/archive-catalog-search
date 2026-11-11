const query = document.getElementById("query");
const mode = document.getElementById("mode");
const results = document.getElementById("results");
const status = document.getElementById("status");
let records = [];
let source = "fictional sample";

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
  const parts = [
    "Fond " + field(row, "fund_number", "fund_no", "fund"),
    "Opis " + field(row, "opis_number", "inventory_number", "inventory_no", "inventory"),
    "Delo " + field(row, "delo_number", "file_number", "file_no", "number")
  ].filter(Boolean);
  meta.textContent = parts.join(" · ") || "Catalogue record";
  const title = document.createElement("h3");
  title.textContent = field(row, "delo_title", "title", "file_title", "name", "opis_title") || "Untitled record";
  const details = document.createElement("p");
  details.textContent = [field(row, "fund_title"), field(row, "opis_title"), field(row, "description", "text", "notes")].filter(Boolean).join(" · ");
  const date = document.createElement("p");
  date.className = "meta";
  date.textContent = [field(row, "date_start", "date", "dates", "year"), field(row, "date_end")].filter(Boolean).join(" – ");
  article.append(meta, title, details, date);
  return article;
}

function search() {
  const terms = query.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  const matches = records.filter(row => {
    if (!terms.length) return true;
    const text = searchableText(row);
    return mode.value === "any" ? terms.some(term => text.includes(term)) : terms.every(term => text.includes(term));
  });
  results.replaceChildren();
  for (const row of matches.slice(0, 100)) results.append(makeResult(row));
  if (!matches.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No matches. Try another term or switch to Any term.";
    results.append(empty);
  }
  status.textContent = matches.length + " match" + (matches.length === 1 ? "" : "es") + " in " + records.length + " records (" + source + ")." + (matches.length > 100 ? " Showing the first 100." : "");
}

async function loadSample() {
  try {
    const response = await fetch("./sample_index.jsonl");
    if (!response.ok) throw new Error("Could not load the sample index.");
    records = parseJsonl(await response.text());
    source = "fictional sample";
    search();
  } catch (error) {
    status.textContent = error.message;
  }
}

document.getElementById("search").addEventListener("click", search);
query.addEventListener("keydown", event => { if (event.key === "Enter") search(); });
mode.addEventListener("change", search);
document.getElementById("sample").addEventListener("click", loadSample);
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

loadSample();
