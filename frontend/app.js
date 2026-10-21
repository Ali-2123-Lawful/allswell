// Allswell dashboard client. Polls /api/state and renders the calm-or-alert view.
// It re-renders only when the day's state actually changes, so the 8-second poll
// never flickers, and clicks get instant feedback before the server answers.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const DAY = 24 * 60;
  const ROOM_ORDER = ["kitchen", "living_room", "front_door", "bedroom"];
  let lastSig = null;
  let lastHeadline = null;

  const pretty = (zone) => zone.replace(/_/g, " ");
  const pct = (minute) => (Math.max(0, Math.min(DAY, minute)) / DAY) * 100 + "%";
  // Event times are local ISO strings ("2026-10-22T03:04:00"); read the clock directly.
  const minuteOf = (iso) => Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16));

  function clock(minute) {
    const h = Math.floor(minute / 60) % 24;
    const m = String(minute % 60).padStart(2, "0");
    return (h % 12 || 12) + ":" + m + " " + (h < 12 ? "AM" : "PM");
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function describe(e) {
    const zone = pretty(e.zone);
    const map = {
      doorbell: "Doorbell rang at the " + zone,
      person: "Someone at the " + zone,
      motion: "Movement in the " + zone,
      delivery: "Delivery at the " + zone,
    };
    return map[e.type] || e.type + " · " + zone;
  }

  // Why an event breaks the rhythm, or null if it doesn't: it fell in the quiet
  // hours, or it is a delivery the engine flagged as not picked up.
  function flagReason(e, s) {
    const m = minuteOf(e.at);
    if (m >= s.baseline.quiet_start_minute && m < s.baseline.quiet_end_minute) return "quiet hours";
    if (e.type === "delivery" && s.anomalies.some((a) => a.code === "UNRETRIEVED_DELIVERY")) {
      return "not picked up";
    }
    return null;
  }

  // ---------------------------------------------------------------- hero
  function renderHero(s) {
    const card = $("statusCard");
    const sev = s.is_all_well ? "ok" : s.digest.status || "warn";
    card.className = "status" + (s.is_all_well ? "" : " " + sev);
    if (lastHeadline !== null && lastHeadline !== s.digest.headline) {
      card.classList.remove("changed");
      void card.offsetWidth; // restart the entrance animation
      card.classList.add("changed");
    }
    lastHeadline = s.digest.headline;

    $("statusIcon").textContent = s.is_all_well ? "✓" : "!";
    $("statusEyebrow").textContent = s.is_all_well ? "Today · all's well" : "Today · needs a look";
    $("statusHeadline").textContent = s.digest.headline;
    $("statusMessage").textContent = s.digest.message;
    $("digestSrc").textContent =
      s.digest.source === "bedrock" ? "written by Amazon Bedrock" : "auto-summary";

    const live = $("live");
    live.className = "live " + (s.is_all_well ? "ok" : "alert");
    live.textContent = s.is_all_well ? "all's well" : "attention";

    // The check-in button shows only when something is off.
    $("checkinBtn").hidden = s.is_all_well;
    const note = $("checkedNote");
    note.hidden = !s.checked_in_at;
    if (s.checked_in_at) {
      const t = new Date(s.checked_in_at);
      note.textContent =
        "You reached out at " + t.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) + ".";
    }
  }

  // ---------------------------------------------------------------- alerts
  function renderAlerts(s) {
    const alerts = $("alerts");
    alerts.innerHTML = "";
    $("alertsSection").hidden = !s.anomalies.length;
    s.anomalies.forEach((a) => {
      const crit = a.severity === "critical";
      const div = el("div", "alert" + (crit ? " critical" : ""));
      const head = el("div", "a-head");
      head.append(el("span", "pill " + (crit ? "critical" : "warn"), a.severity), el("b", "", a.title));
      div.append(head, el("p", "", a.detail));
      alerts.appendChild(div);
    });
  }

  // ---------------------------------------------------------------- rhythm chart
  function renderRhythm(s) {
    const root = $("rhythm");
    const b = s.baseline;
    const rank = (z) => (ROOM_ORDER.includes(z) ? ROOM_ORDER.indexOf(z) : ROOM_ORDER.length);
    const zones = [...new Set([...Object.keys(b.profiles), ...s.timeline.map((e) => e.zone)])].sort(
      (x, y) => rank(x) - rank(y)
    );
    const missing = new Set(
      s.anomalies.filter((a) => a.code === "MISSING_MORNING_ROUTINE").map((a) => a.zone)
    );
    root.innerHTML = "";

    zones.forEach((zone) => {
      const profile = b.profiles[zone];
      const row = el("div", "r-row" + (missing.has(zone) ? " missing" : ""));
      const label = el("div", "r-label", pretty(zone));
      if (missing.has(zone)) label.append(el("small", "", "no activity yet"));
      else if (!profile) label.append(el("small", "muted", "not usually active"));

      const track = el("div", "r-track");
      const quiet = el("div", "r-quiet");
      quiet.style.left = pct(b.quiet_start_minute);
      quiet.style.width = pct(b.quiet_end_minute - b.quiet_start_minute);
      track.append(quiet);

      if (profile) {
        // A zone seen at one moment each day (e.g. the midday door) still gets a visible band.
        let start = profile.first_minute;
        let end = profile.last_minute;
        if (end - start < 30) {
          start -= 15;
          end += 15;
        }
        const band = el("div", "r-band");
        band.style.left = pct(start);
        band.style.width = pct(end - start);
        band.title = "Usually " + clock(profile.first_minute) + "–" + clock(profile.last_minute);
        track.append(band);
      }

      s.timeline
        .filter((e) => e.zone === zone)
        .forEach((e) => {
          const m = minuteOf(e.at);
          const reason = flagReason(e, s);
          const tip = e.time_label + " · " + describe(e) + (reason ? " · " + reason : "");
          const mark = el("button", "r-mark" + (reason ? " flag" : ""));
          mark.type = "button";
          mark.style.left = pct(m);
          mark.dataset.tip = tip;
          mark.setAttribute("aria-label", tip);
          if (m < 150) mark.classList.add("edge-l");
          if (m > DAY - 150) mark.classList.add("edge-r");
          mark.append(el("i"));
          track.append(mark);
        });

      row.append(label, track);
      root.append(row);
    });

    // Hour axis: majors every 6h, minors every 3h (hidden on phones).
    const axis = el("div", "r-axis");
    const ticks = el("div", "r-ticks");
    for (let h = 0; h <= 24; h += 3) {
      const t = el("span", h % 6 ? "minor" : "", clock((h % 24) * 60).replace(":00", ""));
      t.style.left = pct(h * 60);
      ticks.append(t);
    }
    axis.append(el("div"), ticks);
    root.append(axis);

    // "Now" marker. The demo evaluates the day as of early afternoon.
    const overlay = el("div", "r-overlay");
    const now = el("div", "r-now");
    now.style.left = pct(s.now_minute);
    now.append(el("span", "", "Now · " + clock(s.now_minute)));
    overlay.append(now);
    root.append(overlay);
  }

  // ---------------------------------------------------------------- timeline
  function renderTimeline(s) {
    const tl = $("timeline");
    tl.innerHTML = "";
    if (!s.timeline.length) {
      tl.append(el("li", "empty", "No activity recorded today."));
      return;
    }
    s.timeline.forEach((e) => {
      const reason = flagReason(e, s);
      const li = el("li", reason ? "off" : "");
      li.append(el("span", "t", e.time_label), el("span", "e", describe(e)));
      if (reason) li.append(el("span", "tag", reason));
      tl.appendChild(li);
    });
  }

  // ---------------------------------------------------------------- sidebar
  function renderSide(s) {
    $("baselineNote").textContent =
      "Learned from " + s.baseline.days_observed + " days of activity in the " +
      s.baseline.zones.map(pretty).join(", ") + ". Today is compared against that.";

    const sc = $("scenarios");
    if (!sc.children.length) {
      Object.entries(s.scenarios).forEach(([key, label]) => {
        const sev = (label.match(/\((critical|warn)\)$/) || [])[1] || "calm";
        const b = el("button", "scn");
        b.type = "button";
        b.dataset.key = key;
        const text = el("span");
        text.append(el("b", "", label.replace(/\s*\((critical|warn)\)$/, "")), el("small", "", sev));
        b.append(el("i", "sev " + sev), text);
        b.addEventListener("click", () => switchScenario(key));
        sc.appendChild(b);
      });
    }
    setActive(s.scenario);
  }

  function setActive(key) {
    document.querySelectorAll(".scn").forEach((b) => {
      b.classList.toggle("active", b.dataset.key === key);
      b.setAttribute("aria-pressed", b.dataset.key === key ? "true" : "false");
    });
  }

  // ---------------------------------------------------------------- data flow
  function render(s) {
    renderHero(s);
    renderAlerts(s);
    renderRhythm(s);
    renderTimeline(s);
    renderSide(s);
  }

  async function refresh() {
    try {
      const r = await fetch("/api/state");
      if (!r.ok) throw new Error("state " + r.status);
      const s = await r.json();
      $("offline").hidden = true;
      const sig = JSON.stringify({ ...s, generated_at: null });
      if (sig !== lastSig) {
        lastSig = sig;
        render(s);
      }
    } catch (e) {
      $("offline").hidden = false;
      $("live").textContent = "offline";
    }
  }

  async function switchScenario(key) {
    setActive(key); // instant feedback; the server confirms on refresh
    const main = $("main");
    main.classList.add("busy");
    try {
      await fetch("/api/scenario/" + key, { method: "POST" });
      await refresh();
    } finally {
      main.classList.remove("busy");
    }
  }

  $("checkinBtn").addEventListener("click", async () => {
    const btn = $("checkinBtn");
    btn.disabled = true;
    btn.textContent = "Checking in…";
    try {
      await fetch("/api/check-in", { method: "POST" });
      await refresh();
    } finally {
      btn.disabled = false;
      btn.textContent = "Check in on Mum";
    }
  });

  refresh();
  setInterval(refresh, 8000);
})();
