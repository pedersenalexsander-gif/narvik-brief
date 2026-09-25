const KEY = "alexProductionProfilesV1";
let profiles = load();
let selectedPeriod = "all";
const $ = (s) => document.querySelector(s);
const dialog = $("#profileDialog");
const DEFAULT_PROFILES = [
  {
    "id": "seed-1",
    "name": "Auto-Pluss AS - Sandeid/ MECA",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 90,
    "date": "2026-09-25",
    "notes": "",
    "createdAt": 1790337600000
  },
  {
    "id": "seed-2",
    "name": "Auto-Pluss AS Haugesund/ MECA",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 50,
    "date": "2026-09-24",
    "notes": "",
    "createdAt": 1790251200001
  },
  {
    "id": "seed-3",
    "name": "Sørlandets Bilverksted",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 43,
    "date": "2026-09-24",
    "notes": "",
    "createdAt": 1790251200002
  },
  {
    "id": "seed-4",
    "name": "Huset Kafé Raufoss",
    "category": "kafe",
    "producer": "Alex",
    "minutes": 12,
    "date": "2026-09-22",
    "notes": "",
    "createdAt": 1790078400003
  },
  {
    "id": "seed-5",
    "name": "Kaffeskvetten",
    "category": "kafe",
    "producer": "Alex",
    "minutes": 28,
    "date": "2026-09-22",
    "notes": "",
    "createdAt": 1790078400004
  },
  {
    "id": "seed-6",
    "name": "ProCare Helse BPA Narvik",
    "category": "Helse og velvære",
    "producer": "Alex",
    "minutes": 41,
    "date": "2026-09-22",
    "notes": "",
    "createdAt": 1790078400005
  },
  {
    "id": "seed-7",
    "name": "Gordon Hotel",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 75,
    "date": "2026-09-22",
    "notes": "",
    "createdAt": 1790078400006
  },
  {
    "id": "seed-8",
    "name": "Storfjord Auto",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 56,
    "date": "2026-09-21",
    "notes": "",
    "createdAt": 1789992000007
  },
  {
    "id": "seed-9",
    "name": "Gordon Hotel",
    "category": "Hotell",
    "producer": "Alex",
    "minutes": 60,
    "date": "2026-09-21",
    "notes": "",
    "createdAt": 1789992000008
  },
  {
    "id": "seed-10",
    "name": "ProCare Helse BPA Finnsnes",
    "category": "Helse og velvære",
    "producer": "Alex",
    "minutes": 60,
    "date": "2026-09-18",
    "notes": "",
    "createdAt": 1789732800009
  },
  {
    "id": "seed-11",
    "name": "Fengselet Gjestegård",
    "category": "Hotell",
    "producer": "Alex",
    "minutes": 59,
    "date": "2026-09-17",
    "notes": "",
    "createdAt": 1789646400010
  },
  {
    "id": "seed-12",
    "name": "Craftel",
    "category": "Elektriker",
    "producer": "Alex",
    "minutes": 127,
    "date": "2026-09-17",
    "notes": "",
    "createdAt": 1789646400011
  },
  {
    "id": "seed-13",
    "name": "Autosentrum AS / MECA",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 27,
    "date": "2026-09-16",
    "notes": "",
    "createdAt": 1789560000012
  },
  {
    "id": "seed-14",
    "name": "Ulstein Bil / MECA bilverksted",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 97,
    "date": "2026-09-16",
    "notes": "",
    "createdAt": 1789560000013
  },
  {
    "id": "seed-15",
    "name": "Florø Bilverksted AS",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 38,
    "date": "2026-09-14",
    "notes": "",
    "createdAt": 1789387200014
  },
  {
    "id": "seed-16",
    "name": "Økoråd Helgeland",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 35,
    "date": "2026-09-14",
    "notes": "",
    "createdAt": 1789387200015
  },
  {
    "id": "seed-17",
    "name": "AutoSwap AS - Bilverksted i Fyllingsdalen",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 90,
    "date": "2026-09-11",
    "notes": "",
    "createdAt": 1789128000016
  },
  {
    "id": "seed-18",
    "name": "Rabbenkroken Bil AS (Mekonomen)",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 30,
    "date": "2026-09-11",
    "notes": "",
    "createdAt": 1789128000017
  },
  {
    "id": "seed-19",
    "name": "Lakselv Motor",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 37,
    "date": "2026-09-11",
    "notes": "",
    "createdAt": 1789128000018
  },
  {
    "id": "seed-20",
    "name": "Trofors Bil og Landbruksverksted AS (Mekonomen)",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 11,
    "date": "2026-09-11",
    "notes": "",
    "createdAt": 1789128000019
  },
  {
    "id": "seed-21",
    "name": "Flissundet Motorservice AS",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 47,
    "date": "2026-09-11",
    "notes": "",
    "createdAt": 1789128000020
  },
  {
    "id": "seed-22",
    "name": "Lunner Auto AS (Mekonomen)",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 41,
    "date": "2026-09-11",
    "notes": "",
    "createdAt": 1789128000021
  },
  {
    "id": "seed-23",
    "name": "Kristiansand Bilverksted AS",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 52,
    "date": "2026-09-11",
    "notes": "",
    "createdAt": 1789128000022
  },
  {
    "id": "seed-24",
    "name": "Sandøy Byggservice AS",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 60,
    "date": "2026-09-10",
    "notes": "",
    "createdAt": 1789041600023
  },
  {
    "id": "seed-25",
    "name": "Vang Auto Hamar",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 60,
    "date": "2026-09-08",
    "notes": "",
    "createdAt": 1788868800024
  },
  {
    "id": "seed-26",
    "name": "Valdres Lastebilservice AS (MECA)",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 60,
    "date": "2026-09-08",
    "notes": "",
    "createdAt": 1788868800025
  },
  {
    "id": "seed-27",
    "name": "Thuen & Matre",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 50,
    "date": "2026-09-04",
    "notes": "",
    "createdAt": 1788523200026
  },
  {
    "id": "seed-28",
    "name": "Varmepumpe Bergen Vestrheim",
    "category": "varmepumpeforhandler",
    "producer": "Alex",
    "minutes": 28,
    "date": "2026-09-03",
    "notes": "",
    "createdAt": 1788436800027
  },
  {
    "id": "seed-29",
    "name": "Volden Tollefsen (Hauge i Dalane)",
    "category": "Rørlegger",
    "producer": "Alex",
    "minutes": 78,
    "date": "2026-09-03",
    "notes": "",
    "createdAt": 1788436800028
  },
  {
    "id": "seed-30",
    "name": "Servicehallen Dombås AS",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 67,
    "date": "2026-09-03",
    "notes": "",
    "createdAt": 1788436800029
  },
  {
    "id": "seed-31",
    "name": "S Holand Bilverksted",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 41,
    "date": "2026-09-03",
    "notes": "",
    "createdAt": 1788436800030
  },
  {
    "id": "seed-32",
    "name": "MECA PlanetHifi",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 71,
    "date": "2026-09-03",
    "notes": "",
    "createdAt": 1788436800031
  },
  {
    "id": "seed-33",
    "name": "Rotstigen AS",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 120,
    "date": "2026-09-02",
    "notes": "",
    "createdAt": 1788350400032
  },
  {
    "id": "seed-34",
    "name": "Mesterhus Innlandet AS avd. Hedmark",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 65,
    "date": "2026-09-02",
    "notes": "",
    "createdAt": 1788350400033
  },
  {
    "id": "seed-35",
    "name": "Greverud Grill & Indisk",
    "category": "Restaurant",
    "producer": "Alex",
    "minutes": 85,
    "date": "2026-09-02",
    "notes": "",
    "createdAt": 1788350400034
  },
  {
    "id": "seed-36",
    "name": "Sauda Bilverksted",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 31,
    "date": "2026-09-02",
    "notes": "",
    "createdAt": 1788350400035
  },
  {
    "id": "seed-37",
    "name": "Mesterhus Innlandet AS",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 73,
    "date": "2026-09-01",
    "notes": "",
    "createdAt": 1788264000036
  },
  {
    "id": "seed-38",
    "name": "Brobekk Grill & Pizza",
    "category": "Restaurant",
    "producer": "Alex",
    "minutes": 60,
    "date": "2026-09-01",
    "notes": "",
    "createdAt": 1788264000037
  },
  {
    "id": "seed-39",
    "name": "Volden Tollefsen (Egersund)",
    "category": "Rørlegger",
    "producer": "Alex",
    "minutes": 64,
    "date": "2026-08-31",
    "notes": "",
    "createdAt": 1788177600038
  },
  {
    "id": "seed-40",
    "name": "Skadesenteret Riko",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 68,
    "date": "2026-08-31",
    "notes": "",
    "createdAt": 1788177600039
  },
  {
    "id": "seed-41",
    "name": "Nærøy Bil AS",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 123,
    "date": "2026-08-31",
    "notes": "",
    "createdAt": 1788177600040
  },
  {
    "id": "seed-42",
    "name": "Jærprosjekt AS",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 114,
    "date": "2026-08-28",
    "notes": "",
    "createdAt": 1787918400041
  },
  {
    "id": "seed-43",
    "name": "Andreassen Brønnboring og Energiboring AS",
    "category": "boring",
    "producer": "Alex",
    "minutes": 67,
    "date": "2026-08-28",
    "notes": "",
    "createdAt": 1787918400042
  },
  {
    "id": "seed-44",
    "name": "Stoa Autorep MECA bilverksted Arendal",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 51,
    "date": "2026-08-26",
    "notes": "",
    "createdAt": 1787745600043
  },
  {
    "id": "seed-45",
    "name": "Steam Tours Tromsø",
    "category": "aktiviteter",
    "producer": "Alex",
    "minutes": 39,
    "date": "2026-08-26",
    "notes": "",
    "createdAt": 1787745600044
  },
  {
    "id": "seed-46",
    "name": "Steam Sauna Tromsø",
    "category": "badstu",
    "producer": "Alex",
    "minutes": 42,
    "date": "2026-08-25",
    "notes": "",
    "createdAt": 1787659200045
  },
  {
    "id": "seed-47",
    "name": "Skadesenteret Riko",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 60,
    "date": "2026-08-25",
    "notes": "",
    "createdAt": 1787659200046
  },
  {
    "id": "seed-48",
    "name": "Forma Studio AS",
    "category": "interiør selger",
    "producer": "Alex",
    "minutes": 120,
    "date": "2026-08-25",
    "notes": "",
    "createdAt": 1787659200047
  },
  {
    "id": "seed-49",
    "name": "Johs. E. Øvsthus AS",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 180,
    "date": "2026-08-24",
    "notes": "",
    "createdAt": 1787572800048
  },
  {
    "id": "seed-50",
    "name": "Steam Pier",
    "category": "Hotell",
    "producer": "Alex",
    "minutes": 32,
    "date": "2026-08-24",
    "notes": "",
    "createdAt": 1787572800049
  },
  {
    "id": "seed-51",
    "name": "Revisorgruppen Fjordane",
    "category": "Regnskap og revisjon",
    "producer": "Alex",
    "minutes": 11,
    "date": "2026-08-20",
    "notes": "",
    "createdAt": 1787227200050
  },
  {
    "id": "seed-52",
    "name": "Byggmesterfirma Jørgensen & Kemkers AS",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 100,
    "date": "2026-08-20",
    "notes": "",
    "createdAt": 1787227200051
  },
  {
    "id": "seed-53",
    "name": "Sevland Autoteknikk",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 54,
    "date": "2026-08-20",
    "notes": "",
    "createdAt": 1787227200052
  },
  {
    "id": "seed-54",
    "name": "Digital Revisor AS",
    "category": "Regnskap og revisjon",
    "producer": "Alex",
    "minutes": 102,
    "date": "2026-08-19",
    "notes": "",
    "createdAt": 1787140800053
  },
  {
    "id": "seed-55",
    "name": "Digital Revisor AS - Bergen",
    "category": "Regnskap og revisjon",
    "producer": "Alex",
    "minutes": 98,
    "date": "2026-08-19",
    "notes": "",
    "createdAt": 1787140800054
  },
  {
    "id": "seed-56",
    "name": "Byggefirma Nilsen & Andersen AS",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 101,
    "date": "2026-08-18",
    "notes": "",
    "createdAt": 1787054400055
  },
  {
    "id": "seed-57",
    "name": "Narvik Car Rental",
    "category": "bil utleie",
    "producer": "Alex",
    "minutes": 46,
    "date": "2026-08-18",
    "notes": "",
    "createdAt": 1787054400056
  },
  {
    "id": "seed-58",
    "name": "Kafé & restaurant Spesial Bergen",
    "category": "kafe",
    "producer": "Alex",
    "minutes": 105,
    "date": "2026-08-17",
    "notes": "",
    "createdAt": 1786968000057
  },
  {
    "id": "seed-59",
    "name": "Byggmester Liljebakk",
    "category": "Håndverker",
    "producer": "Alex",
    "minutes": 82,
    "date": "2026-08-17",
    "notes": "",
    "createdAt": 1786968000058
  },
  {
    "id": "seed-60",
    "name": "Bilstellet AS",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 94,
    "date": "2026-08-14",
    "notes": "",
    "createdAt": 1786708800059
  },
  {
    "id": "seed-61",
    "name": "Ledge Construction LLC",
    "category": "anleggsarbeider",
    "producer": "Alex",
    "minutes": 92,
    "date": "2026-08-14",
    "notes": "",
    "createdAt": 1786708800060
  },
  {
    "id": "seed-62",
    "name": "Elektriker på Hjul Hovedkontor",
    "category": "Elektriker",
    "producer": "Alex",
    "minutes": 88,
    "date": "2026-08-12",
    "notes": "",
    "createdAt": 1786536000061
  },
  {
    "id": "seed-63",
    "name": "Stormglass AS",
    "category": "glassmontør",
    "producer": "Alex",
    "minutes": 125,
    "date": "2026-08-12",
    "notes": "",
    "createdAt": 1786536000062
  },
  {
    "id": "seed-64",
    "name": "Superdekk Bømlo Bil",
    "category": "Bilverksted",
    "producer": "Alex",
    "minutes": 114,
    "date": "2026-08-11",
    "notes": "",
    "createdAt": 1786449600063
  }
];
function load() {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.length) return parsed;
    }
    localStorage.setItem(KEY, JSON.stringify(DEFAULT_PROFILES));
    return DEFAULT_PROFILES.map((p) => ({ ...p }));
  } catch {
    return DEFAULT_PROFILES.map((p) => ({ ...p }));
  }
}
function save() {
  localStorage.setItem(KEY, JSON.stringify(profiles));
  render();
}
function esc(s = "") {
  return String(s).replace(
    /[&<>'"]/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[
        c
      ],
  );
}
function mins(p) {
  return Number(p.minutes) || 0;
}
function fmtTime(m) {
  m = Number(m) || 0;
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60),
    r = m % 60;
  return r ? `${h} t ${r} min` : `${h} t`;
}
function fmtDate(d) {
  return new Intl.DateTimeFormat("nb-NO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(d + "T12:00:00"));
}
function countBy(field, data = profiles) {
  return data.reduce((a, p) => {
    const k = p[field] || "Ukjent";
    a[k] = (a[k] || 0) + 1;
    return a;
  }, {});
}
function topOf(obj) {
  return Object.entries(obj).sort((a, b) => b[1] - a[1])[0];
}
function within(days, p) {
  const t = new Date(p.date + "T23:59:59").getTime();
  return t >= Date.now() - days * 864e5;
}
function toast(t) {
  const x = $("#toast");
  x.textContent = t;
  x.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => x.classList.remove("show"), 2200);
}
function openForm(p = null) {
  $("#profileForm").reset();
  $("#editId").value = p?.id || "";
  $("#formTitle").textContent = p
    ? "Rediger registrering"
    : "Registrer produsert bedrift";
  $("#productionDate").value = p?.date || new Date().toISOString().slice(0, 10);
  if (p) {
    $("#companyName").value = p.name;
    $("#companyCategory").value = p.category;
    $("#producer").value = p.producer;
    $("#timeHours").value = Math.floor(p.minutes / 60) || "";
    $("#timeMinutes").value = p.minutes % 60;
    $("#notes").value = p.notes || "";
  }
  dialog.showModal();
}
function closeForm() {
  dialog.close();
}
function renderStats(data) {
  const total = data.length,
    tm = data.reduce((s, p) => s + mins(p), 0),
    avg = total ? Math.round(tm / total) : 0;
  $("#totalProfiles").textContent = total;
  $("#profilesThisMonth").textContent = periodLabel();
  $("#avgTime").textContent = fmtTime(avg);
  const sorted = [...data].sort((a, b) => mins(a) - mins(b));
  $("#fastestTime").textContent = sorted.length
    ? `Raskest: ${fmtTime(mins(sorted[0]))}`
    : "Ingen data ennå";
  $("#totalTime").textContent =
    tm < 60 ? `${tm} min` : `${(tm / 60).toFixed(tm % 60 ? 1 : 0)} t`;
  $("#estimatedDays").textContent =
    `${(tm / 480).toFixed(1)} arbeidsdager á 8 t`;
  const tc = topOf(countBy("category", data));
  $("#topCategory").textContent = tc?.[0] || "—";
  $("#topCategoryCount").textContent = tc
    ? `${tc[1]} profiler`
    : "Ingen data ennå";
  $("#fastestProfile").textContent = sorted.length
    ? `${sorted[0].name} · ${fmtTime(sorted[0].minutes)}`
    : "—";
  $("#slowestProfile").textContent = sorted.length
    ? `${sorted.at(-1).name} · ${fmtTime(sorted.at(-1).minutes)}`
    : "—";
  $("#last7Days").textContent = data.length;
  $("#last30Days").textContent = Object.keys(countBy("category", data)).length;
}
function renderRanks(id, obj) {
  const el = $(id),
    arr = Object.entries(obj)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);
  if (!arr.length) {
    el.className = "rank-list empty-state";
    el.textContent = "Ingen registreringer ennå.";
    return;
  }
  el.className = "rank-list";
  const max = arr[0][1];
  el.innerHTML = arr
    .map(
      ([n, c]) =>
        `<div class="rank-row"><span class="rank-name">${esc(n)}</span><span class="rank-count">${c}</span><div class="rank-track"><div class="rank-fill" style="width:${(c / max) * 100}%"></div></div></div>`,
    )
    .join("");
}
function monthKey(d) {
  const x = new Date(d + "T12:00:00");
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}`;
}
function monthKeyFromDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}
function offsetMonth(key, offset) {
  const [year, month] = key.split("-").map(Number);
  return monthKeyFromDate(new Date(year, month - 1 + offset, 1));
}
function currentMonthKey() {
  return monthKeyFromDate(new Date());
}
function selectedMonthKey() {
  if (selectedPeriod === "current") return currentMonthKey();
  if (selectedPeriod === "previous") return offsetMonth(currentMonthKey(), -1);
  if (selectedPeriod.startsWith("month:")) return selectedPeriod.slice(6);
  return null;
}
function periodLabel(value = selectedPeriod) {
  if (value === "all") return "Alle måneder";
  if (value === "current") return "Denne måneden";
  if (value === "previous") return "Forrige måned";
  const key = value.startsWith("month:") ? value.slice(6) : value;
  const [year, month] = key.split("-").map(Number);
  const label = new Intl.DateTimeFormat("nb-NO", {
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, 1));
  return label.charAt(0).toUpperCase() + label.slice(1);
}
function periodData() {
  const key = selectedMonthKey();
  return key ? profiles.filter((p) => monthKey(p.date) === key) : [...profiles];
}
function updatePeriodFilter() {
  const select = $("#periodFilter");
  const existing = selectedPeriod;
  const keys = [...new Set(profiles.map((p) => monthKey(p.date)))]
    .filter(Boolean)
    .sort()
    .reverse();
  select.innerHTML =
    '<option value="current">Denne måneden</option>' +
    '<option value="previous">Forrige måned</option>' +
    '<option value="all">Alle måneder</option>' +
    keys
      .map(
        (key) =>
          `<option value="month:${key}">${esc(periodLabel(`month:${key}`))}</option>`,
      )
      .join("");
  select.value = [...select.options].some((option) => option.value === existing)
    ? existing
    : "all";
  selectedPeriod = select.value;
}
function renderPeriodSummary(data) {
  const label = periodLabel();
  $("#selectedPeriodLabel").textContent = label;
  $("#selectedPeriodCount").textContent = data.length;
  $("#historyTitle").textContent =
    selectedPeriod === "all"
      ? "Alle produserte profiler"
      : `Profiler – ${label.toLowerCase()}`;
  const change = $("#selectedPeriodChange");
  change.className = "";
  const key = selectedMonthKey();
  if (!key) {
    change.textContent = "Velg en måned for sammenligning";
    return;
  }
  const previousCount = profiles.filter(
    (p) => monthKey(p.date) === offsetMonth(key, -1),
  ).length;
  if (!previousCount) {
    change.textContent = data.length
      ? `${data.length} mot 0 måneden før`
      : "Ingen data måneden før";
    return;
  }
  const percent = Math.round(
    ((data.length - previousCount) / previousCount) * 100,
  );
  change.textContent = `${percent >= 0 ? "+" : ""}${percent}% (${previousCount} måneden før)`;
  change.className = percent >= 0 ? "positive" : "negative";
}
function renderChart() {
  const months = [];
  const now = new Date();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push({
      key: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
      label: new Intl.DateTimeFormat("nb-NO", { month: "short" }).format(d),
    });
  }
  const counts = months.map(
      (m) => profiles.filter((p) => monthKey(p.date) === m.key).length,
    ),
    max = Math.max(...counts, 1);
  $("#monthlyChart").innerHTML = months
    .map(
      (m, i) =>
        `<div class="bar-col"><span class="bar-value">${counts[i]}</span><div class="bar" style="height:${Math.max(counts[i] ? 8 : 2, (counts[i] / max) * 160)}px"></div><span class="bar-label">${m.label}</span></div>`,
    )
    .join("");
  const prev = counts.at(-2) || 0,
    cur = counts.at(-1) || 0;
  $("#monthlyTrend").textContent = prev
    ? `${cur >= prev ? "+" : ""}${Math.round(((cur - prev) / prev) * 100)}% vs. forrige mnd`
    : `${cur} denne måneden`;
}
function updateFilters() {
  const cat = $("#categoryFilter"),
    prod = $("#producerFilter"),
    cv = cat.value,
    pv = prod.value;
  cat.innerHTML =
    '<option value="">Alle kategorier</option>' +
    Object.keys(countBy("category"))
      .sort()
      .map((x) => `<option>${esc(x)}</option>`)
      .join("");
  prod.innerHTML =
    '<option value="">Alle produsenter</option>' +
    Object.keys(countBy("producer"))
      .sort()
      .map((x) => `<option>${esc(x)}</option>`)
      .join("");
  cat.value = cv;
  prod.value = pv;
}
function renderTable(periodProfiles = periodData()) {
  const q = $("#searchInput").value.trim().toLowerCase(),
    cat = $("#categoryFilter").value,
    prod = $("#producerFilter").value;
  const data = [...periodProfiles]
    .filter(
      (p) =>
        (!q ||
          `${p.name} ${p.category} ${p.producer}`.toLowerCase().includes(q)) &&
        (!cat || p.category === cat) &&
        (!prod || p.producer === prod),
    )
    .sort((a, b) => b.date.localeCompare(a.date) || b.createdAt - a.createdAt);
  $("#profileTable").innerHTML = data.length
    ? data
        .map(
          (p) =>
            `<tr><td>${esc(p.name)}</td><td><span class="pill">${esc(p.category)}</span></td><td>${esc(p.producer)}</td><td>${fmtTime(p.minutes)}</td><td>${fmtDate(p.date)}</td><td><div class="row-actions"><button class="row-btn edit" data-id="${p.id}" title="Rediger">✎</button><button class="row-btn delete" data-id="${p.id}" title="Slett">×</button></div></td></tr>`,
        )
        .join("")
    : '<tr><td colspan="6" class="table-empty">Ingen profiler matcher filteret.</td></tr>';
}
function render() {
  updatePeriodFilter();
  const data = periodData();
  renderPeriodSummary(data);
  renderStats(data);
  renderRanks("#categoryList", countBy("category", data));
  renderRanks("#producerList", countBy("producer", data));
  renderChart();
  updateFilters();
  renderTable(data);
}
$("#openFormBtn").onclick = () => openForm();
$("#periodFilter").addEventListener("change", (event) => {
  selectedPeriod = event.target.value;
  render();
});
$("#closeDialogBtn").onclick = closeForm;
$("#cancelBtn").onclick = closeForm;
$("#profileForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const h = Number($("#timeHours").value || 0),
    m = Number($("#timeMinutes").value || 0),
    total = h * 60 + m;
  if (total <= 0) return toast("Legg inn tidsbruk.");
  const id = $("#editId").value;
  const item = {
    id: id || crypto.randomUUID(),
    name: $("#companyName").value.trim(),
    category: $("#companyCategory").value.trim(),
    producer: $("#producer").value.trim(),
    minutes: total,
    date: $("#productionDate").value,
    notes: $("#notes").value.trim(),
    createdAt: id
      ? profiles.find((p) => p.id === id)?.createdAt || Date.now()
      : Date.now(),
  };
  if (id) profiles = profiles.map((p) => (p.id === id ? item : p));
  else profiles.push(item);
  save();
  closeForm();
  toast(id ? "Registrering oppdatert." : "Profil registrert.");
});
$("#profileTable").addEventListener("click", (e) => {
  const id = e.target.dataset.id;
  if (!id) return;
  if (e.target.classList.contains("edit"))
    openForm(profiles.find((p) => p.id === id));
  if (
    e.target.classList.contains("delete") &&
    confirm("Slette denne registreringen?")
  ) {
    profiles = profiles.filter((p) => p.id !== id);
    save();
    toast("Registrering slettet.");
  }
});
["#searchInput", "#categoryFilter", "#producerFilter"].forEach((s) =>
  $(s).addEventListener("input", renderTable),
);
$("#exportBtn").onclick = () => {
  const blob = new Blob(
      [
        JSON.stringify(
          { exportedAt: new Date().toISOString(), profiles },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    ),
    a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `alex-brief-produksjon-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  toast("Data eksportert.");
};
$("#importInput").onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  try {
    const data = JSON.parse(await f.text()),
      arr = Array.isArray(data) ? data : data.profiles;
    if (!Array.isArray(arr)) throw Error();
    if (
      confirm(
        `Importere ${arr.length} registreringer? Dette erstatter dagens data.`,
      )
    ) {
      profiles = arr;
      save();
      toast("Data importert.");
    }
  } catch {
    toast("Kunne ikke lese filen.");
  }
  e.target.value = "";
};
dialog.addEventListener("click", (e) => {
  const r = dialog.getBoundingClientRect();
  if (
    e.clientX < r.left ||
    e.clientX > r.right ||
    e.clientY < r.top ||
    e.clientY > r.bottom
  )
    closeForm();
});
render();